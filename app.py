from copy import deepcopy
from html import escape
import random

import streamlit as st

from career import record_season_history, start_next_season
from budgets import career_budget_mappings
from contracts import calculate_wage_spend, renew_contract, requested_weekly_wage
from data import CLUBS, SQUADS, calculate_team_strength
from discipline import availability_status
from fixtures import advance_gameweek, generate_fixtures, get_club_fixture
from fitness import is_available
from game import simulate_gameweek, simulate_half
from league import create_league_table, get_sorted_league_table
from match_stats import (
    calculate_season_aggregates, create_history_record, generate_half_statistics,
    record_match_history,
)
from morale import ensure_player_morale_form, form_label, form_score, morale_label
from progression import process_end_of_season
from scouting import (
    KNOWLEDGE_NAMES, assign_scout, initialise_scouting, knowledge_level,
    player_id, process_scouting, visible_player_data,
)
from stats import create_player_statistics, get_current_squad_statistics
from squad_management import (
    SQUAD_ROLES, accept_transfer_request, assign_default_roles, change_squad_role,
    ensure_squad_management, promise_more_playing_time, satisfaction_label,
    set_transfer_listed,
)
from transfer import buy_player, format_money, sell_player, sign_free_agent
from transfer_offers import (
    accept_offer, counter_offer, generate_ai_offers, reject_offer,
)
from tactics import (
    FORMATIONS, TACTICAL_STYLES, apply_substitutions,
    validate_bench, validate_starting_xi,
)
from dashboard import NAVIGATION, initialise_navigation, render_dashboard
from ui_styles import apply_global_styles
from real_world_data import (
    RealWorldDataError, get_current_squad, get_premier_league_player_statistics,
    get_premier_league_teams, is_api_configured, join_squad_statistics,
)
from player_ratings import create_simulator_player
from real_career import REAL_DATA_SEASON, build_real_career_squads


def render_real_world_data():
    """Show a read-only API preview; never alter the fictional career state."""
    st.header("Real World Data")
    st.caption("Current 2026 Premier League clubs and registered squads from API-Football.")
    if st.session_state.get("career_source") == "real":
        st.info("Real World Data is a live/cached preview. Your active career uses the snapshot taken when it began.")
    try:
        teams = get_premier_league_teams()
        st.subheader("Current Premier League clubs")
        st.write(", ".join(team["name"] for team in teams))
        choices = {team["name"]: team for team in teams}
        club = st.selectbox("Choose a real-world club", list(choices), index=None)
        if club:
            team = choices[club]
            squad = get_current_squad(team["team_id"], team["name"])
            st.subheader(club)
            basic_tab, ratings_tab = st.tabs(["Basic Squad", "Simulator Ratings"])
            with basic_tab:
                st.dataframe([{
                    "Player": player["name"], "Age": player["age"],
                    "Position": player["position"],
                    "Shirt Number": player["shirt_number"],
                } for player in squad], hide_index=True, use_container_width=True)
            with ratings_tab:
                st.caption(
                    "Overall, Potential, Transfer Value and Wage are simulator-generated "
                    "estimates based on available real-world information and are not official "
                    "ratings or salary data."
                )
                try:
                    joined = join_squad_statistics(
                        squad, get_premier_league_player_statistics()
                    )
                    rated = [create_simulator_player(player) for player in joined]
                    st.dataframe([{
                        "Player": player["name"], "Age": player["age"],
                        "Position": player["position"], "Overall": player["overall"],
                        "Potential": player["potential"],
                        "Transfer Value": format_money(player["transfer_value"]),
                        "Weekly Wage": f"{format_money(player['weekly_wage'])}/week",
                    } for player in rated], hide_index=True, use_container_width=True)
                except RealWorldDataError as exc:
                    st.warning(f"Simulator ratings are unavailable: {exc}")
                    st.info("The Basic Squad and your fictional career are unaffected.")
                with st.expander("How ratings are calculated"):
                    st.write(
                        "Each position uses different performance factors. Playing time improves "
                        "confidence, while very small samples are protected from extreme ratings. "
                        "Potential is estimated mainly from age and current ability. All ratings "
                        "are unique to this simulator."
                    )
    except RealWorldDataError as exc:
        st.warning(str(exc))
        st.info("Your fictional career is still available and has not been changed.")


def render_transfer_market(active_club, career_squads, squad):
    st.header("Transfer Market")
    st.write("Browse players at other Premier League clubs or sell from your squad.")
    buy_tab, sell_tab = st.tabs(["Buy Players", "Sell Players"])

    with buy_tab:
        position_options = sorted(
            {player["position"] for club in career_squads for player in career_squads[club]}
        )
        position_filter = st.selectbox("Position", ["All"] + position_options)
        club_filter = st.selectbox(
            "Club", ["All"] + [club for club in career_squads if club != active_club]
        )
        market_players = [
            (club, player)
            for club in career_squads
            if club != active_club
            for player in career_squads[club]
            if position_filter == "All" or player["position"] == position_filter
            if club_filter == "All" or club == club_filter
        ]
        knowledge = st.session_state["scouting_knowledge"]
        st.dataframe(
            [dict(
                visible_player_data(
                    player, knowledge_level(player, club, active_club, knowledge)
                ),
                Club=club,
                Knowledge=KNOWLEDGE_NAMES[knowledge_level(
                    player, club, active_club, knowledge
                )],
            ) for club, player in market_players],
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
                st.session_state["club_wage_budgets"][active_club],
                st.session_state["transfer_history"],
                st.session_state["season_number"],
                st.session_state["club_transfer_budgets"],
                st.session_state["scouting_knowledge"],
            )
            if success:
                st.session_state["transfer_budget"] = new_budget
                st.session_state["club_transfer_budgets"][active_club] = new_budget
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
            f"Squad Role: **{ensure_squad_management(contract_player)['squad_role']}**. "
            f"Current: **{contract_player['contract_years']} year(s)** at "
            f"**{format_money(contract_player['wage'])}/week**. Requested wage: "
            f"**{format_money(requested_weekly_wage(contract_player))}/week**."
        )
    if st.button("Renew Contract", disabled=contract_player is None):
        success, message = renew_contract(
            contract_player, extension, squad,
            st.session_state["club_wage_budgets"][active_club]
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
            listed = "Yes" if selected_sale.get("transfer_listed") else "No"
            st.write(
                f"Sale value: **{format_money(selected_sale['value'])}**. "
                f"Transfer listed: **{listed}**."
            )
        confirm_sale = st.checkbox("I confirm that I want to sell this player")
        live_match = st.session_state.get("match_phase") in {"Half-time", "Second half"}
        if live_match:
            st.info("Finish the match before selling a player from the matchday squad.")
        if st.button(
            "Sell Player",
            disabled=player_to_sell is None or not confirm_sale or live_match,
        ):
            success, new_budget, message = sell_player(
                career_squads, active_club, player_to_sell,
                st.session_state["transfer_budget"], st.session_state["transfer_pool"],
            )
            if success:
                st.session_state["transfer_budget"] = new_budget
                st.session_state["club_transfer_budgets"][active_club] = new_budget
                st.success(message)
            else:
                st.warning(message)

    st.header("Free Agents")
    free_agents = st.session_state["free_agents"]
    if free_agents:
        st.dataframe(
            [{
            "Player": player["name"], "Position": player["position"],
            "Age": player["age"], "Overall": player["overall"],
            "Potential": visible_player_data(
                player,
                st.session_state["scouting_knowledge"].get(player_id(player), 0),
                free_agent=True,
            )["Potential"],
            "Wage Expectation": f"{format_money(player['wage'])}/week",
            "Value": visible_player_data(
                player,
                st.session_state["scouting_knowledge"].get(player_id(player), 0),
                free_agent=True,
            )["Value"],
            } for player in free_agents],
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("No free agents currently available.")
    free_name = st.selectbox(
        "Free agent to sign", [player["name"] for player in free_agents], index=None
    )
    free_contract = st.selectbox("New contract length", [1, 2, 3, 4, 5])
    if st.button("Sign Free Agent", disabled=free_name is None):
        success, message = sign_free_agent(
            career_squads, active_club, free_agents, free_name,
            free_contract, st.session_state["club_wage_budgets"][active_club],
            st.session_state["transfer_history"], st.session_state["season_number"],
            st.session_state["scouting_knowledge"],
        )
        (st.success if success else st.warning)(message)


def render_scouting(active_club, career_squads):
    """Show compact assignment controls and persistent completed reports."""
    st.header("Scouting")
    knowledge = st.session_state["scouting_knowledge"]
    assignments = st.session_state["scouting_assignments"]
    reports = st.session_state["scout_reports"]
    candidates = [
        (club, player) for club, squad in career_squads.items() if club != active_club
        for player in squad
    ] + [("Free Agent", player) for player in st.session_state["free_agents"]]
    club_filter = st.selectbox(
        "Scouting club", ["All"] + sorted({club for club, _ in candidates})
    )
    position_filter = st.selectbox(
        "Scouting position", ["All"] + sorted({p["position"] for _, p in candidates})
    )
    level_filter = st.selectbox("Knowledge level", ["All"] + KNOWLEDGE_NAMES)
    filtered = [
        (club, player) for club, player in candidates
        if club_filter == "All" or club == club_filter
        if position_filter == "All" or player["position"] == position_filter
        if level_filter == "All" or KNOWLEDGE_NAMES[
            knowledge.get(player_id(player), 0)
        ] == level_filter
    ]
    choices = {f"{p['name']} — {club} ({p['position']})": (club, p)
               for club, p in filtered if knowledge.get(player_id(p), 0) < 3}
    choice = st.selectbox("Player to scout", list(choices), index=None)
    if st.button("Assign Scout", disabled=choice is None):
        club, player = choices[choice]
        success, message = assign_scout(
            player, club, active_club, knowledge, assignments,
            st.session_state["season_number"], st.session_state["current_gameweek"],
        )
        (st.success if success else st.warning)(message)

    st.subheader(f"Active Assignments ({len(assignments)} / 3)")
    if assignments:
        st.dataframe([{
            "Player": a["player_name"], "Club": a["club"],
            "Status": "In Progress", "Completion": "After next league gameweek",
        } for a in assignments], hide_index=True, use_container_width=True)
    else:
        st.write("No active scouting assignments.")

    st.subheader("Scout Reports")
    players = {player_id(p): (club, p) for club, squad in career_squads.items()
               for p in squad}
    players.update({player_id(p): ("Free Agent", p)
                    for p in st.session_state["free_agents"]})
    for report in reversed(reports):
        found = players.get(report["player_id"])
        if not found:
            continue
        club, player = found
        details = visible_player_data(player, report["knowledge_level"], club == "Free Agent")
        st.markdown(f"**{player['name']} — {club}**  ")
        st.caption(
            f"Season {report['season']}, Gameweek {report['gameweek_completed']} · "
            f"Knowledge: {KNOWLEDGE_NAMES[report['knowledge_level']]}"
        )
        st.dataframe([details], hide_index=True, use_container_width=True)
    if not reports:
        st.info("No completed scout reports yet.")

def render_transfer_offers(active_club, career_squads):
    """Show active negotiations and completed transfer history."""
    st.header("Transfer Offers")
    offers = st.session_state["transfer_offers"]
    live_match = st.session_state.get("match_phase") in {"Half-time", "Second half"}
    if live_match:
        st.info("Finish the match before completing an outgoing transfer.")
    squad = career_squads[active_club]
    rows = []
    for offer in offers:
        player = next((p for p in squad if p["name"] == offer["player"]), None)
        rows.append({
            "Player": offer["player"], "Buying Club": offer["buying_club"],
            "Overall": player["overall"] if player else "—",
            "Age": player["age"] if player else "—",
            "Market Value": format_money(player["value"]) if player else "—",
            "Offer": format_money(offer["offered_fee"]), "Status": offer["status"],
        })
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("No active transfer offers.")

    for offer in offers:
        if offer["status"] not in {"Pending", "Countered"}:
            continue
        player = next((p for p in squad if p["name"] == offer["player"]), None)
        if player is None:
            continue
        st.write(f"**{offer['buying_club']}** offer {format_money(offer['offered_fee'])} for **{offer['player']}**")
        accept_col, reject_col = st.columns(2)
        if accept_col.button(
            "Accept", key=f"accept_offer_{offer['id']}", disabled=live_match
        ):
            success, message = accept_offer(
                offer, career_squads, active_club,
                st.session_state["club_transfer_budgets"],
                st.session_state["transfer_history"], st.session_state["season_number"],
            )
            st.session_state["transfer_budget"] = st.session_state["club_transfer_budgets"][active_club]
            (st.success if success else st.warning)(f"Transfer Completed\n\n{message}")
            st.rerun()
        if reject_col.button("Reject", key=f"reject_offer_{offer['id']}"):
            reject_offer(offer)
            st.info("Transfer offer rejected.")
            st.rerun()
        asking_price = st.number_input(
            "Counter Offer", min_value=100_000, step=100_000,
            value=max(offer["offered_fee"] + 100_000, player["value"]),
            key=f"counter_value_{offer['id']}",
        )
        if st.button("Submit Counter Offer", key=f"counter_offer_{offer['id']}"):
            response = counter_offer(
                offer, asking_price, player,
                st.session_state["club_transfer_budgets"],
            )
            if response == "Accepted":
                st.success(f"Counter Accepted\n\n{offer['buying_club']} accepted your {format_money(asking_price)} asking price.")
            elif response == "Improved":
                st.info(f"Improved Offer: {format_money(offer['offered_fee'])}.")
            else:
                st.warning("The buying club withdrew from negotiations.")
            st.rerun()

    st.subheader("Transfer History")
    history = st.session_state["transfer_history"]
    if history:
        st.dataframe([{
            "Season": row["season"], "Player": row["player"],
            "From": row["from_club"], "To": row["to_club"],
            "Fee": format_money(row["fee"]), "Type": row["type"],
        } for row in history], hide_index=True, use_container_width=True)
    else:
        st.write("No completed transfers in this career.")


st.set_page_config(
    page_title="PL Manager · Career Mode", page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded",
)
apply_global_styles(st)
st.markdown(
    """<section class="game-hero">
      <div class="eyebrow">The touchline is yours</div>
      <div class="game-title">Premier League<br>Manager Simulator</div>
      <div class="game-subtitle">Build the squad. Set the standard. Shape a career across every matchday.</div>
    </section>""",
    unsafe_allow_html=True,
)

selected_club = None
if "active_club" not in st.session_state:
    database_label = st.radio(
        "Career Database",
        ["Real Premier League Squads", "Fictional Squads"],
        index=0 if is_api_configured() else 1,
    )
    source = "real" if database_label.startswith("Real") else "fictional"
    selectable_clubs = CLUBS
    if source == "real":
        st.caption(
            "Real Squads creates a snapshot of current API-Football squad data when "
            "your career begins. After kickoff, transfers, development, contracts, "
            "injuries and retirements belong to your simulated career and are not "
            "overwritten by real-world updates."
        )
        try:
            selectable_clubs = [team["name"] for team in get_premier_league_teams()]
        except RealWorldDataError as exc:
            selectable_clubs = []
            st.warning(str(exc))
            st.info("Retry, or choose Fictional Squads to play without the API.")
    selected_club = st.selectbox("Choose your club", selectable_clubs, index=None)
if "active_club" not in st.session_state and st.button("Start Career"):
    if selected_club:
        try:
            with st.spinner("Preparing real Premier League squads..." if source == "real" else "Preparing fictional squads..."):
                # Everything is prepared locally; session state changes only after success.
                squads = build_real_career_squads() if source == "real" else deepcopy(SQUADS)
                clubs = list(squads) if source == "real" else list(CLUBS)
                if selected_club not in squads:
                    raise RealWorldDataError("The selected club is no longer in the returned league snapshot.")
                fixtures = generate_fixtures(clubs, random)
                table = create_league_table(clubs)
                transfer_budgets, wage_budgets = career_budget_mappings(squads)
                assign_default_roles(squads[selected_club])
                new_state = {
                    "active_club": selected_club, "career_source": source,
                    "career_clubs": clubs, "fixtures": fixtures,
                    "league_table": table, "career_squads": squads,
                    "current_gameweek": 1, "completed_gameweeks": set(),
                    "transfer_budget": transfer_budgets[selected_club],
                    "club_transfer_budgets": transfer_budgets,
                    "club_wage_budgets": wage_budgets,
                    "transfer_offers": [], "processed_offer_gameweeks": set(),
                    "transfer_history": [], "transfer_pool": [], "free_agents": [],
                    "player_statistics": create_player_statistics(squads[selected_club]),
                    "recorded_stat_gameweeks": set(), "processed_health_gameweeks": set(),
                    "processed_discipline_gameweeks": set(), "processed_morale_gameweeks": set(),
                    "processed_seasons": set(), "season_number": 1, "career_history": [],
                    "match_history": [], "retirement_history": [],
                    "scouting_knowledge": initialise_scouting(squads, selected_club),
                    "scouting_assignments": [], "scout_reports": [],
                    "processed_scouting_gameweeks": set(), "match_phase": "Kickoff",
                    "navigation": "Dashboard",
                }
                if source == "real":
                    new_state["real_data_season"] = REAL_DATA_SEASON
            st.session_state.update(new_state)
            st.success(f"Welcome to {selected_club}! Your career starts at Gameweek 1.")
        except RealWorldDataError as exc:
            st.error(f"The Real Squads career could not be prepared: {exc}")
            st.info("No career was created. Retry, or choose Fictional Squads.")
    else:
        st.warning("Please choose a club before starting your career.")

if "active_club" in st.session_state:
    active_club = st.session_state["active_club"]
    career_squads = st.session_state["career_squads"]
    squad = career_squads[active_club]
    if st.session_state.get("career_source") == "real":
        st.caption(f"Career database: Real Premier League snapshot · API season {st.session_state.get('real_data_season', REAL_DATA_SEASON)}")
    else:
        st.caption("Career database: Fictional squads")
    gameweek = st.session_state["current_gameweek"]
    fixture = get_club_fixture(st.session_state["fixtures"], gameweek, active_club)
    is_complete = gameweek in st.session_state["completed_gameweeks"]

    initialise_navigation(st.session_state)
    st.sidebar.markdown(
        '<div class="sidebar-brand"><strong>⚽ PL Manager</strong>Career Mode</div>',
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio("Manager Menu", NAVIGATION, key="navigation")
    st.sidebar.caption(
        f"{active_club} · Season {st.session_state['season_number']} · "
        f"Gameweek {gameweek}"
    )

    if page == "Dashboard":
        render_dashboard(st, st.session_state, st.session_state["club_wage_budgets"][active_club], format_money)
        st.stop()
    if page == "Transfers":
        st.header("Transfers")
        transfer_tab, offers_tab = st.tabs(["Market & Free Agents", "Offers & History"])
        with transfer_tab:
            render_transfer_market(active_club, career_squads, squad)
        with offers_tab:
            render_transfer_offers(active_club, career_squads)
        st.stop()
    if page == "Scouting":
        render_scouting(active_club, career_squads)
        st.stop()
    if page == "Contracts":
        st.header("Contracts")
        spend = calculate_wage_spend(squad)
        budget = st.session_state["club_wage_budgets"][active_club]
        cols = st.columns(3)
        cols[0].metric("Current Wage Spend", f"{format_money(spend)}/week")
        cols[1].metric("Wage Budget", f"{format_money(budget)}/week")
        cols[2].metric("Remaining", f"{format_money(budget - spend)}/week")
        contract_name = st.selectbox("Player contract", [p["name"] for p in squad], index=None)
        contract_player = next((p for p in squad if p["name"] == contract_name), None)
        extension = st.selectbox("Contract extension", [1, 2, 3, 4])
        if contract_player:
            st.info(f"{contract_player['contract_years']} year(s) remaining · "
                    f"{format_money(contract_player['wage'])}/week · Requested: "
                    f"{format_money(requested_weekly_wage(contract_player))}/week")
        if st.button("Renew Contract", disabled=contract_player is None):
            success, message = renew_contract(contract_player, extension, squad, budget)
            (st.success if success else st.warning)(message)
        st.stop()
    if page in {"Squad", "Player Stats"}:
        st.header(page)
        sort_by = st.selectbox("Sort by", ["Goals", "Appearances", "Overall", "Form", "Morale", "Player"])
        st.dataframe(get_current_squad_statistics(squad, st.session_state["player_statistics"], sort_by),
                     hide_index=True, use_container_width=True)
        st.caption("Morale is player happiness. Form is recent individual match performance; Potential is projected future Overall.")
        st.stop()
    if page == "League":
        st.header("Premier League")
        st.caption(f"Season {st.session_state['season_number']} · Gameweek {gameweek}")
        st.dataframe(get_sorted_league_table(st.session_state["league_table"]), hide_index=True,
                     use_container_width=True)
        with st.expander("League fixture and result history"):
            if st.session_state.get("gameweek_results"):
                st.dataframe(st.session_state["gameweek_results"], hide_index=True, use_container_width=True)
            else:
                st.write("No results recorded for the current gameweek.")
        st.stop()
    if page == "Career":
        st.header("Career")
        history = st.session_state.setdefault("career_history", [])
        st.subheader("Completed Seasons")
        if history:
            st.dataframe(history, hide_index=True, use_container_width=True)
        else:
            st.info("Complete your first season to begin Career History.")
        st.subheader("Retirement History")
        retirements = st.session_state.setdefault("retirement_history", [])
        if retirements:
            st.dataframe(retirements, hide_index=True, use_container_width=True)
        else:
            st.caption("No players have retired during this career yet.")
        st.stop()
    if page == "Real World Data":
        render_real_world_data()
        st.stop()
    # Tactics shares Matchday because selections and tactical changes are part
    # of the same stateful match flow.  No simulation work occurs when merely
    # switching navigation sections.

    st.header(f"Season {st.session_state['season_number']}")
    st.metric("Transfer Budget", format_money(st.session_state["transfer_budget"]))
    wage_spend = calculate_wage_spend(squad)
    wage_budget = st.session_state["club_wage_budgets"][active_club]
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

    current_phase = st.session_state.setdefault("match_phase", "Kickoff")
    phase_labels = ("Pre-match", "Kickoff", "Half-time", "Second half", "Full-time")
    active_phase = "Pre-match" if current_phase == "Kickoff" else current_phase
    st.markdown(
        '<div class="phase-strip">' + ''.join(
            f'<span class="{"active" if label == active_phase else ""}">{label}</span>'
            for label in phase_labels
        ) + '</div>',
        unsafe_allow_html=True,
    )

    st.subheader(f"{active_club} Squad")
    squad_table = [
        {
            "Player": player["name"],
            "Position": player["position"],
            "Age": player["age"],
            "Overall": player["overall"],
            "Squad Role": ensure_squad_management(player)["squad_role"],
            "Fitness": player.get("fitness", 100),
            "Morale": (
                f"{ensure_player_morale_form(player)['morale']} "
                f"({morale_label(player['morale'])})"
            ),
            "Role Satisfaction": satisfaction_label(player["role_satisfaction"]),
            "Transfer Request": "Yes" if player["transfer_requested"] else "No",
            "Transfer Listed": "Yes" if player["transfer_listed"] else "No",
            "Form": (
                "N/A" if form_score(player) is None
                else f"{form_score(player):.1f} ({form_label(form_score(player))})"
            ),
            "Availability": availability_status(player),
            "Potential": player["potential"],
            "Wage": f"{format_money(player['wage'])}/week",
            "Contract": f"{player['contract_years']} year(s)",
        }
        for player in squad
    ]
    st.dataframe(squad_table, hide_index=True, use_container_width=True)

    st.subheader("Squad Management")
    managed_name = st.selectbox(
        "Manage player", [player["name"] for player in squad], index=None
    )
    managed_player = next((p for p in squad if p["name"] == managed_name), None)
    if managed_player:
        ensure_squad_management(managed_player, squad=squad)
        new_role = st.selectbox(
            "Squad Role", SQUAD_ROLES,
            index=SQUAD_ROLES.index(managed_player["squad_role"]),
        )
        if st.button("Update Squad Role"):
            change_squad_role(managed_player, new_role)
            st.success("Squad Role updated. Satisfaction will adjust gradually.")
        promise = managed_player.get("playing_time_promise")
        if promise and promise["active"]:
            st.info(
                f"Active playing-time promise: {promise['games_elapsed']} / "
                f"{promise['length']} league games, {promise['appearances']} appearances."
            )
        if managed_player["transfer_requested"]:
            col1, col2 = st.columns(2)
            if col1.button("Promise More Playing Time"):
                promise_more_playing_time(managed_player)
                st.success("A five-game playing-time promise is now active.")
            if col2.button("Accept Transfer Request"):
                accept_transfer_request(managed_player)
                st.success("Player marked as transfer listed and remains selectable.")
        list_label = "Remove from Transfer List" if managed_player["transfer_listed"] else "Add to Transfer List"
        if st.button(list_label):
            set_transfer_listed(managed_player, not managed_player["transfer_listed"])
            st.success("Transfer-list status updated.")

    st.subheader("Player Stats")
    stat_sort = st.selectbox(
        "Sort player stats by",
        ["Goals", "Appearances", "Overall", "Form", "Morale", "Player"],
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

    st.subheader("Team Statistics")
    team_stats = calculate_season_aggregates(
        st.session_state.setdefault("match_history", []),
        st.session_state["season_number"],
    )
    stat_columns = st.columns(3)
    stat_columns[0].metric("Average Possession", f"{team_stats['average_possession']:.1f}%")
    stat_columns[1].metric("Total Shots", team_stats["total_shots"])
    stat_columns[2].metric("Shots on Target", team_stats["total_shots_on_target"])
    stat_columns = st.columns(3)
    stat_columns[0].metric("Total xG", f"{team_stats['total_xg']:.2f}")
    stat_columns[1].metric("Average xG", f"{team_stats['average_xg']:.2f}")
    stat_columns[2].metric("Total Goals", team_stats["total_goals"])

    with st.expander("Match History"):
        current_history = [row for row in st.session_state["match_history"]
                           if row["season"] == st.session_state["season_number"]]
        if current_history:
            st.dataframe(current_history, hide_index=True, use_container_width=True)
        else:
            st.write("No league matches completed this season.")

    if not is_complete:
        phase = current_phase
        st.subheader(f"Match Flow: {phase}")
        available_players = [player for player in squad if is_available(player)]
        if len(available_players) < 11:
            st.error(
                f"Only {len(available_players)} healthy players are available. "
                "You cannot play until 11 eligible starters are available."
            )
        formation = st.selectbox(
            "Formation", list(FORMATIONS), key=f"formation_{gameweek}",
            disabled=phase != "Kickoff",
        )
        style = st.selectbox(
            "Tactical style", TACTICAL_STYLES, key=f"style_{gameweek}",
            disabled=phase != "Kickoff",
        )
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
                    first_half["stats"] = generate_half_statistics(
                        strength, opponent_strength, first_half["home_score"],
                        first_half["away_score"], style, "Balanced"
                    )
                else:
                    first_half = simulate_half(opponent_strength, strength, "Balanced", style)
                    first_half["stats"] = generate_half_statistics(
                        opponent_strength, strength, first_half["home_score"],
                        first_half["away_score"], "Balanced", style
                    )
                st.session_state["first_half_result"] = first_half
                st.session_state["kickoff_style"] = style
                st.session_state["kickoff_formation"] = formation
                st.session_state["match_phase"] = "Half-time"
                st.rerun()

        if phase in {"Half-time", "Second half"}:
            formation = st.session_state.get("kickoff_formation", formation)
            style = st.session_state.get("kickoff_style", style)
            first = st.session_state["first_half_result"]
            st.info(f"Half-time: **{fixture['home']} {first['home_score']} - {first['away_score']} {fixture['away']}**")
            half_stats = first["stats"]
            st.markdown(
                f"**Possession:** {half_stats['home']['possession']}% – {half_stats['away']['possession']}%  \n"
                f"**Shots:** {half_stats['home']['shots']} – {half_stats['away']['shots']}  \n"
                f"**Shots on Target:** {half_stats['home']['shots_on_target']} – {half_stats['away']['shots_on_target']}  \n"
                f"**xG:** {half_stats['home']['xg']:.2f} – {half_stats['away']['xg']:.2f}"
            )
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
                    processed_discipline_gameweeks=st.session_state.setdefault(
                        "processed_discipline_gameweeks", set()
                    ),
                    processed_morale_gameweeks=st.session_state.setdefault(
                        "processed_morale_gameweeks", set()
                    ),
                    formation=formation,
                    tactical_style=second_style,
                    bench=bench,
                    substitutions=existing,
                    first_half_result=st.session_state["first_half_result"],
                    career_squads=career_squads,
                )
                st.session_state["match_phase"] = "Full-time"
                user_match = next(result for result in st.session_state["gameweek_results"]
                                  if active_club in (result["home_club"], result["away_club"]))
                record_match_history(
                    st.session_state.setdefault("match_history", []),
                    create_history_record(st.session_state["season_number"], gameweek,
                                          active_club, user_match),
                )
                st.rerun()

    if is_complete:
        completed_reports = process_scouting(
            st.session_state["scouting_assignments"],
            st.session_state["scouting_knowledge"],
            st.session_state["scout_reports"], career_squads,
            st.session_state["season_number"], gameweek,
            st.session_state["processed_scouting_gameweeks"],
            st.session_state["free_agents"],
        )
        for report in completed_reports:
            st.success(
                f"Scout Report Complete: {report['player_name']} — "
                f"{KNOWLEDGE_NAMES[report['knowledge_level']]}"
            )
        new_offers = generate_ai_offers(
            career_squads, active_club,
            st.session_state["club_transfer_budgets"],
            st.session_state["transfer_offers"], gameweek,
            st.session_state["season_number"],
            st.session_state["processed_offer_gameweeks"],
        )
        for offer in new_offers:
            st.info(
                f"Transfer Offer\n\n{offer['buying_club']} have offered "
                f"{format_money(offer['offered_fee'])} for {offer['player']}."
            )
        st.subheader(f"Gameweek {gameweek} Results")
        for result in st.session_state["gameweek_results"]:
            scoreline = (
                f"{result['home_club']} {result['home_score']} - "
                f"{result['away_score']} {result['away_club']}"
            )
            if active_club in (result["home_club"], result["away_club"]):
                st.markdown(
                    '<div class="match-card"><div class="eyebrow">Full Time</div>'
                    f'<div class="match-teams"><span>{escape(result["home_club"])} '
                    f'<strong>{result["home_score"]}</strong></span><span class="versus">—</span>'
                    f'<span><strong>{result["away_score"]}</strong> '
                    f'{escape(result["away_club"])}</span></div>'
                    f'<div class="match-meta">Gameweek {gameweek}</div></div>',
                    unsafe_allow_html=True,
                )
                st.success(f"⭐ **{scoreline}** — Your match")
                stats = result["match_stats"]
                st.markdown("### Match Stats")
                st.dataframe([
                    {"Statistic": "Possession", result["home_club"]: f"{stats['home']['possession']}%", result["away_club"]: f"{stats['away']['possession']}%"},
                    {"Statistic": "Shots", result["home_club"]: stats["home"]["shots"], result["away_club"]: stats["away"]["shots"]},
                    {"Statistic": "Shots on Target", result["home_club"]: stats["home"]["shots_on_target"], result["away_club"]: stats["away"]["shots_on_target"]},
                    {"Statistic": "xG", result["home_club"]: f"{stats['home']['xg']:.2f}", result["away_club"]: f"{stats['away']['xg']:.2f}"},
                ], hide_index=True, use_container_width=True)
                st.write("**Match events:**")
                match_events = [
                    {**event, "label": "Goal"} for event in result["goal_events"]
                ] + [
                    {**event, "label": "Yellow Card" if event["type"] == "yellow" else "Red Card"}
                    for event in result.get("card_events", [])
                ]
                if match_events:
                    for event in sorted(match_events, key=lambda item: item["minute"]):
                        st.write(f"{event['minute']}' {event['label']} — {event['player']}")
                else:
                    st.write("None")
                for event in result.get("injury_events", []):
                    st.error(
                        f"Injury: {event['player']} suffered a {event['injury']}. "
                        f"Out for {event['gameweeks']} gameweek(s)."
                    )
                for player_name in result.get("recovery_events", []):
                    st.success(f"{player_name} has recovered and is available again.")
                for player_name in result.get("suspension_recovery_events", []):
                    st.success(f"{player_name} has served their suspension and is available again.")
                for event in result.get("transfer_request_events", []):
                    st.error(
                        f"Transfer Request\n\n{event['player']} has submitted a transfer "
                        f"request.\n\nReason: {event['reason']}"
                    )
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
                st.session_state.pop("first_half_result", None)
                st.session_state.pop("kickoff_formation", None)
                st.session_state.pop("kickoff_style", None)
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
                start_next_season(st.session_state, st.session_state["career_clubs"])
                st.rerun()
