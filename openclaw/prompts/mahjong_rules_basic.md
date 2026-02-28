# Mahjong Rules (Basic, Universal)

This project only needs **universal basics** (not regional scoring / fan types).

## Core Concepts
- Tile groups:
  - Suits: Characters (万), Bamboos (条), Dots (筒)
  - Honors: Winds (东南西北), Dragons (中发白)
- Melds:
  - Chow (顺子): 3 consecutive in same suit
  - Pong (刻子): 3 identical tiles
  - Kong (杠): 4 identical tiles (optional)
- Basic winning shape (simplified): **4 melds + 1 pair**

## Coaching Heuristics (beginner-friendly)
- Early game: prioritize flexible sequences in suits
- Avoid keeping too many isolated honor tiles (unless you’re building a set)
- When uncertain, prefer tiles that can connect to neighbors (e.g., 2/3/4/5)

## Demo Simplification
We only classify two labels:
- `white_dragon` (白板) → default action: THROW
- `one_dot` (一筒/一饼) → default action: RETURN

Always explain in 1 sentence.
