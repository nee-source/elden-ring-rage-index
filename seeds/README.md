# Seed tables

Hand-maintained mapping tables, versioned in git. This is a **draft**: verify and extend it as a team. Scope is the base game only; DLC bosses have no achievements.

- `achievement_boss_map.csv`: maps each Steam achievement code to its display name and boss.
  - Codes were matched to names by unlock %, comparing the public achievements page with the API, on 2026-09-25.
  - `ACH17` and `ACH15` have the same % and may be swapped. Neither is a boss.
  - `main_path_order` marks the bosses every player must beat to finish the game.
- `boss_aliases.csv`: the names used to find boss mentions in review text.
  - Aliases are lowercase and matched on whole words only.
  - One boss can have several aliases.
  - Ambiguous aliases are marked in `note`.
