# Draft Skill v0 — Mahjong Brain (Discord Input → Mac Hub Actions)

> Scope for Hackathon MVP:
> - Learn **basic universal Mahjong rules** (explain + coach)
> - Integrate **two demo scenes**:
>   - If **white_dragon** (白板) → **throw** (Scene A)
>   - If **one_dot** (一饼/一筒) → **return** + optional follow-up action
>
> OpenClaw (EC2) is the **decision owner**.
> Mac Local Hub is the **I/O owner**.

---

## 1) Command Surface (Discord)

Recommended namespace:
- `/mj start`
- `/mj scene A|B`
- `/mj style polite|meme`
- `/mj safe on|off`
- `/mj explain <topic>` (rules explainer)
- `/mj coach` (give coaching tips)
- `/mj status`
- `/mj stop`
- `/mj estop`

---

## 2) Brain State (minimal memory)

Store per-session:
- `style`: polite|meme
- `safe`: bool
- `session_id`: string
- `last_label`: white_dragon|one_dot

Optional (coach mode):
- `known_tiles_context`: user-provided hints (e.g., “I have 2&3 dots”)

---

## 3) External APIs

### 3.1 Mac Hub (FastAPI)
- `POST /session/start` → `{ session_id }`
- `POST /run_scene` `{ scene:A|B, style, safe }`
- `POST /brain/decision` `{ session_id, action:throw|return, line_key, ui_text, sfx? }`
- `GET  /status`
- `POST /estop`

> For MVP, we can do: `start → run_scene` only.
> The `brain/decision` path is the “Brain showcases personalization” path.

---

## 4) Decision Logic (MVP)

When recognition arrives:
- label == `white_dragon` → action = `throw` (Scene A)
- label == `one_dot` → action = `return` (Scene B)

Explainability (what to say):
- white_dragon: “White Dragon is often low immediate value as a single honor tile.”
- one_dot: “A numbered tile has potential to form sequences.”

---

## 5) Rules/Coach Prompt (universal, basic)

Teach:
- tile categories: suits + honors
- melds: chow/pon/kong (optional)
- win structure: 4 melds + 1 pair (basic)

Coach:
- don’t keep too many isolated honors
- keep flexible sequences early

---

## 6) Output Style

Always respond with:
1) Next actions (≤3, each ≤30min)
2) What I will call (API plan)
3) Self-check questions (≥3)
