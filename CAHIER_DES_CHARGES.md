# Cahier des charges — Jeu de mots type Cemantix (Proximot)

## 1. Concept

Un jeu quotidien où le joueur doit deviner **12 mots secrets** répartis en **3 parties de 4 mots** (contre 1 dans Cemantix). Pour chaque mot secret, le joueur propose des mots et reçoit un **score de proximité sémantique** (0–1000). L'objectif est de trouver les 12 mots avec le moins de tentatives possible.

---

## 2. Sources de données

### 2.1 Lexique 4 (déjà disponible)
- Fichier : `data/Lexique4.tsv`
- ~190 000 formes fléchies du français
- Colonnes utilisées :
  - `1_Mot` — forme orthographique
  - `5_Cgram` — catégorie grammaticale (`NOM`, `ADJ`, `VER`)
  - `7_Genre` — genre (`m`, `f`, `e` pour adjectifs épicènes)
  - `8_Nombre` — nombre (`s` singulier, `p` pluriel)
  - `9_InfoVER` — info verbe (`inf` = infinitif)
  - `10_FreqMot` — fréquence (corpus sous-titres, 316M mots)

### 2.2 Vecteurs sémantiques (embeddings)
- **Modèle** : fastText français (`cc.fr.300.bin` — Facebook, ~2 Go)
- **Stockage final** : matrice `data/embeddings.npy` en **float16** (~9 700 × 300 = **~6 Mo**)
- **Extraction** : faite **une seule fois en local**, puis le fichier fastText (~2 Go) est **effacé** (ne doit pas être commité)

---

## 3. Filtrage et classement des mots

### 3.1 Critères de filtrage
On conserve uniquement les mots correspondant à ces critères grammaticaux :

| Catégorie | Code Cgram | Genre     | Nombre         | Condition          |
|-----------|------------|-----------|----------------|--------------------|
| Noms      | `NOM`      | —         | `s` (singulier)| —                  |
| Adjectifs | `ADJ`      | `m` ou `e` | `s`, `i` ou vide | qualificatifs masc. |
| Verbes    | `VER`      | —         | —              | `InfoVER == inf`   |

⚠️ Un même mot peut avoir plusieurs lignes (ex. `NOM,VER`, `NOM,ADJ`). On dédoublonne par `1_Mot`.

### 3.2 Filtre qualité (prévalence + fréquence)
Deux seuils supplémentaires pour garantir que les mots sont connus du grand public :

| Critère        | Colonne Lexique  | Seuil retenu       |
|----------------|------------------|--------------------|
| **Prévalence** | `33_Preval`      | `> 90%`            |
| **Fréquence**  | `10_FreqMot`     | `>= 0.4`           |

- **Prévalence** : % de locuteurs qui connaissent le mot (enquête lexicale)
- **Fréquence** : apparitions dans le corpus de sous-titres (316M mots)

### 3.3 Classement final
Les mots retenus sont triés par **prévalence décroissante** puis **fréquence décroissante** (départage). Il n'y a pas de limite de taille : le double filtre définit seul la liste.

### 3.4 Effectifs
| Filtre                            | Nombre de mots |
|-----------------------------------|:--------------:|
| Critères grammaticaux             | ~49 800        |
| + prévalence > 90% ET freq ≥ 0.4 | **~9 700**     |

---

### ⚠️ IMPORTANT — Procédure d'extraction des embeddings (une seule fois)

1. Télécharger `cc.fr.300.bin` depuis [fastText](https://fasttext.cc/docs/en/crawl-vectors.html) (~2 Go)
2. Extraire les vecteurs float16 pour les ~9 700 mots filtrés → `data/embeddings.npy`
3. **Effacer impérativement `cc.fr.300.bin`** — ce fichier ne doit **jamais** être commité dans le repo
4. Le script `scripts/generate_daily.py` utilise uniquement `data/embeddings.npy` (~6 Mo)

---

## 4. Mécanique de jeu

### 4.1 Parties et mots
- **3 parties par jour**, chacune avec **4 mots secrets** (12 mots au total)
- Les parties sont indépendantes : le joueur choisit laquelle commencer
- Chaque partie a sa propre seed pour le tirage

### 4.2 Interface d'ensemble
Le joueur voit les **4 emplacements anonymes** de la partie en cours (numérotés 1 à 4) :

```
┌──────────────────────────────┐
│ Partie 1/3   Mot ? ___ [►]   │
│                              │
│ 1: ▓▓▓▓▓▓▓░░░ 89%  57%     │
│ 2: ▓░░░░░░░░░░  8%   3%     │
│ 3: ▓▓▓▓▓▓▓▓░░ 81%  42%     │
│ 4: ▓▓░░░░░░░░░ 32%  11%     │
│                              │
│ ── Historique ──             │
│ table                        │
│   🔥89%  🥶3%  🔥81% 🥵32% │
│ chaise                       │
│   🔥57%  🥶8%  🔥42% 🥵11% │
└──────────────────────────────┘
```

Chaque ligne de la zone haute affiche :
- **Numéro** du mot secret
- **Barre de progression** : meilleur score atteint
- **Chiffre** : meilleur score
- **Chiffre** : score du dernier essai pour ce mot

Chaque ligne d'historique affiche :
- **Mot proposé**
- **Retour à la ligne**
- **Les 4 scores** du mot proposé, avec une pastille de couleur (dégradé froid↔chaud) et le pourcentage

### 4.3 Vue détaillée
Appui sur une barre (ou un numéro) → vue détaillée classique à la Cemantix pour ce mot :
- Liste complète des essais déjà faits pour ce mot, classés du plus chaud au plus froid avec °C et ‰

### 4.4 Enchaînement des parties
- Pas d'onglets : le joueur commence par la **partie 1**
- Une fois les 4 mots trouvés (ou abandon), un bouton **"Nouvelle Partie"** apparaît
- Lancement de la **partie 2**, puis **partie 3**
- Si le joueur tente de lancer une 4e partie : message *"Reviens demain pour une nouvelle partie !"*

### 4.5 Écran d'accueil (règles)
Au premier chargement de la journée, un écran présente les règles :
- **Bouton "Jouer !"** placé **en haut** de l'écran (pas besoin de scroller si on connaît déjà)
- Règres en dessous pour les nouveaux joueurs
- L'écran ne s'affiche qu'une fois par jour (mémorisé via localStorage)

### 4.6 Historique des jours précédents
En bas de l'écran d'accueil (ou accessible depuis un lien) :
- Affichage des **mots secrets des 2-3 derniers jours**
- Permet au joueur de se faire une idée du style et de la difficulté des mots
- Exemple :
  ```
  ── Jours précédents ──
  Hier (07/07) : chaise, peinture, douceur, escalader
  Avant-hier (06/07) : nuage, fragile, chanter, horizon
  ```

## 5. Cycle quotidien (GitHub Action)

Déclencheur : **tous les jours à 2h00** (`cron: "0 2 * * *"`)

### 5.1 Étapes de l'action

```
1. Cloner le repo
2. Installer Python + dépendances (numpy)
3. Exécuter le script de génération :
   a. Charger les 40 000 mots + matrice embeddings (data/embeddings.npy)
   b. Tirer 12 mots secrets : 3 parties × 4 mots (seed = date + index de partie)
   c. Pour chaque mot secret, calculer la similarité cosinus avec les 40 000 mots
   d. Garder le top 1000 par mot
   e. Écrire un fichier binaire au format compressé
   f. Mettre à jour index.json
4. Committer et pusher les fichiers générés
```

### 5.2 Algorithme de tirage
- **Seed pseudo-aléatoire** : `hash(date + partie)` garantit reproductibilité
- Vérification : pas de doublon entre les 12 mots du jour ni avec les mots des 2 jours précédents

### 5.3 Format de stockage (binaire compressé)

**`public/data/words.json`** (généré une fois, 40 000 mots dans l'ordre) :
```json
["abaisser", "abandon", "abeille", ..., "zythum"]
```

**`public/data/YYYY-MM-DD.bin`** (fichier binaire quotidien) :
- `Uint16Array` plat pour chaque partie :
  - 4 blocs (un par mot secret)
  - Chaque bloc : `index:uint16 (0-39999) + score:uint16 (0-10000) × 1000`
  - Soit 4 × 1000 × 4 octets = 16 Ko par partie
- 3 parties = **48 Ko par jour** (~17 Mo/an)

### 5.4 Index des jours disponibles

`public/data/index.json` :
```json
[
  {"date": "2026-07-08", "parts": 3},
  {"date": "2026-07-07", "parts": 3}
]
```

---

## 6. Pipeline de données (synthèse)

```
Lexique4.tsv
    │
    ▼
[ Filtre grammaire : NOM(s) / ADJ(m/e) / VER(inf) ]
    │
    ▼
[ Filtre qualité : prévalence > 90% ET fréquence ≥ 0.4 ]
    │
    ▼
[ data/words_order.json ] ──── ~9 700 mots
    │
[ cc.fr.300.bin ~2 Go ]     │
    │  (local, 1 fois)      │
    ▼                        │
[ data/embeddings.npy ~6 Mo ]   │  ← float16
    │  (pusher dans le repo) │
    │                        │
[ Tirage : 3 parties × 4 mots ] ← seed = date (uniforme, pas pondéré)
    │                        │
    ▼                        ▼
[ Calcule 12 × ~9 700 similarités → top 1000 ]
    │
    ▼
[ public/data/YYYY-MM-DD.bin ] → GitHub Pages
```

**Important :** Le fichier `cc.fr.300.bin` (~2 Go) est téléchargé localement pour l'extraction initiale, puis **effacé**. Il n'est jamais dans le repo. La GitHub Action charge directement `embeddings.npy` (~6 Mo, float16).

---

## 7. Définition de la proximité sémantique

- **Métrique** : similarité cosinus entre vecteurs de mots
- **Top 1000** : on conserve les 1000 mots les plus proches pour chaque mot secret
- **Score 0** : tout mot hors du top 1000 reçoit un score de 0 (le joueur ne voit pas la différence)
- **Normalisation** : linéaire de [cos_min, cos_max] vers [0, 1000]

---

## 8. Architecture du frontend (GitHub Pages)

### 8.1 Stack
- **HTML / CSS / JS vanilla** (pas de framework)
- Déploiement via GitHub Pages depuis `public/`

### 8.2 Thème visuel
- **Mode sombre par défaut** : fond noir (`#0a0a0f`), accents bleu nuit (`#1a1a3e`, `#2a2a5e`)
- Scores : dégradé du 🧊 froid (bleu foncé) au 🔥 chaud (rouge/orange)
- Police : sans-serif, confortable en mobile

### 8.3 Pages

| Route          | Description                           |
|----------------|---------------------------------------|
| `/`            | Écran d'accueil (règles) + jeu du jour |
| `/archive`     | Jours précédents (mots secrets)       |

### 8.4 Écran d'accueil
- Bouton **"Jouer !"** en haut, immédiatement visible sans scroll
- Règles du jeu en dessous (pour les nouveaux joueurs)
- Ne s'affiche qu'une fois par jour (localStorage)
- En bas : historique des mots des 2-3 derniers jours

### 8.5 Normalisation de la saisie (tolérance maximale)

Avant la recherche dans le dictionnaire, la saisie est normalisée ainsi :

1. **Minuscule** → `Joli`, `JOLI`, `joli` → `joli`
2. **Accents supprimés** → `mère`, `MÈRE`, `mere` → `mere`
3. **Trait d'union accepté** → `pense-bête`, `pense-bete`, `PENSE-BETE` → `pense-bete`
4. **Espace transformé en trait d'union** → `pense bete`, `pense bête` → `pense-bete`
5. **Collé sans séparateur** → `pensebete` → pas de correspondance (respect de l'orthographe)

### 8.6 Fonctionnalités frontend
- Chargement du fichier binaire via `fetch` + `arrayBuffer` + `Uint16Array`
- Décodage : `score = raw / 10000 * 1000` ; `mot = words[index]`
- Autocomplétion sur les 40 000 mots (depuis `words.json`)
- Barres horizontales avec animation de remplissage
- Pastilles de couleur pour les scores dans l'historique
- Vue détaillée (appui sur un mot secret)
- Bouton "Nouvelle Partie" après avoir fini ou abandonné une partie
- Message de fin : "Reviens demain !" après la 3e partie

### 8.7 Performances
- Décodage du binaire : < 1 ms
- Recherche du score d'un mot proposé : O(log n) via `words.indexOf` simplifié ou `Map`

---

## 9. Dépendances techniques

### GitHub Action
- Python 3.11+
- `numpy` (chargement de la matrice, calculs de similarité)

### Frontend
- Aucune dépendance externe
- Pas de bundler, vanilla JS

---

## 10. Contraintes et limites

| Contrainte                | Solution                                                           |
|---------------------------|--------------------------------------------------------------------|
| Taille des embeddings     | `embeddings.npy` en float16 = **~6 Mo** dans le repo              |
| Limite GitHub Pages       | 1 Go par dépôt ; ~17 Mo/an pour les `.bin` → infime               |
| Stockage repo             | 6 Mo (embeddings) + ~17 Mo/an (données) → très confortable         |
| Temps d'exécution Action  | < 1 min (simple chargement numpy + calcul 12 × ~10k)              |
| Extraction initiale       | Une fois en local ; supprimer `cc.fr.300.bin` (~2 Go) après       |
| Mise à jour des données   | Annuelle via nouvelle version de Lexique                           |

---

## 11. Améliorations futures (v2)

- Statistiques personnelles (localStorage)
- Partage d'une partie spécifique (mode défi)
- Animations et thème sombre
- PWA (Progressive Web App)

---

## 12. Arborescence proposée

```
proximot/
├── .github/
│   └── workflows/
│       └── daily-generate.yml     # GitHub Action cron
├── data/
│   ├── Lexique4.tsv               # Données lexicales (inchangé)
│   ├── embeddings.npy             # Matrice float16 40k×300 (~23 Mo)
│   └── words_order.json           # 40 000 mots dans l'ordre des lignes
├── scripts/
│   ├── filter_words.py            # Filtre + classement des 40k mots
│   ├── extract_embeddings.py      # Extraction locale (1 fois) depuis fastText
│   └── generate_daily.py          # Tirage + calcul des scores
├── public/
│   ├── index.html                 # Page principale du jeu
│   ├── archive.html               # Calendrier des jours passés
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── game.js
│   └── data/
│       ├── index.json             # Index des dates disponibles
│       ├── words.json             # 40 000 mots (autocomplétion)
│       └── YYYY-MM-DD.bin         # Données quotidiennes (48 Ko)
└── README.md
```

---

*Document créé le 08/07/2026*

**Décisions validées :**
- 3 parties × 4 mots par jour (12 mots)
- Dictionnaire : double filtre prévalence > 90% ET fréquence ≥ 0,4 → ~9 700 mots
- Tri : prévalence ↓ puis fréquence ↓ ; tirage uniforme (non pondéré)
- Top 1000 similarités stocké par mot (score 0 si hors top)
- Format binaire Uint16 → 48 Ko/jour (~17 Mo/an)
- Embeddings float16 → `data/embeddings.npy` (~6 Mo, dans le repo)
- Extraction fastText locale unique, suppression de `cc.fr.300.bin` (~2 Go) après usage
- Vue compacte : 4 barres + meilleur score + dernier score
- Historique : mot + retour à la ligne + 4 pastilles de score
- Pas d'onglets : bouton "Nouvelle Partie" après chaque partie
- Écran d'accueil avec bouton "Jouer !" en haut, règles en dessous
- Historique des mots des 3 derniers jours visible
- Mode sombre (noir + bleu nuit)
- Saisie tolérante : minuscule, accents supprimés, espaces → tirets
- Normalisation des mots du dictionnaire : minuscule, sans accents, espaces → tirets
