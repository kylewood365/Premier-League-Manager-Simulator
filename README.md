# Premier League Manager Simulator

A beginner-friendly, fictional Premier League management simulator. Pick one
of 20 fictional squads and build a persistent career across complete
38-gameweek double round-robin seasons.

## Features

- Staged matchdays with formations, tactics, benches and substitutions
- Goalscorers, cards, suspensions, injuries, fitness, morale and form
- Possession, shots, expected goals (xG), fixtures, tables and player statistics
- Transfers, AI offers, free agents, contracts, wages and scouting
- Squad roles, development, aging, retirements and unique youth replacements
- Persistent dashboards and multi-season career history

## How to play

1. Start a career by choosing a club.
2. Check the Dashboard for your next fixture, finances and squad status.
3. Pick your Starting XI, bench, formation and tactics.
4. Play the gameweek, make half-time changes, and review the results.
5. Manage your squad, transfers, contracts and scouting between matches.
6. Complete seasons and develop your squad over a multi-season career.

## Run the game

```bash
streamlit run app.py
```

Each gameweek gives every club one match. Your selected XI determines your
club's strength, while the other nine fixtures are simulated automatically
using each club's best XI. Results update the full league table before you move
on to the next gameweek.

## Custom Visual Assets

The interface uses a dark stadium-inspired gradient by default. To use your own
stadium atmosphere, place a JPEG image at:

```text
assets/stadium-background.jpg
```

The image is centred, covers the viewport, and receives a dark readability
overlay. If the file is missing or cannot be read, the app automatically falls
back to the built-in gradient without displaying a broken image.

## Run the tests

```bash
pytest -q
```
