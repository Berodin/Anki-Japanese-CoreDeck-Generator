import os
import yaml
import genanki
from anki_model import AnkiModelFactory
from sudachipy import tokenizer
from sudachipy import dictionary
import xml.etree.ElementTree as ET
import jaconv
import re
from typing import Tuple, List, Optional

class FuriganaGenerator:
    """
    The FuriganaGenerator class is responsible for generating furigana (phonetic
    readings in HTML ruby format) for Japanese words that contain kanji.
    
    It uses:
    - SudachiPy for Japanese text tokenization.
    - A JMdict XML file to look up kanji words and their associated readings.
    
    Attributes:
        tokenizer_obj: An instance of the SudachiPy tokenizer.
        mode: The splitting mode for tokenization (using full segmentation).
        cache: A dictionary used to cache previous furigana lookups.
        word_dict: A dictionary mapping kanji words to a list of their possible readings,
                   loaded from a JMdict XML file.
    """
    def __init__(self, jmdict_path: str = "JMdict_e.xml"):
        # Initialize the SudachiPy tokenizer using the default dictionary.
        self.tokenizer_obj = dictionary.Dictionary().create()  
        # Set the tokenizer splitting mode to 'C' (maximal segmentation).
        self.mode = tokenizer.Tokenizer.SplitMode.C   
        # Initialize an empty cache for storing computed furigana.         
        self.cache = {}
        # Load the JMdict XML file and build a dictionary mapping kanji words to readings.
        self.word_dict = self.load_jmdict(jmdict_path)
    
    def contains_kanji(self, text: str) -> bool:
        """
        Checks if the provided text contains any kanji characters.
        
        Args:
            text (str): The text to check.
            
        Returns:
            bool: True if at least one character in the text is a kanji, False otherwise.
        """
        return any("\u4e00" <= ch <= "\u9faf" for ch in text)
    
    def load_jmdict(self, file_path: str) -> dict:
        """
        Loads the JMdict XML file and creates a dictionary that maps kanji words
        (from the <keb> elements) to a list of their readings (from the <reb> elements).
        
        Args:
            file_path (str): Path to the JMdict XML file.
            
        Returns:
            dict: A mapping from a kanji word (str) to a list of reading strings.
                  If the file is not found, returns an empty dictionary.
        """
        if not os.path.exists(file_path):
            print(f"⚠️ JMdict file not found: {file_path}")
            return {}
        tree = ET.parse(file_path)
        root = tree.getroot()
        word_dict = {}
        # Iterate through each 'entry' in the XML.
        for entry in root.findall("entry"):
            # For each entry, find the kanji element(s).
            for kanji_elem in entry.findall("k_ele"):
                keb = kanji_elem.find("keb") # The actual kanji word.
                # Skip entries with missing or empty kanji.
                if keb is None or keb.text is None:
                    continue
                kanji_word = keb.text
                # Find all reading elements (<reb>) under <r_ele> in the same entry.
                readings = [r_ele.find("reb").text for r_ele in entry.findall("r_ele") if r_ele.find("reb") is not None]
                # Map the kanji word to its list of readings.
                word_dict[kanji_word] = readings
        return word_dict
    
    def generate_furigana_word(self, word: str, target_reading: str = None) -> str:
        """
        Generates an HTML ruby annotation for a Japanese word if it contains kanji.
        
        Args:
            word (str): The kanji word to annotate.
            target_reading (str, optional): The target reading to use. If provided and valid,
                                            it will be used directly.
                                            
        Returns:
            str: The word, either unmodified or wrapped in a <ruby> tag with <rt> for the furigana.
        """
        # If the word does not contain any kanji, return it as-is.
        if not self.contains_kanji(word):
            return word
        # If a target reading is provided:
        if target_reading:
            # If the target reading contains a "/" (suggesting multiple readings),
            # we decide not to annotate and return the word unchanged.
            if "/" in target_reading:
                return word
            # Otherwise, return the word with a ruby annotation.
            return f"<ruby>{word}<rt>{target_reading}</rt></ruby>"

        # If no target reading is provided, look up the word in the JMdict-based dictionary.    
        readings = self.word_dict.get(word, [])
        # If exactly one reading is found, annotate the word with that reading.
        if len(readings) == 1:
            return f"<ruby>{word}<rt>{readings[0]}</rt></ruby>"
        # If multiple or no readings are found, return the original word without annotation.
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
        self.furigana_generator = FuriganaGenerator(jmdict_path)

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
