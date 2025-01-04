import genanki

def load_template(file_path):
    """Lädt den HTML-Inhalt einer Datei."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_reading_listening_model(model_id, lc):
    """Erstellt ein Anki-Modell für Reading- und Listening-Karten."""
    front_reading = load_template('templates/front_reading.html')
    back_reading = load_template('templates/back_reading.html')
    front_listening = load_template('templates/front_listening.html')
    back_listening = load_template('templates/back_listening.html')
    css = load_template('templates/style.css')

    return genanki.Model(
        model_id,
        f'Japanese Vocab ({lc}) - Reading & Listening',
        fields=[
            {'name': 'Expression'},
            {'name': 'Meaning'},
            {'name': 'Reading'},
            {'name': 'Sentence'},
            {'name': 'SentenceKana'},
            {'name': 'SentenceTranslation'},
            {'name': 'SentenceAudio'},
            {'name': 'ExpressionAudio'},
            {'name': 'ImageURI'},
        ],
        templates=[
            {
                'name': 'Reading Card',
                'qfmt': front_reading,
                'afmt': back_reading,
            },
            {
                'name': 'Listening Card',
                'qfmt': front_listening,
                'afmt': back_listening,
            },
        ],
        css=css
    )

def get_translation_model(model_id, lc):
    """Erstellt ein Anki-Modell für Translation-Karten."""
    front_translation = load_template('templates/front_translation.html')
    back_translation = load_template('templates/back_translation.html')
    css = load_template('templates/style.css')

    return genanki.Model(
        model_id,
        f'Japanese Vocab ({lc}) - Translation',
        fields=[
            {'name': 'Meaning'},
            {'name': 'SentenceTranslation'},
            {'name': 'Expression'},
            {'name': 'Reading'},
            {'name': 'Sentence'},
            {'name': 'SentenceKana'},
            {'name': 'SentenceAudio'},
            {'name': 'ExpressionAudio'},
            {'name': 'ImageURI'},
        ],
        templates=[
            {
                'name': 'Translation Card',
                'qfmt': front_translation,
                'afmt': back_translation,
            },
        ],
        css=css
    )