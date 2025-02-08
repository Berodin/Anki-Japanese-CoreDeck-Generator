import os
import genanki

class TemplateLoader:
    """
    Loads HTML and CSS templates from the specified directory.
    """
    def __init__(self, template_dir='templates'):
        self.template_dir = template_dir

    def load_template(self, filename):
        """
        Loads the text from a template file (HTML or CSS).
        """
        path = os.path.join(self.template_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

class AnkiModelFactory:
    """
    Creates different Anki models (Reading, Listening, Translation) for a given language code.
    """
    def __init__(self, lc, template_dir='templates'):
        self.lc = lc
        self.template_loader = TemplateLoader(template_dir=template_dir)
        # Load the shared CSS once
        self.css = self.template_loader.load_template('style.css')

    def get_reading_model(self, model_id):
        """
        Returns the 'Reading' model for the given language code.
        """
        front = self.template_loader.load_template('front_reading.html')
        back = self.template_loader.load_template('back_reading.html')
        return genanki.Model(
            model_id,
            f'Japanese Vocab ({self.lc}) - Reading',
            fields=[
                {'name': 'Expression'},
                {'name': 'Furigana'},
                {'name': 'Meaning'},
                {'name': 'Reading'},
                {'name': 'Sentence'},
                {'name': 'SentenceKana'},
                {'name': 'SentenceFurigana'},
                {'name': 'SentenceTranslation'},
                {'name': 'SentenceAudio'},
                {'name': 'ExpressionAudio'},
                {'name': 'ImageURI'},
                {'name': 'Note'},
            ],
            templates=[
                {
                    'name': 'Reading Card',
                    'qfmt': front,
                    'afmt': back,
                }
            ],
            css=self.css
        )

    def get_listening_model(self, model_id):
        """
        Returns the 'Listening' model for the given language code.
        """
        front = self.template_loader.load_template('front_listening.html')
        back = self.template_loader.load_template('back_listening.html')
        return genanki.Model(
            model_id,
            f'Japanese Vocab ({self.lc}) - Listening',
            fields=[
                {'name': 'Expression'},
                {'name': 'Furigana'},  
                {'name': 'Meaning'},
                {'name': 'Reading'},
                {'name': 'Sentence'},
                {'name': 'SentenceKana'},
                {'name': 'SentenceFurigana'},
                {'name': 'SentenceTranslation'},
                {'name': 'SentenceAudio'},
                {'name': 'ExpressionAudio'},
                {'name': 'ImageURI'},
                {'name': 'Note'},
            ],
            templates=[
                {
                    'name': 'Listening Card',
                    'qfmt': front,
                    'afmt': back,
                }
            ],
            css=self.css
        )

    def get_translation_model(self, model_id):
        """
        Returns the 'Translation' model for the given language code.
        """
        front = self.template_loader.load_template('front_translation.html')
        back = self.template_loader.load_template('back_translation.html')
        return genanki.Model(
            model_id,
            f'Japanese Vocab ({self.lc}) - Translation',
            fields=[
                {'name': 'Meaning'},
                {'name': 'SentenceTranslation'},
                {'name': 'Expression'},
                {'name': 'Furigana'},
                {'name': 'Reading'},
                {'name': 'Sentence'},
                {'name': 'SentenceKana'},
                {'name': 'SentenceFurigana'},
                {'name': 'SentenceAudio'},
                {'name': 'ExpressionAudio'},
                {'name': 'ImageURI'},
                {'name': 'Note'},
            ],
            templates=[
                {
                    'name': 'Translation Card',
                    'qfmt': front,
                    'afmt': back,
                }
            ],
            css=self.css
        )
