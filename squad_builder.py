"""Streamlit-native matchday squad builder presentation and state helpers."""

from html import escape

from tactics import FORMATIONS, POSITION_GROUPS


# These are visual labels only.  Eligibility continues to come from FORMATIONS and
# POSITION_GROUPS, the same rules used by matchday validation.
FORMATION_LAYOUTS = {
    "4-3-3": (("ST",), ("LW", "RW"), ("CM", "CM"), ("CDM",), ("LB", "CB", "CB", "RB"), ("GK",)),
    "4-2-3-1": (("ST",), ("LM", "CAM", "RM"), ("CDM", "CDM"), ("LB", "CB", "CB", "RB"), ("GK",)),
    "4-4-2": (("ST", "ST"), ("LM", "CM", "CM", "RM"), ("LB", "CB", "CB", "RB"), ("GK",)),
    "3-5-2": (("ST", "ST"), ("LM", "CM", "CAM", "CM", "RM"), ("CB", "CB", "CB"), ("GK",)),
    "5-3-2": (("ST", "ST"), ("CM", "CM", "CM"), ("LWB", "CB", "CB", "CB", "RWB"), ("GK",)),
}

DISPLAY_TO_RULE = {
    "GK": "GK", "CB": "CB", "LB": "DEF", "RB": "DEF", "LWB": "DEF", "RWB": "DEF",
    "CM": "MID", "CDM": "MID", "LM": "MID", "RM": "MID", "CAM": "AM",
    "LW": "FWD", "RW": "FWD", "ST": "ST",
}


def formation_slots(formation):
    """Return stable, unique slot records in top-to-bottom visual order."""
    if formation not in FORMATIONS:
        raise ValueError("Unknown formation.")
    seen = {}
    slots = []
    for row_index, row in enumerate(FORMATION_LAYOUTS[formation]):
        row_slots = []
        for label in row:
            seen[label] = seen.get(label, 0) + 1
            row_slots.append({"key": f"{label}_{seen[label]}", "label": label,
                              "rule": DISPLAY_TO_RULE[label]})
        slots.append(row_slots)
    return slots


def is_position_match(player, slot):
    """Use the match engine's existing compatibility groups for a visual slot."""
    return player.get("position") in POSITION_GROUPS[slot["rule"]]


def reconcile_assignments(assignments, selected_ids, players, formation):
    """Retain selections across reruns/formations, preferring compatible slots."""
    flat_slots = [slot for row in formation_slots(formation) for slot in row]
    valid_ids = {player["id"] for player in players}
    wanted = [identifier for identifier in selected_ids if identifier in valid_ids]
    by_id = {player["id"]: player for player in players}
    result, used = {}, set()
    for slot in flat_slots:
        identifier = assignments.get(slot["key"])
        if identifier in wanted and identifier not in used:
            result[slot["key"]] = identifier
            used.add(identifier)
    for identifier in wanted:
        if identifier in used:
            continue
        open_slots = [slot for slot in flat_slots if slot["key"] not in result]
        compatible = [slot for slot in open_slots if is_position_match(by_id[identifier], slot)]
        if open_slots:
            chosen = (compatible or open_slots)[0]
            result[chosen["key"]] = identifier
            used.add(identifier)
    return result


def _initials(name):
    return "".join(part[0] for part in name.split()[:2]).upper()


def _card_label(player, position, out_of_position=False, empty=False, compact=False):
    if empty:
        return f"＋\n{position}"
    warning = "\n⚠ OOP" if out_of_position else ""
    fitness = player.get("fitness")
    fitness_text = f"  ·  {fitness}% FIT" if fitness is not None else ""
    return (f"{position}  ·  {player.get('overall', '—')}\n"
            f"{_initials(player['name'])}\n{player['name']}\n"
            f"{player.get('position', '—')}{fitness_text}{warning}")


def squad_builder_css():
    """CSS scoped to squad-builder marker containers."""
    return """
    <style>
    .squad-progress-head{display:flex;justify-content:space-between;align-items:center;margin:.8rem 0 .35rem;
      font-weight:900;letter-spacing:.09em}.squad-progress-head span:last-child{color:#35e0a1}
    .squad-progress{height:5px;background:#132b35;border-radius:9px;overflow:hidden;margin-bottom:.8rem}
    .squad-progress i{display:block;height:100%;background:linear-gradient(90deg,#35e0a1,#55a8ff);box-shadow:0 0 12px #35e0a1}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-pitch-marker){background:
      linear-gradient(rgba(7,35,38,.82),rgba(5,27,34,.94)),repeating-linear-gradient(0deg,transparent 0 12.3%,rgba(68,170,128,.06) 12.5% 25%);
      border:1px solid rgba(78,228,180,.45)!important;border-radius:22px!important;box-shadow:inset 0 0 45px rgba(0,0,0,.32),0 18px 45px rgba(0,0,0,.25);position:relative}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-pitch-marker):before{content:"";position:absolute;inset:12px;border:1px solid rgba(190,255,229,.22);border-radius:10px;pointer-events:none}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-pitch-marker):after{content:"";position:absolute;left:12px;right:12px;top:50%;border-top:1px solid rgba(190,255,229,.22);pointer-events:none}
    .squad-pitch-marker{height:0}.pitch-row-gap{height:.18rem}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-pitch-marker) .stButton button{white-space:pre-line;width:100%;min-height:94px;padding:.35rem .18rem;color:#f5f8fb;
      background:linear-gradient(155deg,rgba(14,49,58,.96),rgba(6,22,34,.98));border:1px solid rgba(72,225,177,.58);font-size:clamp(.62rem,1vw,.78rem);line-height:1.25;box-shadow:0 8px 18px rgba(0,0,0,.34)}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-pitch-marker) .stButton button:hover{color:white;background:linear-gradient(155deg,#123f47,#092837);transform:translateY(-2px)}
    .selector-title{margin-top:1rem;padding:.7rem 1rem;border-left:3px solid #35e0a1;background:rgba(9,29,41,.75);font-weight:900;letter-spacing:.1em}
    .squad-bench-marker{height:0}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-bench-marker){background:rgba(7,22,34,.86);border:1px solid rgba(78,228,180,.24)!important;border-radius:16px!important}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.squad-bench-marker) .stButton button{white-space:pre-line;width:100%;min-height:86px;padding:.3rem .12rem;color:#f5f8fb;background:linear-gradient(155deg,rgba(14,49,58,.96),rgba(6,22,34,.98));border:1px solid rgba(72,225,177,.46);font-size:clamp(.58rem,.9vw,.72rem);line-height:1.2}
    @media(max-width:700px){[data-testid="stVerticalBlockBorderWrapper"]:has(.squad-pitch-marker) .stButton button{min-height:76px;font-size:.55rem;padding:.15rem}}
    </style>"""


def render_squad_builder(st, players, formation, selected_key, bench_key, disabled=False):
    """Render the pitch, selectors and bench while updating legacy ID-list keys."""
    st.markdown(squad_builder_css(), unsafe_allow_html=True)
    assignments_key = f"{selected_key}_slots"
    assignments = reconcile_assignments(
        st.session_state.get(assignments_key, {}), st.session_state.get(selected_key, []),
        players, formation,
    )
    by_id = {player["id"]: player for player in players}
    active_key = f"{selected_key}_active"
    bench_active_key = f"{bench_key}_active"
    selected_count = len(assignments)
    complete = selected_count == 11
    st.markdown(
        f'<div class="squad-progress-head"><span>STARTING XI</span><span>{selected_count} / 11 '
        f'{"✓" if complete else "SELECTED"}</span></div><div class="squad-progress"><i style="width:{selected_count / 11 * 100:.1f}%"></i></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown('<div class="squad-pitch-marker"></div>', unsafe_allow_html=True)
        for row in formation_slots(formation):
            side = max(0.12, (5 - len(row)) / 2)
            columns = st.columns([side] + [1] * len(row) + [side], gap="small")
            for column, slot in zip(columns[1:-1], row):
                identifier = assignments.get(slot["key"])
                player = by_id.get(identifier)
                label = _card_label(player, slot["label"], player is not None and not is_position_match(player, slot), empty=player is None)
                if column.button(label, key=f"pick_{selected_key}_{slot['key']}", disabled=disabled, use_container_width=True):
                    st.session_state[active_key] = slot["key"]

    flat_slots = [slot for row in formation_slots(formation) for slot in row]
    active_slot = next((slot for slot in flat_slots if slot["key"] == st.session_state.get(active_key)), None)
    if active_slot and not disabled:
        st.markdown(f'<div class="selector-title">SELECT {escape(active_slot["label"])}</div>', unsafe_allow_html=True)
        search = st.text_input("Search player", key=f"search_{selected_key}_{active_slot['key']}", placeholder="Search the squad…")
        used = set(assignments.values()) - {assignments.get(active_slot["key"])}
        choices = [p for p in players if p["id"] not in used and search.lower() in p["name"].lower()]
        choices.sort(key=lambda p: (not is_position_match(p, active_slot), -p.get("overall", 0), p["name"]))
        for start in range(0, len(choices), 4):
            for column, player in zip(st.columns(4), choices[start:start + 4]):
                oop = not is_position_match(player, active_slot)
                if column.button(_card_label(player, active_slot["label"], oop), key=f"choose_{selected_key}_{active_slot['key']}_{player['id']}", use_container_width=True):
                    assignments[active_slot["key"]] = player["id"]
                    st.session_state[active_key] = None
                    st.session_state[assignments_key] = assignments
                    st.session_state[selected_key] = list(assignments.values())
                    st.rerun()
        actions = st.columns([1, 1, 2])
        if assignments.get(active_slot["key"]) and actions[0].button("Remove player", key=f"remove_{selected_key}_{active_slot['key']}"):
            assignments.pop(active_slot["key"], None)
            st.session_state[active_key] = None
            st.session_state[assignments_key] = assignments
            st.session_state[selected_key] = list(assignments.values())
            st.rerun()
        if actions[1].button("Close", key=f"close_{selected_key}_{active_slot['key']}"):
            st.session_state[active_key] = None
            st.rerun()

    st.session_state[assignments_key] = assignments
    st.session_state[selected_key] = list(assignments.values())
    bench_ids = [identifier for identifier in st.session_state.get(bench_key, [])
                 if identifier in by_id and identifier not in assignments.values()][:7]
    st.session_state[bench_key] = bench_ids
    st.markdown(f'<div class="squad-progress-head"><span>SUBSTITUTES</span><span>{len(bench_ids)} / 7</span></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="squad-bench-marker"></div>', unsafe_allow_html=True)
        bench_columns = st.columns(7, gap="small")
        for index, column in enumerate(bench_columns):
            player = by_id.get(bench_ids[index]) if index < len(bench_ids) else None
            label = _card_label(player, "SUB", empty=player is None, compact=True)
            if column.button(label, key=f"benchslot_{bench_key}_{index}", disabled=disabled, use_container_width=True):
                st.session_state[bench_active_key] = index

    bench_index = st.session_state.get(bench_active_key)
    if bench_index is not None and not disabled:
        st.markdown('<div class="selector-title">SELECT SUBSTITUTE</div>', unsafe_allow_html=True)
        search = st.text_input("Search substitutes", key=f"search_{bench_key}_{bench_index}", placeholder="Search the squad…")
        excluded = set(assignments.values()) | (set(bench_ids) - ({bench_ids[bench_index]} if bench_index < len(bench_ids) else set()))
        choices = [p for p in players if p["id"] not in excluded and search.lower() in p["name"].lower()]
        choices.sort(key=lambda p: (-p.get("overall", 0), p["name"]))
        for start in range(0, len(choices), 4):
            for column, player in zip(st.columns(4), choices[start:start + 4]):
                if column.button(_card_label(player, player.get("position", "SUB")), key=f"benchchoose_{bench_key}_{bench_index}_{player['id']}", use_container_width=True):
                    if bench_index < len(bench_ids):
                        bench_ids[bench_index] = player["id"]
                    else:
                        bench_ids.append(player["id"])
                    st.session_state[bench_key] = bench_ids
                    st.session_state[bench_active_key] = None
                    st.rerun()
        actions = st.columns([1, 1, 2])
        if bench_index < len(bench_ids) and actions[0].button("Remove substitute", key=f"benchremove_{bench_key}_{bench_index}"):
            bench_ids.pop(bench_index)
            st.session_state[bench_key] = bench_ids
            st.session_state[bench_active_key] = None
            st.rerun()
        if actions[1].button("Close", key=f"benchclose_{bench_key}_{bench_index}"):
            st.session_state[bench_active_key] = None
            st.rerun()

    return list(assignments.values()), bench_ids
