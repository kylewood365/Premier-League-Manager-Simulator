"""Read-only dashboard calculations and Streamlit presentation helpers.

The functions in this module never mutate career state.  Keeping the summary
logic separate makes navigation reruns safe and keeps simulation code in its
existing modules.
"""

from contracts import calculate_wage_spend
from fitness import is_available
from league import get_sorted_league_table
from morale import ensure_player_morale_form, form_score


NAVIGATION = (
    "Dashboard", "Matchday", "Squad", "Tactics", "Transfers", "Scouting",
    "Contracts", "Player Stats", "League", "Career",
)


def ordinal(number):
    """Return an integer with its English ordinal suffix."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def league_rows(table):
    """Return positioned league rows without changing the authoritative table."""
    return [dict(row, Position=index) for index, row in
            enumerate(get_sorted_league_table(table), 1)]


def next_fixture(fixtures, gameweek, club, table=None):
    """Find the club's next unplayed fixture at or after ``gameweek``."""
    rows = league_rows(table) if table else []
    positions = {row["Club"]: row["Position"] for row in rows}
    for week in range(gameweek, len(fixtures) + 1):
        matches = fixtures[week - 1]
        for match in matches:
            if club not in (match["home"], match["away"]):
                continue
            home = match["home"] == club
            opponent = match["away"] if home else match["home"]
            return {
                "gameweek": week, "home": match["home"], "away": match["away"],
                "opponent": opponent, "venue": "Home" if home else "Away",
                "opponent_position": positions.get(opponent),
            }
    return None


def recent_results(history, season, club, limit=5):
    """Build scorelines for the latest user matches from Match History."""
    matches = [row for row in history if row.get("season") == season]
    output = []
    for row in sorted(matches, key=lambda item: item["gameweek"], reverse=True)[:limit]:
        user_goals, opponent_goals = (int(value) for value in row["score"].split("-"))
        result = "W" if user_goals > opponent_goals else "L" if user_goals < opponent_goals else "D"
        home = row.get("home_away") == "Home"
        output.append({
            "result": result,
            "home_team": club if home else row["opponent"],
            "home_score": user_goals if home else opponent_goals,
            "away_score": opponent_goals if home else user_goals,
            "away_team": row["opponent"] if home else club,
            "gameweek": row["gameweek"],
        })
    return output


def club_form(history, season, club, limit=5):
    """Return chronological W/D/L form based on the shared Match History."""
    return [row["result"] for row in reversed(recent_results(history, season, club, limit))]


def squad_status(squad):
    """Count current health, discipline and squad-management states."""
    injured = sum(bool(player.get("injured")) for player in squad)
    suspended = sum(player.get("suspension_matches", 0) > 0 for player in squad)
    unhappy = sum(player.get("morale", 75) < 50 for player in squad)
    return {
        "squad_size": len(squad),
        "available": sum(is_available(player) for player in squad),
        "injured": injured,
        "suspended": suspended,
        "unhappy": unhappy,
        "transfer_requests": sum(bool(player.get("transfer_requested")) for player in squad),
    }


def top_players(squad, statistics):
    """Identify squad leaders using current squad players only."""
    if not squad:
        return {key: None for key in ("top_scorer", "best_form", "highest_rated", "highest_potential")}
    if isinstance(statistics, dict):
        stat_by_name = {
            name: {"Goals": totals.get("Goals", totals.get("goals", 0)), **totals}
            for name, totals in statistics.items()
        }
    else:
        stat_by_name = {row.get("Player", row.get("name")): row for row in statistics}
    for player in squad:
        ensure_player_morale_form(player)
    scorer = max(squad, key=lambda p: stat_by_name.get(p["name"], {}).get("Goals", 0))
    best = max(squad, key=lambda p: form_score(p) if form_score(p) is not None else float("-inf"))
    return {
        "top_scorer": (scorer, stat_by_name.get(scorer["name"], {}).get("Goals", 0)),
        "best_form": (best, form_score(best)),
        "highest_rated": (max(squad, key=lambda p: p["overall"]), max(p["overall"] for p in squad)),
        "highest_potential": (max(squad, key=lambda p: p["potential"]), max(p["potential"] for p in squad)),
    }


def financial_summary(squad, transfer_budget, wage_budget):
    spend = calculate_wage_spend(squad)
    return {"transfer_budget": transfer_budget, "wage_spend": spend,
            "wage_budget": wage_budget, "wage_remaining": wage_budget - spend}


def career_summary(history, club):
    finishes = [entry["user_position"] for entry in history]
    return {"seasons_completed": len(history), "best_finish": min(finishes) if finishes else None,
            "titles": sum(entry.get("champion") == club or entry["user_position"] == 1 for entry in history)}


def initialise_navigation(state):
    """Add UI-only navigation state without replacing any career values."""
    state.setdefault("navigation", "Dashboard")
    return state["navigation"]


def render_dashboard(st, state, wage_budget, format_money):
    """Render the active-career dashboard from existing state."""
    club, season, gameweek = state["active_club"], state["season_number"], state["current_gameweek"]
    squad, table = state["career_squads"][club], state["league_table"]
    rows = league_rows(table)
    club_row = next(row for row in rows if row["Club"] == club)
    finances = financial_summary(squad, state["transfer_budget"], wage_budget)
    st.header(f"{club} Manager Dashboard")
    cols = st.columns(4)
    for column, label, value in zip(cols, ("Career Season", "Gameweek", "League Position", "Points"),
                                    (season, gameweek, ordinal(club_row["Position"]), club_row["Points"])):
        column.metric(label, value)
    cols = st.columns(3)
    cols[0].metric("Transfer Budget", format_money(finances["transfer_budget"]))
    cols[1].metric("Wage Budget Remaining", f'{format_money(finances["wage_remaining"])}/week')
    cols[2].metric("Club Form", " ".join(club_form(state.get("match_history", []), season, club)) or "—")

    fixture = next_fixture(state["fixtures"], gameweek, club, table)
    st.subheader("Next Match")
    if fixture:
        st.caption(f'Gameweek {fixture["gameweek"]}')
        st.markdown(f'### {fixture["home"]}  vs  {fixture["away"]}')
        detail = fixture["venue"]
        if fixture["opponent_position"]:
            detail += f' · {fixture["opponent"]} league position: {ordinal(fixture["opponent_position"])}'
        st.info(detail)
    else:
        st.info("No remaining league fixture this season.")

    left, right = st.columns(2)
    with left:
        st.subheader("Recent Results")
        results = recent_results(state.get("match_history", []), season, club)
        if not results:
            st.caption("No league matches completed this season.")
        for result in results:
            st.write(f'**{result["result"]}**  {result["home_team"]} {result["home_score"]}-{result["away_score"]} {result["away_team"]}')
    with right:
        st.subheader("League Summary")
        preview = rows[:5]
        if club not in {row["Club"] for row in preview}:
            preview.append(club_row)
        st.dataframe([{"Pos": row["Position"], "Club": f'⭐ {row["Club"]}' if row["Club"] == club else row["Club"],
                       "P": row["Played"], "Pts": row["Points"]} for row in preview],
                     hide_index=True, use_container_width=True)
        st.caption("Open League from the sidebar for the full table.")

    status = squad_status(squad)
    st.subheader("Squad Status")
    cols = st.columns(6)
    for column, key, label in zip(cols, status, ("Squad Size", "Available", "Injured", "Suspended", "Unhappy", "Transfer Requests")):
        column.metric(label, status[key])
    st.caption("Morale describes happiness; player Form is recent individual performance.")

    leaders = top_players(squad, state.get("player_statistics", {}))
    st.subheader("Top Players")
    cols = st.columns(4)
    labels = (("top_scorer", "Top Scorer", "goals"), ("best_form", "Best Form", "Form"),
              ("highest_rated", "Highest Rated", "Overall"), ("highest_potential", "Highest Potential", "Potential"))
    for column, (key, label, unit) in zip(cols, labels):
        player, value = leaders[key]
        column.metric(label, player["name"], f'{"—" if value is None else value} {unit}')
    st.caption("Potential is an estimate of a player's possible future Overall.")

    left, right = st.columns(2)
    with left:
        st.subheader("Club Finances")
        for label, key in (("Transfer Budget", "transfer_budget"), ("Current Wage Spend", "wage_spend"),
                           ("Wage Budget", "wage_budget"), ("Remaining Wage Budget", "wage_remaining")):
            st.metric(label, format_money(finances[key]) + ("" if key == "transfer_budget" else "/week"))
    with right:
        st.subheader("Transfer Activity")
        st.metric("Pending AI Offers", sum(o.get("status") in {"Pending", "Countered"} for o in state.get("transfer_offers", [])))
        st.metric("Active Scouting Assignments", len(state.get("scouting_assignments", [])))
        st.metric("Transfer-listed Players", sum(bool(p.get("transfer_listed")) for p in squad))
        st.metric("Free Agents", len(state.get("free_agents", [])))

    summary = career_summary(state.get("career_history", []), club)
    st.subheader("Career Summary")
    cols = st.columns(3)
    cols[0].metric("Seasons Completed", summary["seasons_completed"])
    cols[1].metric("Best League Finish", ordinal(summary["best_finish"]) if summary["best_finish"] else "Not yet")
    cols[2].metric("Premier League Titles", summary["titles"])
    if not summary["seasons_completed"]:
        st.caption("Complete your first season to begin your career history.")
