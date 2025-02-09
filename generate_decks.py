import os
import yaml
import genanki
from anki_model import AnkiModelFactory
from sudachipy import tokenizer
from sudachipy import dictionary
import xml.etree.ElementTree as ET
import jaconv
import re
from typing import Tuple, List, Optional, Dict, Set
import itertools

class FuriganaGenerator:
    """
    Generates furigana (HTML ruby annotations) for Japanese words containing kanji.
    
    This class uses:
      - SudachiPy to tokenize Japanese text and retrieve readings for individual kanji.
      - A JMdict XML file to look up candidate readings for kanji words.
    
    It works by splitting the input word into segments (literal parts and kanji blocks),
    retrieving candidate readings for each kanji (including applying rendaku and iteration rules),
    and then aligning these candidates with a target reading string. If a direct match is found,
    the corresponding ruby HTML is generated; if not, a fallback algorithm generates all possible
    splits of the target reading and selects the best match based on a cost measure.
    
    Attributes:
      global_debug (bool): If True, debug messages are printed for all words.
      debug_words (Set[str]): If provided, debug messages are printed only for these words.
    """
    
    def __init__(self, jmdict_path: str = "JMdict_e.xml", 
                 global_debug: bool = False, debug_words: Optional[List[str]] = None) -> None:
        # Initialize the SudachiPy tokenizer with the default dictionary.
        self.tokenizer_obj = dictionary.Dictionary().create()
        # Set the splitting mode to 'C' (maximal segmentation).
        self.mode = tokenizer.Tokenizer.SplitMode.C
        # A cache dictionary (not used in the current implementation but available for future optimizations).
        self.cache: Dict = {}
        # Load the JMdict XML file and build a mapping from kanji words to a list of readings.
        self.word_dict = self.load_jmdict(jmdict_path)
        # Global debug flag: if True, debug messages are printed for all words.
        self.global_debug: bool = global_debug
        # If a list of specific words is provided, convert them to a set for quick membership testing.
        self.debug_words: Set[str] = set(debug_words) if debug_words is not None else set()
        # This flag is set in generate_furigana_word per word to control debug output.
        self.debug_mode: bool = False  

    def contains_kanji(self, text: str) -> bool:
        """
        Checks whether the given text contains any kanji characters.
        Also considers the iteration mark '々' as a kanji.
        """
        return any(("\u4e00" <= ch <= "\u9faf") or (ch == "々") for ch in text)

    def load_jmdict(self, file_path: str) -> Dict[str, List[str]]:
        """
        Parses the JMdict XML file and returns a dictionary mapping each kanji word
        to its list of candidate readings.
        
        :param file_path: Path to the JMdict XML file.
        :return: Dictionary where keys are kanji words and values are lists of readings.
        """
        if not os.path.exists(file_path):
            print(f"⚠️ JMdict file not found: {file_path}")
            return {}
        tree = ET.parse(file_path)
        root = tree.getroot()
        word_dict: Dict[str, List[str]] = {}
        # Loop over each dictionary entry in the JMdict.
        for entry in root.findall("entry"):
            # For each entry, process each kanji element (<k_ele>).
            for k_ele in entry.findall("k_ele"):
                keb = k_ele.find("keb")
                if keb is None or keb.text is None:
                    continue
                kanji_word = keb.text
                # Gather all readings from <reb> elements within the entry.
                readings = [
                    r_ele.find("reb").text
                    for r_ele in entry.findall("r_ele")
                    if r_ele.find("reb") is not None
                ]
                word_dict[kanji_word] = readings
        return word_dict

    def _katakana_to_hiragana(self, text: str) -> str:
        """
        Converts any Katakana characters in the text to their corresponding Hiragana.
        
        This function loops through each character and, if the character's Unicode codepoint
        is in the Katakana range, subtracts a fixed offset (0x60) to convert it to Hiragana.
        
        :param text: Input text (possibly in Katakana).
        :return: Text converted to Hiragana.
        """
        result = ""
        for ch in text:
            code = ord(ch)
            if 0x30A1 <= code <= 0x30F6:
                result += chr(code - 0x60)
            else:
                result += ch
        return result

    def _get_candidate_readings(self, kanji: str) -> Set[str]:
        """
        Retrieves candidate readings for a given kanji using both SudachiPy and JMdict.
        
        Steps:
         1. Tokenizes the kanji using SudachiPy and collects the reading forms (converted to Hiragana).
         2. Adds any readings from the JMdict lookup.
         3. (Optionally) adds any exception readings if defined.
         4. Adds rendaku variants by converting the first character to its voiced version if applicable.
        
        :param kanji: The single kanji character for which to retrieve readings.
        :return: A set of candidate readings (strings).
        """
        tokens = self.tokenizer_obj.tokenize(kanji, self.mode)
        candidates: Set[str] = set()
        for token in tokens:
            r = token.reading_form()
            if r:
                # Convert token reading (in Katakana) to Hiragana.
                candidates.add(self._katakana_to_hiragana(r))
        if kanji in self.word_dict:
            for r in self.word_dict[kanji]:
                candidates.add(r)
        # Exception readings could be added here if defined.
        if hasattr(self, "exception_readings") and kanji in self.exception_readings:
            candidates.update(self.exception_readings[kanji])
        # Define a mapping for rendaku conversion (voicing of initial consonants).
        rendaku_map = {
            "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
            "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
            "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
            "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
        }
        additional: Set[str] = set()
        for cand in candidates:
            if cand and cand[0] in rendaku_map:
                # Add the rendaku variant (e.g., "たい" becomes "だい").
                additional.add(rendaku_map[cand[0]] + cand[1:])
        candidates.update(additional)
        if not candidates:
            candidates.add(kanji)
        if self.debug_mode:
            print(f"DEBUG: Candidates for '{kanji}': {sorted(candidates)}")
        return candidates

    def iteration_readings(self, previous_reading: str) -> Set[str]:
        """
        For an iteration mark '々', derive candidate readings based on the previous reading.
        
        For example, if the previous reading is "ひと", the function might also yield "びと".
        
        :param previous_reading: The reading of the previous kanji character.
        :return: A set of candidate readings for the iteration mark.
        """
        mapping = {
            "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
            "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
            "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
            "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
        }
        candidates: Set[str] = set()
        if previous_reading:
            first = previous_reading[0]
            rest = previous_reading[1:]
            candidates.add(previous_reading)
            if first in mapping:
                candidates.add(mapping[first] + rest)
        if self.debug_mode:
            print(f"DEBUG: Iteration readings for previous '{previous_reading}': {candidates}")
        return candidates

    def _annotate_kanji_block(self, block: str, block_reading: str) -> str:
        """
        Annotates a block of kanji by matching candidate readings for each character against
        the provided block reading.
        
        Process:
         1. For each character in the block, retrieve candidate readings using _get_candidate_readings.
         2. For iteration marks ('々'), derive candidates from the previous candidate set.
         3. Build a list (candidates_list) where each element is the sorted list of candidates for a kanji.
         4. Try to find a combination (using Cartesian product) of candidate readings that, when concatenated,
            exactly equals block_reading.
         5. If a direct match is found, join the annotated kanji (with a space and a span for spacing).
         6. Otherwise, generate all possible splits of block_reading into as many segments as there are kanji,
            filter them to only accept splits where each segment is in the candidate set for the corresponding kanji,
            and then select the best split based on a cost measure.
         
        The final annotated string is returned as HTML with <ruby> tags and an extra <span class="kanji-space"></span>
        inserted between each annotated kanji.
        
        :param block: The substring of the word containing kanji (e.g., "大人").
        :param block_reading: The corresponding reading for the kanji block (e.g., "おとな").
        :return: An HTML string with ruby annotations and spacing.
        """
        if self.debug_mode:
            print(f"DEBUG: _annotate_kanji_block: block='{block}', block_reading='{block_reading}'")
        candidates_list: List[List[str]] = []
        for i, ch in enumerate(block):
            # For the iteration mark '々', derive candidates from the previous kanji's candidates.
            if ch == "々":
                if i == 0:
                    candidates = list(self._get_candidate_readings(ch))
                else:
                    prev_candidates = candidates_list[i - 1]
                    cand: Set[str] = set()
                    for pc in prev_candidates:
                        cand.update(self.iteration_readings(pc))
                    candidates = list(cand)
            else:
                candidates = set(self._get_candidate_readings(ch))
                # If the block is a single character, also add the full block reading.
                if len(block) == 1:
                    candidates.add(block_reading)
                candidates = sorted(list(candidates))
            if self.debug_mode:
                print(f"DEBUG: Candidates for block[{i}] '{ch}': {candidates}")
            candidates_list.append(candidates)
        
        # Try to find a direct combination of candidates that equals block_reading.
        matching = [combo for combo in itertools.product(*candidates_list)
                    if "".join(combo) == block_reading]
        if self.debug_mode:
            print(f"DEBUG: Matching combinations for block '{block}': {matching}")
        if matching:
            chosen = matching[0]
            # Join each annotated kanji with a space and a <span> for spacing.
            annotated = "".join(
                f"<ruby>{ch}<rt>{r}</rt></ruby><span class='kanji-space'></span>"
                for ch, r in zip(block, chosen)
            )
            if self.debug_mode:
                print(f"DEBUG: Chosen combination for block '{block}': {chosen} => {annotated}")
            return annotated
        else:
            # Fallback: generate all possible splits of block_reading into len(block) parts.
            splits = list(self._generate_splits(block_reading, len(block)))
            if self.debug_mode:
                print(f"DEBUG: All fallback splits for block '{block}': {splits}")
            valid_splits = []
            for split in splits:
                valid = True
                for i, seg in enumerate(split):
                    valid_candidates = self._get_candidate_readings(block[i])
                    if seg not in valid_candidates:
                        valid = False
                        if self.debug_mode:
                            print(f"DEBUG: Split {split} rejected: '{seg}' not in candidates for '{block[i]}' ({valid_candidates})")
                        break
                if valid:
                    valid_splits.append(split)
            if self.debug_mode:
                print(f"DEBUG: Valid fallback splits for block '{block}': {valid_splits}")
            best_split = None
            best_cost = float('inf')
            # The ideal segment length is the total reading length divided by the number of kanji.
            ideal = len(block_reading) / len(block)
            for split in valid_splits:
                cost = sum(abs(len(seg) - ideal) for seg in split)
                if self.debug_mode:
                    print(f"DEBUG: Split {split} with cost {cost}")
                if cost < best_cost - 1e-6:
                    best_cost = cost
                    best_split = split
                elif abs(cost - best_cost) < 1e-6:
                    if tuple(len(s) for s in split) > tuple(len(s) for s in best_split):
                        best_split = split
            if best_split is not None:
                annotated = "".join(
                    f"<ruby>{ch}<rt>{seg}</rt></ruby><span class='kanji-space'></span>"
                    for ch, seg in zip(block, best_split)
                )
                if self.debug_mode:
                    print(f"DEBUG: Best fallback split for block '{block}': {best_split} => {annotated}")
                return annotated
            return f"<ruby>{block}<rt>{block_reading}</rt></ruby>"

    def _generate_splits(self, reading: str, n: int) -> List[List[str]]:
        """
        Recursively generates all splits of 'reading' into n non-empty parts.
        
        :param reading: The reading string to be split (e.g., "おとな").
        :param n: The number of parts to split the string into (typically the number of kanji in the block).
        :return: A list of lists, where each sublist represents one possible split.
        """
        if n == 1:
            return [[reading]]
        splits = []
        for i in range(1, len(reading) - n + 2):
            for rest in self._generate_splits(reading[i:], n - 1):
                splits.append([reading[:i]] + rest)
        return splits

    def _split_surface(self, surface: str) -> List[Tuple[str, str]]:
        """
        Splits the surface string into segments.
        
        Each segment is a tuple (type, content):
          - Type 'L' indicates a literal segment (non-kanji).
          - Type 'K' indicates a kanji block.
          
        :param surface: The original word (e.g., "大人しい").
        :return: A list of segments, for example: [('K', '大人'), ('L', 'しい')]
        """
        segments = []
        i = 0
        while i < len(surface):
            if not self.contains_kanji(surface[i]):
                lit = ""
                while i < len(surface) and not self.contains_kanji(surface[i]):
                    lit += surface[i]
                    i += 1
                segments.append(('L', lit))
            else:
                kanji = ""
                while i < len(surface) and self.contains_kanji(surface[i]):
                    kanji += surface[i]
                    i += 1
                segments.append(('K', kanji))
        if self.debug_mode:
            print(f"DEBUG: _split_surface: {segments}")
        return segments

    def _align_segments(self, segments: List[Tuple[str, str]], reading: str, 
                        seg_idx: int = 0, read_idx: int = 0,
                        memo: Optional[Dict[Tuple[int, int], Optional[str]]] = None) -> Optional[str]:
        """
        Recursively aligns the list of segments (from _split_surface) with the full reading.
        
        It processes literal segments by directly comparing them (after normalizing to Hiragana)
        and processes kanji blocks via _annotate_kanji_block. If an alignment for all segments is
        found, the concatenated annotated string is returned.
        
        :param segments: List of tuples representing segments of the word.
        :param reading: The full reading string (target reading).
        :param seg_idx: The current index in the segments list.
        :param read_idx: The current index in the reading string.
        :param memo: A memoization dictionary to speed up recursion.
        :return: The concatenated annotated string if alignment is successful, else None.
        """
        if memo is None:
            memo = {}
        key = (seg_idx, read_idx)
        if key in memo:
            return memo[key]
        if seg_idx == len(segments) and read_idx == len(reading):
            return ""
        if seg_idx == len(segments):
            return None
        if self.debug_mode:
            print(f"DEBUG: _align_segments: seg_idx={seg_idx}, read_idx={read_idx}, remaining reading='{reading[read_idx:]}'")
        typ, seg = segments[seg_idx]
        if typ == 'L':
            # For literal segments, compare the segment after converting to Hiragana.
            seg_norm = self._katakana_to_hiragana(seg)
            literal_segment = reading[read_idx:read_idx + len(seg)]
            literal_segment_norm = self._katakana_to_hiragana(literal_segment)
            if literal_segment_norm == seg_norm:
                rest = self._align_segments(segments, reading, seg_idx + 1, read_idx + len(seg), memo)
                if rest is not None:
                    memo[key] = seg + rest
                    if self.debug_mode:
                        print(f"DEBUG: _align_segments (L): Matched literal '{seg}' (norm: '{seg_norm}') with reading segment '{literal_segment}' (norm: '{literal_segment_norm}'), new read_idx={read_idx+len(seg)}")
                    return seg + rest
            memo[key] = None
            if self.debug_mode:
                print(f"DEBUG: _align_segments (L): Failed to match literal '{seg}' (norm: '{seg_norm}') at read_idx={read_idx}, got '{literal_segment_norm}'")
            return None
        else:
            # For kanji blocks, try different segment lengths for the block.
            k = len(seg)
            max_possible = len(reading) - read_idx
            for L in range(max_possible, k - 1, -1):
                block_reading = reading[read_idx:read_idx+L]
                annotated_block = self._annotate_kanji_block(seg, block_reading)
                rest = self._align_segments(segments, reading, seg_idx + 1, read_idx + L, memo)
                if self.debug_mode:
                    print(f"DEBUG: Trying block '{seg}' with block_reading='{block_reading}', L={L}")
                if rest is not None:
                    memo[key] = annotated_block + rest
                    if self.debug_mode:
                        print(f"DEBUG: _align_segments (K): Success for block '{seg}' with reading='{block_reading}'")
                    return annotated_block + rest
            memo[key] = None
            if self.debug_mode:
                print(f"DEBUG: _align_segments (K): Failed to match block '{seg}' at read_idx={read_idx}")
            return None

    def _annotate_word(self, surface: str, full_reading: str) -> str:
        """
        Coordinates the process of splitting the surface word and aligning it with the full reading.
        
        It first splits the word into segments (literal and kanji-blocks), then uses _align_segments
        to get the annotated (ruby) output. If no alignment is found, the original surface is returned.
        
        :param surface: The original word (e.g., "大人しい").
        :param full_reading: The target reading (e.g., "おとなしい").
        :return: The HTML annotated string with ruby tags.
        """
        if self.debug_mode:
            print(f"DEBUG: _annotate_word called with surface='{surface}', full_reading='{full_reading}'")
        segments = self._split_surface(surface)
        result = self._align_segments(segments, full_reading)
        if self.debug_mode:
            print(f"DEBUG: _annotate_word result: '{result}'")
        if result is None:
            print(f"⚠️ Warnung: Kein vollständiges Alignment gefunden für '{surface}' mit Lesung '{full_reading}'")
            return surface
        return result

    def generate_furigana_word(self, word: str, target_reading: Optional[str] = None) -> str:
        """
        Generates the annotated furigana for the given word using the provided target reading.
        
        Debugging is activated either globally (global_debug) or for specific words (debug_words).
        If no target reading is provided, the word is looked up in the JMdict dictionary.
        
        :param word: The input word (e.g., "大人しい").
        :param target_reading: The reading to use for annotation (e.g., "おとなしい").
        :return: The HTML string with ruby annotations.
        """
        # Activate debug mode if global_debug is True or if the current word is in debug_words.
        if self.global_debug or (self.debug_words and word in self.debug_words):
            self.debug_mode = True
            print(f"DEBUG: Processing word '{word}' with target_reading='{target_reading}'")
        else:
            self.debug_mode = False
        # If the word does not contain kanji, return it as-is.
        if not self.contains_kanji(word):
            return word
        # If a target reading is provided, use the annotation process.
        if target_reading:
            if "/" in target_reading:
                return word
            return self._annotate_word(word, target_reading)
        else:
            readings = self.word_dict.get(word, [])
            if len(readings) == 1:
                return f"<ruby>{word}<rt>{readings[0]}</rt></ruby>"
            return word

class VocabYamlLoader:
    """
    Loads a nested YAML file that looks like this:

    - word: ああ
      tags: [Tonari_no_Totoro]
      readings:
        - reading: ああ
          expression_audio: ああ.mp3
          meaning:
            en: "oh"
            de: "oh"
          sentences:
            - sentence: "ああうるさい人は苦手です。"
              sentence_kana: "ああ うるさい ひと は にがて です"
              sentence_audio: "ああ_sentence.mp3"
              translations:
                en: "Oh, I can't stand noisy people."
                de: "Oh, ich kann laute Menschen nicht ausstehen."
    """
    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path

    def load_data(self):
        """
        Reads the YAML file and returns a list of vocabulary entries.
        Each entry is expected to be a dictionary with fields like:
          - expression
          - reading
          - sentence
          - sentence_kana
          - sentence_audio
          - expression_audio
          - image_uri
          - tags (list)
          - translations (dict with language codes)
        """
        if not os.path.exists(self.yaml_path):
            raise FileNotFoundError(f"YAML file not found: {self.yaml_path}")

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list):
            raise ValueError("YAML must be a list of items.")

        return data

class NoteFactory:
    """
    The NoteFactory class creates Anki notes (cards) for different learning modalities:
      - Reading: Focused on kanji, furigana, meaning, and example sentences.
      - Listening: Includes audio fields for pronunciation.
      - Translation: Focuses on the meaning and translations of the word and sentences.
      
    It uses specific Anki models (templates) for each note type and leverages the
    FuriganaGenerator to generate annotated (ruby) versions of the word.
    """
    def __init__(self, reading_model, listening_model, translation_model, furigana_generator):
        """
        Initializes the NoteFactory with specific Anki models and a FuriganaGenerator.
        
        Args:
            reading_model: Anki model for reading cards.
            listening_model: Anki model for listening cards.
            translation_model: Anki model for translation cards.
            furigana_generator: Instance of FuriganaGenerator for generating ruby annotations.
        """
        self.reading_model = reading_model
        self.listening_model = listening_model
        self.translation_model = translation_model
        self.furigana_generator = furigana_generator  

    def create_notes_for_reading(self, word_str, reading_data, tags, lang_code):
        """
        Creates multiple Anki notes (cards) for a vocabulary entry in various modes.
        
        Args:
            word_str (str): The base kanji word.
            reading_data (dict): Dictionary containing details for the word's reading, audio,
                                 sentences, and translations.
            tags (list): List of tags to associate with the note.
            lang_code (str): Language code (e.g., 'en' for English, 'de' for German) to select
                             the appropriate translation.
        
        Process:
            - Extracts reading, audio, meaning, and additional note information.
            - Generates furigana (ruby HTML) for the kanji expression.
            - Aggregates sentences, their kana, translations, and audio.
            - Creates three types of notes:
                1. Reading Note: General information including furigana, meaning, and sentences.
                2. Listening Note: Includes audio fields (only if expression_audio exists).
                3. Translation Note: Focused on meaning and sentence translations (only if
                   both meaning and translated sentence exist).
        
        Returns:
            list: A list of genanki.Note objects corresponding to the different note types.
        """
        # Retrieve the target reading for the word.
        reading_str = reading_data.get("reading", "")
        # Get the audio file name for the expression.
        expression_audio = reading_data.get("expression_audio", "")
        # Extract the meaning dictionary and get the meaning in the specified language.
        meaning_dict = reading_data.get("meaning", {})
        meaning_for_lang = meaning_dict.get(lang_code, "")
        # Retrieve any additional note content, if available.
        note_dict = reading_data.get("note", {}) 
        note_for_lang = note_dict.get(lang_code, "")

        # Generate the furigana annotated version of the word using the provided reading.
        furigana_expression = self.furigana_generator.generate_furigana_word(word_str, target_reading=reading_str)

        # Prepare lists to collect sentences and related fields.
        sentences = reading_data.get("sentences", [])
        sentence_lines, sentence_kana_lines, sentence_translation_lines, sentence_audio_list = [], [], [], []

        # Process each sentence entry in the vocabulary data.
        for s in sentences:
            # Extract individual elements from the sentence dictionary.
            sentence_text = s.get("sentence", "")
            sentence_kana = s.get("sentence_kana", "")
            s_audio = s.get("sentence_audio", "")
            translations = s.get("translations", {})
            trans_lang = translations.get(lang_code, "")

            # Append the sentence text if available.
            if sentence_text:
                sentence_lines.append(sentence_text)
            # Append the kana reading if available.
            if sentence_kana:
                sentence_kana_lines.append(sentence_kana)
            # Append the translation if available.
            if trans_lang:
                sentence_translation_lines.append(trans_lang)
            # Append the audio filename if available.
            if s_audio:
                sentence_audio_list.append(s_audio)

        # Join the sentence elements into multi-line strings for the Anki note fields.
        joined_sentence = "\n".join(sentence_lines)
        joined_sentence_kana = "\n".join(sentence_kana_lines)
        joined_sentence_translation = "\n".join(sentence_translation_lines)
        joined_sentence_furigana = "" # Placeholder for any furigana annotations on sentences (if needed).
        # Use the first sentence audio if available.
        final_sentence_audio = sentence_audio_list[0] if sentence_audio_list else ""

        # Initialize an empty list to hold the created notes.
        notes = []


        # -----------------------------------------------------------------------------
        # Create the READING NOTE
        # -----------------------------------------------------------------------------
        # Generate a unique GUID for the reading note using a combination of word, reading,
        # language code, and a string identifier.
        reading_guid = genanki.guid_for(word_str + reading_str + lang_code + "reading")
        # Create the reading note with the reading model.
        # Fields include: word, furigana, meaning, reading, sentences, kana, furigana (if any),
        # sentence translation, audio files (if available), and additional note.
        notes.append(genanki.Note(
            model=self.reading_model,
            fields=[
                word_str,                                        # Base word (kanji)
                furigana_expression,                             # Word with furigana annotation
                meaning_for_lang,                                # Meaning in the target language
                reading_str,                                     # Reading string (phonetics)
                joined_sentence,                                 # Joined sentences (example usage)
                joined_sentence_kana,                            # Joined kana readings for sentences
                joined_sentence_furigana,                        # Placeholder for sentence furigana
                joined_sentence_translation,                     # Joined sentence translations
                f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',  # Sentence audio
                f'[sound:{expression_audio}]' if expression_audio else '',          # Expression audio
                '',                                              # Placeholder for Image file
                note_for_lang                                    # Additional note information
            ],
            tags=tags,                                           # Tags associated with this note
            guid=reading_guid                                    # Unique identifier for the note
        ))


        # -----------------------------------------------------------------------------
        # Create the LISTENING NOTE (only if expression audio is provided)
        # -----------------------------------------------------------------------------
        if expression_audio:
            # Generate a unique GUID for the listening note.
            listening_guid = genanki.guid_for(word_str + reading_str + lang_code + "listening")
            # Create the listening note using the listening model.
            notes.append(genanki.Note(
                model=self.listening_model,
                fields=[
                    word_str,                                        # Base word (kanji)
                    furigana_expression,                             # Word with furigana
                    meaning_for_lang,                                # Meaning in target language
                    reading_str,                                     # Reading string
                    joined_sentence,                                 # Joined sentences
                    joined_sentence_kana,                            # Joined sentence kana
                    joined_sentence_furigana,                        # Placeholder for sentence furigana
                    joined_sentence_translation,                     # Joined sentence translations
                    f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',  # Sentence audio
                    f'[sound:{expression_audio}]',                   # Expression audio (must exist)
                    '',                                              # Placeholder for Image file
                    note_for_lang                                    # Additional note information
                ],
                tags=tags,
                guid=listening_guid
            ))

        # -----------------------------------------------------------------------------
        # Create the TRANSLATION NOTE (only if both meaning and sentence translation exist)
        # -----------------------------------------------------------------------------
        if meaning_for_lang and joined_sentence_translation:
            # Generate a unique GUID for the translation note.
            translation_guid = genanki.guid_for(word_str + reading_str + lang_code + "translation")
            # Create the translation note using the translation model.
            notes.append(genanki.Note(
                model=self.translation_model,
                fields=[
                    meaning_for_lang,                                # Meaning in target language
                    joined_sentence_translation,                     # Joined sentence translations
                    word_str,                                        # Base word (kanji)
                    furigana_expression,                             # Word with furigana
                    reading_str,                                     # Reading string
                    joined_sentence,                                 # Joined sentences (example usage)
                    joined_sentence_kana,                            # Joined sentence kana
                    joined_sentence_furigana,                        # Placeholder for sentence furigana
                    f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',  # Sentence audio
                    f'[sound:{expression_audio}]' if expression_audio else '',          # Expression audio
                    '',                                              # Placeholder for Image file
                    note_for_lang                                    # Additional note information
                ],
                tags=tags,
                guid=translation_guid
            ))
        # Return the list of created notes for this reading.
        return notes

class VocabDeckGenerator:
    """
    The VocabDeckGenerator class loads vocabulary data from a YAML file and uses it to create
    an Anki deck. It performs the following tasks:
      - Loads the nested vocabulary data using VocabYamlLoader.
      - Initializes a FuriganaGenerator to annotate kanji words.
      - Uses NoteFactory to generate Anki notes for each vocabulary entry.
      - Adds any media files (e.g., audio) required for the notes.
      - Writes out the complete Anki deck as a .apkg file.
    """
    def __init__(self, yaml_path, jmdict_path="JMdict_e.xml"):
        """
        Initializes the deck generator with paths to the YAML vocabulary data and the JMdict file.
        
        Args:
            yaml_path (str): Path to the YAML file containing vocabulary entries.
            jmdict_path (str): Path to the JMdict XML file for reading lookups.
        """
        self.yaml_path = yaml_path
        loader = VocabYamlLoader(yaml_path)
        self.nested_data = loader.load_data()
        self.furigana_generator = FuriganaGenerator(jmdict_path, global_debug=False, debug_words=None)

    def create_deck_for_language(self, lang_code, output_dir="output"):
        """
        Creates an Anki deck for the specified language by processing all vocabulary entries.
        
        Args:
            lang_code (str): Language code ("en" for English, "de" for German, etc.).
            output_dir (str): Directory where the resulting .apkg file will be saved.
        
        Process:
            - Defines unique model IDs for reading, listening, and translation cards.
            - Retrieves Anki models using AnkiModelFactory.
            - Initializes an Anki deck and package.
            - Uses NoteFactory to create notes for each vocabulary entry and adds them to the deck.
            - Incorporates media files (e.g., audio files) into the deck.
            - Writes the complete deck to a file.
        """
        # Define unique model IDs for each note type (these should match your Anki template IDs).
        reading_model_id = 1607392319
        listening_model_id = 1607392321
        translation_model_id = 1607392320

        # Create Anki models using the AnkiModelFactory, passing in the language code and template directory.
        model_factory = AnkiModelFactory(lang_code, template_dir='templates')
        reading_model = model_factory.get_reading_model(reading_model_id)
        listening_model = model_factory.get_listening_model(listening_model_id)
        translation_model = model_factory.get_translation_model(translation_model_id)

        # Create a new Anki deck with the reading model ID as the deck ID and a descriptive name.
        deck = genanki.Deck(reading_model_id, f"Japanese Vocab Deck ({lang_code})")
        # Initialize an Anki package to hold the deck and its media files.
        package = genanki.Package(deck)

        # Create an instance of NoteFactory with the generated models and the furigana generator.
        note_factory = NoteFactory(reading_model, listening_model, translation_model, self.furigana_generator)

        # Iterate over each vocabulary entry in the loaded YAML data.
        for item in self.nested_data:
            # Each item is expected to have keys like:
            #   'word': the base kanji word,
            #   'tags': a list of associated tags,
            #   'readings': a list of dictionaries containing reading details.
            word_str = item.get('word', '')
            tags_raw = item.get('tags', [])
            # Replace spaces in tags with underscores to ensure compatibility with Anki's tag format.
            tags = [t.replace(" ", "_") for t in tags_raw]

            # Process each reading variant for the word.
            readings = item.get('readings', [])
            for reading_data in readings:
                # Generate notes for this reading using NoteFactory.
                notes = note_factory.create_notes_for_reading(word_str, reading_data, tags, lang_code)
                # Add each created note to the deck.
                for note in notes:
                    deck.add_note(note)

                # Add the media files (audio) referenced in this reading to the package.
                self._add_media_files(package, word_str, reading_data)

        # Ensure the output directory exists.
        os.makedirs(output_dir, exist_ok=True)
        # Define the output filename using the language code.
        output_file = os.path.join(output_dir, f"japanese_coredeck_{lang_code}.apkg")
        # Write the completed deck package (including media) to the output file.
        package.write_to_file(output_file)
        print(f"Deck created: {output_file}")

    def _add_media_files(self, package, word_str, reading_data):
        """
        Adds any necessary media files (e.g., audio) to the Anki package.
        
        Args:
            package (genanki.Package): The Anki package to which media files will be added.
            word_str (str): The base word (not used directly here but available for context).
            reading_data (dict): The reading data containing keys for 'expression_audio' and
                                 'sentences' that might include 'sentence_audio'.
        
        Process:
            - Constructs file paths for audio files based on the YAML file's directory.
            - Checks if each file exists before adding it to the media_files list.
            - Prints a warning if any referenced audio file is not found.
        """
        # Determine the base directory relative to the YAML file.
        base_dir = os.path.dirname(self.yaml_path)
        # Assume audio files are stored in a subdirectory named 'audio'.
        audio_dir = os.path.join(base_dir, "audio")
        # Assume image files are stored in a subdirectory named 'images'
        image_dir = os.path.join(base_dir, "images")  

        # -----------------------------------------------------------------------------
        # Add expression audio (if available)
        # -----------------------------------------------------------------------------
        expr_audio = reading_data.get("expression_audio", "")
        if expr_audio:
            expr_audio_path = os.path.join(audio_dir, expr_audio)
            if os.path.exists(expr_audio_path):
                # Append the valid audio file path to the package's media_files list.
                package.media_files.append(expr_audio_path)
            else:
                print(f"Warning: Audio file not found: {expr_audio_path}")

        # -----------------------------------------------------------------------------
        # Add sentence audio for each sentence in the reading (if available)
        # -----------------------------------------------------------------------------
        for s_data in reading_data.get("sentences", []):
            s_audio = s_data.get("sentence_audio", "")
            if s_audio:
                s_audio_path = os.path.join(audio_dir, s_audio)
                if os.path.exists(s_audio_path):
                    package.media_files.append(s_audio_path)
                else:
                    print(f"Warning: Audio file not found: {s_audio_path}")

# =============================================================================
# Main Execution Block
# =============================================================================
if __name__ == "__main__":
    # Define the path to the YAML file containing vocabulary data.
    yaml_file = "data/vocab.yaml"
    # Define the path to the JMdict XML file for Japanese dictionary lookup.
    jmdict_path = "JMdict_e.xml"
    # Create an instance of VocabDeckGenerator with the given YAML file.
    generator = VocabDeckGenerator(yaml_file)

    # Create an Anki deck for German ('de') translations.
    generator.create_deck_for_language("de")

    # Create an Anki deck for English ('en') translations.
    generator.create_deck_for_language("en")
