import genanki

def load_template(file_path):
    """Lädt den HTML-Inhalt einer Datei."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_model(model_id, mother_tongue):
    """Erstellt ein Anki-Modell mit Templates und Styling."""
    front_reading = load_template('templates/front_reading.html')
    back_reading = load_template('templates/back_reading.html')
    front_listening = load_template('templates/front_listening.html')
    back_listening = load_template('templates/back_listening.html')
    css = load_template('templates/style.css')

    return genanki.Model(
        model_id,
        f'Japanese Vocab ({mother_tongue})',
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
