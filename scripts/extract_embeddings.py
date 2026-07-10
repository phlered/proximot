import argparse
import json
import os
import sys

import fasttext
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WORDS_ORDER_PATH = os.path.join(DATA_DIR, "words_order.json")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")


def main():
    parser = argparse.ArgumentParser(description="Extract embeddings from fastText")
    parser.add_argument("--fasttext", required=True, help="Path to cc.fr.300.bin")
    parser.add_argument("--dims", type=int, default=300, help="Vector dimensions (default: 300)")
    args = parser.parse_args()

    print("Chargement du modèle fastText (~2 Go)...")
    sys.stdout.flush()
    model = fasttext.load_model(args.fasttext)

    print("Chargement de la liste des mots...")
    with open(WORDS_ORDER_PATH, "r", encoding="utf-8") as f:
        words = json.load(f)

    print(f"Extraction des vecteurs pour {len(words)} mots...")
    dims = args.dims
    matrix = np.zeros((len(words), dims), dtype=np.float32)
    missing = []

    for i, word in enumerate(words):
        v = model.get_word_vector(word)
        if v.sum() == 0.0:
            missing.append(word)
        else:
            matrix[i] = v
        if (i + 1) % 10000 == 0:
            print(f"  {i+1}/{len(words)}...")

    if missing:
        print(f"  Attention : {len(missing)} mots avec vecteur nul: {missing[:10]}...")

    print(f"  {len(words) - len(missing)}/{len(words)} vecteurs extraits")

    matrix_float16 = matrix.astype(np.float16)
    np.save(EMBEDDINGS_PATH, matrix_float16)
    file_size = os.path.getsize(EMBEDDINGS_PATH)
    print(f"Matrice sauvegardée : {EMBEDDINGS_PATH} ({file_size / 1e6:.1f} Mo)")

    print()
    print("⚠️  Ne pas oublier de supprimer cc.fr.300.bin (~2 Go) !")


if __name__ == "__main__":
    main()
