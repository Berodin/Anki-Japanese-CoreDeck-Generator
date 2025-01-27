import genanki
import csv
import os
from merge_data import merge_data
from anki_model import get_reading_model, get_translation_model, get_listening_model

def sanitize_tags(tags):
    """Ersetzt Leerzeichen in Tags durch Unterstriche und bereinigt sie."""
    return [tag.replace(" ", "_").strip() for tag in tags]

def create_deck(lc):
    merged_file = merge_data(lc)
    if not merged_file:
        print(f"Skip deck creation: No merged file found for '{lc}'.")
        return 

    reading_listening_model_id = 1607392319
    translation_model_id = 1607392320 
    listening_model_id = 1607392321

    reading_model  = get_reading_model(reading_listening_model_id, lc)
    translation_model = get_translation_model(translation_model_id, lc)
    listening_model = get_listening_model(listening_model_id, lc)

    deck = genanki.Deck(reading_listening_model_id, f'Japanese Vocab Deck ({lc})')
    package = genanki.Package(deck)

    # Add data
    with open(merged_file, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:

            tags = row.get("tags", "").split(";") if "tags" in row else []
            tags = sanitize_tags(tags)
            guid = genanki.guid_for(row['expression'] + row['reading'])

            # Reading Card
            reading_fields = [
                row['expression'],
                row['meaning'],
                row['reading'],
                row['sentence'],
                row['sentence_kana'],
                row.get('sentence_translation', ''),  # optional
                f'[sound:{row["sentence_audio"]}]' if row['sentence_audio'] else '',  # optional
                f'[sound:{row["expression_audio"]}]' if row['expression_audio'] else '',  # optional
                row["image_uri"] if row["image_uri"] else ''  # optional
            ]
            reading_note = genanki.Note(
                model=reading_model,
                fields=reading_fields,
                tags=tags,
                guid=guid
            )
            deck.add_note(reading_note)

            # Listening Card (only if ExpressionAudio is provided)
            if row["expression_audio"]:
                listening_fields = [
                    row['expression'],
                    row['meaning'],
                    row['reading'],
                    row['sentence'],
                    row['sentence_kana'],
                    row.get('sentence_translation', ''),  # optional
                    f'[sound:{row["sentence_audio"]}]' if row['sentence_audio'] else '',  # optional
                    f'[sound:{row["expression_audio"]}]',  
                    row["image_uri"] if row["image_uri"] else ''  # optional
                ]
                listening_note = genanki.Note(
                    model=listening_model,
                    fields=listening_fields,
                    tags=tags,
                    guid=guid
                )
                deck.add_note(listening_note)
            # Translation Card
            if row.get("meaning") and row.get("sentence_translation"):
                translation_fields = [
                    row['meaning'],
                    row.get('sentence_translation', ''),
                    row['expression'],
                    row['reading'],
                    row['sentence'],
                    row['sentence_kana'],
                    f'[sound:{row["sentence_audio"]}]' if row['sentence_audio'] else '',  # optional
                    f'[sound:{row["expression_audio"]}]' if row['expression_audio'] else '',  # optional
                    row['image_uri'] if row['image_uri'] else ''  # optional
                ]
                translation_note = genanki.Note(
                    model=translation_model,
                    fields=translation_fields,
                    tags=tags,
                    guid=guid
                )
                deck.add_note(translation_note)

            # Add media files
            if row["sentence_audio"]:
                sentence_audio_path = f"data/audio/{row['sentence_audio']}"
                if os.path.exists(sentence_audio_path):
                    package.media_files.append(sentence_audio_path)
                else:
                    print(f"Warning: Audio file not found: {sentence_audio_path}")

            if row["expression_audio"]:
                expression_audio_path = f"data/audio/{row['expression_audio']}"
                if os.path.exists(expression_audio_path):
                    package.media_files.append(expression_audio_path)
                else:
                    print(f"Warning: Audio file not found: {expression_audio_path}")

            if row["image_uri"]:
                image_path = f"data/images/{row['image_uri']}"
                if os.path.exists(image_path):
                    package.media_files.append(image_path)
                else:
                    print(f"Warning: Image file not found: {image_path}")

    # Save deck
    os.makedirs("output", exist_ok=True)
    output_file = f'output/japanese_coredeck_{lc}.apkg'
    package.write_to_file(output_file)
    print(f"Deck created: {output_file}")

if __name__ == "__main__":
    create_deck("de")
    create_deck("en")
