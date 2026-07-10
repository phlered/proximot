import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "public", "data")

LEXIQUE_PATH = os.path.join(DATA_DIR, "Lexique4.tsv")
WORDS_ORDER_PATH = os.path.join(DATA_DIR, "words_order.json")
GUESS_WORDS_PATH = os.path.join(PUBLIC_DATA_DIR, "words.json")
TARGETS_ORDER_PATH = os.path.join(DATA_DIR, "targets_order.json")

FREQ_MIN = 0.4
PREVAL_MIN = 90

STRICT_PLURAL_OVERRIDES = {"vacances"}


def is_valid_target(row):
    cgram = row["5_Cgram"]
    nombre = row.get("8_Nombre", "")
    infover = row.get("9_InfoVER", "")
    genre = row.get("7_Genre", "")

    if cgram == "NOM" and nombre in ("s", "i"):
        return True
    if cgram == "ADJ" and nombre in ("s", "", "i") and genre in ("m", "e", ""):
        return True
    if cgram == "VER" and "inf" in infover.split(","):
        return True
    return False


def is_valid_guessable(row):
    cgram = row["5_Cgram"]
    nombre = row.get("8_Nombre", "")
    infover = row.get("9_InfoVER", "")
    genre = row.get("7_Genre", "")

    if cgram == "NOM" and nombre in ("s", "i"):
        return True
    if cgram == "NOM" and nombre == "p" and row.get("14_IsLem", "") == "1":
        return True
    if cgram == "ADJ" and nombre in ("s", "", "i") and genre in ("m", "e", ""):
        return True
    if cgram == "VER" and "inf" in infover.split(","):
        return True
    return False


def main():
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)

    guessable_words = {}
    target_words = {}

    with open(LEXIQUE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            mot = row["1_Mot"]
            try:
                freq = float(row["10_FreqMot"])
            except (ValueError, KeyError):
                freq = 0.0
            try:
                preval = float(row["33_Preval"]) if row.get("33_Preval", "") else -1
            except (ValueError, KeyError):
                preval = -1

            if is_valid_guessable(row) or mot in STRICT_PLURAL_OVERRIDES:
                if mot not in guessable_words or freq > guessable_words[mot][0]:
                    guessable_words[mot] = (freq, preval)

            if is_valid_target(row):
                if mot not in target_words or freq > target_words[mot][0]:
                    target_words[mot] = (freq, preval)

    # --- Liste 1 : tous les mots proposables ---
    guessable = sorted(guessable_words.keys(), key=lambda w: -guessable_words[w][0])
    with open(WORDS_ORDER_PATH, "w", encoding="utf-8") as f:
        json.dump(guessable, f, ensure_ascii=False)
    with open(GUESS_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(guessable, f, ensure_ascii=False)

    # --- Liste 2 : mots à trouver (double filtre prévalence + fréquence) ---
    targets = [(mot, freq, preval) for mot, (freq, preval) in target_words.items()
               if freq >= FREQ_MIN and preval > PREVAL_MIN]
    targets.sort(key=lambda x: (-x[2], -x[1]))
    target_words_list = [t[0] for t in targets]

    with open(TARGETS_ORDER_PATH, "w", encoding="utf-8") as f:
        json.dump(target_words_list, f, ensure_ascii=False)

    print(f"Liste proposable : {len(guessable)} mots (filtre grammaire élargi)")
    print(f"  → {WORDS_ORDER_PATH}")
    print(f"  → {GUESS_WORDS_PATH}")
    print(f"Liste à trouver  : {len(target_words_list)} mots (grammaire + preval > {PREVAL_MIN}% + freq >= {FREQ_MIN})")
    print(f"  → {TARGETS_ORDER_PATH}")


if __name__ == "__main__":
    main()
