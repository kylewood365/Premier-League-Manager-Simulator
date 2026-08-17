from copy import deepcopy
import random

import streamlit as st

from career import record_season_history, start_next_season
from contracts import calculate_wage_spend, renew_contract, requested_weekly_wage
from data import CLUBS, CLUB_BUDGETS, CLUB_WAGE_BUDGETS, SQUADS, calculate_team_strength
from fixtures import advance_gameweek, generate_fixtures, get_club_fixture
from fitness import is_available
from game import simulate_gameweek, simulate_half
from league import create_league_table, get_sorted_league_table
from progression import process_end_of_season
from stats import create_player_statistics, get_current_squad_statistics
from transfer import buy_player, format_money, sell_player, sign_free_agent
from tactics import (
    FORMATIONS, TACTICAL_STYLES, apply_substitutions,
    validate_bench, validate_starting_xi,
)


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
                CLUB_WAGE_BUDGETS[active_club],
            )
            if success:
                st.session_state["transfer_budget"] = new_budget
                st.success(message)
            else:
                st.warning(message)

    st.header("Contract Management")
    contract_name = st.selectbox(
        "Player contract", [player["name"] for player in squad], index=None
    )
    contract_player = next(
        (player for player in squad if player["name"] == contract_name), None
    )
    extension = st.selectbox("Contract extension", [1, 2, 3, 4])
    if contract_player:
        st.write(
            f"Current: **{contract_player['contract_years']} year(s)** at "
            f"**{format_money(contract_player['wage'])}/week**. Requested wage: "
            f"**{format_money(requested_weekly_wage(contract_player))}/week**."
        )
    if st.button("Renew Contract", disabled=contract_player is None):
        success, message = renew_contract(
            contract_player, extension, squad, CLUB_WAGE_BUDGETS[active_club]
        )
        (st.success if success else st.warning)(message)

    st.header("Free Agents")
    free_agents = st.session_state["free_agents"]
    st.dataframe(
        [{
            "Player": player["name"], "Position": player["position"],
            "Age": player["age"], "Overall": player["overall"],
            "Potential": player["potential"],
            "Wage Expectation": f"{format_money(player['wage'])}/week",
            "Value": format_money(player["value"]),
        } for player in free_agents],
        hide_index=True, use_container_width=True,
    )
    free_name = st.selectbox(
        "Free agent to sign", [player["name"] for player in free_agents], index=None
    )
    free_contract = st.selectbox("New contract length", [1, 2, 3, 4, 5])
    if st.button("Sign Free Agent", disabled=free_name is None):
        success, message = sign_free_agent(
            career_squads, active_club, free_agents, free_name,
            free_contract, CLUB_WAGE_BUDGETS[active_club],
        )
        (st.success if success else st.warning)(message)

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
st.write("Choose a Premier League club and build a multi-season career.")

if "league_table" not in st.session_state:
    st.session_state["league_table"] = create_league_table(CLUBS)

selected_club = st.selectbox("Choose your club", CLUBS, index=None)
if st.button("Start Career"):
    if selected_club:
        # A new career always receives a fresh schedule and league table.
        st.session_state["active_club"] = selected_club
        st.session_state["fixtures"] = generate_fixtures(CLUBS, random)
        st.session_state["current_gameweek"] = 1
        st.session_state["completed_gameweeks"] = set()
        st.session_state["league_table"] = create_league_table(CLUBS)
        st.session_state["career_squads"] = deepcopy(SQUADS)
        st.session_state["transfer_budget"] = CLUB_BUDGETS[selected_club]
        st.session_state["transfer_pool"] = []
        st.session_state["free_agents"] = []
        st.session_state["player_statistics"] = create_player_statistics(
            st.session_state["career_squads"][selected_club]
        )
        st.session_state["recorded_stat_gameweeks"] = set()
        st.session_state["processed_health_gameweeks"] = set()
        st.session_state["processed_seasons"] = set()
        st.session_state["season_number"] = 1
        st.session_state["career_history"] = []
        st.session_state["retirement_history"] = []
        st.session_state.pop("season_summary", None)
        st.session_state.pop("gameweek_results", None)
        st.session_state["match_phase"] = "Kickoff"
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

    st.header(f"Season {st.session_state['season_number']}")
    st.metric("Transfer Budget", format_money(st.session_state["transfer_budget"]))
    wage_spend = calculate_wage_spend(squad)
    wage_budget = CLUB_WAGE_BUDGETS[active_club]
    wage_columns = st.columns(3)
    wage_columns[0].metric("Wage Budget", f"{format_money(wage_budget)}/week")
    wage_columns[1].metric("Current Wage Spend", f"{format_money(wage_spend)}/week")
    wage_columns[2].metric("Remaining Wage Budget", f"{format_money(wage_budget - wage_spend)}/week")

    st.subheader("Career History")
    history = st.session_state.setdefault("career_history", [])
    if history:
        for entry in history:
            position = entry["user_position"]
            suffix = (
                "th"
                if 10 <= position % 100 <= 20
                else {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
            )
            st.markdown(
                f"**Season {entry['season']}**  \n"
                f"Champion: {entry['champion']}  \n"
                f"Your Finish: {position}{suffix}  \n"
                f"Top Scorer: {entry['top_scorer']} — "
                f"{entry['top_scorer_goals']} goals"
            )
    else:
        st.write("Complete a season to add it to your history.")

    st.subheader("Retirement History")
    retirement_history = st.session_state.setdefault("retirement_history", [])
    if retirement_history:
        st.dataframe(
            [{
                "Player": row["player"], "Club": row["club"],
                "Age": row["retirement_age"], "Season": row["season"],
            } for row in retirement_history],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.write("No players have retired during this career yet.")

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
            "Fitness": player.get("fitness", 100),
            "Availability": (
                f"Injured ({player.get('injury_gameweeks', 0)} GW)"
                if player.get("injured", False) else "Available"
            ),
            "Potential": player["potential"],
            "Wage": f"{format_money(player['wage'])}/week",
            "Contract": f"{player['contract_years']} year(s)",
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
    top_goals = (
        stat_rows[0]["Goals"]
        if stat_rows and stat_sort == "Goals"
        else max((row["Goals"] for row in stat_rows), default=0)
    )
    top_scorers = [row["Player"] for row in stat_rows if row["Goals"] == top_goals]
    top_scorer_name = ", ".join(top_scorers) if top_goals else "No goals yet"
    st.metric("Top Scorer", top_scorer_name, f"{top_goals} goals")
    st.dataframe(stat_rows, hide_index=True, use_container_width=True)

    if not is_complete:
        phase = st.session_state.setdefault("match_phase", "Kickoff")
        st.subheader(f"Match Flow: {phase}")
        available_players = [player for player in squad if is_available(player)]
        if len(available_players) < 11:
            st.error(
                f"Only {len(available_players)} healthy players are available. "
                "You cannot play until 11 eligible starters are available."
            )
        formation = st.selectbox("Formation", list(FORMATIONS), key=f"formation_{gameweek}")
        style = st.selectbox("Tactical style", TACTICAL_STYLES, key=f"style_{gameweek}")
        selected_names = st.multiselect(
            "Select exactly 11 players",
            [player["name"] for player in available_players],
            key=f"starting_xi_{active_club}_{gameweek}",
            disabled=phase != "Kickoff",
        )
        selected_xi = [player for player in squad if player["name"] in selected_names]
        bench_names = st.multiselect(
            "Bench (up to 7)",
            [p["name"] for p in available_players if p["name"] not in selected_names],
            key=f"bench_{active_club}_{gameweek}",
            max_selections=7,
            disabled=phase != "Kickoff",
        )
        bench = [player for player in squad if player["name"] in bench_names]

        selection_error = None
        try:
            validate_starting_xi(selected_xi, formation)
            validate_bench(bench, selected_xi)
        except ValueError as error:
            selection_error = str(error)
        if phase == "Kickoff" and selection_error:
            st.warning(selection_error)
        elif phase == "Kickoff":
            strength = calculate_team_strength(selected_xi)
            st.success("Your starting XI is ready!")
            st.metric("Team Strength", f"{strength:.1f} / 100")
            if st.button("Kickoff"):
                opponent_strength = calculate_team_strength(
                    sorted(career_squads[opponent], key=lambda p: p["overall"], reverse=True)[:11]
                )
                if venue == "Home":
                    first_half = simulate_half(strength, opponent_strength, style, "Balanced")
                else:
                    first_half = simulate_half(opponent_strength, strength, "Balanced", style)
                st.session_state["first_half_result"] = first_half
                st.session_state["kickoff_style"] = style
                st.session_state["match_phase"] = "Half-time"
                st.rerun()

        if phase in {"Half-time", "Second half"}:
            first = st.session_state["first_half_result"]
            st.info(f"Half-time: **{fixture['home']} {first['home_score']} - {first['away_score']} {fixture['away']}**")
            second_style = st.selectbox(
                "Tactic for the second half", TACTICAL_STYLES,
                index=TACTICAL_STYLES.index(style), key=f"second_style_{gameweek}",
            )
            existing = st.session_state.setdefault("match_substitutions", [])
            current_pitch = apply_substitutions(selected_xi, bench, existing)
            used_on = {on for _, on in existing}
            off = st.selectbox("Player off", [p["name"] for p in current_pitch], index=None)
            on = st.selectbox(
                "Player on", [p["name"] for p in bench if p["name"] not in used_on], index=None,
            )
            if st.button("Make substitution", disabled=off is None or on is None or len(existing) >= 5):
                try:
                    apply_substitutions(selected_xi, bench, existing + [(off, on)])
                    existing.append((off, on))
                    st.rerun()
                except ValueError as error:
                    st.warning(str(error))
            st.caption(f"Substitutions used: {len(existing)} / 5")
            if phase == "Half-time" and st.button("Start Second Half"):
                st.session_state["match_phase"] = "Second half"
                st.rerun()
            if phase == "Second half" and st.button("Full-time"):
                st.session_state["gameweek_results"] = simulate_gameweek(
                    gameweek,
                    st.session_state["fixtures"],
                    active_club,
                    selected_xi,
                    st.session_state["league_table"],
                    st.session_state["completed_gameweeks"],
                    player_statistics=st.session_state["player_statistics"],
                    recorded_stat_gameweeks=st.session_state["recorded_stat_gameweeks"],
                    user_squad=squad,
                    processed_health_gameweeks=st.session_state[
                        "processed_health_gameweeks"
                    ],
                    formation=formation,
                    tactical_style=second_style,
                    bench=bench,
                    substitutions=existing,
                    first_half_result=st.session_state["first_half_result"],
                )
                st.session_state["match_phase"] = "Full-time"
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
                for event in result.get("injury_events", []):
                    st.error(
                        f"Injury: {event['player']} suffered a {event['injury']}. "
                        f"Out for {event['gameweeks']} gameweek(s)."
                    )
                for player_name in result.get("recovery_events", []):
                    st.success(f"{player_name} has recovered and is available again.")
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
                st.session_state["match_phase"] = "Kickoff"
                st.session_state.pop("match_substitutions", None)
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
                    retirement_history=st.session_state["retirement_history"],
                    free_agents=st.session_state["free_agents"],
                )
                if summary is not None:
                    st.session_state["season_summary"] = summary
                    record_season_history(
                        st.session_state["career_history"],
                        st.session_state["season_number"],
                        summary,
                    )

            summary = st.session_state["season_summary"]
            position = summary["user_position"]
            suffix = (
                "th"
                if 10 <= position % 100 <= 20
                else {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
            )
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

            user_retirements = [
                event for event in summary["retirements"]
                if event["club"] == active_club
            ]
            if user_retirements:
                st.subheader("PLAYER RETIREMENT")
                for event in user_retirements:
                    youth = event["youth"]
                    st.warning(
                        f"{event['player']} has retired at age "
                        f"{event['retirement_age']}."
                    )
                    st.success("Youth Academy Promotion")
                    st.markdown(
                        f"**{youth['name']}**  \nAge: {youth['age']}  \n"
                        f"Position: {youth['position']}  \n"
                        f"Overall: {youth['overall']}  \n"
                        f"Potential: {youth['potential']}"
                    )

            user_contract_events = [
                event for event in summary["contract_events"]
                if event["club"] == active_club
            ]
            for event in user_contract_events:
                if event["type"] == "warning":
                    st.warning(
                        f"Contract Warning: {event['player']} has 1 year remaining."
                    )
                else:
                    st.error(
                        f"Contract Expired: {event['player']} has left "
                        f"{active_club} on a free transfer."
                    )

            if st.button("Start Next Season"):
                start_next_season(st.session_state, CLUBS)
                st.rerun()
