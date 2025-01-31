
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
├── data/
│   ├── vocab.yaml           # Japanese vocabulary data (nested YAML format)
│   ├── audio/               # Audio files for expressions & sentences
│   ├── images/              # Image files for vocabulary (optional)
├── output/                  # Generated Anki decks (.apkg)
├── templates/
│   ├── front_reading.html
│   ├── back_reading.html
│   ├── front_listening.html
│   ├── back_listening.html
│   ├── front_translation.html
│   ├── back_translation.html
│   └── style.css
├── generate_decks.py        # Script to generate Anki decks (multiple notes per reading)
├── anki_model.py            # Defines Anki card models and loads templates
└── .github/
    └── workflows/
        └── release.yml      # CI/CD workflow for automated deck generation
```

---

## How to Use

1. Prepare your vocab.yaml in data/ (nested format specifying word, readings, sentences, etc.).
2. Run the `generate_decks.py` script to create the decks:
   ```bash
   python generate_decks.py
   ```
3. The generated `.apkg` files will be saved in the `output/` folder.
4. Import the `.apkg` files into Anki to start using the decks.

---

## Data Format 

Instead of multiple CSV files (e.g., `vocab_jp.csv`, `translations_{language}.csv`), we now use a **single YAML file** that captures multiple readings and sentences for each word. Below is an overview:

### `vocab.yaml` (Nested Format)

Each entry in `vocab.yaml` is an object with the following structure:

```yaml
- word: <string>
  tags:
    - <string>
    - <string>
  readings:
    - reading: <string>
      expression_audio: <string> (optional)
      meaning:
        en: <string>
        de: <string> 
        # More language codes as needed
      sentences:
        - sentence: <string> (example sentence)
          sentence_kana: <string> (kana version of the sentence)
          sentence_audio: <string> (optional audio for the sentence)
          translations:
            en: <string> (translation of the sentence in English)
            de: <string> (translation of the sentence in German)
            # More language codes as needed
    - ... # More readings
- ... # More word objects
```
### Top-Level Fields

| Field | Type               | Description                                                                  |
|------ |--------------------|------------------------------------------------------------------------------|
| `word` | String            | The headword or dictionary form, e.g. 「ああ」 or 「開く」.                   |
| `tags` | List of Strings   | (Optional) Tags for categorizing or filtering in Anki (e.g., `JLPT_N5`).      |
| `readings` | List of Objects | One or more readings for this word (see below).                            |

---

## `readings` List

Each item in the `readings` array provides:

| Field              | Type               | Description                                                                                          |
|--------------------|--------------------|------------------------------------------------------------------------------------------------------|
| `reading`          | String             | Specific reading for the word, e.g. 「ああ」 or 「ひらく」.                                           |
| `expression_audio` | String (optional)  | Filename of the audio for this reading (e.g., `ああ.mp3`).                                           |
| `meaning`          | Dict               | Key-value pairs for each language code (e.g., `en`, `de`) to store the reading’s meaning.           |
| `sentences`        | List of Objects    | Zero or more example sentences (see below) illustrating this reading.                               |

---

## `sentences` List

Each sentence object may include:

| Field            | Type               | Description                                                                                          |
|------------------|--------------------|------------------------------------------------------------------------------------------------------|
| `sentence`       | String             | Example sentence in Japanese.                                                                        |
| `sentence_kana`  | String             | Kana version of the above sentence.                                                                  |
| `sentence_audio` | String (optional)  | Filename of the audio for this sentence (e.g., `ああ_sentence.mp3`).                                 |
| `translations`   | Dict               | Key-value pairs for each language code (e.g., `en`, `de`), storing the sentence’s translation.       |


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
