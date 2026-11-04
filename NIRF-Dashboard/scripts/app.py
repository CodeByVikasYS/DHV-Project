from __future__ import annotations

from pathlib import Path
import os
import re
import html
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# NIRF INSIGHTS | Streamlit dashboard
# Interactive analytics across NIRF 2017–2025 rankings.
# Uses clean canonical normalization, synchronized visual/table data,
# and independent historical trend queries.
# ============================================================

st.set_page_config(
    page_title="NIRF Insights",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_CANDIDATES = [
    Path(os.getenv("NIRF_DATA_PATH", "")) if os.getenv("NIRF_DATA_PATH") else None,
    APP_DIR / "data" / "processed" / "nirf_clean.csv",
    APP_DIR.parent / "data" / "processed" / "nirf_clean.csv",
    APP_DIR / "nirf_clean.csv",
]

PARAMETERS = ["tlr", "rpc", "go", "oi", "pr"]
PARAMETER_LABELS = {
    "tlr": "Teaching, Learning & Resources (TLR)",
    "rpc": "Research & Professional Practice (RPC)",
    "go": "Graduation Outcomes (GO)",
    "oi": "Outreach & Inclusivity (OI)",
    "pr": "Perception (PR)",
}

PAGE_INFO = {
    "Overview": ("⌂", "A quick snapshot of the selected institutions and their performance."),
    "Rankings & Trends": ("↗", "Track score and rank changes across academic years."),
    "Score Analysis": ("▥", "Explore overall scores and the five NIRF parameters."),
    "Multivariate Analysis": ("◈", "Compare institutions across multiple performance dimensions."),
    "Transitions & Outliers": ("⇄", "Identify rank movements and unusual score patterns."),
    "Sample Questions": ("?", "Choose a research question and run its analysis."),
    "Dynamic Explorer": ("▦", "Build a chart using the variables you want to investigate."),
    "Ask NIRF": ("⌕", "Ask questions about the dataset using the built-in rule-based query tool."),
    "Data Quality": ("✓", "Inspect missing values, duplicates and dataset coverage."),
}
PAGES = list(PAGE_INFO.keys())

SAMPLE_QUESTIONS = {
    "Time & Ranking Trends": [
        "How has an institution's rank changed over time?",
        "Which institutions improved their rank the most?",
        "Which institutions declined in rank the most?",
        "How has the average score changed over time?",
        "Which institutions remained in the top 10?",
    ],
    "Geography": [
        "Which states have the most top-100 institutions?",
        "How has top-100 representation changed by state?",
        "Which states improved their top-100 representation?",
        "Compare Karnataka and Tamil Nadu rankings.",
    ],
    "Scores & Correlation": [
        "Show overall score distribution.",
        "Show the distribution of institutional ranks.",
        "Show average, median, minimum and maximum score.",
        "Which parameter has the strongest correlation with overall score?",
        "Show RPC versus overall score.",
        "Show perception versus overall score.",
    ],
    "Institution Performance": [
        "Compare the top five institutions across parameters.",
        "Which institutions have high RPC but low TLR?",
        "Which institutions have high TLR but low PR?",
        "Which institutions have the largest parameter gap?",
    ],
    "Transitions & Outliers": [
        "Which institutions moved from rank 51–100 to top 50?",
        "Which institutions entered or exited the top 10?",
        "Which institutions have the largest rank movements?",
        "Which institutions have the most volatile ranks?",
    ],
}

# --------------------------- Styling -------------------------
st.markdown(
    """
    <style>
    :root {
      --navy: #102A43; --blue: #1D4ED8; --accent: #3B82F6;
      --bg: #F5F7FB; --surface: #FFFFFF; --text: #172B4D;
      --muted: #64748B; --border: #E2E8F0;
    }
    .stApp, [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text); }
    .block-container { max-width: 1480px; padding-top: 1.5rem; padding-bottom: 2.5rem; }
    [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--border); }
    [data-testid="stSidebar"] * { color: var(--text); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
    h1, h2, h3, h4, p, label, span, .stCaption, [data-testid="stMarkdownContainer"] { color: var(--text); }
    h1, h2, h3 { letter-spacing: -0.025em; }
    .hero {
      padding: 26px 30px; border-radius: 18px; margin-bottom: 18px;
      background: linear-gradient(115deg, #102A43 0%, #1D4E89 100%);
      color: #FFFFFF; box-shadow: 0 8px 24px rgba(16,42,67,.10);
    }
    .hero h1 { color: #FFFFFF !important; font-size: 2rem; margin: 0 0 7px 0; }
    .hero p { color: #E6F0FA !important; margin: 0; font-size: 1rem; }
    .eyebrow { color: #93C5FD !important; text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 700; margin-bottom: 8px; }
    .guide {
      border: 1px solid #DBEAFE; background: #EFF6FF; border-radius: 12px;
      padding: 12px 16px; margin: 10px 0 18px 0; color: #1E3A8A;
    }
    .guide strong { color: #1E3A8A; }
    .section-note { color: var(--muted) !important; margin-top: -7px; margin-bottom: 16px; font-size: .92rem; }
    .soft-card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 15px 17px; }
    .insight-card { background: #FFFFFF; border: 1px solid var(--border); border-left: 4px solid #3B82F6; border-radius: 10px; padding: 12px 15px; margin: 8px 0; }
    .muted { color: #64748B !important; font-size: .88rem; }
    div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid var(--border); padding: 15px 17px; border-radius: 13px; box-shadow: 0 2px 7px rgba(16,42,67,.035); }
    div[data-testid="stMetric"] label { color: #64748B !important; }
    div[data-testid="stMetricValue"] { color: #102A43 !important; font-weight: 750; }
    div[data-testid="stMetricDelta"] { font-size: .8rem; }
    div[data-testid="stAlert"] { border-radius: 11px; }
    div[data-testid="stAlert"] p { color: inherit !important; }
    .stButton > button { border-radius: 9px; font-weight: 650; }
    .stDownloadButton > button { border-radius: 9px; }
    div[data-testid="stRadio"] label, div[data-testid="stRadio"] label p { color: #172B4D !important; }
    div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label,
    div[data-testid="stTextInput"] label { color: #334155 !important; font-weight: 600; }
    div[data-baseweb="select"] * { color: #172B4D; }
    input, textarea { color: #172B4D !important; }
    hr { border-color: #E2E8F0; }
    [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
    @media (max-width: 800px) {
      .block-container { padding-left: 1rem; padding-right: 1rem; }
      .hero { padding: 20px; }
      .hero h1 { font-size: 1.6rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------- Normalization & Identity ----------------------------
def find_data_path() -> Optional[Path]:
    for candidate in DATA_CANDIDATES:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    return None


def clean_state_name(s: str) -> str:
    if not s or pd.isna(s):
        return "Unknown"
    s = str(s).strip()
    if s.lower() in ["jammu and kashmir", "jammu & kashmir"]:
        return "Jammu and Kashmir"
    return s.title()


def clean_display_name(name: str) -> str:
    """Format institution name consistently, removing superfluous commas and formatting errors."""
    if not name or pd.isna(name):
        return "Unknown"
    s = str(name).strip()
    # Normalize backticks and smart quotes
    s = s.replace("`", "'").replace("’", "'").replace("‘", "'")
    # Put space after dots if followed by multiple letters (e.g., I.C.College -> I. C. College)
    s = re.sub(r"([A-Za-z])\.([A-Za-z]{2,})", r"\1. \2", s)
    # Remove commas inside institution names (e.g. 'Technology, Dharwad' -> 'Technology Dharwad')
    s = s.replace(",", " ")
    # Collapse multiple whitespace
    s = re.sub(r"\s+", " ", s).strip()
    
    # Standardize casing of minor connecting words
    words = s.split()
    fixed_words = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in {"of", "and", "the", "for", "in", "at", "to"}:
            fixed_words.append(lw)
        elif w.isupper() and len(w) <= 4:
            fixed_words.append(w)
        elif w.islower():
            fixed_words.append(w.capitalize())
        else:
            fixed_words.append(w)
    return " ".join(fixed_words)


def normalize_text_key(name: str) -> str:
    """
    Produce a canonical, stable search & identity key that treats abbreviations
    (e.g., IIT, NIT, IIM) and punctuation variations identically.
    """
    if not name or pd.isna(name):
        return ""
    s = str(name).strip()
    s = s.replace("`", "'").replace("’", "'").replace("‘", "'")
    s = re.sub(r"([A-Za-z])\.([A-Za-z]{2,})", r"\1. \2", s)
    s = s.replace("'", "").replace(".", "")
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s).lower()
    
    tokens = [t for t in s.split() if t not in {"and", "of", "the", "in", "at", "for"}]
    merged_tokens = []
    i = 0
    while i < len(tokens):
        if len(tokens[i]) == 1 and i + 1 < len(tokens) and len(tokens[i+1]) == 1:
            seq = [tokens[i]]
            while i + 1 < len(tokens) and len(tokens[i+1]) == 1:
                i += 1
                seq.append(tokens[i])
            merged_tokens.append("".join(seq))
            i += 1
        else:
            merged_tokens.append(tokens[i])
            i += 1
    
    expanded = []
    for t in merged_tokens:
        if t == "iit":
            expanded.extend(["indian", "institute", "technology"])
        elif t == "nit":
            expanded.extend(["national", "institute", "technology"])
        elif t == "iim":
            expanded.extend(["indian", "institute", "management"])
        elif t == "iiit":
            expanded.extend(["indian", "institute", "information", "technology"])
        else:
            expanded.append(t)
    return " ".join(expanded)


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def name_is_mentioned(name: str, query: str) -> bool:
    """Match full institution names or common initialisms such as IIT Bombay."""
    norm_name = normalize_text_key(name)
    norm_query = normalize_text_key(query)
    if norm_name and norm_name in norm_query:
        return True
    
    name_tokens = set(norm_name.split())
    query_tokens = set(norm_query.split())
    if len(name_tokens) >= 2 and name_tokens.issubset(query_tokens):
        return True
    return False


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


@st.cache_data(show_spinner="Loading and preparing the NIRF dataset…")
def load_data(path: str, modified_time: float) -> pd.DataFrame:
    del modified_time  # cache invalidation when the file changes
    frame = pd.read_csv(path, low_memory=False)
    frame.columns = (
        frame.columns.astype(str).str.strip().str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_")
    )

    aliases = {
        "institution": "institution_name", "institute": "institution_name",
        "name": "institution_name", "institute_name": "institution_name",
        "overall": "overall_score", "score": "overall_score", "nirf_score": "overall_score",
        "nirf_rank": "rank", "ranking": "rank", "academic_year": "year",
        "state_name": "state", "category_name": "category",
        "teaching_learning_resources": "tlr", "research_professional_practice": "rpc",
        "graduation_outcomes": "go", "outreach_inclusivity": "oi", "perception": "pr",
    }
    for old, new in aliases.items():
        if old in frame.columns and new not in frame.columns:
            frame.rename(columns={old: new}, inplace=True)

    essential = [c for c in ["year", "category", "institution_name"] if c not in frame.columns]
    if essential:
        raise ValueError("Required column(s) not found: " + ", ".join(essential))

    for column in ["institution_id", "institution_name", "category", "state", "city"]:
        if column not in frame.columns:
            frame[column] = "Unknown"
        frame[column] = (frame[column].astype("string").fillna("Unknown")
                         .str.strip().str.replace(r"\s+", " ", regex=True))

    frame["year"] = numeric(frame["year"])
    frame = frame.dropna(subset=["year"]).copy()
    frame["year"] = frame["year"].astype(int)

    # Standardize State & Category names
    frame["state"] = frame["state"].map(clean_state_name).astype("string")
    frame["category"] = frame["category"].astype(str).str.strip().str.title().astype("string")

    for column in ["rank", "overall_score", *PARAMETERS]:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = numeric(frame[column])

    if "rank_original" not in frame.columns:
        frame["rank_original"] = frame["rank"].astype("string").fillna("")
    else:
        frame["rank_original"] = frame["rank_original"].astype("string").fillna("").str.strip()
    extracted = frame["rank_original"].str.extract(r"^\s*(\d+)\s*$", expand=False)
    frame["rank_num"] = frame["rank"].fillna(numeric(extracted))

    # Canonical Institution Identity
    frame["clean_display_name"] = frame["institution_name"].map(clean_display_name)
    frame["norm_name_key"] = frame["institution_name"].map(normalize_text_key)

    # Disambiguate identical names within the same category & state that have multiple distinct cities
    city_counts = frame.groupby(["category", "state", "norm_name_key"])["city"].nunique()
    ambiguous_groups = set(city_counts[city_counts > 1].index)
    
    def assign_canonical_name(row):
        key = (row["category"], row["state"], row["norm_name_key"])
        base = row["clean_display_name"]
        if key in ambiguous_groups and pd.notna(row["city"]) and str(row["city"]).strip() and str(row["city"]).strip() != "Unknown":
            return f"{base} ({str(row['city']).strip()})"
        return base

    frame["canonical_name"] = frame.apply(assign_canonical_name, axis=1).astype("string")
    
    is_ambiguous = frame.apply(lambda r: (r["category"], r["state"], r["norm_name_key"]) in ambiguous_groups, axis=1)
    city_suffix = np.where(is_ambiguous, "::" + frame["city"].astype(str).str.strip().str.lower(), "")
    frame["canonical_key"] = frame["category"] + "::" + frame["state"] + "::" + frame["norm_name_key"] + city_suffix
    frame["institution_key"] = frame["canonical_key"]

    # Deduplication management: flag duplicates while prioritizing rows with complete scores
    param_cols = [c for c in ["tlr", "rpc", "go", "oi", "pr", "overall_score"] if c in frame.columns]
    frame["_score_completeness"] = frame[param_cols].notna().sum(axis=1) if param_cols else 0
    frame = frame.sort_values(by=["year", "category", "_score_completeness"], ascending=[True, True, False])
    duplicate_key = ["year", "category", "canonical_key"]
    frame["_duplicate_record"] = frame.duplicated(subset=duplicate_key, keep="first")
    frame = frame.sort_values(by=["year", "category", "rank_num"]).reset_index(drop=True)

    frame["_search_name"] = frame["canonical_name"].map(normalize_text)
    frame["_search_state"] = frame["state"].map(normalize_text)
    frame["rank_band"] = pd.cut(
        frame["rank_num"],
        bins=[0, 10, 50, 100, 150, 200, 300, np.inf],
        labels=["1–10", "11–50", "51–100", "101–150", "151–200", "201–300", "301+"],
        right=True,
    ).astype("string").fillna("Unranked / band only")
    return frame


def analysis_data(df: pd.DataFrame) -> pd.DataFrame:
    """Use records excluding flagged duplicates for analytical integrity."""
    if "_duplicate_record" not in df.columns:
        return df.copy()
    return df.loc[~df["_duplicate_record"]].copy()


def chart_layout(fig, height: int = 390):
    fig.update_layout(
        template="plotly_white", height=height,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", color="#172B4D", size=12),
        title=dict(font=dict(size=17, color="#102A43"), x=0.02, xanchor="left"),
        margin=dict(l=25, r=20, t=65, b=35),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(gridcolor="#EEF2F7", linecolor="#E2E8F0", zeroline=False)
    return fig


def show_table(data: pd.DataFrame, columns=None, height: int = 360):
    if data is None or data.empty:
        st.info("There are no records to display for this analysis.")
        return
    display = data.copy()
    if columns:
        display = display[[c for c in columns if c in display.columns]]
    display = display.drop(columns=[c for c in display.columns if c.startswith("_")], errors="ignore")
    st.dataframe(display, use_container_width=True, height=height, hide_index=True)


def safe_corr(x, y) -> float:
    pair = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(pair) < 2 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return np.nan
    return float(pair["x"].corr(pair["y"]))


def plot_empty(message="There is not enough valid data to draw this chart."):
    st.info(message)


def add_rank_direction(fig):
    fig.update_yaxes(autorange="reversed", title="Rank (a lower number is better)")
    return fig


def plot_score_trend(data: pd.DataFrame, score_column="overall_score", title=None):
    work = data.dropna(subset=[score_column]).sort_values("year")
    trend = work.groupby("year", as_index=False).agg(
        average_score=(score_column, "mean"),
        institutions=("canonical_key", "nunique"),
        min_score=(score_column, "min"),
        max_score=(score_column, "max"),
    )
    if trend.empty:
        plot_empty("No valid scores are available across the selected years.")
        return
    trend["average_score"] = trend["average_score"].round(2)
    fig = px.line(trend, x="year", y="average_score", markers=True,
                  title=title or "Average Overall Score by Academic Year",
                  labels={"year": "Academic Year", "average_score": "Average Score (0–100)"})
    st.plotly_chart(chart_layout(fig), use_container_width=True)
    show_table(trend, ["year", "average_score", "institutions", "min_score", "max_score"], height=220)


def plot_scatter(data: pd.DataFrame, x: str, y: str, title: str, show_metric=True):
    if x not in data or y not in data:
        plot_empty("The requested columns are not available in this dataset.")
        return
    work = data.dropna(subset=[x, y]).copy()
    if len(work) < 2:
        plot_empty("At least two complete records are required for this relationship.")
        return
    color = "state" if work["state"].nunique() <= 8 else None
    hover_name = "canonical_name" if "canonical_name" in work else "institution_name"
    fig = px.scatter(work, x=x, y=y, color=color, hover_name=hover_name,
                     hover_data=[c for c in ["year", "category", "state", "rank_num"] if c in work],
                     title=title, opacity=.72,
                     labels={x: x.replace("_", " ").upper(), y: y.replace("_", " ").title()})
    if work[x].nunique() > 1:
        try:
            slope, intercept = np.polyfit(work[x].astype(float), work[y].astype(float), 1)
            x_line = np.linspace(work[x].min(), work[x].max(), 80)
            fig.add_trace(go.Scatter(x=x_line, y=slope * x_line + intercept,
                                     mode="lines", name="Linear trend", line=dict(dash="dash")))
        except (ValueError, np.linalg.LinAlgError):
            pass
    st.plotly_chart(chart_layout(fig), use_container_width=True)
    corr = safe_corr(work[x], work[y])
    if show_metric and pd.notna(corr):
        st.metric("Pearson correlation", f"{corr:.3f}", help="Measures linear association; correlation does not establish causation.")


def parameter_gap(data: pd.DataFrame) -> pd.DataFrame:
    valid = [c for c in PARAMETERS if c in data]
    if len(valid) < 2:
        return pd.DataFrame()
    work = data.dropna(subset=valid).copy()
    if work.empty:
        return work
    work["strongest_parameter"] = work[valid].idxmax(axis=1).map(PARAMETER_LABELS)
    work["weakest_parameter"] = work[valid].idxmin(axis=1).map(PARAMETER_LABELS)
    work["parameter_gap"] = (work[valid].max(axis=1) - work[valid].min(axis=1)).round(2)
    return work.sort_values("parameter_gap", ascending=False)

# ------------------------- Filtering (Category -> State -> Institution) -------------------------
def sidebar_controls(df: pd.DataFrame):
    years = sorted(df["year"].dropna().astype(int).unique().tolist(), reverse=True)
    categories = sorted(df["category"].dropna().astype(str).unique().tolist())
    if not years or not categories:
        st.error("The dataset does not contain usable academic years or ranking categories.")
        st.stop()

    default_year = years[0]
    default_category = next((c for c in categories if "engineering" in c.casefold()), categories[0])
    
    st.sidebar.markdown("# 🎓 NIRF Insights")
    st.sidebar.caption("Institutional Ranking Analytics")
    st.sidebar.divider()

    st.session_state.setdefault("global_year", default_year)
    st.session_state.setdefault("global_category", default_category)
    st.session_state.setdefault("global_state", "All states")
    st.session_state.setdefault("global_institution", "All institutions")
    st.session_state.setdefault("global_search", "")
    st.session_state.setdefault("nav_page", "Overview")

    if st.session_state["global_year"] not in years:
        st.session_state["global_year"] = default_year
    if st.session_state["global_category"] not in categories:
        st.session_state["global_category"] = default_category
    if st.session_state["nav_page"] not in PAGES:
        st.session_state["nav_page"] = "Overview"

    st.sidebar.markdown("### 1 · Filter Data")
    if st.sidebar.button("↺ Reset filters", use_container_width=True):
        st.session_state["global_year"] = default_year
        st.session_state["global_category"] = default_category
        st.session_state["global_state"] = "All states"
        st.session_state["global_institution"] = "All institutions"
        st.session_state["global_search"] = ""

    year = st.sidebar.selectbox("Academic year", years, key="global_year", help="Applied to cross-sectional snapshot views (historical trend pages use full year range).")
    category = st.sidebar.selectbox("Ranking category", categories, key="global_category", help="Select NIRF ranking category.")
    
    # Category -> Available States
    cat_df = df[df["category"] == category]
    available_states = ["All states"] + sorted([s for s in cat_df["state"].dropna().unique() if s and s != "Unknown"])
    if st.session_state["global_state"] not in available_states:
        st.session_state["global_state"] = "All states"
    selected_state = st.sidebar.selectbox("State (optional)", available_states, key="global_state", help="Filter by state belonging to selected category.")

    # State -> Available Institutions
    state_df = cat_df if selected_state == "All states" else cat_df[cat_df["state"] == selected_state]
    available_institutions = ["All institutions"] + sorted(state_df["canonical_name"].dropna().unique().tolist())
    if st.session_state["global_institution"] not in available_institutions:
        st.session_state["global_institution"] = "All institutions"
    selected_institution = st.sidebar.selectbox("Institution (optional)", available_institutions, key="global_institution", help="Filter by specific institution.")

    search = st.sidebar.text_input("Search name or acronym", key="global_search", placeholder="e.g. IIT Dharwad", help="Filter by keyword or acronym.")

    st.sidebar.divider()
    st.sidebar.markdown("### 2 · Explore Sections")
    page = st.sidebar.radio("Dashboard section", PAGES, key="nav_page", label_visibility="collapsed")

    # Slicing datasets
    # Context keeps all historical years for Category -> State -> Institution
    context = cat_df.copy()
    if selected_state != "All states":
        context = context[context["state"] == selected_state]
    if selected_institution != "All institutions":
        context = context[context["canonical_name"] == selected_institution]
    if search.strip():
        tokens = [normalize_text_key(t) for t in search.split() if t]
        def search_match(row):
            text = normalize_text_key(f"{row['canonical_name']} {row['state']}")
            return all(tok in text for tok in tokens)
        context = context[context.apply(search_match, axis=1)]

    # Current represents the specific single-year slice
    current = context[context["year"] == int(year)].copy()

    st.sidebar.divider()
    st.sidebar.markdown("### Current selection")
    st.sidebar.markdown(f"**{int(year)}** · {html.escape(category)}")
    st.sidebar.caption(f"{len(current):,} records in {int(year)}")
    if selected_state != "All states":
        st.sidebar.caption(f"State: {selected_state}")
    if selected_institution != "All institutions":
        st.sidebar.caption(f"Institution: {selected_institution}")

    return current, context, page, int(year), category, selected_state, selected_institution, search

# --------------------------- Overview ------------------------
def render_overview(data: pd.DataFrame, year: int, category: str):
    st.subheader("Your NIRF snapshot")
    st.markdown(f"<p class='section-note'>Snapshot of <b>{year}</b> · {html.escape(category)}. Use the sidebar to explore performance across parameters.</p>", unsafe_allow_html=True)
    if data.empty:
        st.warning(f"No records match the current filters for {year} in category '{category}'. Note that some categories (e.g. Dental, Agriculture) were introduced after 2017.")
        return

    score = data["overall_score"].dropna()
    institutions = data["canonical_key"].nunique()
    ranked = data["rank_num"].dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Institutions", f"{institutions:,}")
    c2.metric("Average overall score", f"{score.mean():.2f}" if not score.empty else "—")
    c3.metric("Highest overall score", f"{score.max():.2f}" if not score.empty else "—")
    c4.metric("Institutions with numeric rank", f"{ranked.size:,}")

    st.markdown("### Performance at a glance")
    left, right = st.columns(2)
    with left:
        work = data.dropna(subset=["overall_score"])
        if work.empty:
            plot_empty("No overall score values are available for this selection.")
        else:
            fig = px.histogram(work, x="overall_score", nbins=24, title="Overall score distribution",
                               labels={"overall_score": "Overall score", "count": "Institutions"})
            st.plotly_chart(chart_layout(fig), use_container_width=True)
    with right:
        state_counts = data.groupby("state", as_index=False).agg(institutions=("canonical_key", "nunique"))
        state_counts = state_counts[state_counts["state"] != "Unknown"].nlargest(12, "institutions")
        if state_counts.empty:
            plot_empty("State information is not available for this selection.")
        else:
            fig = px.bar(state_counts.sort_values("institutions"), x="institutions", y="state", orientation="h",
                         title="Institutions by state (top 12)")
            st.plotly_chart(chart_layout(fig), use_container_width=True)

    st.markdown("### Top-ranked institutions")
    top = data.dropna(subset=["rank_num"]).sort_values("rank_num").head(10)
    show_table(top, ["rank_num", "canonical_name", "city", "state", "overall_score", *PARAMETERS])

# ---------------------- Rankings & Trends -------------------
def render_trends(data: pd.DataFrame, selected_year: int, selected_institution: str = "All institutions"):
    st.subheader("Rankings & trends")
    st.markdown("<p class='section-note'>This section uses the full historical dataset for the selected category and filters. The year filter in the sidebar does not restrict multi-year trends.</p>", unsafe_allow_html=True)
    if data.empty:
        plot_empty("No records are available for the selected category and optional filters.")
        return
    years = sorted(data["year"].dropna().unique().tolist())
    if len(years) < 2:
        st.info("Only one academic year is available after applying current filters. Clear optional filters to compare multiple years.")
        return
    year_range = st.select_slider("Years to include", options=years, value=(years[0], years[-1]), key="trend_year_range")
    work = data[data["year"].between(year_range[0], year_range[1])].copy()
    
    l, r = st.columns(2)
    with l:
        work_score = work.dropna(subset=["overall_score"]).sort_values("year")
        trend_score = work_score.groupby("year", as_index=False).agg(
            average_score=("overall_score", "mean"),
            institutions_evaluated=("canonical_key", "nunique"),
            min_score=("overall_score", "min"),
            max_score=("overall_score", "max")
        )
        if trend_score.empty:
            plot_empty("No score data available.")
        else:
            trend_score["average_score"] = trend_score["average_score"].round(2)
            fig_score = px.line(trend_score, x="year", y="average_score", markers=True,
                                title="Average Overall Score by Academic Year",
                                labels={"year": "Academic Year", "average_score": "Average Overall Score (0–100)"})
            st.plotly_chart(chart_layout(fig_score), use_container_width=True)
            show_table(trend_score, ["year", "average_score", "institutions_evaluated", "min_score", "max_score"], height=200)

    with r:
        participation = work.groupby("year", as_index=False).agg(institutions=("canonical_key", "nunique"))
        fig_part = px.line(participation, x="year", y="institutions", markers=True,
                           title="Institutional Participation by Year",
                           labels={"year": "Academic Year", "institutions": "Institutions"})
        st.plotly_chart(chart_layout(fig_part), use_container_width=True)
        show_table(participation, ["year", "institutions"], height=200)

    st.markdown("### Institution rank and score history")
    choices = sorted(work["canonical_name"].dropna().unique().tolist())
    if not choices:
        plot_empty("No institutions found for the current selection.")
        return
    default_idx = choices.index(selected_institution) if selected_institution in choices else 0
    institution = st.selectbox("Choose an institution", choices, index=default_idx, key="trend_institution")
    
    inst_work = work[work["canonical_name"] == institution].copy()
    metric = st.radio("History metric", ["Rank", "Overall score"], horizontal=True, key="trend_metric")
    y = "rank_num" if metric == "Rank" else "overall_score"
    chart_data = inst_work.dropna(subset=[y]).sort_values("year")
    
    if chart_data.empty:
        plot_empty(f"No {metric.lower()} history is available for {institution}.")
    else:
        # Group to ensure exactly 1 synchronized row per year
        grouped_history = chart_data.groupby(["year", "canonical_name", "state"], as_index=False).agg({
            "rank_num": "min",
            "overall_score": "mean",
            "tlr": "mean", "rpc": "mean", "go": "mean", "oi": "mean", "pr": "mean"
        }).sort_values("year")
        if metric == "Overall score":
            grouped_history["overall_score"] = grouped_history["overall_score"].round(2)

        y_label = "Rank (lower number is better)" if metric == "Rank" else "Overall Score (0–100)"
        fig_inst = px.line(grouped_history, x="year", y=y, markers=True,
                           title=f"{metric} History — {institution}",
                           labels={"year": "Academic Year", y: y_label})
        if y == "rank_num":
            add_rank_direction(fig_inst)
        st.plotly_chart(chart_layout(fig_inst), use_container_width=True)
        show_table(grouped_history, ["year", "canonical_name", "state", "rank_num", "overall_score", *PARAMETERS])

    st.markdown("### Top-100 representation by state")
    top100 = work[work["rank_num"].le(100) & work["rank_num"].notna()]
    if top100.empty:
        plot_empty("No numeric top-100 ranks were found in this year range.")
    else:
        state_year = top100.groupby(["year", "state"], as_index=False).agg(institutions=("canonical_key", "nunique"))
        top_states = state_year.groupby("state")["institutions"].sum().nlargest(8).index
        state_year_top = state_year[state_year["state"].isin(top_states)]
        fig_state = px.line(state_year_top, x="year", y="institutions", color="state", markers=True,
                            title="Top-100 Institutions by State (Top 8 States)",
                            labels={"year": "Academic Year", "institutions": "Institutions in Top 100", "state": "State"})
        st.plotly_chart(chart_layout(fig_state), use_container_width=True)
        pivot_state = state_year_top.pivot(index="state", columns="year", values="institutions").fillna(0).astype(int).reset_index()
        show_table(pivot_state)

# ------------------------- Score Analysis --------------------
def render_scores(data: pd.DataFrame):
    st.subheader("Score analysis")
    st.markdown("<p class='section-note'>Understand how institutions score overall and across the five NIRF performance parameters.</p>", unsafe_allow_html=True)
    if data.empty:
        plot_empty("No records match the current filters.")
        return
    left, right = st.columns(2)
    with left:
        values = data.dropna(subset=["overall_score"])
        if values.empty:
            plot_empty("No overall score values are available.")
        else:
            fig = px.histogram(values, x="overall_score", nbins=28, title="Overall score distribution")
            st.plotly_chart(chart_layout(fig), use_container_width=True)
    with right:
        long = data.melt(id_vars=["canonical_name"], value_vars=PARAMETERS,
                         var_name="parameter", value_name="score").dropna(subset=["score"])
        if long.empty:
            plot_empty("No NIRF parameter values are available.")
        else:
            long["parameter"] = long["parameter"].map(PARAMETER_LABELS)
            fig = px.box(long, x="parameter", y="score", points="outliers", title="Distribution of NIRF parameters")
            fig.update_xaxes(tickangle=-25)
            st.plotly_chart(chart_layout(fig), use_container_width=True)

    numeric_fields = [c for c in ["overall_score", *PARAMETERS] if data[c].notna().sum() >= 2 and data[c].nunique(dropna=True) > 1]
    st.markdown("### How do the parameters relate to overall score?")
    if len(numeric_fields) >= 2:
        corr = data[numeric_fields].corr(min_periods=2)
        fig = px.imshow(corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                        title="Correlation matrix")
        st.plotly_chart(chart_layout(fig, 430), use_container_width=True)
        corr_to_overall = corr["overall_score"].drop("overall_score", errors="ignore").dropna().sort_values(key=abs, ascending=False)
        if not corr_to_overall.empty:
            best = corr_to_overall.index[0]
            st.info(f"Among the available parameters, **{PARAMETER_LABELS.get(best, best)}** has the strongest linear correlation with overall score (r = {corr_to_overall.iloc[0]:.3f}).")
    else:
        plot_empty("At least two numeric fields with variation are needed for correlation analysis.")

    left, right = st.columns(2)
    with left:
        plot_scatter(data, "rpc", "overall_score", "Research & Professional Practice vs overall score")
    with right:
        plot_scatter(data, "pr", "overall_score", "Perception vs overall score")

    st.markdown("### Average parameter scores")
    means = data[PARAMETERS].mean().dropna().rename("average_score").reset_index().rename(columns={"index": "parameter"})
    if not means.empty:
        means["parameter"] = means["parameter"].map(PARAMETER_LABELS)
        fig = px.bar(means, x="parameter", y="average_score", title="Average score by NIRF parameter", text_auto=".2f")
        fig.update_xaxes(tickangle=-20)
        st.plotly_chart(chart_layout(fig), use_container_width=True)

# ---------------------- Multivariate Analysis ----------------
def render_multivariate(data: pd.DataFrame):
    st.subheader("Multivariate analysis")
    st.markdown("<p class='section-note'>Compare multiple performance dimensions together across institutions.</p>", unsafe_allow_html=True)
    if data.empty:
        plot_empty("No records match the current filters.")
        return
    top = data.dropna(subset=["rank_num"]).nsmallest(5, "rank_num")
    if top.empty:
        plot_empty("No numeric ranks are available to identify the top five institutions.")
    else:
        long = top.melt(id_vars=["canonical_name"], value_vars=PARAMETERS, var_name="parameter", value_name="score").dropna()
        if long.empty:
            plot_empty("The top institutions do not have parameter scores available.")
        else:
            long["parameter"] = long["parameter"].map(PARAMETER_LABELS)
            fig = px.bar(long, x="parameter", y="score", color="canonical_name", barmode="group",
                         title="Top five institutions across NIRF parameters")
            fig.update_xaxes(tickangle=-25)
            st.plotly_chart(chart_layout(fig, 470), use_container_width=True)

    st.markdown("### Largest gap between parameters")
    gaps = parameter_gap(data).head(20)
    if gaps.empty:
        plot_empty("At least two parameter values per institution are needed to calculate a gap.")
    else:
        show_table(gaps, ["canonical_name", "year", "category", "strongest_parameter", "weakest_parameter", "parameter_gap", *PARAMETERS])
        st.caption("Parameter gap = highest parameter score minus lowest parameter score.")

    st.markdown("### Principal component view (PCA)")
    features = [c for c in PARAMETERS if data[c].notna().sum() >= 3 and data[c].nunique(dropna=True) > 1]
    complete = data.dropna(subset=features).copy() if len(features) >= 2 else pd.DataFrame()
    if len(features) < 2 or len(complete) < 3:
        plot_empty("PCA needs at least two varying parameters and three complete institution records.")
    else:
        matrix = complete[features].astype(float).to_numpy()
        std = matrix.std(axis=0, ddof=0)
        matrix = (matrix - matrix.mean(axis=0)) / np.where(std == 0, 1, std)
        try:
            u, singular, _ = np.linalg.svd(matrix, full_matrices=False)
            coords = u[:, :2] * singular[:2]
            pca_data = pd.DataFrame({"PC1": coords[:, 0], "PC2": coords[:, 1],
                                     "canonical_name": complete["canonical_name"].values,
                                     "state": complete["state"].values})
            variance = singular ** 2 / max(np.sum(singular ** 2), 1e-12)
            fig = px.scatter(pca_data, x="PC1", y="PC2", color="state" if pca_data.state.nunique() <= 8 else None,
                             hover_name="canonical_name", title="Institutions projected onto two principal components")
            st.plotly_chart(chart_layout(fig), use_container_width=True)
            st.caption(f"PC1 explains {variance[0]*100:.1f}% and PC2 explains {variance[1]*100:.1f}% of standardized parameter variation.")
        except np.linalg.LinAlgError:
            plot_empty("PCA could not be calculated for this selection.")

# --------------------- Transitions & Outliers ---------------
def rank_pivot(data: pd.DataFrame, year_a: int, year_b: int) -> pd.DataFrame:
    work = data[data["year"].isin([year_a, year_b])].dropna(subset=["rank_num"])
    pivot = work.pivot_table(index=["canonical_key", "canonical_name"], columns="year", values="rank_num", aggfunc="min").reset_index()
    if year_a not in pivot.columns or year_b not in pivot.columns:
        return pd.DataFrame()
    pivot = pivot.dropna(subset=[year_a, year_b]).copy()
    pivot["rank_movement"] = pivot[year_a] - pivot[year_b]  # positive means rank improved
    pivot["movement"] = np.select([pivot["rank_movement"] > 0, pivot["rank_movement"] < 0], ["Moved up", "Moved down"], default="No change")
    return pivot


def render_transitions(data: pd.DataFrame):
    st.subheader("Transitions & outliers")
    st.markdown("<p class='section-note'>Analyze rank movements and outlier scores across historical years.</p>", unsafe_allow_html=True)
    if data.empty:
        plot_empty("No records are available for this category and optional filters.")
        return
    years = sorted(data["year"].dropna().unique().tolist())
    if len(years) < 2:
        st.info("At least two years are needed for transition analysis.")
        return
    c1, c2 = st.columns(2)
    ya = c1.selectbox("From year", years[:-1], index=0, key="transition_from")
    later = [y for y in years if y > ya]
    yb = c2.selectbox("To year", later, index=len(later)-1, key="transition_to")
    pivot = rank_pivot(data, int(ya), int(yb))
    if pivot.empty:
        st.warning("No institutions have numeric ranks in both selected years.")
    else:
        counts = pivot["movement"].value_counts().rename_axis("movement").reset_index(name="institutions")
        fig = px.bar(counts, x="movement", y="institutions", color="movement", title=f"Rank movement: {ya} to {yb}")
        st.plotly_chart(chart_layout(fig), use_container_width=True)
        left, right = st.columns(2)
        with left:
            st.markdown("**Largest rank improvements**")
            show_table(pivot.sort_values("rank_movement", ascending=False).head(15), ["canonical_name", ya, yb, "rank_movement"])
        with right:
            st.markdown("**Largest rank declines**")
            show_table(pivot.sort_values("rank_movement").head(15), ["canonical_name", ya, yb, "rank_movement"])

        from_rows = data[data["year"] == ya].dropna(subset=["rank_num"])[["canonical_key", "rank_num"]].rename(columns={"rank_num": "rank_from"})
        to_rows = data[data["year"] == yb].dropna(subset=["rank_num"])[["canonical_key", "canonical_name", "rank_num"]].rename(columns={"rank_num": "rank_to"})
        joined = from_rows.merge(to_rows, on="canonical_key")
        moved = joined[joined["rank_from"].between(51, 100) & joined["rank_to"].le(50)]
        st.markdown("**Moved from rank 51–100 into top 50**")
        show_table(moved.sort_values("rank_to"), ["canonical_name", "rank_from", "rank_to"])

    st.markdown("### Most volatile ranks")
    valid = data.dropna(subset=["rank_num"])
    volatility = valid.groupby(["canonical_key", "canonical_name"], as_index=False).agg(
        years_ranked=("year", "nunique"), average_rank=("rank_num", "mean"), rank_volatility=("rank_num", "std"))
    volatility = volatility[volatility["years_ranked"] >= 3].sort_values("rank_volatility", ascending=False).head(15)
    show_table(volatility, ["canonical_name", "years_ranked", "average_rank", "rank_volatility"])

    st.markdown("### Overall-score outliers (IQR method)")
    scores = data.dropna(subset=["overall_score"]).copy()
    if len(scores) < 4:
        plot_empty("At least four valid overall scores are needed for IQR outlier detection.")
    else:
        q1, q3 = scores["overall_score"].quantile([.25, .75])
        iqr = q3 - q1
        outliers = scores[(scores["overall_score"] < q1 - 1.5*iqr) | (scores["overall_score"] > q3 + 1.5*iqr)]
        st.caption(f"IQR bounds: {q1 - 1.5*iqr:.2f} to {q3 + 1.5*iqr:.2f}.")
        show_table(outliers.sort_values("overall_score"), ["canonical_name", "year", "overall_score", "rank_num", *PARAMETERS])

# ------------------------- Sample Questions ------------------
def render_sample_questions(context: pd.DataFrame, current: pd.DataFrame, selected_year: int, selected_category: str):
    st.subheader("Sample questions")
    st.markdown("<p class='section-note'>Choose a research question from the NIRF project specification to execute analytical visualizations.</p>", unsafe_allow_html=True)
    topic = st.selectbox("Choose a topic", list(SAMPLE_QUESTIONS.keys()), key="sample_topic")
    question = st.selectbox("Choose a question", SAMPLE_QUESTIONS[topic], key="sample_question")
    st.markdown(f"<div class='soft-card'><b>Your question</b><br>{html.escape(question)}</div>", unsafe_allow_html=True)
    if st.button("Run analysis", type="primary", key="run_sample_question"):
        st.session_state["last_sample_question"] = question
    chosen = st.session_state.get("last_sample_question")
    if chosen and chosen == question:
        st.markdown("### Analysis result")
        run_sample_analysis(chosen, context, current, selected_year, selected_category)
    elif chosen:
        st.info("Select **Run analysis** to execute the newly selected question.")


def run_sample_analysis(question: str, context: pd.DataFrame, current: pd.DataFrame, selected_year: int, selected_category: str):
    q = question.casefold()
    years = sorted(context["year"].dropna().unique().tolist()) if not context.empty else []

    if "rank changed over time" in q:
        options = sorted(context["canonical_name"].dropna().unique().tolist())
        if len(years) < 2 or not options:
            plot_empty("Not enough historical data to inspect institution rank history.")
            return
        institution = st.selectbox("Institution", options, key="sample_history_institution")
        hist = context[(context["canonical_name"] == institution) & context["rank_num"].notna()].sort_values("year")
        if hist.empty:
            plot_empty("No numeric rank history is available.")
        else:
            hist_grouped = hist.groupby(["year", "canonical_name", "state"], as_index=False).agg({
                "rank_num": "min", "overall_score": "mean"
            }).sort_values("year")
            fig = px.line(hist_grouped, x="year", y="rank_num", markers=True, title=f"Rank history — {institution}",
                          labels={"year": "Academic Year", "rank_num": "Rank (lower is better)"})
            add_rank_direction(fig)
            st.plotly_chart(chart_layout(fig), use_container_width=True)
            show_table(hist_grouped, ["year", "canonical_name", "rank_num", "overall_score"])

    elif "improved their rank" in q or "declined in rank" in q or "largest rank movements" in q:
        if len(years) < 2:
            plot_empty("At least two years are needed for rank movement analysis.")
            return
        c1, c2 = st.columns(2)
        ya = c1.selectbox("From year", years[:-1], index=0, key="sample_move_from")
        yb_options = [y for y in years if y > ya]
        yb = c2.selectbox("To year", yb_options, index=len(yb_options)-1, key="sample_move_to")
        pivot = rank_pivot(context, int(ya), int(yb))
        if pivot.empty:
            plot_empty("No matched institutions have numeric ranks in both years.")
        else:
            if "largest rank movements" in q:
                pivot["absolute_movement"] = pivot["rank_movement"].abs()
                result = pivot.sort_values("absolute_movement", ascending=False).head(15)
            else:
                improved = "declined in rank" not in q
                result = pivot.sort_values("rank_movement", ascending=not improved).head(15)
            st.caption(f"Rank movement between {ya} and {yb}. Positive rank movement indicates rank improvement.")
            show_table(result, ["canonical_name", ya, yb, "rank_movement", "movement"])

    elif "average score changed" in q:
        trend = context.dropna(subset=["overall_score"]).groupby("year", as_index=False).agg(
            average_overall_score=("overall_score", "mean"),
            institutions_evaluated=("canonical_key", "nunique"),
            min_score=("overall_score", "min"),
            max_score=("overall_score", "max")
        ).sort_values("year")
        trend["average_overall_score"] = trend["average_overall_score"].round(2)
        fig = px.line(trend, x="year", y="average_overall_score", markers=True,
                      title="Average Overall Score Over Time",
                      labels={"year": "Academic Year", "average_overall_score": "Average Score (0–100)"})
        st.plotly_chart(chart_layout(fig), use_container_width=True)
        show_table(trend)

    elif "remained in the top 10" in q:
        if len(years) < 2:
            plot_empty("At least two years are needed to identify institutions that consistently remained in the top 10.")
            return
        top = context[context["rank_num"].le(10) & context["rank_num"].notna()]
        counts = top.groupby(["canonical_key", "canonical_name"], as_index=False).agg(years_in_top10=("year", "nunique"))
        result = counts[counts["years_in_top10"] == len(years)].sort_values("canonical_name")
        st.caption(f"Institutions that maintained rank 1–10 across all {len(years)} available years in {selected_category}.")
        show_table(result, ["canonical_name", "years_in_top10"])

    elif "top-100 institutions" in q or ("top 100" in q and "state" in q):
        top = current[current["rank_num"].le(100) & current["rank_num"].notna()]
        counts = top.groupby("state", as_index=False).agg(institutions=("canonical_key", "nunique")).nlargest(15, "institutions")
        if counts.empty:
            plot_empty(f"No top-100 numeric ranks were found for {selected_year}.")
        else:
            fig = px.bar(counts.sort_values("institutions"), x="institutions", y="state", orientation="h",
                         title=f"Top-100 Institutions by State in {selected_year}")
            st.plotly_chart(chart_layout(fig), use_container_width=True)
            show_table(counts)

    elif "representation changed by state" in q or "improved their top-100 representation" in q:
        top = context[context["rank_num"].le(100) & context["rank_num"].notna()]
        counts = top.groupby(["year", "state"], as_index=False).agg(institutions=("canonical_key", "nunique"))
        if counts.empty or len(years) < 2:
            plot_empty("There is not enough top-100 representation data across years.")
        else:
            fig = px.line(counts, x="year", y="institutions", color="state", markers=True,
                          title="Top-100 Representation by State Across Years")
            st.plotly_chart(chart_layout(fig, 450), use_container_width=True)
            pivot = counts.pivot(index="state", columns="year", values="institutions").fillna(0).astype(int).reset_index()
            show_table(pivot)

    elif "compare karnataka and tamil nadu" in q:
        target_states = context[context["state"].isin(["Karnataka", "Tamil Nadu"])]
        result = target_states.groupby(["year", "state"], as_index=False).agg(
            institutions=("canonical_key", "nunique"),
            average_rank=("rank_num", "mean"),
            average_score=("overall_score", "mean"),
            top100_count=("rank_num", lambda s: int(s.le(100).sum()))
        ).sort_values(["year", "state"])
        result["average_rank"] = result["average_rank"].round(1)
        result["average_score"] = result["average_score"].round(2)
        if result.empty:
            st.info("Karnataka and/or Tamil Nadu are not represented in the current selection.")
        else:
            fig = px.line(result, x="year", y="top100_count", color="state", markers=True,
                          title="Top-100 Institutions: Karnataka vs Tamil Nadu")
            st.plotly_chart(chart_layout(fig), use_container_width=True)
            show_table(result)

    elif "overall score distribution" in q:
        work = current.dropna(subset=["overall_score"])
        if work.empty:
            plot_empty(f"No overall scores available for {selected_year}.")
        else:
            fig = px.histogram(work, x="overall_score", nbins=25, title=f"Overall Score Distribution ({selected_year})")
            st.plotly_chart(chart_layout(fig), use_container_width=True)
            show_table(work[["canonical_name", "state", "overall_score", "rank_num"]].sort_values("overall_score", ascending=False).head(25))

    elif "distribution of institutional ranks" in q:
        work = current.dropna(subset=["rank_num"])
        if work.empty:
            plot_empty("No numeric rank values are available.")
        else:
            fig = px.histogram(work, x="rank_num", nbins=25, title=f"Distribution of Numeric Ranks ({selected_year})")
            st.plotly_chart(chart_layout(fig), use_container_width=True)

    elif "average, median, minimum and maximum" in q:
        s = current["overall_score"].dropna()
        if s.empty:
            plot_empty("No overall score values are available.")
        else:
            a, b, c, d = st.columns(4)
            a.metric("Average", f"{s.mean():.2f}")
            b.metric("Median", f"{s.median():.2f}")
            c.metric("Minimum", f"{s.min():.2f}")
            d.metric("Maximum", f"{s.max():.2f}")

    elif "strongest correlation" in q:
        corr = {p: safe_corr(current[p], current["overall_score"]) for p in PARAMETERS}
        result = pd.DataFrame([{"parameter": PARAMETER_LABELS[p], "correlation_with_overall": v} for p, v in corr.items() if pd.notna(v)])
        if result.empty:
            plot_empty("Not enough valid paired scores to calculate correlation.")
        else:
            result["absolute_correlation"] = result["correlation_with_overall"].abs()
            result = result.sort_values("absolute_correlation", ascending=False).drop(columns="absolute_correlation")
            st.metric("Strongest parameter relationship", result.iloc[0]["parameter"], f"r = {result.iloc[0]['correlation_with_overall']:.3f}")
            show_table(result)

    elif "rpc versus overall" in q:
        plot_scatter(current, "rpc", "overall_score", f"RPC vs Overall Score ({selected_year})")

    elif "perception versus overall" in q:
        plot_scatter(current, "pr", "overall_score", f"Perception vs Overall Score ({selected_year})")

    elif "top five institutions" in q:
        top = current.dropna(subset=["rank_num"]).sort_values("rank_num").head(5)
        long = top.melt(id_vars=["canonical_name"], value_vars=PARAMETERS, var_name="parameter", value_name="score").dropna()
        if long.empty:
            plot_empty(f"Top 5 institutions in {selected_year} do not contain parameter scores.")
        else:
            long["parameter"] = long["parameter"].map(PARAMETER_LABELS)
            fig = px.bar(long, x="parameter", y="score", color="canonical_name", barmode="group",
                         title=f"Top 5 Institutions Across NIRF Parameters ({selected_year})")
            fig.update_xaxes(tickangle=-25)
            st.plotly_chart(chart_layout(fig, 450), use_container_width=True)
            show_table(top, ["rank_num", "canonical_name", "overall_score", *PARAMETERS])

    elif "high rpc but low tlr" in q or "high tlr but low pr" in q:
        high_col, low_col = ("rpc", "tlr") if "high rpc" in q else ("tlr", "pr")
        work = current.dropna(subset=[high_col, low_col]).copy()
        if work.empty:
            plot_empty("The required parameter values are not available.")
        else:
            high_cut = work[high_col].quantile(.75)
            low_cut = work[low_col].quantile(.25)
            result = work[(work[high_col] >= high_cut) & (work[low_col] <= low_cut)].sort_values(high_col, ascending=False)
            st.caption(f"Selection quartiles: high {high_col.upper()} ≥ {high_cut:.2f}; low {low_col.upper()} ≤ {low_cut:.2f}.")
            show_table(result, ["canonical_name", "state", high_col, low_col, "overall_score", "rank_num"])

    elif "largest parameter gap" in q:
        result = parameter_gap(current).head(20)
        show_table(result, ["canonical_name", "year", "strongest_parameter", "weakest_parameter", "parameter_gap", *PARAMETERS])

    elif "moved from rank 51" in q or "entered or exited the top 10" in q:
        if len(years) < 2:
            plot_empty("At least two years are needed for transition analysis.")
            return
        c1, c2 = st.columns(2)
        ya = c1.selectbox("From year", years[:-1], key="sample_band_from")
        yb_list = [y for y in years if y > ya]
        yb = c2.selectbox("To year", yb_list, index=len(yb_list)-1, key="sample_band_to")
        a = context[context.year == ya].dropna(subset=["rank_num"])[["canonical_key", "rank_num"]].rename(columns={"rank_num": "rank_from"})
        b = context[context.year == yb].dropna(subset=["rank_num"])[["canonical_key", "canonical_name", "rank_num"]].rename(columns={"rank_num": "rank_to"})
        joined = a.merge(b, on="canonical_key")
        if "rank 51" in q:
            result = joined[joined.rank_from.between(51, 100) & joined.rank_to.le(50)]
            show_table(result.sort_values("rank_to"), ["canonical_name", "rank_from", "rank_to"])
        else:
            entered = joined[joined.rank_from.gt(10) & joined.rank_to.le(10)].assign(transition="Entered top 10")
            exited = joined[joined.rank_from.le(10) & joined.rank_to.gt(10)].assign(transition="Exited top 10")
            show_table(pd.concat([entered, exited]).sort_values("rank_to"), ["canonical_name", "rank_from", "rank_to", "transition"])

    elif "volatile ranks" in q:
        volatility = context.dropna(subset=["rank_num"]).groupby(["canonical_key", "canonical_name"], as_index=False).agg(
            years_ranked=("year", "nunique"), average_rank=("rank_num", "mean"), rank_volatility=("rank_num", "std"))
        show_table(volatility[volatility.years_ranked >= 3].sort_values("rank_volatility", ascending=False).head(20),
                   ["canonical_name", "years_ranked", "average_rank", "rank_volatility"])
    else:
        st.warning("This question does not yet have a specialized handler. Try another question or use Dynamic Explorer.")

# ------------------------- Dynamic Explorer ------------------
def render_dynamic_explorer(data: pd.DataFrame, context: pd.DataFrame):
    st.subheader("Dynamic chart explorer")
    st.markdown("<p class='section-note'>Configure and build custom visualizations dynamically across any attributes.</p>", unsafe_allow_html=True)
    use_all_years = st.toggle("Include all academic years", value=False, help="Turn on to visualize longitudinal historical records.")
    source = context if use_all_years else data
    if source.empty:
        plot_empty("No records are available for this selection.")
        return
    numeric_cols = [c for c in ["overall_score", "rank_num", *PARAMETERS] if c in source and source[c].notna().sum() > 1]
    if not numeric_cols:
        plot_empty("No numeric variables are available for visualization.")
        return
    with st.form("dynamic_chart_form"):
        c1, c2, c3 = st.columns(3)
        chart_type = c1.selectbox("1. Chart type", ["Scatter plot", "Bar chart", "Line chart", "Histogram", "Box plot"])
        x = c2.selectbox("2. X-axis / grouping", ["year", "state", "category", "canonical_name", *numeric_cols])
        y = c3.selectbox("3. Numeric measure", numeric_cols, index=numeric_cols.index("overall_score") if "overall_score" in numeric_cols else 0)
        c4, c5 = st.columns(2)
        aggregation = c4.selectbox("Aggregation", ["Mean", "Median", "Sum", "Count", "Maximum", "Minimum"])
        show_trend = c5.checkbox("Show trend line (scatter only)", value=True)
        submitted = st.form_submit_button("Generate visualization", type="primary", use_container_width=True)
    if not submitted:
        st.info("Choose chart settings above and select **Generate visualization**.")
        return

    work = source.dropna(subset=[y]).copy()
    if chart_type == "Histogram":
        fig = px.histogram(work, x=y, nbins=28, title=f"Distribution of {y.replace('_', ' ').title()}",
                           labels={y: y.replace("_", " ").title()})
        st.plotly_chart(chart_layout(fig, 450), use_container_width=True)
        show_table(work[["canonical_name", "year", "state", y]].head(100))
    elif chart_type == "Scatter plot":
        if x not in numeric_cols or x == y:
            st.warning("For a scatter plot, select a numeric X-axis distinct from the Y-axis.")
            return
        work = work.dropna(subset=[x, y])
        fig = px.scatter(work, x=x, y=y, color="state" if work.state.nunique() <= 8 else None,
                         hover_name="canonical_name", title=f"{y.title()} vs {x.title()}")
        if show_trend and len(work) >= 2 and work[x].nunique() > 1:
            try:
                slope, intercept = np.polyfit(work[x].astype(float), work[y].astype(float), 1)
                line_x = np.linspace(work[x].min(), work[x].max(), 80)
                fig.add_trace(go.Scatter(x=line_x, y=slope * line_x + intercept, mode="lines", name="Trend"))
            except (ValueError, np.linalg.LinAlgError):
                pass
        st.plotly_chart(chart_layout(fig, 450), use_container_width=True)
        show_table(work[["canonical_name", "year", "state", x, y]].head(100))
    elif chart_type == "Box plot":
        if x in numeric_cols:
            st.warning("Select a grouping categorical field (year, state, category or canonical_name) for box plot.")
            return
        fig = px.box(work, x=x, y=y, points="outliers", title=f"{y.title()} Distribution by {x.title()}")
        st.plotly_chart(chart_layout(fig, 450), use_container_width=True)
        show_table(work[["canonical_name", "year", "state", y]].head(100))
    elif chart_type in ["Bar chart", "Line chart"]:
        if x in numeric_cols:
            st.warning("Choose a grouping field (year, state, category or canonical_name) for bar and line charts.")
            return
        agg_map = {"Mean": "mean", "Median": "median", "Sum": "sum", "Count": "count", "Maximum": "max", "Minimum": "min"}
        grouped = work.groupby(x, as_index=False)[y].agg(agg_map[aggregation])
        grouped = grouped.sort_values(x).head(40)
        grouped[y] = grouped[y].round(2)
        fig = (px.line(grouped, x=x, y=y, markers=True, title=f"{aggregation} {y.title()} by {x.title()}")
               if chart_type == "Line chart" else
               px.bar(grouped, x=x, y=y, title=f"{aggregation} {y.title()} by {x.title()}"))
        st.plotly_chart(chart_layout(fig, 450), use_container_width=True)
        show_table(grouped)
        st.download_button("Download chart data (CSV)", grouped.to_csv(index=False).encode("utf-8"),
                           file_name="nirf_explorer_chart_data.csv", mime="text/csv")

# ---------------------------- Ask NIRF -----------------------
def render_ask_nirf(current: pd.DataFrame, context: pd.DataFrame):
    st.subheader("Ask NIRF")
    st.markdown("<p class='section-note'>Natural language querying with deterministic data querying and chart generation.</p>", unsafe_allow_html=True)
    examples = ["Top 10 engineering institutions in 2025", "Average overall score by year", "IIT Dharwad ranking history", "Which state has the most top-100 institutions?"]
    st.caption("Sample queries: " + " · ".join(examples))
    with st.form("ask_nirf_form"):
        query = st.text_input("Your question", placeholder="e.g. IIT Bombay ranking history", key="ask_nirf_query")
        run = st.form_submit_button("Ask NIRF", type="primary")
    if not run:
        st.info("Enter a question and select **Ask NIRF**.")
        return
    if not query.strip():
        st.warning("Please enter a question first.")
        return
    execute_natural_query(query, context if not context.empty else current)


def execute_natural_query(query: str, data: pd.DataFrame):
    q = query.casefold()
    work = data.copy()

    year_match = re.search(r"\b(201[7-9]|202[0-9])\b", q)
    if year_match:
        y = int(year_match.group(1))
        if y in set(work.year):
            work = work[work.year == y]
            st.caption(f"Detected academic year: {y}")
        else:
            st.warning(f"No records found for year {y}.")
            return

    # Detect state
    state_match = None
    for state in sorted(work.state.dropna().unique(), key=lambda s: len(str(s)), reverse=True):
        if normalize_text(state) in normalize_text(q):
            state_match = state
            break
    if state_match:
        work = work[work["state"] == state_match]
        st.caption(f"Detected state: {state_match}")

    # Detect institution
    matched_institutions = []
    for inst in sorted(work.canonical_name.dropna().unique(), key=lambda s: len(str(s)), reverse=True):
        if name_is_mentioned(inst, query):
            matched_institutions.append(inst)

    if matched_institutions:
        work = work[work["canonical_name"].isin(matched_institutions)]
        st.caption(f"Detected institution: {', '.join(matched_institutions)}")

    param_map = {"tlr": "tlr", "teaching": "tlr", "rpc": "rpc", "research": "rpc",
                 "graduation": "go", "go": "go", "outreach": "oi", "inclusivity": "oi",
                 "perception": "pr", "pr": "pr"}
    chosen_param = next((col for word, col in param_map.items() if re.search(rf"\b{re.escape(word)}\b", q)), None)
    metric = chosen_param or ("rank_num" if "rank" in q else "overall_score")

    if "trend" in q or "over time" in q or "history" in q or "changed" in q or len(work.year.unique()) > 1 and matched_institutions:
        grouped = work.dropna(subset=[metric]).groupby(["year", "canonical_name"], as_index=False).agg({
            metric: "min" if metric == "rank_num" else "mean",
            "overall_score": "mean",
            "state": "first"
        }).sort_values("year")
        if grouped.empty:
            plot_empty(f"No {metric} history available.")
        else:
            fig = px.line(grouped, x="year", y=metric, color="canonical_name" if len(matched_institutions) > 1 else None,
                          markers=True, title=f"{metric.replace('_', ' ').title()} History")
            if metric == "rank_num":
                add_rank_direction(fig)
            st.plotly_chart(chart_layout(fig), use_container_width=True)
            show_table(grouped)
    elif "top" in q or "best" in q:
        count_match = re.search(r"top\s+(\d+)", q)
        n = int(count_match.group(1)) if count_match else 10
        sort_col = metric if ("score" in q or chosen_param) else "rank_num"
        valid = work.dropna(subset=[sort_col])
        result = valid.nlargest(n, sort_col) if sort_col != "rank_num" else valid.nsmallest(n, sort_col)
        st.markdown(f"### Top {len(result)} institutions")
        show_table(result, ["canonical_name", "category", "year", "state", "rank_num", "overall_score", *PARAMETERS])
    else:
        show_table(work[["canonical_name", "category", "year", "state", "rank_num", "overall_score", *PARAMETERS]])

# --------------------------- Data Quality --------------------
def render_data_quality(raw_data: pd.DataFrame):
    st.subheader("Data quality & coverage")
    st.markdown("<p class='section-note'>Inspect missing values, duplicates, and coverage across all 2017–2025 raw loaded records.</p>", unsafe_allow_html=True)
    duplicate_count = int(raw_data.get("_duplicate_record", pd.Series(dtype=bool)).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows loaded", f"{len(raw_data):,}")
    c2.metric("Columns", f"{len([c for c in raw_data.columns if not c.startswith('_')]):,}")
    c3.metric("Duplicate records flagged", f"{duplicate_count:,}")
    c4.metric("Academic years", f"{raw_data.year.nunique():,}")

    public_cols = [c for c in raw_data.columns if not c.startswith("_")]
    missing = raw_data[public_cols].isna().sum().rename("missing_values").reset_index().rename(columns={"index": "column"})
    missing["missing_percentage"] = (missing["missing_values"] / max(len(raw_data), 1) * 100).round(2)
    st.markdown("### Missing values by column")
    fig = px.bar(missing.sort_values("missing_percentage", ascending=False).head(20), x="column", y="missing_percentage",
                 title="Top 20 columns by missing-value percentage", text="missing_percentage")
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(chart_layout(fig, 430), use_container_width=True)
    show_table(missing.sort_values("missing_percentage", ascending=False), height=320)

    st.markdown("### Dataset coverage")
    coverage = raw_data.groupby(["year", "category"], as_index=False).agg(
        records=("canonical_key", "size"), institutions=("canonical_key", "nunique"))
    show_table(coverage, height=340)

    st.markdown("### Scores outside the expected 0–100 range")
    invalid_rows = []
    for column in ["overall_score", *PARAMETERS]:
        invalid = raw_data[column].notna() & ~raw_data[column].between(0, 100)
        invalid_rows.append({"field": column, "values_outside_0_100": int(invalid.sum())})
    show_table(pd.DataFrame(invalid_rows))

    st.markdown("### Column data types")
    dtypes = pd.DataFrame({"column": public_cols, "data_type": [str(raw_data[c].dtype) for c in public_cols]})
    show_table(dtypes, height=300)

# ------------------------------ Main -------------------------
def main():
    st.markdown(
        "<div class='hero'><div class='eyebrow'>Institutional performance analytics · 2017–2025</div>"
        "<h1>🎓 NIRF Insights</h1>"
        "<p>Explore India's institutional rankings, performance scores, regional patterns and ranking trends.</p></div>",
        unsafe_allow_html=True,
    )
    data_path = find_data_path()
    if data_path is None:
        st.error("NIRF dataset not found.")
        st.markdown("Place **nirf_clean.csv** in `data/processed/` relative to the project root, or set the `NIRF_DATA_PATH` environment variable.")
        st.code("project/\n├── app.py\n└── data/\n    └── processed/\n        └── nirf_clean.csv", language="text")
        st.stop()

    try:
        raw = load_data(str(data_path), data_path.stat().st_mtime)
    except Exception as exc:
        st.error(f"Could not load the NIRF dataset: {exc}")
        st.info("Check that the CSV contains at least year, category and institution_name columns.")
        st.stop()
    if raw.empty:
        st.error("The dataset loaded successfully but contains no usable records.")
        st.stop()

    clean = analysis_data(raw)
    current, context, page, year, category, state, institution, search = sidebar_controls(clean)

    st.markdown(
        "<div class='guide'><strong>Workflow:</strong> ① Choose a category & state in the sidebar &nbsp;→&nbsp; "
        "② Optionally select an institution &nbsp;→&nbsp; ③ Explore sections below. Historical trends preserve all available years.</div>",
        unsafe_allow_html=True,
    )

    if page == "Overview":
        render_overview(current, year, category)
    elif page == "Rankings & Trends":
        render_trends(context, year, selected_institution=institution)
    elif page == "Score Analysis":
        render_scores(current)
    elif page == "Multivariate Analysis":
        render_multivariate(current)
    elif page == "Transitions & Outliers":
        render_transitions(context)
    elif page == "Sample Questions":
        render_sample_questions(context, current, year, category)
    elif page == "Dynamic Explorer":
        render_dynamic_explorer(current, context)
    elif page == "Ask NIRF":
        render_ask_nirf(current, context)
    elif page == "Data Quality":
        render_data_quality(raw)

    st.divider()
    st.caption("NIRF Insights · Data covering 2017–2025 across all NIRF categories · Category-specific rankings.")
  

if __name__ == "__main__":
    main()
