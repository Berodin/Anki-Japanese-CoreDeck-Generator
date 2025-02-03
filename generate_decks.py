import os
import yaml
import genanki

from anki_model import AnkiModelFactory

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
    Creates (Reading, Listening, Translation) notes for a SINGLE reading 
    in the nested structure.
    """
    def __init__(self, reading_model, listening_model, translation_model):
        self.reading_model = reading_model
        self.listening_model = listening_model
        self.translation_model = translation_model

    def create_notes_for_reading(self, word_str, reading_data, tags, lang_code):
        """
        :param word_str: e.g. "ああ"
        :param reading_data: e.g. {
           "reading": "ああ",
           "expression_audio": "ああ.mp3",
           "meaning": {"en": "oh", "de": "oh"},
           "sentences": [...]
        }
        :param tags: list of tags
        :param lang_code: "en" or "de"

        Returns up to three genanki.Note objects (reading, listening, translation).
        """
        reading_str = reading_data.get("reading", "")
        expression_audio = reading_data.get("expression_audio", "")
        meaning_dict = reading_data.get("meaning", {})
        meaning_for_lang = meaning_dict.get(lang_code, "")
        explanation_dict = reading_data.get("explanation", {}) 
        explanation_for_lang = explanation_dict.get(lang_code, "")

        # Collect all sentences for this reading
        sentences = reading_data.get("sentences", [])
        # We'll combine them into multiline strings:
        sentence_lines, sentence_kana_lines, sentence_translation_lines, sentence_audio_list = [], [], [], []

        for s in sentences:
            # s is like: { "sentence": "..", "sentence_kana": "..", "sentence_audio": "..", "translations": {...} }
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

        # Join them with newline (or any separator)
        joined_sentence = "\n".join(sentence_lines)
        joined_sentence_kana = "\n".join(sentence_kana_lines)
        joined_sentence_translation = "\n".join(sentence_translation_lines)

        # For 'SentenceAudio', we might just pick the FIRST one, if any
        final_sentence_audio = sentence_audio_list[0] if sentence_audio_list else ""
        
        # Prepare a list of notes to return
        notes = []

        # READING NOTE
        reading_fields = [
            word_str,                           # 0: Expression
            meaning_for_lang,                   # 1: Meaning
            reading_str,                        # 2: Reading
            joined_sentence,                    # 3: Sentence
            joined_sentence_kana,              # 4: SentenceKana
            joined_sentence_translation,        # 5: SentenceTranslation
            f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',  # 6: SentenceAudio
            f'[sound:{expression_audio}]' if expression_audio else '',          # 7: ExpressionAudio
            '',  # 8: ImageURI 
            explanation_for_lang # 9: Explanation
        ]
        reading_guid = genanki.guid_for(word_str + reading_str + lang_code + "reading")
        reading_note = genanki.Note(
            model=self.reading_model,
            fields=reading_fields,
            tags=tags,
            guid=reading_guid
        )
        notes.append(reading_note)

        # LISTENING NOTE (only if expression_audio exists)
        if expression_audio:
            listening_fields = [
                word_str,
                meaning_for_lang,
                reading_str,
                joined_sentence,
                joined_sentence_kana,
                joined_sentence_translation,
                f'[sound:{final_sentence_audio}]' if final_sentence_audio else '',
                f'[sound:{expression_audio}]',
                '',
                explanation_for_lang
            ]
            listening_guid = genanki.guid_for(word_str + reading_str + lang_code + "listening")
            listening_note = genanki.Note(
                model=self.listening_model,
                fields=listening_fields,
                tags=tags,
                guid=listening_guid
            )
            notes.append(listening_note)

        # TRANSLATION NOTE (only if meaning_for_lang is not empty and we have translations)
        if meaning_for_lang and joined_sentence_translation:
            translation_fields = [
                meaning_for_lang,                   # 0: Meaning
                joined_sentence_translation,        # 1: SentenceTranslation
                word_str,                           # 2: Expression
                reading_str,                        # 3: Reading
                joined_sentence,                    # 4: Sentence
                joined_sentence_kana,              # 5: SentenceKana
                f'[sound:{final_sentence_audio}]' if final_sentence_audio else '', # 6: SentenceAudio
                f'[sound:{expression_audio}]' if expression_audio else '', # 7: ExpressionAudio
                '', # 8: ImageURI 
                explanation_for_lang # 9: Explanation
            ]
            translation_guid = genanki.guid_for(word_str + reading_str + lang_code + "translation")
            translation_note = genanki.Note(
                model=self.translation_model,
                fields=translation_fields,
                tags=tags,
                guid=translation_guid
            )
            notes.append(translation_note)

        return notes


class VocabDeckGenerator:
    """
    Main class that loads the nested YAML and creates 
    multiple notes per 'word' (one note per reading).
    """
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        loader = VocabYamlLoader(yaml_path)
        self.nested_data = loader.load_data()

    def create_deck_for_language(self, lang_code, output_dir="output"):
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
        note_factory = NoteFactory(reading_model, listening_model, translation_model)

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
    generator = VocabDeckGenerator(yaml_file)

    # Create deck in German
    generator.create_deck_for_language("de")

    # Create deck in English
    generator.create_deck_for_language("en")
