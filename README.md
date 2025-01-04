# Japanese Vocabulary Anki Deck Generator

This project provides a Python-based system for generating custom Anki decks tailored for Japanese vocabulary learning. The system supports creating cards with various formats such as reading and listening, including features like clickable audio playback and image support.

## Features

- **Reading Cards**: Focus on recognizing vocabulary, their meanings, and example sentences.
- **Listening Cards**: Test your listening comprehension with audio playback for both expressions and example sentences.
- **Translation Cards** Test your translation skills by showing words in your native language for you to translate to japanese.
- **Dynamic Templates**: Easily customizable card layouts using HTML and CSS templates.
- **Robust Data Handling**: Allows incomplete entries (e.g., missing audio or images) while still generating functional cards.
- **Multi-language Support**: Translation files allow creating decks in multiple target languages.
- **Automated Deck Building**: Generate `.apkg` files ready for import into Anki.
- **CI/CD Integration**: GitHub Actions workflow for automated deck generation on new releases.

---

## Table of Contents

1. [Installation](#installation)
2. [Project Structure](#project-structure)
3. [How to Use](#how-to-use)
4. [Data Format](#data-format)
5. [Customization](#customization)
6. [Contributing](#contributing)
7. [License](#license)

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/japanese-vocab-deck-generator.git
   cd japanese-vocab-deck-generator
   ```

2. Install dependencies:
   ```bash
   pip install genanki
   ```

3. (Optional) Set up a virtual environment for Python:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

---

## Project Structure

```
.
├── data/
│   ├── vocab_jp.csv         # Japanese vocabulary data
│   ├── translations_{language codes}.csv  # Translations (e.g., de for German)
│   ├── audio/               # Audio files for expressions and sentences
│   └── images/              # Image files for vocabulary
├── output/                  # Generated Anki decks (.apkg)
├── scripts/
│   ├── generate_deck.py     # Script to generate Anki decks
│   ├── anki_model.py        # Defines Anki card model
│   └── merge_data.py        # Merges vocab and translation data
├── templates/
│   ├── back_listening.html  # Back template for listening cards
│   ├── back_reading.html    # Back template for reading cards
│   ├── front_listening.html # Front template for listening cards
│   ├── front_reading.html   # Front template for reading cards
│   ├── front_translation.html # Front template for translation cards
│   ├── back_translation.html # back template for translation cards
│   └── style.css            # Styling for Anki cards
├── .github/
│   └── workflows/
│       └── release.yml      # CI/CD workflow for automated deck generation
└── README.md
```

---

## How to Use

1. Prepare the `vocab_jp.csv` and corresponding translation files (e.g., `translations_de.csv`) in the `data/` folder.
2. Run the `generate_deck.py` script to create the decks:
   ```bash
   python scripts/generate_deck.py
   ```
3. The generated `.apkg` files will be saved in the `output/` folder.
4. Import the `.apkg` files into Anki to start using the decks.

---

## Data Format

### `vocab_jp.csv`
Contains the Japanese vocabulary data and details.

| Field             | Description                                    |
|-------------------|------------------------------------------------|
| `expression`      | The Japanese vocabulary word.                 |
| `reading`         | The reading of the vocabulary word in kana.   |
| `sentence`        | An example sentence using the vocabulary.     |
| `sentence_kana`   | The kana reading of the example sentence.     |
| `sentence_audio`  | (Optional) Audio file for the example sentence.|
| `expression_audio`| (Optional) Audio file for the expression.      |
| `image_uri`       | (Optional) Image file path for the vocabulary. |

### `translations_{language code}.csv`
Contains the translations for the respective language.

| Field             | Description                                    |
|-------------------|------------------------------------------------|
| `expression`      | The Japanese vocabulary word.                 |
| `meaning`         | The meaning of the word in the target language.|
| `sentence_translation` | The translation of the example sentence.    |

**Note**: All files must use consistent formatting.

---

## Customization

You can modify card templates in the `templates/` folder and the Python scripts in the `scripts/` folder to customize the output decks.

---

## Contributing

Contributions are welcome.

---

## License

This project is licensed under the MIT License.
