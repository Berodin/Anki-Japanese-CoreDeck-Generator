import csv
import os

def merge_data(lc):
    # Load translations based on the mother tongue
    translations_file = f"data/translations_{lc}.csv"
    vocab_file = "data/vocab_jp.csv"

    if not os.path.exists(translations_file):
        print(f"Skip deck creation: No translation file found for '{lc}'.")
        return None
    if not os.path.exists(vocab_file):
        raise FileNotFoundError(f"Vocabulary file not found: {vocab_file}")

    # Load vocab data into a dictionary
    vocab_data = {}
    with open(vocab_file, encoding='utf-8') as vocab_f:
        vocab_reader = csv.DictReader(vocab_f)
        for row in vocab_reader:
            vocab_data[row["expression"]] = row

    # Merge vocab data with translations
    merged_data = []
    used_vocab = set()
    with open(translations_file, encoding='utf-8') as trans_f:
        trans_reader = csv.DictReader(trans_f)
        for row in trans_reader:
            expression = row["expression"]
            if expression in vocab_data:
                used_vocab.add(expression)
                vocab_entry = vocab_data[expression]
                # Combine vocab and translation data
                merged_entry = {
                    **vocab_entry,  # Add all vocab fields
                    "meaning": row["meaning"],  # Add meaning
                    "sentence_translation": row.get("sentence_translation", ""),  # Add sentence translation
                    "tags": vocab_entry.get("tags", "")
                }
                merged_data.append(merged_entry)
            else:
                print(f"Warning: Expression '{expression}' in translations not found in vocab file.")

   # Find vocab expressions not in translations
    unused_vocab = set(vocab_data.keys()) - used_vocab
    if unused_vocab:
        print(f"Warning: The following expressions are in vocab but not in translations: {', '.join(unused_vocab)}")

    # Save merged data
    output_file = f"data/merged_{lc}.csv"
    if merged_data:  # Only save if there is data
        with open(output_file, "w", encoding='utf-8', newline='') as f:
            fieldnames = list(merged_data[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged_data)
        print(f"Merged data saved: {output_file}")
        return output_file
    else:
        print("No merged data to save.")
        return None
