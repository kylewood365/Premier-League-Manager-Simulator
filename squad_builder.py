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


def _short_name(name, limit=15):
    """Keep tactical-card names compact without changing stored player data."""
    if len(name) <= limit:
        return name
    parts = name.split()
    shortened = f"{parts[0][0]}. {parts[-1]}" if len(parts) > 1 else name
    return shortened[:limit - 1] + "…" if len(shortened) > limit else shortened


def _card_label(player, position, out_of_position=False, empty=False, compact=False):
    if empty:
        return f"＋\n{position}"
    warning = "\n⚠ OOP" if out_of_position else ""
    fitness = player.get("fitness")
    fitness_text = f"{fitness}% FIT" if fitness is not None else "FIT —"
    if compact:
        return (f"{player.get('overall', '—')}  ·  {player.get('position', position)}\n"
                f"{_initials(player['name'])}\n{_short_name(player['name'], 11)}")
    return (f"{player.get('overall', '—')}  ·  {position}\n"
            f"◯  {_initials(player['name'])}  ◯\n{_short_name(player['name'])}\n"
            f"{fitness_text}  ·  CHANGE{warning}")


def squad_builder_css():
    """CSS scoped to squad-builder marker containers."""
    return """
    <style>
    .squad-progress-head{display:flex;justify-content:space-between;align-items:center;margin:.8rem 0 .35rem;
      font-weight:900;letter-spacing:.09em}.squad-progress-head span:last-child{color:#35e0a1}
    .squad-progress{height:5px;background:#132b35;border-radius:9px;overflow:hidden;margin-bottom:1rem}
    .squad-progress i{display:block;height:100%;background:linear-gradient(90deg,#35e0a1,#55a8ff);box-shadow:0 0 12px #35e0a1}
    [class*="st-key-squad_pitch_"]{background:
      linear-gradient(180deg,rgba(2,18,18,.12),rgba(1,12,18,.28)),
      repeating-linear-gradient(90deg,#0b3831 0,#0b3831 12.5%,#0d4036 12.5%,#0d4036 25%);
      border:1px solid rgba(115,220,190,.5)!important;border-radius:24px!important;
      box-shadow:inset 0 0 70px rgba(0,5,8,.6),0 22px 55px rgba(0,0,0,.34);position:relative;
      overflow:hidden;padding:1.25rem 1.1rem!important;isolation:isolate}
    [class*="st-key-squad_pitch_"] > div{position:relative;z-index:2}
    .squad-pitch-marker{height:0}.pitch-row-gap{height:clamp(.35rem,.8vw,.7rem)}
    .pitch-geometry,.pitch-geometry *{position:absolute;pointer-events:none;box-sizing:border-box}
    .pitch-geometry{position:absolute!important;z-index:0!important;inset:12px!important;width:auto!important;height:auto!important;border:1px solid rgba(213,255,241,.34);border-radius:9px}
    .pitch-halfway{left:0;right:0;top:50%;border-top:1px solid rgba(213,255,241,.3)}
    .pitch-circle{width:104px;height:104px;border:1px solid rgba(213,255,241,.3);border-radius:50%;left:50%;top:50%;transform:translate(-50%,-50%)}
    .pitch-spot{width:5px;height:5px;background:rgba(213,255,241,.5);border-radius:50%;left:50%;top:50%;transform:translate(-50%,-50%)}
    .pitch-box{width:48%;height:13%;border:1px solid rgba(213,255,241,.3);left:26%}
    .pitch-box.top{top:-1px}.pitch-box.bottom{bottom:-1px}
    .pitch-six{width:23%;height:5.5%;border:1px solid rgba(213,255,241,.3);left:38.5%}
    .pitch-six.top{top:-1px}.pitch-six.bottom{bottom:-1px}
    .pitch-goal{width:14%;height:8px;border:1px solid rgba(213,255,241,.34);left:43%}
    .pitch-goal.top{top:-9px}.pitch-goal.bottom{bottom:-9px}
    [class*="st-key-squad_pitch_"] .stButton button{white-space:pre-line;width:100%;height:102px!important;min-height:102px!important;max-height:102px!important;
      overflow:hidden;padding:.46rem .22rem;color:#ecf7f4;background:linear-gradient(160deg,rgba(8,29,39,.96),rgba(4,17,28,.98));
      border:1px solid rgba(83,189,168,.54);border-radius:15px 15px 19px 19px;font-size:clamp(.59rem,.9vw,.76rem);line-height:1.34;
      box-shadow:inset 0 1px rgba(255,255,255,.035),0 9px 22px rgba(0,0,0,.38);transition:.18s ease}
    [class*="st-key-squad_pitch_"] .stButton button p{white-space:pre-line;overflow:hidden;max-height:88px;font-weight:750;letter-spacing:.035em}
    [class*="st-key-squad_pitch_"] [class*="_empty"] button{color:#44daa7;background:linear-gradient(160deg,rgba(7,29,36,.76),rgba(4,17,27,.82));border-style:dashed;border-color:rgba(70,202,165,.46);font-size:.8rem}
    [class*="st-key-squad_pitch_"] [class*="_filled"] button{border-color:rgba(91,190,181,.62)}
    [class*="st-key-squad_pitch_"] [class*="_oop"] button{border-color:rgba(242,177,67,.8);box-shadow:inset 0 -3px rgba(242,177,67,.2),0 9px 22px rgba(0,0,0,.38)}
    [class*="st-key-squad_pitch_"] .stButton button:hover{color:white;border-color:#42dfa8;background:linear-gradient(155deg,#103c43,#071f2e);transform:translateY(-2px);box-shadow:0 0 0 1px rgba(66,223,168,.2),0 11px 25px rgba(0,0,0,.42)}
    .selector-title{margin-top:1rem;padding:.7rem 1rem;border-left:3px solid #35e0a1;background:rgba(9,29,41,.75);font-weight:900;letter-spacing:.1em}
    .squad-bench-marker{height:0}
    [class*="st-key-squad_bench_"]{background:linear-gradient(145deg,rgba(6,21,33,.94),rgba(8,35,39,.84));border:1px solid rgba(78,190,165,.28)!important;border-radius:17px!important;padding:.9rem!important}
    [class*="st-key-squad_bench_"] .stButton button{white-space:pre-line;width:100%;height:88px!important;min-height:88px!important;max-height:88px!important;overflow:hidden;padding:.3rem .1rem;color:#eaf5f2;background:linear-gradient(155deg,rgba(11,37,46,.96),rgba(5,20,31,.98));border:1px solid rgba(72,185,160,.44);border-radius:12px 12px 15px 15px;font-size:clamp(.53rem,.78vw,.68rem);line-height:1.2}
    [class*="st-key-squad_bench_"] .stButton button p{white-space:pre-line;overflow:hidden;max-height:76px}
    [class*="st-key-squad_bench_"] [class*="_empty"] button{color:#43d7a4;border-style:dashed;background:rgba(5,22,31,.72)}
    [class*="st-key-squad_bench_"] .stButton button:hover{border-color:#42dfa8;background:#0d343b;transform:translateY(-2px)}
    @media(max-width:700px){[class*="st-key-squad_pitch_"]{padding:1rem .55rem!important}[class*="st-key-squad_pitch_"] .stButton button{height:88px!important;min-height:88px!important;max-height:88px!important;font-size:.52rem;padding:.12rem}.pitch-circle{width:72px;height:72px}.pitch-row-gap{height:.35rem}[class*="st-key-squad_bench_"]{overflow-x:auto}}
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
    with st.container(border=True, key=f"squad_pitch_{selected_key}"):
        st.markdown(
            '<div class="squad-pitch-marker"></div><div class="pitch-geometry">'
            '<i class="pitch-halfway"></i><i class="pitch-circle"></i><i class="pitch-spot"></i>'
            '<i class="pitch-box top"></i><i class="pitch-box bottom"></i>'
            '<i class="pitch-six top"></i><i class="pitch-six bottom"></i>'
            '<i class="pitch-goal top"></i><i class="pitch-goal bottom"></i></div>',
            unsafe_allow_html=True,
        )
        rows = formation_slots(formation)
        for row_index, row in enumerate(rows):
            side = max(0.12, (5 - len(row)) / 2)
            columns = st.columns([side] + [1] * len(row) + [side], gap="small")
            for column, slot in zip(columns[1:-1], row):
                identifier = assignments.get(slot["key"])
                player = by_id.get(identifier)
                out_of_position = player is not None and not is_position_match(player, slot)
                label = _card_label(player, slot["label"], out_of_position, empty=player is None)
                card_state = "empty" if player is None else ("oop" if out_of_position else "filled")
                if column.button(
                    label, key=f"pick_{selected_key}_{slot['key']}_{card_state}",
                    help=(f"Change {player['name']}" if player else f"Select a {slot['label']}"),
                    disabled=disabled, use_container_width=True,
                ):
                    st.session_state[active_key] = slot["key"]
            if row_index < len(rows) - 1:
                st.markdown('<div class="pitch-row-gap"></div>', unsafe_allow_html=True)

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
    with st.container(border=True, key=f"squad_bench_{bench_key}"):
        st.markdown('<div class="squad-bench-marker"></div>', unsafe_allow_html=True)
        bench_columns = st.columns(7, gap="small")
        for index, column in enumerate(bench_columns):
            player = by_id.get(bench_ids[index]) if index < len(bench_ids) else None
            label = _card_label(player, "SUB", empty=player is None, compact=True)
            card_state = "filled" if player else "empty"
            if column.button(
                label, key=f"benchslot_{bench_key}_{index}_{card_state}",
                help=(f"Change {player['name']}" if player else "Select a substitute"),
                disabled=disabled, use_container_width=True,
            ):
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
