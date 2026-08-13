import streamlit as st


# Configure the browser tab and show the app heading.
st.set_page_config(page_title="Premier League Manager Simulator", page_icon="⚽")
st.title("Premier League Manager Simulator")
st.write("Welcome! Choose a Premier League club to begin your management career.")


# These are the clubs available for the first version of the game.
clubs = [
    "Arsenal",
    "Aston Villa",
    "Bournemouth",
    "Brentford",
    "Brighton",
    "Burnley",
    "Chelsea",
    "Crystal Palace",
    "Everton",
    "Fulham",
    "Leeds United",
    "Liverpool",
    "Manchester City",
    "Manchester United",
    "Newcastle United",
    "Nottingham Forest",
    "Sunderland",
    "Tottenham Hotspur",
    "West Ham United",
    "Wolverhampton Wanderers",
]


# Let the user choose a club and start their career.
selected_club = st.selectbox("Choose your club", clubs, index=None)

if st.button("Start Career"):
    if selected_club:
        st.success(f"Welcome to {selected_club}! Your managerial career starts now.")
    else:
        st.warning("Please choose a club before starting your career.")
