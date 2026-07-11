import argparse
import json
import os
import sys

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WORDS_ORDER_PATH = os.path.join(DATA_DIR, "words_order.json")
TARGETS_ORDER_PATH = os.path.join(DATA_DIR, "targets_order.json")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
WORDS_FILTERED_PATH = os.path.join(DATA_DIR, "words_order.json")
TARGETS_FILTERED_PATH = os.path.join(DATA_DIR, "targets_order.json")


def load_word2vec_bin(path, our_words_set):
    with open(path, "rb") as f:
        header = b""
        while True:
            b = f.read(1)
            if b == b"\n":
                break
            header += b
        parts = header.decode("utf-8").split()
        vocab_size = int(parts[0])
        dim = int(parts[1])
        print(f"Modèle: {vocab_size} mots, {dim} dims")

        word_to_vec = {}
        for i in range(vocab_size):
            wb = []
            while True:
                b = f.read(1)
                if b == b" ":
                    break
                wb.append(b)
            word = b"".join(wb).decode("utf-8", errors="replace").strip()
            vec = np.fromfile(f, dtype=np.float32, count=dim)
            if word in our_words_set:
                word_to_vec[word] = vec
            if (i + 1) % 20000 == 0:
                print(f"  Lecture: {i+1}/{vocab_size} (trouvé {len(word_to_vec)})")
        print(f"  Lecture: {vocab_size}/{vocab_size} (trouvé {len(word_to_vec)})")
        return word_to_vec, dim


def main():
    parser = argparse.ArgumentParser(
        description="Extract embeddings from word2vec binary model"
    )
    parser.add_argument("--w2v", required=True, help="Path to .bin word2vec model")
    args = parser.parse_args()

    with open(WORDS_ORDER_PATH, "r", encoding="utf-8") as f:
        all_words = json.load(f)
    with open(TARGETS_ORDER_PATH, "r", encoding="utf-8") as f:
        all_targets = json.load(f)

    print(f"Mots guessable: {len(all_words)}, targets: {len(all_targets)}")

    our_set = set(all_words)
    word_to_vec, dim = load_word2vec_bin(args.w2v, our_set)

    covered_words = [w for w in all_words if w in word_to_vec]
    covered_targets = [w for w in all_targets if w in word_to_vec]

    print(f"Mots couverts: {len(covered_words)} / {len(all_words)}")
    print(f"Targets couverts: {len(covered_targets)} / {len(all_targets)}")

    matrix = np.zeros((len(covered_words), dim), dtype=np.float32)
    missing = []
    for i, word in enumerate(covered_words):
        v = word_to_vec[word]
        if v.sum() == 0.0:
            missing.append(word)
        else:
            matrix[i] = v
        if (i + 1) % 10000 == 0:
            print(f"  Assemblage: {i+1}/{len(covered_words)}...")

    if missing:
        print(f"  Attention: {len(missing)} vecteurs nuls: {missing[:10]}...")

    matrix_float16 = matrix.astype(np.float16)
    np.save(EMBEDDINGS_PATH, matrix_float16)
    file_size = os.path.getsize(EMBEDDINGS_PATH)
    print(f"Matrice: {EMBEDDINGS_PATH} ({file_size / 1e6:.1f} Mo)")

    with open(WORDS_FILTERED_PATH, "w", encoding="utf-8") as f:
        json.dump(covered_words, f, ensure_ascii=False)
    with open(TARGETS_FILTERED_PATH, "w", encoding="utf-8") as f:
        json.dump(covered_targets, f, ensure_ascii=False)
    print(f"Listes filtrées sauvegardées: {len(covered_words)} mots, {len(covered_targets)} targets")

    print()
    print("⚠️  Ne pas oublier de supprimer le modèle word2vec !")


if __name__ == "__main__":
    main()
