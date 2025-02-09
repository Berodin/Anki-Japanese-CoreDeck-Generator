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
    def __init__(self, jmdict_path: str = "JMdict_e.xml"):
        self.tokenizer_obj = dictionary.Dictionary().create()  # SudachiPy-Tokenizer
        self.mode = tokenizer.Tokenizer.SplitMode.C            
        self.cache = {}
        self.word_dict = self.load_jmdict(jmdict_path)
    
    def contains_kanji(self, text: str) -> bool:
        return any("\u4e00" <= ch <= "\u9faf" for ch in text)
    
    def load_jmdict(self, file_path: str) -> dict:
        if not os.path.exists(file_path):
            print(f"⚠️ JMdict file not found: {file_path}")
            return {}
        tree = ET.parse(file_path)
        root = tree.getroot()
        word_dict = {}
        for entry in root.findall("entry"):
            for kanji_elem in entry.findall("k_ele"):
                keb = kanji_elem.find("keb")
                if keb is None or keb.text is None:
                    continue
                kanji_word = keb.text
                readings = [r_ele.find("reb").text for r_ele in entry.findall("r_ele") if r_ele.find("reb") is not None]
                word_dict[kanji_word] = readings
        return word_dict
    
    def generate_furigana_word(self, word: str, target_reading: str = None) -> str:
        if not self.contains_kanji(word):
            return word
        if target_reading:
            if "/" in target_reading:
                return word
            return f"<ruby>{word}<rt>{target_reading}</rt></ruby>"
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
    Creates different types of Anki notes (Reading, Listening, Translation).
    
    Responsibilities:
    - Generates a Reading Note (Kanji, Furigana, Meaning, Sentences)
    - Generates a Listening Note (Includes audio fields)
    - Generates a Translation Note (Focuses on meaning and translations)

    Each note follows a specific model (reading, listening, or translation).
    """
    def __init__(self, reading_model, listening_model, translation_model, furigana_generator):
        """Initializes NoteFactory with Anki models and a Furigana generator."""
        self.reading_model = reading_model
        self.listening_model = listening_model
        self.translation_model = translation_model
        self.furigana_generator = furigana_generator  

    def create_notes_for_reading(self, word_str, reading_data, tags, lang_code):
        """
        Creates Anki notes (Reading, Listening, Translation) for a vocabulary entry.

        - word_str: The base Kanji word
        - reading_data: Dictionary containing information about the word's reading
        - tags: Tags associated with the word
        - lang_code: Language code (e.g., 'en' for English, 'de' for German)
        
        Returns:
        - A list of genanki.Note objects, each representing an Anki card.
        """
        reading_str = reading_data.get("reading", "")
        expression_audio = reading_data.get("expression_audio", "")
        meaning_dict = reading_data.get("meaning", {})
        meaning_for_lang = meaning_dict.get(lang_code, "")
        note_dict = reading_data.get("note", {}) 
        note_for_lang = note_dict.get(lang_code, "")

        # Ofurigana für das Wort generieren
        furigana_expression = self.furigana_generator.generate_furigana_word(word_str, target_reading=reading_str)

        sentences = reading_data.get("sentences", [])
        sentence_lines, sentence_kana_lines, sentence_translation_lines, sentence_audio_list = [], [], [], []

        for s in sentences:
            sentence_text = s.get("sentence", "")
            sentence_kana = s.get("sentence_kana", "")
            s_audio = s.get("sentence_audio", "")
            translations = s.get("translations", {})
            trans_lang = translations.get(lang_code, "")

            if sentence_text:
                sentence_lines.append(sentence_text)
            if sentence_kana:
                sentence_kana_lines.append(sentence_kana)
            if trans_lang:
                sentence_translation_lines.append(trans_lang)
            if s_audio:
                sentence_audio_list.append(s_audio)

        joined_sentence = "\n".join(sentence_lines)
        joined_sentence_kana = "\n".join(sentence_kana_lines)
        joined_sentence_translation = "\n".join(sentence_translation_lines)
        joined_sentence_furigana = ""
        final_sentence_audio = sentence_audio_list[0] if sentence_audio_list else ""

        notes = []

        # READING NOTE 
        reading_guid = genanki.guid_for(word_str + reading_str + lang_code + "reading")
        notes.append(genanki.Note(
            model=self.reading_model,
            fields=[
                word_str, furigana_expression, meaning_for_lang, reading_str,
                joined_sentence, joined_sentence_kana, joined_sentence_furigana, joined_sentence_translation,
                f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',
                f'[sound:{expression_audio}]' if expression_audio else '',
                '', note_for_lang
            ],
            tags=tags,
            guid=reading_guid
        ))

        # LISTENING NOTE 
        if expression_audio:
            listening_guid = genanki.guid_for(word_str + reading_str + lang_code + "listening")
            notes.append(genanki.Note(
                model=self.listening_model,
                fields=[
                    word_str, furigana_expression, meaning_for_lang, reading_str,
                    joined_sentence, joined_sentence_kana, joined_sentence_furigana, joined_sentence_translation,
                    f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',
                    f'[sound:{expression_audio}]', '', note_for_lang
                ],
                tags=tags,
                guid=listening_guid
            ))

        # TRANSLATION NOTE (Nur wenn es Übersetzungen gibt)
        if meaning_for_lang and joined_sentence_translation:
            translation_guid = genanki.guid_for(word_str + reading_str + lang_code + "translation")
            notes.append(genanki.Note(
                model=self.translation_model,
                fields=[
                    meaning_for_lang, joined_sentence_translation, word_str,
                    furigana_expression, reading_str, joined_sentence,
                    joined_sentence_kana, joined_sentence_furigana, f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',
                    f'[sound:{expression_audio}]' if expression_audio else '',
                    '', note_for_lang
                ],
                tags=tags,
                guid=translation_guid
            ))

        return notes

class VocabDeckGenerator:
    """
    Loads vocabulary from a YAML file and creates an Anki deck.

    Responsibilities:
    - Reads a YAML file containing vocabulary entries
    - Uses FuriganaGenerator for reading generation
    - Generates Anki notes via NoteFactory
    - Saves the Anki deck as a .apkg file
    """
    def __init__(self, yaml_path, jmdict_path="JMdict_e.xml"):
        """Initializes the generator with a YAML file containing vocabulary data and the JMdict dictionary."""
        self.yaml_path = yaml_path
        loader = VocabYamlLoader(yaml_path)
        self.nested_data = loader.load_data()
        self.furigana_generator = FuriganaGenerator(jmdict_path)

    def create_deck_for_language(self, lang_code, output_dir="output"):
        """
        Creates an Anki deck for a specific language (e.g., English or German).

        - lang_code: "en" for English, "de" for German
        - output_dir: Directory where the .apkg file will be saved
        """
        # Model IDs
        reading_model_id = 1607392319
        listening_model_id = 1607392321
        translation_model_id = 1607392320

        # Create models via factory
        model_factory = AnkiModelFactory(lang_code, template_dir='templates')
        reading_model = model_factory.get_reading_model(reading_model_id)
        listening_model = model_factory.get_listening_model(listening_model_id)
        translation_model = model_factory.get_translation_model(translation_model_id)

        # Create Deck
        deck = genanki.Deck(reading_model_id, f"Japanese Vocab Deck ({lang_code})")
        package = genanki.Package(deck)

        # Create NoteFactory
        note_factory = NoteFactory(reading_model, listening_model, translation_model, self.furigana_generator)

        # Build notes
        for item in self.nested_data:
            # item is like:
            # {
            #   'word': 'ああ',
            #   'tags': [...],
            #   'readings': [ {...}, {...} ]
            # }
            word_str = item.get('word', '')
            tags_raw = item.get('tags', [])
            # Replace spaces with underscores
            tags = [t.replace(" ", "_") for t in tags_raw]

            readings = item.get('readings', [])
            for reading_data in readings:
                notes = note_factory.create_notes_for_reading(word_str, reading_data, tags, lang_code)
                for note in notes:
                    deck.add_note(note)

                # Add media for each reading
                self._add_media_files(package, word_str, reading_data)

        # Save deck
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"japanese_coredeck_{lang_code}.apkg")
        package.write_to_file(output_file)
        print(f"Deck created: {output_file}")

    def _add_media_files(self, package, word_str, reading_data):
        """
        Adds audio files for expression_audio, plus each sentence_audio in the reading.
        If you have images at a top level, you can adapt it accordingly.
        """
        base_dir = os.path.dirname(self.yaml_path)
        audio_dir = os.path.join(base_dir, "audio")
        image_dir = os.path.join(base_dir, "images")  

        # expression_audio
        expr_audio = reading_data.get("expression_audio", "")
        if expr_audio:
            expr_audio_path = os.path.join(audio_dir, expr_audio)
            if os.path.exists(expr_audio_path):
                package.media_files.append(expr_audio_path)
            else:
                print(f"Warning: Audio file not found: {expr_audio_path}")

        # sentences
        for s_data in reading_data.get("sentences", []):
            s_audio = s_data.get("sentence_audio", "")
            if s_audio:
                s_audio_path = os.path.join(audio_dir, s_audio)
                if os.path.exists(s_audio_path):
                    package.media_files.append(s_audio_path)
                else:
                    print(f"Warning: Audio file not found: {s_audio_path}")
        
        

if __name__ == "__main__":
    # Example usage
    yaml_file = "data/vocab.yaml"
    jmdict_path = "JMdict_e.xml"
    generator = VocabDeckGenerator(yaml_file)

    # Create deck in German
    generator.create_deck_for_language("de")

    # Create deck in English
    generator.create_deck_for_language("en")
