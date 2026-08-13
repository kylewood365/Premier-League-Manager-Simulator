import streamlit as st

from data import CLUBS, SQUADS, calculate_team_strength
from fixtures import advance_gameweek, generate_fixtures, get_club_fixture
from game import simulate_gameweek
from league import create_league_table, get_sorted_league_table


st.set_page_config(page_title="Premier League Manager Simulator", page_icon="⚽")
st.title("Premier League Manager Simulator")
st.write("Choose a Premier League club and guide it through a 38-gameweek season.")

if "league_table" not in st.session_state:
    st.session_state["league_table"] = create_league_table(CLUBS)

selected_club = st.selectbox("Choose your club", CLUBS, index=None)
if st.button("Start Career"):
    if selected_club:
        # A new career always receives a fresh schedule and league table.
        st.session_state["active_club"] = selected_club
        st.session_state["fixtures"] = generate_fixtures(CLUBS)
        st.session_state["current_gameweek"] = 1
        st.session_state["completed_gameweeks"] = set()
        st.session_state["league_table"] = create_league_table(CLUBS)
        st.session_state.pop("gameweek_results", None)
        st.success(f"Welcome to {selected_club}! Your career starts at Gameweek 1.")
    else:
        st.warning("Please choose a club before starting your career.")

if "active_club" in st.session_state:
    active_club = st.session_state["active_club"]
    squad = SQUADS[active_club]
    gameweek = st.session_state["current_gameweek"]
    fixture = get_club_fixture(st.session_state["fixtures"], gameweek, active_club)
    is_complete = gameweek in st.session_state["completed_gameweeks"]

    st.header(f"Gameweek {gameweek}")
    if fixture:
        venue = "Home" if fixture["home"] == active_club else "Away"
        opponent = fixture["away"] if venue == "Home" else fixture["home"]
        st.info(
            f"Next fixture: **{fixture['home']} vs {fixture['away']}** "
            f"— {active_club} are **{venue}**"
        )

    st.subheader(f"{active_club} Squad")
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

    if not is_complete:
        st.subheader("Choose Your Starting XI")
        selected_names = st.multiselect(
            "Select exactly 11 players",
            [player["name"] for player in squad],
            key=f"starting_xi_{active_club}_{gameweek}",
        )
        selected_xi = [player for player in squad if player["name"] in selected_names]

        if len(selected_xi) < 11:
            st.warning(f"Select {11 - len(selected_xi)} more player(s) to complete your starting XI.")
        elif len(selected_xi) > 11:
            st.warning(f"Remove {len(selected_xi) - 11} player(s). A starting XI must have exactly 11 players.")
        else:
            strength = calculate_team_strength(selected_xi)
            st.success("Your starting XI is ready!")
            st.metric("Team Strength", f"{strength:.1f} / 100")
            if st.button("Play Gameweek"):
                st.session_state["gameweek_results"] = simulate_gameweek(
                    gameweek,
                    st.session_state["fixtures"],
                    active_club,
                    selected_xi,
                    st.session_state["league_table"],
                    st.session_state["completed_gameweeks"],
                )
                st.rerun()

    if is_complete:
        st.subheader(f"Gameweek {gameweek} Results")
        for result in st.session_state["gameweek_results"]:
            scoreline = (
                f"{result['home_club']} {result['home_score']} - "
                f"{result['away_score']} {result['away_club']}"
            )
            if active_club in (result["home_club"], result["away_club"]):
                st.success(f"⭐ **{scoreline}** — Your match")
            else:
                st.write(scoreline)

        st.subheader("League Table")
        st.dataframe(
            get_sorted_league_table(st.session_state["league_table"]),
            hide_index=True,
            use_container_width=True,
        )

        if gameweek < len(st.session_state["fixtures"]):
            next_fixture = get_club_fixture(
                st.session_state["fixtures"], gameweek + 1, active_club
            )
            next_venue = "Home" if next_fixture["home"] == active_club else "Away"
            next_opponent = (
                next_fixture["away"] if next_venue == "Home" else next_fixture["home"]
            )
            st.info(f"Up next: **{next_opponent}** ({next_venue})")
            if st.button("Continue to next gameweek"):
                st.session_state["current_gameweek"] = advance_gameweek(
                    gameweek, st.session_state["completed_gameweeks"]
                )
                st.session_state.pop("gameweek_results", None)
                st.rerun()
        else:
            st.success("Season complete! All 38 Premier League gameweeks have been played.")
