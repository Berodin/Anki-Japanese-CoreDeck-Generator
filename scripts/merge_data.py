import csv
import os

def merge_data(mother_tongue):
    # Load translations based on the mother tongue
    translations_file = f"data/translations_{mother_tongue}.csv"
    vocab_file = "data/vocab_jp.csv"

    if not os.path.exists(translations_file):
        print(f"Skip deck creation: No translation file found for '{mother_tongue}'.")
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
    with open(translations_file, encoding='utf-8') as trans_f:
        trans_reader = csv.DictReader(trans_f)
        for row in trans_reader:
            expression = row["expression"]
            if expression in vocab_data:
                vocab_entry = vocab_data[expression]
                # Combine vocab and translation data
                merged_entry = {
                    **vocab_entry,  # Add all vocab fields
                    "meaning": row["meaning"],  # Add meaning
                    "sentence_translation": row.get("sentence_translation", ""),  # Add sentence translation
                }
                merged_data.append(merged_entry)
            else:
                print(f"Warning: Expression '{expression}' in translations not found in vocab file.")

    # Save merged data
    output_file = f"data/merged_{mother_tongue}.csv"
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
