
## About

This project provides a Python-based system for generating custom Anki decks tailored for Japanese vocabulary learning. The system supports creating cards with various formats such as reading, listening, and translation, including features like clickable audio playback and image support.

**Disclaimer**: Some example sentence audios in the dataset may be incorrect or incomplete. I am fixing those over the time. 

Unfortunately Anki doesn't seem to overwrite media files but instead adds another media files with a GUID but it doesn't get used as mentioned in:

https://forums.ankiweb.net/t/anki-import-images-card-references-are-renamed-with-appendix/37078

https://forums.ankiweb.net/t/import-media-in-importer-without-updating-notes/42650/5

This means: When you import newer deck versions, the new media files aren't updated in your existing anki notes.

My solution was to delete the audio files from collection.media content. 

Windows: `%appdata%\Anki2\<ankiuser>\collection.media`

This folder contains all used media files. When the audio files are deleted, they are getting reimported when you import the new deck.
Important: First delete the media files, then import the new deck.

I don't have a way for ankidroid only so this involves using anki on a desktop pc.

## Features

- **Reading Cards**: Focus on recognizing vocabulary, their meanings, and example sentences.  
- **Listening Cards**: Test your listening comprehension with audio playback for both expressions and example sentences.  
- **Translation Cards**: Practice translating words from your native language to Japanese.  
- **Dynamic Templates**: Easily customizable card layouts using HTML/CSS templates.  
- **Robust Data Handling**: Allows incomplete entries (missing audio/images) and still generates functional cards.  
- **Multi-language Support**: Create decks for multiple target languages by loading different translation files.  
- **Automated Deck Building**: Generate `.apkg` files ready for import into Anki.  
- **CI/CD Integration**: GitHub Actions workflow automatically generates new decks on each tagged release.

## Table of Contents

1. [Installation](#installation)  
2. [Project Structure](#project-structure)  
3. [How to Use](#how-to-use)  
4. [Data Format](#data-format)  
5. [Customization](#customization)  
6. [Contributing](#contributing)  
7. [License](#license)

## Installation

1. **Clone** the repository:
    ```bash
    git clone https://github.com/<your-username>/japanese-vocab-deck-generator.git
    cd japanese-vocab-deck-generator
    ```

2. **Install** dependencies:
    ```bash
    pip install genanki pyyaml
    ```

3. (Optional) **Set up a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

## Project Structure

```plaintext
.
- data/
  - vocab/
    - index.json          # List of vocab files to load (new format)
    - freq-high.jsonl     # High-frequency entries (JSONL)
    - freq-mid.jsonl      # Mid-frequency entries (JSONL)
    - freq-low.jsonl      # Low-frequency entries (JSONL)
  - translations/
    - en.json             # English meanings/sentence translations
    - de.json             # German meanings/sentence translations
  - audio/               # Audio files for expressions & sentences
  - images/              # Image files for vocabulary (optional)
- output/                # Generated Anki decks (.apkg)
- templates/
  - front_reading.html
  - back_reading.html
  - front_listening.html
  - back_listening.html
  - front_translation.html
  - back_translation.html
  - style.css
- generate_decks.py      # Script to generate Anki decks (multiple notes per reading)
- anki_model.py          # Defines Anki card models and loads templates
- .github/
  - workflows/
    - release.yml        # CI/CD workflow for automated deck generation
```

---

## How to Use

1. Prepare your vocab files in data/vocab/ (see Data Format below).
2. Run the `generate_decks.py` script to create the decks:
   ```bash
   python generate_decks.py
   ```
3. The generated `.apkg` files will be saved in the `output/` folder.
4. Import the `.apkg` files into Anki to start using the decks.

---

## Data Format

- **Vocab files** in `data/vocab/` (JSONL, Japanese data + tags + IDs)
- **Translation files** in `data/translations/` (JSON, per-language meanings/notes/sentence translations)
- A `data/vocab/index.json` file that lists which vocab files to load

### `data/vocab/index.json`

```json
{
  "vocab_files": [
    "freq-high.jsonl",
    "freq-mid.jsonl",
    "freq-low.jsonl"
  ]
}
```

### Vocab files (JSONL format)

Each line in a vocab file is a JSON object with the following structure:

```json
{"word_id":"???","word":"???","tags":["noun","freq-high"],"readings":[{"reading_id":"???__???","reading":"???","expression_audio":"taberu.mp3","sentences":[{"sentence_id":"???__???__s1","sentence":"?????????","sentence_kana":"???????????","sentence_audio":"taberu_sentence_1.mp3"}]}]}
```

### Top-Level Fields

| Field | Type               | Description                                                                  |
|------ |--------------------|------------------------------------------------------------------------------|
| `word_id` | String          | Stable identifier for the word (used by translations).                     |
| `word` | String            | The headword or dictionary form.                                           |
| `tags` | List of Strings   | (Optional) Tags for categorizing or filtering in Anki.                      |
| `readings` | List of Objects | One or more readings for this word (see below).                           |

---

## `readings` List

Each item in the `readings` array provides:

| Field              | Type               | Description                                                                                          |
|--------------------|--------------------|------------------------------------------------------------------------------------------------------|
| `reading_id`       | String             | Stable identifier for this reading.                                                                  |
| `reading`          | String             | Specific reading for the word.                                                                       |
| `expression_audio` | String (optional)  | Filename of the audio for this reading.                                                              |
| `sentences`        | List of Objects    | Zero or more example sentences (see below) illustrating this reading.                                |

---

## `sentences` List

Each sentence object may include:

| Field            | Type               | Description                                                                                          |
|------------------|--------------------|------------------------------------------------------------------------------------------------------|
| `sentence_id`    | String             | Stable identifier for the sentence.                                                                  |
| `sentence`       | String             | Example sentence in Japanese.                                                                        |
| `sentence_kana`  | String             | Kana version of the above sentence.                                                                  |
| `sentence_audio` | String (optional)  | Filename of the audio for this sentence.                                                             |

---

### Translation files

Translations are stored per language in `data/translations/<lang>.json`:

```json
{
  "reading": {
    "???__???": {"meaning": "essen", "note": "transitiv"}
  },
  "sentence": {
    "???__???__s1": {"translation": "Ich esse Brot."}
  }
}
```

---

## Customization

Templates can be edited in templates/ if you want to change the HTML/CSS of the Anki cards.
Models (Reading, Listening, Translation) are defined in anki_model.py.

---

## Contributing

Contributions are welcome.

---

## License

This project is licensed under the MIT License.
