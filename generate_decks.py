import os
import yaml
import genanki

from anki_model import AnkiModelFactory

class VocabYamlLoader:
    """
    Loads vocabulary data from a single YAML file (e.g. 'vocab.yaml').
    """
    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path

    def load_vocab(self):
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
            raise ValueError("YAML file must contain a list of entries.")

        return data

class NoteFactory:
    """
    Creates different Anki notes (Reading, Listening, Translation) for a given entry and language.
    """
    def __init__(self, reading_model, listening_model, translation_model):
        self.reading_model = reading_model
        self.listening_model = listening_model
        self.translation_model = translation_model

    def create_notes_for_entry(self, entry, lang_code):
        """
        Produces up to three notes (Reading, Listening, Translation) for the given entry.

        'entry' is a dictionary:
          {
            "expression": "...",
            "reading": "...",
            "sentence": "...",
            "sentence_kana": "...",
            "sentence_audio": "...",
            "expression_audio": "...",
            "image_uri": "...",
            "tags": [...],
            "translations": {
              "en": {"meaning": "...", "sentence_translation": "..."},
              "de": ...
            }
          }

        'lang_code' is the target language code, like "en" or "de".
        """
        expression = entry.get("expression", "")
        reading = entry.get("reading", "")
        sentence = entry.get("sentence", "")
        sentence_kana = entry.get("sentence_kana", "")
        sentence_audio = entry.get("sentence_audio", "")
        expression_audio = entry.get("expression_audio", "")
        image_uri = entry.get("image_uri", "")
        tags = entry.get("tags", [])
        # Replace spaces with underscores
        tags = [tag.replace(" ", "_") for tag in tags]
        
        translations = entry.get("translations", {})
        lang_data = translations.get(lang_code, {})
        meaning = lang_data.get("meaning", "")
        sentence_translation = lang_data.get("sentence_translation", "")

        # Generate a unique GUID
        guid = genanki.guid_for(expression + reading + lang_code)

        notes = []

        # --- Reading Card ---
        reading_fields = [
            expression,                    # 0: Expression
            meaning,                       # 1: Meaning
            reading,                       # 2: Reading
            sentence,                      # 3: Sentence
            sentence_kana,                # 4: SentenceKana
            sentence_translation,         # 5: SentenceTranslation
            f'[sound:{sentence_audio}]' if sentence_audio else '',  # 6: SentenceAudio
            f'[sound:{expression_audio}]' if expression_audio else '',  # 7: ExpressionAudio
            image_uri                      # 8: ImageURI
        ]
        reading_note = genanki.Note(
            model=self.reading_model,
            fields=reading_fields,
            tags=tags,
            guid=guid
        )
        notes.append(reading_note)

        # --- Listening Card ---
        # Only if we have expression_audio
        if expression_audio:
            listening_fields = [
                expression,                    # 0: Expression
                meaning,                       # 1: Meaning
                reading,                       # 2: Reading
                sentence,                      # 3: Sentence
                sentence_kana,                # 4: SentenceKana
                sentence_translation,         # 5: SentenceTranslation
                f'[sound:{sentence_audio}]' if sentence_audio else '',  # 6: SentenceAudio
                f'[sound:{expression_audio}]',                           # 7: ExpressionAudio
                image_uri                      # 8: ImageURI
            ]
            listening_note = genanki.Note(
                model=self.listening_model,
                fields=listening_fields,
                tags=tags,
                guid=guid
            )
            notes.append(listening_note)

        # --- Translation Card ---
        # Only if meaning and sentence_translation are present
        if meaning and sentence_translation:
            translation_fields = [
                meaning,                       # 0: Meaning
                sentence_translation,          # 1: SentenceTranslation
                expression,                    # 2: Expression
                reading,                       # 3: Reading
                sentence,                      # 4: Sentence
                sentence_kana,                # 5: SentenceKana
                f'[sound:{sentence_audio}]' if sentence_audio else '',  # 6: SentenceAudio
                f'[sound:{expression_audio}]' if expression_audio else '',  # 7: ExpressionAudio
                image_uri                      # 8: ImageURI
            ]
            translation_note = genanki.Note(
                model=self.translation_model,
                fields=translation_fields,
                tags=tags,
                guid=guid
            )
            notes.append(translation_note)

        return notes

class VocabDeckGenerator:
    """
    Main class that:
      - Loads the YAML data
      - Creates and configures Anki models
      - Builds one deck per language
      - Writes .apkg files to disk
    """
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        loader = VocabYamlLoader(yaml_path)
        self.vocab_entries = loader.load_vocab()

    def create_deck_for_language(self, lang_code, output_dir="output"):
        """
        Creates a deck for the given language code (e.g. 'en', 'de') and saves the .apkg.
        """
        # Define model IDs
        reading_model_id = 1607392319
        listening_model_id = 1607392321
        translation_model_id = 1607392320

        # Create models via the factory
        model_factory = AnkiModelFactory(lang_code, template_dir='templates')
        reading_model = model_factory.get_reading_model(reading_model_id)
        listening_model = model_factory.get_listening_model(listening_model_id)
        translation_model = model_factory.get_translation_model(translation_model_id)

        # Create the deck
        deck = genanki.Deck(reading_model_id, f"Japanese Vocab Deck ({lang_code})")
        package = genanki.Package(deck)

        # Create the NoteFactory
        note_factory = NoteFactory(reading_model, listening_model, translation_model)

        # Add notes and media
        for entry in self.vocab_entries:
            notes = note_factory.create_notes_for_entry(entry, lang_code)
            for note in notes:
                deck.add_note(note)
            self._add_media_files(package, entry)

        # Write deck to file
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"japanese_coredeck_{lang_code}.apkg")
        package.write_to_file(output_file)
        print(f"Deck created: {output_file}")

    def _add_media_files(self, package, entry):
        """
        Adds audio/image files (if present) for each vocab entry.
        Expects 'audio/' and 'images/' directories in the same folder as 'vocab.yaml'.
        """
        base_dir = os.path.dirname(self.yaml_path)
        audio_dir = os.path.join(base_dir, "audio")
        image_dir = os.path.join(base_dir, "images")

        sentence_audio = entry.get("sentence_audio", "")
        if sentence_audio:
            sentence_audio_path = os.path.join(audio_dir, sentence_audio)
            if os.path.exists(sentence_audio_path):
                package.media_files.append(sentence_audio_path)
            else:
                print(f"Warning: Audio file not found: {sentence_audio_path}")

        expression_audio = entry.get("expression_audio", "")
        if expression_audio:
            expression_audio_path = os.path.join(audio_dir, expression_audio)
            if os.path.exists(expression_audio_path):
                package.media_files.append(expression_audio_path)
            else:
                print(f"Warning: Audio file not found: {expression_audio_path}")

        image_uri = entry.get("image_uri", "")
        if image_uri:
            image_path = os.path.join(image_dir, image_uri)
            if os.path.exists(image_path):
                package.media_files.append(image_path)
            else:
                print(f"Warning: Image file not found: {image_path}")

if __name__ == "__main__":
    # Example usage: generate decks for German and English
    yaml_file = "data/vocab.yaml"
    generator = VocabDeckGenerator(yaml_file)

    # Create a deck in German
    generator.create_deck_for_language("de")

    # Create a deck in English
    generator.create_deck_for_language("en")
