from copy import deepcopy

import streamlit as st

from data import CLUBS, CLUB_BUDGETS, SQUADS, calculate_team_strength
from fixtures import advance_gameweek, generate_fixtures, get_club_fixture
from game import simulate_gameweek
from league import create_league_table, get_sorted_league_table
from progression import process_end_of_season
from stats import create_player_statistics, get_current_squad_statistics
from transfer import buy_player, format_money, sell_player


def render_transfer_market(active_club, career_squads, squad):
    st.header("Transfer Market")
    st.write("Browse players at other Premier League clubs or sell from your squad.")
    buy_tab, sell_tab = st.tabs(["Buy Players", "Sell Players"])

    with buy_tab:
        position_options = sorted(
            {player["position"] for club in CLUBS for player in career_squads[club]}
        )
        position_filter = st.selectbox("Position", ["All"] + position_options)
        club_filter = st.selectbox(
            "Club", ["All"] + [club for club in CLUBS if club != active_club]
        )
        market_players = [
            (club, player)
            for club in CLUBS
            if club != active_club
            for player in career_squads[club]
            if position_filter == "All" or player["position"] == position_filter
            if club_filter == "All" or club == club_filter
        ]
        st.dataframe(
            [
                {
                    "Player": player["name"],
                    "Club": club,
                    "Position": player["position"],
                    "Age": player["age"],
                    "Overall": player["overall"],
                    "Transfer Value": format_money(player["value"]),
                }
                for club, player in market_players
            ],
            hide_index=True,
            use_container_width=True,
        )
        player_to_buy = st.selectbox(
            "Player to buy",
            [player["name"] for _, player in market_players],
            index=None,
        )
        if st.button("Buy Player", disabled=player_to_buy is None):
            success, new_budget, message = buy_player(
                career_squads,
                active_club,
                player_to_buy,
                st.session_state["transfer_budget"],
            )
            if success:
                st.session_state["transfer_budget"] = new_budget
                st.success(message)
            else:
                st.warning(message)

    with sell_tab:
        player_to_sell = st.selectbox(
            "Player to sell", [player["name"] for player in squad], index=None
        )
        selected_sale = next(
            (player for player in squad if player["name"] == player_to_sell), None
        )
        if selected_sale:
            st.write(f"Sale value: **{format_money(selected_sale['value'])}**")
        confirm_sale = st.checkbox("I confirm that I want to sell this player")
        if st.button(
            "Sell Player", disabled=player_to_sell is None or not confirm_sale
        ):
            success, new_budget, message = sell_player(
                career_squads,
                active_club,
                player_to_sell,
                st.session_state["transfer_budget"],
                st.session_state["transfer_pool"],
            )
            if success:
                st.session_state["transfer_budget"] = new_budget
                st.success(message)
            else:
                st.warning(message)


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
        st.session_state["career_squads"] = deepcopy(SQUADS)
        st.session_state["transfer_budget"] = CLUB_BUDGETS[selected_club]
        st.session_state["transfer_pool"] = []
        st.session_state["player_statistics"] = create_player_statistics(
            st.session_state["career_squads"][selected_club]
        )
        st.session_state["recorded_stat_gameweeks"] = set()
        st.session_state["processed_seasons"] = set()
        st.session_state["season_number"] = 1
        st.session_state.pop("season_summary", None)
        st.session_state.pop("gameweek_results", None)
        st.success(f"Welcome to {selected_club}! Your career starts at Gameweek 1.")
    else:
        st.warning("Please choose a club before starting your career.")

if "active_club" in st.session_state:
    active_club = st.session_state["active_club"]
    career_squads = st.session_state["career_squads"]
    squad = career_squads[active_club]
    gameweek = st.session_state["current_gameweek"]
    fixture = get_club_fixture(st.session_state["fixtures"], gameweek, active_club)
    is_complete = gameweek in st.session_state["completed_gameweeks"]

    st.metric("Transfer Budget", format_money(st.session_state["transfer_budget"]))

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
            "Potential": player["potential"],
        }
        for player in squad
    ]
    st.dataframe(squad_table, hide_index=True, use_container_width=True)

    st.subheader("Player Stats")
    stat_sort = st.selectbox(
        "Sort player stats by", ["Goals", "Appearances", "Overall", "Player"]
    )
    stat_rows = get_current_squad_statistics(
        squad, st.session_state["player_statistics"], stat_sort
    )
    top_goals = stat_rows[0]["Goals"] if stat_rows and stat_sort == "Goals" else max(
        (row["Goals"] for row in stat_rows), default=0
    )
    top_scorers = [row["Player"] for row in stat_rows if row["Goals"] == top_goals]
    top_scorer_name = ", ".join(top_scorers) if top_goals else "No goals yet"
    st.metric("Top Scorer", top_scorer_name, f"{top_goals} goals")
    st.dataframe(stat_rows, hide_index=True, use_container_width=True)

    if not is_complete:
        st.subheader("Choose Your Starting XI")
        selected_names = st.multiselect(
            "Select exactly 11 players",
            [player["name"] for player in squad],
            key=f"starting_xi_{active_club}_{gameweek}",
        )
        selected_xi = [player for player in squad if player["name"] in selected_names]

        if len(selected_xi) < 11:
            st.warning(
                f"Select {11 - len(selected_xi)} more player(s) to complete your starting XI."
            )
        elif len(selected_xi) > 11:
            st.warning(
                f"Remove {len(selected_xi) - 11} player(s). A starting XI must have exactly 11 players."
            )
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
                    player_statistics=st.session_state["player_statistics"],
                    recorded_stat_gameweeks=st.session_state[
                        "recorded_stat_gameweeks"
                    ],
                )
                st.rerun()

    if not is_complete:
        render_transfer_market(active_club, career_squads, squad)

    if is_complete:
        render_transfer_market(active_club, career_squads, squad)
        st.subheader(f"Gameweek {gameweek} Results")
        for result in st.session_state["gameweek_results"]:
            scoreline = (
                f"{result['home_club']} {result['home_score']} - "
                f"{result['away_score']} {result['away_club']}"
            )
            if active_club in (result["home_club"], result["away_club"]):
                st.success(f"⭐ **{scoreline}** — Your match")
                st.write("**Goals:**")
                if result["goal_events"]:
                    for event in result["goal_events"]:
                        st.write(f"{event['player']} {event['minute']}'")
                else:
                    st.write("None")
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
            # This block is revisited on every Streamlit rerun, so progression.py
            # owns the duplicate-protection check before changing any player.
            if "season_summary" not in st.session_state:
                summary = process_end_of_season(
                    career_squads,
                    active_club,
                    st.session_state["player_statistics"],
                    st.session_state["league_table"],
                    st.session_state["processed_seasons"],
                    st.session_state["season_number"],
                )
                if summary is not None:
                    st.session_state["season_summary"] = summary

            summary = st.session_state["season_summary"]
            position = summary["user_position"]
            suffix = "th" if 10 <= position % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
            st.header("SEASON COMPLETE")
            st.success(f"🏆 Premier League Champions: {summary['champion']}")
            st.write(f"**Your Finish:** {position}{suffix}")
            st.write(
                f"**Top Scorer:** {summary['top_scorer']} — "
                f"{summary['top_scorer_goals']} goals"
            )
            st.subheader("Player Development")
            if summary["development"]:
                st.dataframe(
                    [
                        {
                            "Player": row["player"],
                            "Overall": f"{row['old_overall']} → {row['new_overall']}",
                            "Change": f"{row['change']:+d}",
                        }
                        for row in summary["development"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.write("No Overall changes this season.")
