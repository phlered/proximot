"""
Génération quotidienne des parties.

Usage (GitHub Action) :
  python scripts/generate_daily.py

Charge :
  - words_order.json (tous les mots proposables)
  - targets_order.json (mots à trouver, sous-ensemble)
  - embeddings.npy (vecteurs pour tous les mots proposables)

Génère 3 parties × 4 mots tirés depuis targets_order.json,
calcule les top 1000 similarités contre tous les mots proposables,
écrit le .bin et met à jour index.json.
"""

import hashlib
import json
import os
import random
import struct

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "public", "data")

WORDS_ORDER_PATH = os.path.join(DATA_DIR, "words_order.json")
TARGETS_ORDER_PATH = os.path.join(DATA_DIR, "targets_order.json")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
INDEX_PATH = os.path.join(PUBLIC_DATA_DIR, "index.json")

NUM_PARTS = 3
TARGETS_PER_PART = 4
TOP_K = 1000
MAGIC = 0x5058
VERSION = 1


def seed_from_date(date_str: str, part: int) -> int:
    key = f"{date_str}-p{part}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def pick_targets(targets: list, date_str: str, part: int) -> list:
    rng = random.Random(seed_from_date(date_str, part))
    return rng.sample(targets, TARGETS_PER_PART)


def main():
    print("Chargement des mots proposables...")
    with open(WORDS_ORDER_PATH, "r", encoding="utf-8") as f:
        all_words = json.load(f)

    print("Chargement des mots à trouver...")
    with open(TARGETS_ORDER_PATH, "r", encoding="utf-8") as f:
        target_words = json.load(f)

    # Map target words to their indices in the full guessable list
    word_to_idx = {w: i for i, w in enumerate(all_words)}
    target_indices = [word_to_idx[w] for w in target_words]

    print("Chargement des embeddings...")
    matrix = np.load(EMBEDDINGS_PATH).astype(np.float32)

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix_normed = matrix / norms

    today = __import__("datetime").date.today().isoformat()
    print(f"Date : {today}")

    bin_path = os.path.join(PUBLIC_DATA_DIR, f"{today}.bin")
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)

    all_target_indices = set()
    prev_dates = []
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            prev = json.load(f)
            prev_dates = [p["date"] for p in prev[-2:]]
        for pd in prev_dates:
            prev_bin = os.path.join(PUBLIC_DATA_DIR, f"{pd}.bin")
            if os.path.exists(prev_bin):
                with open(prev_bin, "rb") as f:
                    data = f.read()
                offset = 4
                for _p in range(NUM_PARTS):
                    for _t in range(TARGETS_PER_PART):
                        idx = struct.unpack_from("<H", data, offset)[0]
                        all_target_indices.add(idx)
                        offset += 2 + TOP_K * 4

    buf = bytearray()
    buf += struct.pack("<HBB", MAGIC, VERSION, NUM_PARTS)

    for part in range(NUM_PARTS):
        for attempt in range(100):
            candidates = pick_targets(target_words, today, part + attempt * 10)
            c_indices = [word_to_idx[c] for c in candidates]
            if all(i not in all_target_indices for i in c_indices):
                break

        for i, w in enumerate(candidates):
            print(f"  Partie {part + 1}, mot {i + 1} : {w} (idx {c_indices[i]})")

        all_target_indices.update(c_indices)

        for t_idx in c_indices:
            vec = matrix_normed[t_idx]
            sims = matrix_normed @ vec
            top_indices = np.argpartition(-sims, TOP_K)[:TOP_K]
            top_scores = sims[top_indices]
            sorted_order = np.argsort(-top_scores)
            top_indices = top_indices[sorted_order]
            top_scores = top_scores[sorted_order]

            sim_min = top_scores[-1]
            sim_max = top_scores[0]
            sim_range = sim_max - sim_min
            if sim_range == 0:
                scores_normalized = [1000] * TOP_K
            else:
                scores_normalized = ((top_scores - sim_min) / sim_range * 1000).astype(
                    np.uint16
                )

            buf += struct.pack("<H", t_idx)
            for idx_val, sc_val in zip(top_indices, scores_normalized):
                buf += struct.pack("<HH", int(idx_val), int(sc_val))

    with open(bin_path, "wb") as f:
        f.write(buf)

    file_size = len(buf)
    print(f"\nFichier généré : {bin_path} ({file_size} octets, {file_size / 1024:.1f} Ko)")

    index = []
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index = json.load(f)

    index.append({"date": today, "parts": NUM_PARTS})
    index = index[-365:]

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

    print(f"Index mis à jour : {INDEX_PATH} ({len(index)} entrées)")


if __name__ == "__main__":
    main()
