import streamlit as st

from data import CLUBS, SQUADS, calculate_team_strength, get_best_starting_xi
from game import simulate_match


# Configure the browser tab and show the app heading.
st.set_page_config(page_title="Premier League Manager Simulator", page_icon="⚽")
st.title("Premier League Manager Simulator")
st.write("Welcome! Choose a Premier League club to begin your management career.")


# Let the user choose a club and start their career.
selected_club = st.selectbox("Choose your club", CLUBS, index=None)

if st.button("Start Career"):
    if selected_club:
        st.session_state["active_club"] = selected_club
        st.success(f"Welcome to {selected_club}! Your managerial career starts now.")
    else:
        st.warning("Please choose a club before starting your career.")


# Keep the chosen career visible when a selection causes Streamlit to rerun.
if "active_club" in st.session_state:
    active_club = st.session_state["active_club"]
    squad = SQUADS[active_club]

    st.subheader(f"{active_club} Squad")

    # Rename the data keys to friendly headings for the squad table.
    squad_table = [
        {
            "Player": player["name"],
            "Position": player["position"],
            "Age": player["age"],
            "Overall": player["overall"],
        }
        for player in squad
    ]
    st.dataframe(squad_table, hide_index=True, use_container_width=True)

    st.subheader("Choose Your Starting XI")
    player_names = [player["name"] for player in squad]
    selected_names = st.multiselect(
        "Select exactly 11 players",
        player_names,
        key=f"starting_xi_{active_club}",
    )

    selected_count = len(selected_names)
    if selected_count < 11:
        st.warning(f"Select {11 - selected_count} more player(s) to complete your starting XI.")
    elif selected_count > 11:
        st.warning(f"Remove {selected_count - 11} player(s). A starting XI must have exactly 11 players.")
    else:
        starting_xi = [player for player in squad if player["name"] in selected_names]
        average_rating = calculate_team_strength(starting_xi)
        st.success("Your starting XI is ready!")
        st.metric("Average Overall Rating", f"{average_rating:.1f}")
        st.metric("Team Strength", f"{average_rating:.1f} / 100")

        st.subheader("Play Your First Match")
        opponents = [club for club in CLUBS if club != active_club]
        opponent = st.selectbox("Choose an opponent", opponents, index=None)

        if st.button("Simulate Match"):
            if opponent is None:
                st.warning("Please choose an opponent before simulating the match.")
            else:
                opponent_xi = get_best_starting_xi(opponent)
                opponent_strength = calculate_team_strength(opponent_xi)
                match = simulate_match(
                    active_club,
                    opponent,
                    average_rating,
                    opponent_strength,
                )

                st.subheader("Full Time")
                st.write(f"**Your club:** {match['user_club']}")
                st.write(f"**Opponent:** {match['opponent']}")
                st.metric(
                    "Final score",
                    f"{match['user_score']} - {match['opponent_score']}",
                )
                st.success(match["result"])
