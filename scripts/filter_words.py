import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "public", "data")

LEXIQUE_PATH = os.path.join(DATA_DIR, "Lexique4.tsv")
WORDS_ORDER_PATH = os.path.join(DATA_DIR, "words_order.json")
WORDS_PATH = os.path.join(PUBLIC_DATA_DIR, "words.json")

FREQ_MIN = 0.4
PREVAL_MIN = 90


def is_valid(row):
    cgram = row["5_Cgram"]
    nombre = row.get("8_Nombre", "")
    infover = row.get("9_InfoVER", "")
    genre = row.get("7_Genre", "")

    if cgram == "NOM" and nombre == "s":
        return True
    if cgram == "ADJ" and nombre in ("s", "", "i") and genre in ("m", "e", ""):
        return True
    if cgram == "VER" and infover == "inf":
        return True
    return False


def main():
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)

    words = {}
    with open(LEXIQUE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if not is_valid(row):
                continue
            mot = row["1_Mot"]
            try:
                freq = float(row["10_FreqMot"])
            except (ValueError, KeyError):
                freq = 0.0
            if mot not in words or freq > words[mot][0]:
                try:
                    preval = float(row["33_Preval"]) if row.get("33_Preval", "") else -1
                except (ValueError, KeyError):
                    preval = -1
                words[mot] = (freq, preval)

    # Filtre : fréquence minimale ET prévalence minimale
    filtered = [(mot, freq, preval) for mot, (freq, preval) in words.items()
                if freq >= FREQ_MIN and preval > PREVAL_MIN]

    # Tri : prévalence décroissante, puis fréquence décroissante
    filtered.sort(key=lambda x: (-x[2], -x[1]))
    top_words = [w[0] for w in filtered]

    with open(WORDS_ORDER_PATH, "w", encoding="utf-8") as f:
        json.dump(top_words, f, ensure_ascii=False)

    with open(WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(top_words, f, ensure_ascii=False)

    print(f"Filtre terminé : {len(top_words)} mots conservés sur {len(words)} uniques")
    print(f"  Critères : fréquence >= {FREQ_MIN} ET prévalence > {PREVAL_MIN}%")
    print(f"  Dernier mot : {top_words[-1]}" if top_words else "  Liste vide")
    print(f"  → {WORDS_ORDER_PATH}")
    print(f"  → {WORDS_PATH}")


if __name__ == "__main__":
    main()
