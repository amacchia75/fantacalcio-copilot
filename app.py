import json
import os
from datetime import date

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
PLAYERS_SEED = os.path.join(DATA_DIR, "players_seed.json")
RIVALS_SEED = os.path.join(DATA_DIR, "rivals_seed.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

TEAM_NAME = "Roma Non Perdona"
LEAGUE_NAME = "Fanta Logista 26-27"
TOTAL_BUDGET = 500
INITIAL_SLOTS = {"P": 3, "D": 8, "C": 8, "A": 6}
ROLES = ["P", "D", "C", "A"]
ROLE_LABELS = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
TIERS = ["1° Slot", "2° Slot", "3° Slot", "4° Slot", "Bug di Listone", "Scommessa", "Low-Cost"]

st.set_page_config(page_title=f"Fantacalcio Co-Pilot – {TEAM_NAME}", page_icon="⚽", layout="wide")

# ---------------------------------------------------------------------------
# Persistenza stato (rose, budget, quotazioni) su data/state.json
# ---------------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state["players"], state["rivals"], state.get("quotazioni_updated_at")
    with open(PLAYERS_SEED, "r", encoding="utf-8") as f:
        players = json.load(f)
    with open(RIVALS_SEED, "r", encoding="utf-8") as f:
        rivals = json.load(f)
    return players, rivals, "2026-08-23"


def save_state():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "players": st.session_state.players,
                "rivals": st.session_state.rivals,
                "quotazioni_updated_at": st.session_state.quotazioni_updated_at,
            },
            f,
            ensure_ascii=False,
        )


if "players" not in st.session_state:
    players, rivals, quot_date = load_state()
    st.session_state.players = players
    st.session_state.rivals = rivals
    st.session_state.quotazioni_updated_at = quot_date

players_df = pd.DataFrame(st.session_state.players)
rivals_df = pd.DataFrame(st.session_state.rivals)

# ---------------------------------------------------------------------------
# Calcoli derivati (rosa utente, crediti, media punti attesa)
# ---------------------------------------------------------------------------
def compute_squad_summary(df: pd.DataFrame):
    mine = df[df["status"] == "bought_by_user"].copy()
    mine["price"] = mine["purchasePrice"].fillna(mine["fmv"])
    spent = mine["price"].sum()
    remaining = max(0, TOTAL_BUDGET - spent)

    spent_by_role = {r: mine[mine["role"] == r]["price"].sum() for r in ROLES}
    slots_left = {r: max(0, INITIAL_SLOTS[r] - len(mine[mine["role"] == r])) for r in ROLES}

    p_start = mine[mine["role"] == "P"].head(1)
    d_start = mine[mine["role"] == "D"].sort_values("projectedAvgVote", ascending=False).head(3)
    c_start = mine[mine["role"] == "C"].sort_values("projectedFantaVote", ascending=False).head(4)
    a_start = mine[mine["role"] == "A"].sort_values("projectedFantaVote", ascending=False).head(3)

    mod_bonus = 0
    if len(d_start) >= 3 and len(p_start) >= 1:
        avg = (d_start["projectedAvgVote"].sum() + p_start["projectedAvgVote"].iloc[0]) / 4
        if avg >= 6.5:
            mod_bonus = 6
        elif avg >= 6.25:
            mod_bonus = 3
        elif avg >= 6.0:
            mod_bonus = 1

    starters = pd.concat([p_start, d_start, c_start, a_start])
    starter_points = starters["projectedFantaVote"].sum()
    missing = 11 - len(starters)
    filler_points = missing * 6.0
    projected_avg = round(starter_points + filler_points + mod_bonus, 1)

    return {
        "mine": mine,
        "spent": spent,
        "remaining": remaining,
        "spent_by_role": spent_by_role,
        "slots_left": slots_left,
        "mod_bonus": mod_bonus,
        "projected_avg": projected_avg,
    }


summary = compute_squad_summary(players_df)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### ⚽ {TEAM_NAME}")
    st.caption(f"Lega: {LEAGUE_NAME} • Asta Classic • 10 squadre • 500 crediti")
    st.metric("Crediti rimanenti", f"{summary['remaining']:.0f}", f"-{summary['spent']:.0f} spesi")
    st.metric("Media punti attesa", summary["projected_avg"], f"Modificatore +{summary['mod_bonus']}")
    st.write("**Slot rimasti**")
    cols = st.columns(4)
    for i, r in enumerate(ROLES):
        cols[i].metric(r, summary["slots_left"][r])

    st.divider()
    if st.session_state.quotazioni_updated_at:
        st.caption(f"Quotazioni aggiornate al: **{st.session_state.quotazioni_updated_at}**")

    if st.button("🔁 Azzera asta (reset totale)", use_container_width=True):
        players, rivals, _ = (
            json.load(open(PLAYERS_SEED, encoding="utf-8")),
            json.load(open(RIVALS_SEED, encoding="utf-8")),
            None,
        )
        st.session_state.players = players
        st.session_state.rivals = rivals
        st.session_state.quotazioni_updated_at = "2026-08-23"
        save_state()
        st.rerun()

st.title("Fantacalcio Co-Pilot 2026/27")

tab_dash, tab_listone, tab_rivali, tab_quot = st.tabs(
    ["🏠 La mia rosa", "📋 Listone", "⚔️ Rivali", "🔄 Aggiorna Quotazioni"]
)

# ---------------------------------------------------------------------------
# TAB: Dashboard / La mia rosa
# ---------------------------------------------------------------------------
with tab_dash:
    st.subheader(f"Rosa di {TEAM_NAME}")
    mine = summary["mine"]
    if mine.empty:
        st.info("Non hai ancora acquistato nessun calciatore. Vai al tab **Listone** per iniziare l'asta.")
    else:
        for role in ROLES:
            role_players = mine[mine["role"] == role]
            if role_players.empty:
                continue
            st.markdown(f"**{ROLE_LABELS[role]}** ({len(role_players)}/{INITIAL_SLOTS[role]})")
            show = role_players[["name", "team", "tier", "price", "projectedFantaVote", "tacticalNotes"]].rename(
                columns={
                    "name": "Nome",
                    "team": "Squadra",
                    "tier": "Tier",
                    "price": "Prezzo pagato",
                    "projectedFantaVote": "Fantamedia att.",
                    "tacticalNotes": "Note",
                }
            )
            st.dataframe(show, use_container_width=True, hide_index=True)

            for _, row in role_players.iterrows():
                if st.button(f"❌ Rimuovi {row['name']}", key=f"remove-{row['id']}"):
                    for p in st.session_state.players:
                        if p["id"] == row["id"]:
                            p["status"] = "available"
                            p["purchasePrice"] = None
                            p["buyerName"] = None
                    save_state()
                    st.rerun()

# ---------------------------------------------------------------------------
# TAB: Listone
# ---------------------------------------------------------------------------
with tab_listone:
    st.subheader("Listone calciatori")

    f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
    role_filter = f1.selectbox("Ruolo", ["Tutti"] + ROLES)
    team_filter = f2.selectbox("Squadra", ["Tutte"] + sorted(players_df["team"].unique().tolist()))
    tier_filter = f3.selectbox("Tier", ["Tutti"] + TIERS)
    search = f4.text_input("Cerca calciatore")
    only_available = st.checkbox("Mostra solo disponibili", value=True)

    view = players_df.copy()
    if role_filter != "Tutti":
        view = view[view["role"] == role_filter]
    if team_filter != "Tutte":
        view = view[view["team"] == team_filter]
    if tier_filter != "Tutti":
        view = view[view["tier"] == tier_filter]
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]
    if only_available:
        view = view[view["status"] == "available"]

    view = view.sort_values("fmv", ascending=False)

    display_cols = ["name", "team", "role", "tier", "fmv", "fmvMin", "fmvMax", "projectedFantaVote", "status"]
    display = view[display_cols].rename(
        columns={
            "name": "Nome",
            "team": "Squadra",
            "role": "R",
            "tier": "Tier",
            "fmv": "Qt.A",
            "fmvMin": "Min",
            "fmvMax": "Max",
            "projectedFantaVote": "Fantamedia att.",
            "status": "Stato",
        }
    )

    st.caption(f"{len(view)} calciatori trovati")
    event = st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="listone_table",
    )

    selected_rows = event.selection.rows if event and event.selection else []
    if selected_rows:
        sel = view.iloc[selected_rows[0]]
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"### {sel['name']} — {sel['team']} ({sel['role']})")
            st.write(sel["tacticalNotes"])
            if sel.get("coach"):
                st.caption(f"Allenatore: {sel['coach']}")
            st.write(
                f"Qt.A **{sel['fmv']}** (range {sel['fmvMin']}–{sel['fmvMax']}) • "
                f"Media voto att. **{sel['projectedAvgVote']}** • Fantamedia att. **{sel['projectedFantaVote']}**"
            )
        with c2:
            if sel["status"] == "available":
                price = st.number_input(
                    "Prezzo pagato", min_value=1, max_value=TOTAL_BUDGET, value=int(sel["fmv"]), key="buy_price"
                )
                if st.button(f"✅ Assegna a {TEAM_NAME}", use_container_width=True, key="buy_btn"):
                    for p in st.session_state.players:
                        if p["id"] == sel["id"]:
                            p["status"] = "bought_by_user"
                            p["purchasePrice"] = int(price)
                    save_state()
                    st.rerun()

                rival_name = st.selectbox(
                    "Oppure segna comprato da un rivale", [r["name"] for r in st.session_state.rivals], key="rival_sel"
                )
                if st.button("🚫 Segna comprato da rivale", use_container_width=True, key="rival_buy_btn"):
                    for p in st.session_state.players:
                        if p["id"] == sel["id"]:
                            p["status"] = "bought_by_rival"
                            p["buyerName"] = rival_name
                    save_state()
                    st.rerun()
            else:
                st.info(f"Non disponibile — stato: **{sel['status']}**"
                        + (f" ({sel.get('buyerName')})" if sel.get("buyerName") else ""))
                if st.button("↩️ Rimetti disponibile", use_container_width=True, key="release_btn"):
                    for p in st.session_state.players:
                        if p["id"] == sel["id"]:
                            p["status"] = "available"
                            p["purchasePrice"] = None
                            p["buyerName"] = None
                    save_state()
                    st.rerun()

    st.download_button(
        "⬇️ Esporta listone corrente in CSV",
        data=players_df.to_csv(index=False).encode("utf-8"),
        file_name="Listone_Fantacalcio_2026_2027.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------------
# TAB: Rivali
# ---------------------------------------------------------------------------
with tab_rivali:
    st.subheader("Squadre rivali")
    st.caption(f"Lega {LEAGUE_NAME}")

    edited = st.data_editor(
        rivals_df[["name", "manager", "spentCredits"]].rename(
            columns={"name": "Squadra", "manager": "Manager", "spentCredits": "Crediti spesi"}
        ),
        use_container_width=True,
        hide_index=True,
        disabled=["Squadra", "Manager"],
        key="rivals_editor",
    )

    if st.button("💾 Salva budget rivali"):
        for i, row in edited.iterrows():
            st.session_state.rivals[i]["spentCredits"] = int(row["Crediti spesi"])
            st.session_state.rivals[i]["remainingCredits"] = max(0, TOTAL_BUDGET - int(row["Crediti spesi"]))
        save_state()
        st.rerun()

    show_rivals = pd.DataFrame(st.session_state.rivals)
    show_rivals["remainingCredits"] = TOTAL_BUDGET - show_rivals["spentCredits"]
    st.dataframe(
        show_rivals[["name", "manager", "spentCredits", "remainingCredits"]].rename(
            columns={
                "name": "Squadra",
                "manager": "Manager",
                "spentCredits": "Spesi",
                "remainingCredits": "Rimanenti",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# TAB: Aggiorna Quotazioni (chiusura mercato 1 settembre 2026)
# ---------------------------------------------------------------------------
with tab_quot:
    st.subheader("Aggiorna Quotazioni Ufficiali")
    st.write(
        "Carica il file **Quotazioni_Fantacalcio** ufficiale (formato Fantacalcio.it, foglio "
        "**Tutti**) per aggiornare Qt.A, FVM e tier di tutti i calciatori già a listone. "
        "Rose, prezzi pagati e note vengono mantenuti. Usalo alla chiusura del mercato "
        "(1° settembre 2026) o ogni volta che viene ripubblicato un nuovo listone."
    )
    if st.session_state.quotazioni_updated_at:
        st.caption(f"Ultimo aggiornamento: **{st.session_state.quotazioni_updated_at}**")

    uploaded = st.file_uploader("File Quotazioni (.xlsx)", type=["xlsx", "xls"])
    if uploaded is not None:
        try:
            raw = pd.read_excel(uploaded, sheet_name="Tutti", skiprows=1)
        except ValueError:
            raw = pd.read_excel(uploaded, sheet_name=0, skiprows=1)

        raw = raw.dropna(subset=["Nome", "Squadra", "R"])

        def tier_from_pct(pct, fvm):
            if pct <= 0.08:
                return "1° Slot"
            if pct <= 0.22:
                return "2° Slot"
            if pct <= 0.45:
                return "3° Slot"
            if pct <= 0.70:
                return "4° Slot"
            return "Low-Cost" if fvm <= 3 else "Scommessa"

        raw["pct"] = raw.groupby("R")["FVM"].rank(ascending=False, pct=True)
        raw["tier"] = raw.apply(lambda r: tier_from_pct(r["pct"], r["FVM"] or 0), axis=1)

        updates = {}
        for _, r in raw.iterrows():
            qta = float(r["Qt.A"]) if pd.notna(r["Qt.A"]) else 0
            qti = float(r["Qt.I"]) if pd.notna(r["Qt.I"]) else qta
            key = (str(r["Nome"]).strip().lower(), str(r["Squadra"]).strip().lower())
            updates[key] = {
                "fmv": int(qta),
                "fmvMin": int(max(1, min(qta, qti))),
                "fmvMax": int(max(qta, round(qta * 1.15))),
                "tier": r["tier"],
                "fvm": r["FVM"],
            }

        matched = 0
        today = date.today().isoformat()
        for p in st.session_state.players:
            key = (p["name"].strip().lower(), p["team"].strip().lower())
            u = updates.get(key) or updates.get((p["name"].strip().lower(), ""))
            if not u:
                # fallback: match solo per nome se la squadra non combacia (es. cessione)
                for (n, t), val in updates.items():
                    if n == p["name"].strip().lower():
                        u = val
                        break
            if u:
                matched += 1
                p["fmv"] = u["fmv"]
                p["fmvMin"] = u["fmvMin"]
                p["fmvMax"] = u["fmvMax"]
                p["tier"] = u["tier"]
                p["tacticalNotes"] = f"{p['tacticalNotes']} [Aggiornamento quotazioni {today}: Qt.A {u['fmv']} / FVM {u['fvm']}]"

        st.session_state.quotazioni_updated_at = today
        save_state()
        st.success(f"File letto: {len(raw)} calciatori nel listone ufficiale. Quotazioni aggiornate per {matched} calciatori già presenti nel tuo database.")
        st.rerun()
