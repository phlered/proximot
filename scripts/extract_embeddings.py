"""
Extraction unique des embeddings fastText → matrice float16.

Usage :
  1. Télécharger cc.fr.300.bin depuis https://fasttext.cc/docs/en/crawl-vectors.html
  2. pip install gensim numpy
  3. python scripts/extract_embeddings.py --fasttext /chemin/vers/cc.fr.300.bin

Après extraction, supprimer cc.fr.300.bin (~2 Go).
"""

import argparse
import json
import os
import sys

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WORDS_ORDER_PATH = os.path.join(DATA_DIR, "words_order.json")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")


def main():
    parser = argparse.ArgumentParser(description="Extract embeddings from fastText")
    parser.add_argument(
        "--fasttext", required=True, help="Path to cc.fr.300.bin"
    )
    parser.add_argument(
        "--dims", type=int, default=300, help="Vector dimensions (default: 300)"
    )
    args = parser.parse_args()

    from gensim.models.fasttext import load_facebook_model

    print("Chargement du modèle fastText (~2 Go)...")
    model = load_facebook_model(args.fasttext)

    print("Chargement de la liste des mots...")
    with open(WORDS_ORDER_PATH, "r", encoding="utf-8") as f:
        words = json.load(f)

    print(f"Extraction des vecteurs pour {len(words)} mots...")
    vocab = model.wv
    dims = args.dims
    matrix = np.zeros((len(words), dims), dtype=np.float32)
    found = 0
    missing = []

    for i, word in enumerate(words):
        if word in vocab:
            matrix[i] = vocab[word]
            found += 1
        else:
            missing.append(word)

    if missing:
        print(
            f"  Attention : {len(missing)} mots non trouvés dans fastText: "
            f"{missing[:10]}..."
        )

    print(f"  {found}/{len(words)} vecteurs extraits")

    matrix_float16 = matrix.astype(np.float16)
    np.save(EMBEDDINGS_PATH, matrix_float16)
    file_size = os.path.getsize(EMBEDDINGS_PATH)
    print(f"Matrice sauvegardée : {EMBEDDINGS_PATH} ({file_size / 1e6:.1f} Mo)")

    print()
    print("⚠️  Ne pas oublier de supprimer cc.fr.300.bin (~2 Go) !")


if __name__ == "__main__":
    main()
