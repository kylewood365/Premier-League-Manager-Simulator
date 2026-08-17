"""Shared visual styling for the Streamlit football management interface.

This module is deliberately presentation-only.  It reads an optional local
image and injects CSS, but never reads or changes game/session state.
"""

from base64 import b64encode
from functools import lru_cache
from pathlib import Path


ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets"
STADIUM_BACKGROUND = ASSET_DIRECTORY / "stadium-background.png"


@lru_cache(maxsize=1)
def background_image_data(path=STADIUM_BACKGROUND):
    """Return a CSS data URL for the optional stadium image, or ``None``.

    Caching prevents the image from being read and encoded on every Streamlit
    rerun.  An absent or unreadable custom asset always falls back safely.
    """
    try:
        image = Path(path)
        if not image.is_file():
            return None
        return f"data:image/jpeg;base64,{b64encode(image.read_bytes()).decode('ascii')}"
    except OSError:
        return None


def build_global_css(background=None):
    """Build the theme CSS, optionally using a pre-encoded background URL."""
    backdrop = (
        f"linear-gradient(rgba(3, 10, 20, .88), rgba(3, 10, 20, .96)), url('{background}')"
        if background
        else "radial-gradient(circle at 75% 0%, #123b43 0%, #071522 34%, #030912 100%)"
    )
    return f"""
    <style>
    :root {{
      --background: #030912; --panel: rgba(10, 25, 38, .82);
      --panel-strong: rgba(8, 21, 33, .94); --primary: #35e0a1;
      --secondary: #55a8ff; --text: #f5f8fb; --muted: #a7b4c1;
      --warning: #f5b942; --danger: #ff6577; --success: #35e0a1;
      --border: rgba(130, 230, 197, .18); --radius: 15px;
    }}
    html, body, [class*="css"] {{
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif; color: var(--text);
    }}
    .stApp {{ background: {backdrop}; background-size: cover; background-position: center;
      background-attachment: fixed; color: var(--text); }}
    [data-testid="stAppViewContainer"] > .main {{ background: transparent; }}
    .block-container {{ max-width: 1380px; padding-top: 2rem; padding-bottom: 4rem; }}
    h1, h2, h3, [data-testid="stHeading"] {{
      color: var(--text) !important; font-family: "Arial Narrow", "Roboto Condensed",
        Inter, sans-serif !important; font-weight: 800 !important;
      letter-spacing: .055em !important; text-transform: uppercase;
    }}
    h1 {{ font-size: clamp(2rem, 4vw, 3.6rem) !important; line-height: .98 !important; }}
    p, label, .stCaption {{ color: var(--text); }}
    [data-testid="stCaptionContainer"] {{ color: var(--muted); }}
    [data-testid="stSidebar"] {{ background: rgba(3, 12, 22, .96); border-right: 1px solid var(--border); }}
    [data-testid="stSidebar"] > div {{ background: transparent; }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{
      padding: .62rem .7rem; margin: .15rem 0; border-radius: 10px; transition: .18s ease;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
      background: rgba(53, 224, 161, .10); transform: translateX(2px);
    }}
    [data-testid="stSidebar"] [aria-checked="true"] {{
      background: rgba(53, 224, 161, .15); border: 1px solid rgba(53, 224, 161, .28);
    }}
    .sidebar-brand {{ padding: .4rem 0 1rem; color: var(--muted); font-size: .72rem;
      font-weight: 700; letter-spacing: .15em; text-transform: uppercase; }}
    .sidebar-brand strong {{ display: block; color: var(--primary); font-size: 1.2rem;
      line-height: 1.15; letter-spacing: .08em; margin-bottom: .35rem; }}
    [data-testid="stMetric"] {{ background: var(--panel); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: 0 12px 32px rgba(0,0,0,.18); }}
    [data-testid="stMetricLabel"] {{ color: var(--muted); text-transform: uppercase;
      letter-spacing: .08em; font-weight: 700; }}
    [data-testid="stMetricValue"] {{ color: var(--text); font-weight: 800; }}
    [data-testid="stDataFrame"], [data-testid="stTable"], [data-testid="stExpander"],
    [data-testid="stForm"], div[data-testid="stAlert"] {{ border-radius: var(--radius);
      overflow: hidden; border: 1px solid var(--border); box-shadow: 0 12px 30px rgba(0,0,0,.15); }}
    [data-testid="stDataFrame"] {{ background: var(--panel); padding: .25rem; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: .4rem; border-bottom: 1px solid var(--border); }}
    .stTabs [data-baseweb="tab"] {{ border-radius: 10px 10px 0 0; padding: .6rem 1rem;
      font-weight: 750; letter-spacing: .03em; }}
    .stTabs [aria-selected="true"] {{ color: var(--primary) !important; background: rgba(53,224,161,.1); }}
    .stButton > button {{ border-radius: 11px; padding: .58rem 1.15rem; min-height: 2.7rem;
      font-weight: 800; letter-spacing: .035em; border: 1px solid rgba(53,224,161,.55);
      color: #03130e; background: linear-gradient(135deg, #4ae8ad, #20c88d);
      box-shadow: 0 8px 22px rgba(32,200,141,.18); transition: .18s ease; }}
    .stButton > button:hover {{ border-color: #8affd4; color: #02100c;
      transform: translateY(-1px); box-shadow: 0 10px 26px rgba(32,200,141,.3); }}
    .stButton > button:disabled {{ background: #26323b; color: #89949d; border-color: #3a4650; }}
    input, [data-baseweb="select"] > div, [data-baseweb="base-input"] {{
      background-color: rgba(7, 18, 29, .9) !important; border-color: var(--border) !important;
      border-radius: 10px !important; color: var(--text) !important;
    }}
    .game-hero {{ background: linear-gradient(125deg, rgba(8,28,39,.94), rgba(12,48,50,.78));
      border: 1px solid rgba(53,224,161,.3); border-radius: 20px; padding: clamp(1.3rem,3vw,2.4rem);
      margin: .4rem 0 1.4rem; box-shadow: 0 22px 55px rgba(0,0,0,.28); position: relative; overflow: hidden; }}
    .game-hero:after {{ content:""; position:absolute; width:240px; height:240px; right:-80px;
      top:-110px; border: 35px solid rgba(53,224,161,.06); border-radius:50%; }}
    .eyebrow {{ color: var(--primary); font-weight: 800; letter-spacing: .16em;
      text-transform: uppercase; font-size: .74rem; }}
    .game-title {{ color: white; font: 900 clamp(2.1rem,5vw,4.8rem)/.88 "Arial Narrow", Inter, sans-serif;
      text-transform: uppercase; letter-spacing: .025em; margin: .55rem 0 .8rem; }}
    .game-subtitle {{ color: var(--muted); max-width: 640px; font-size: 1.02rem; }}
    .match-card {{ text-align:center; background: linear-gradient(145deg, rgba(9,26,40,.94), rgba(11,49,48,.82));
      border: 1px solid rgba(53,224,161,.28); border-radius: 18px; padding: 1.6rem; margin: .5rem 0 1.3rem; }}
    .match-teams {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:1rem;
      margin: 1rem 0; font-family:"Arial Narrow", Inter, sans-serif; font-size:clamp(1.25rem,3vw,2.2rem);
      font-weight:900; text-transform:uppercase; }}
    .versus {{ color:var(--primary); font-size:.8em; letter-spacing:.12em; }}
    .match-meta {{ color:var(--muted); font-size:.83rem; letter-spacing:.1em; text-transform:uppercase; }}
    .form-row {{ display:flex; gap:.55rem; flex-wrap:wrap; margin:.5rem 0 1rem; }}
    .form-badge {{ display:inline-flex; width:2.2rem; height:2.2rem; align-items:center; justify-content:center;
      border-radius:50%; font-weight:900; border:1px solid currentColor; }}
    .form-W {{ color:#53e6a9; background:rgba(53,224,161,.12); }}
    .form-D {{ color:#f5c45b; background:rgba(245,185,66,.12); }}
    .form-L {{ color:#ff7887; background:rgba(255,101,119,.12); }}
    .phase-strip {{ display:flex; justify-content:space-between; gap:.25rem; padding:.8rem;
      background:var(--panel); border:1px solid var(--border); border-radius:12px; margin:.5rem 0 1rem;
      color:var(--muted); font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:.04em; }}
    .phase-strip .active {{ color:var(--primary); }}
    @media (max-width: 700px) {{ .block-container {{ padding: 1rem; }}
      .match-teams {{ grid-template-columns:1fr; }} .phase-strip {{ overflow-x:auto; justify-content:flex-start; }} }}
    </style>
    """


def apply_global_styles(st):
    """Apply the global theme once near application startup."""
    st.markdown(build_global_css(background_image_data()), unsafe_allow_html=True)

