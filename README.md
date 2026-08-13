# Premier League Manager Simulator

A beginner-friendly Streamlit football management game. Pick one of 20 Premier
League clubs, select a starting XI, and play through a complete 38-gameweek
double round-robin season.

## Run the game

```bash
streamlit run app.py
```

Each gameweek gives every club one match. Your selected XI determines your
club's strength, while the other nine fixtures are simulated automatically
using each club's best XI. Results update the full league table before you move
on to the next gameweek.

## Run the tests

```bash
python -m unittest -v
```
