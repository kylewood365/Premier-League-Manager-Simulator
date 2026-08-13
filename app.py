import streamlit as st

from data import CLUBS, SQUADS


# Configure the browser tab and show the app heading.
st.set_page_config(page_title="Premier League Manager Simulator", page_icon="⚽")
st.title("Premier League Manager Simulator")
st.write("Welcome! Choose a Premier League club to begin your management career.")


# Let the user choose a club and start their career.
selected_club = st.selectbox("Choose your club", CLUBS, index=None)

if st.button("Start Career"):
    if selected_club:
        st.success(f"Welcome to {selected_club}! Your managerial career starts now.")
        st.subheader(f"{selected_club} Squad")

        # Rename the data keys to friendly headings for the squad table.
        squad_table = [
            {
                "Player": player["name"],
                "Position": player["position"],
                "Age": player["age"],
                "Overall": player["overall"],
            }
            for player in SQUADS[selected_club]
        ]
        st.dataframe(squad_table, hide_index=True, use_container_width=True)
    else:
        st.warning("Please choose a club before starting your career.")
