from __future__ import annotations

import json
import os
from html import escape
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import streamlit as st
import streamlit.components.v1 as components
from eventsourcing.utils import clear_topic_cache

from application import InsuranceGraphApplication
from scenario_generator import apply_scenario, generate_complex_scenario


BASE_DIR = Path(__file__).resolve().parent
PLAYGROUND_DB = BASE_DIR / "streamlit_playground.db"
CATALOG_PATH = BASE_DIR / "playground_catalog.json"


def configure_page() -> None:
    st.set_page_config(
        page_title="RTM Events Playground",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(196, 224, 255, 0.35), transparent 28%),
                radial-gradient(circle at top right, rgba(250, 214, 165, 0.30), transparent 24%),
                linear-gradient(180deg, #f5f0e8 0%, #eef3f8 100%);
            color: #16202b;
            font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
        }
        h1, h2, h3 {
            font-family: "Iowan Old Style", "Palatino Linotype", serif;
            letter-spacing: 0.01em;
        }
        .hero {
            padding: 1.2rem 1.4rem;
            border: 1px solid rgba(16, 34, 52, 0.10);
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(230,241,252,0.78));
            box-shadow: 0 20px 50px rgba(38, 66, 92, 0.08);
            margin-bottom: 1rem;
        }
        .note {
            padding: 0.85rem 1rem;
            border-left: 4px solid #b86d2f;
            background: rgba(255, 248, 239, 0.9);
            border-radius: 12px;
            margin: 0.5rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def iso_from_date(value: date, hour: int = 12) -> str:
    return datetime.combine(value, time(hour=hour, tzinfo=timezone.utc)).isoformat()


def one_year_from_today() -> date:
    today = date.today()
    try:
        return today.replace(year=today.year + 1)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year + 1)


def get_app() -> InsuranceGraphApplication:
    # Streamlit reruns the script in-process. The eventsourcing topic cache
    # survives reruns and will reject newly defined class objects with the
    # same topic unless we clear it before constructing aggregates.
    clear_topic_cache()
    os.environ["SQLALCHEMY_URL"] = f"sqlite:///{PLAYGROUND_DB}"
    return InsuranceGraphApplication()


def load_catalog() -> List[Dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    return json.loads(CATALOG_PATH.read_text())


def save_catalog(catalog: List[Dict[str, Any]]) -> None:
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2))


def record_container(container_uuid: UUID, container_code: str, account_holder_id: str) -> None:
    catalog = load_catalog()
    if any(entry["container_uuid"] == str(container_uuid) for entry in catalog):
        return
    catalog.append(
        {
            "container_uuid": str(container_uuid),
            "container_code": container_code,
            "account_holder_id": account_holder_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_catalog(catalog)


def set_current_container(container_uuid: UUID) -> None:
    st.session_state["current_container_uuid"] = str(container_uuid)


def get_current_container_uuid() -> Optional[UUID]:
    value = st.session_state.get("current_container_uuid")
    if not value:
        return None
    return UUID(value)


def set_last_generated_scenario(container_uuid: UUID, scenario: Dict[str, Any]) -> None:
    st.session_state["last_generated_container_uuid"] = str(container_uuid)
    st.session_state["last_generated_scenario"] = scenario


def get_last_generated_scenario(container_uuid: UUID) -> Optional[Dict[str, Any]]:
    if st.session_state.get("last_generated_container_uuid") != str(container_uuid):
        return None
    return st.session_state.get("last_generated_scenario")


def seed_complex_scenario() -> tuple[UUID, Dict[str, Any]]:
    app = get_app()
    scenario = generate_complex_scenario()
    container_uuid = apply_scenario(app, scenario)
    record_container(
        container_uuid,
        scenario["container"]["container_id"],
        scenario["container"]["account_holder_id"],
    )
    set_last_generated_scenario(container_uuid, scenario)
    return container_uuid, scenario


def get_snapshot(container_uuid: UUID) -> Dict[str, Any]:
    return get_app().get_container_snapshot(container_uuid)


def safe_snapshot(container_uuid: Optional[UUID]) -> Optional[Dict[str, Any]]:
    if not container_uuid:
        return None
    try:
        return get_snapshot(container_uuid)
    except Exception:
        return None


def sidebar_controls() -> Optional[UUID]:
    st.sidebar.title("Playground")
    st.sidebar.caption(f"Event store: `{PLAYGROUND_DB.name}`")

    with st.sidebar.expander("Create Container", expanded=True):
        with st.form("create_container_form", clear_on_submit=True):
            container_code = st.text_input("Container Code", value="CONT-001", key="create_container_code")
            account_holder_id = st.text_input("Account Holder ID", value="PRSN-001", key="create_account_holder")
            submitted = st.form_submit_button("Open Container", use_container_width=True)
            if submitted:
                container_uuid = get_app().open_policy_container(
                    container_id=container_code,
                    account_holder_id=account_holder_id,
                )
                record_container(container_uuid, container_code, account_holder_id)
                set_current_container(container_uuid)
                st.success(f"Opened container {container_code}.")

    if st.sidebar.button("Generate Complex Scenario", use_container_width=True, key="seed_demo_button"):
        container_uuid, scenario = seed_complex_scenario()
        set_current_container(container_uuid)
        st.sidebar.success(
            f"Generated {len(scenario['policies'])} policies, {len(scenario['assets'])} assets, and {len(scenario['parties'])} parties."
        )

    catalog = load_catalog()
    if catalog:
        options = {f"{entry['container_code']} · {entry['container_uuid'][:8]}": entry for entry in catalog}
        selected = st.sidebar.selectbox(
            "Known Containers",
            options=list(options.keys()),
            key="known_container_select",
        )
        if st.sidebar.button("Load Selected Container", use_container_width=True, key="load_selected_container"):
            set_current_container(UUID(options[selected]["container_uuid"]))

    current_uuid = get_current_container_uuid()
    if current_uuid:
        st.sidebar.markdown(f"**Current UUID**  \n`{current_uuid}`")
    else:
        st.sidebar.info("Open a container or generate a complex scenario.")
    return current_uuid


def render_hero(snapshot: Optional[Dict[str, Any]]) -> None:
    st.markdown(
        """
        <div class="hero">
            <h1 style="margin:0;">RTM Replacement Playground</h1>
            <p style="margin:0.45rem 0 0 0;">
                Create a container, attach policies, assets, parties, and relationships,
                then apply MTAs and inspect current versus historical state.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if snapshot:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Policies", len(snapshot["policies"]))
        col2.metric("Parties", len(snapshot["parties"]))
        col3.metric("Assets", len(snapshot["assets"]))
        col4.metric("Portfolio Premium", f"£{snapshot['total_portfolio_premium']:.2f}")
    else:
        st.markdown(
            "<div class='note'>Start with an empty container or seed the demo scenario from the sidebar.</div>",
            unsafe_allow_html=True,
        )


def portfolio_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for portfolio_id, portfolio in snapshot["portfolios"].items():
        policy_ids = portfolio.get("policy_ids", [])
        rows.append(
            {
                "portfolio_id": portfolio_id,
                "type": portfolio.get("portfolio_type"),
                "display_name": portfolio.get("display_name"),
                "policies": len(policy_ids),
                "policy_ids": ", ".join(policy_ids),
            }
        )
    return rows


def party_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for party_id, party in snapshot["parties"].items():
        identity = party.get("identity", {})
        risk = party.get("risk_profile", {})
        rows.append(
            {
                "party_id": party_id,
                "name": f"{identity.get('first_name', '')} {identity.get('last_name', '')}".strip(),
                "dob": identity.get("dob"),
                "type": party.get("party_type"),
                "occupation": risk.get("occupation"),
                "licence_points": risk.get("licence_points"),
            }
        )
    return rows


def asset_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for asset_id, asset in snapshot["assets"].items():
        spec = asset.get("specification", {})
        ident = asset.get("identification", {})
        rows.append(
            {
                "asset_id": asset_id,
                "type": asset.get("asset_type"),
                "make_or_address": spec.get("make") or spec.get("address", {}).get("line_1") or spec.get("address"),
                "model_or_style": spec.get("model") or spec.get("property_style"),
                "reference": ident.get("registration_number") or ident.get("uprn") or ident.get("vin"),
            }
        )
    return rows


def policy_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for policy_id, policy in snapshot["policies"].items():
        terms = policy.get("terms", {})
        financials = policy.get("financials", {})
        rows.append(
            {
                "policy_id": policy_id,
                "product": policy.get("product_type"),
                "portfolio": policy.get("portfolio_id"),
                "asset": policy.get("asset_id"),
                "status": policy.get("status"),
                "premium": financials.get("total_payable"),
                "start": terms.get("start_date"),
                "end": terms.get("end_date"),
                "version": policy.get("version"),
            }
        )
    return rows


def relationship_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "relationship_id": rel["relationship_id"],
            "type": rel["relationship_type"],
            "role": rel["role"],
            "from": rel["from_node_id"],
            "to": rel["to_node_id"],
            "policy_context": rel["context_policy_id"],
            "effective_from": rel["effective_from"],
            "effective_to": rel["effective_to"],
            "status": rel["status"],
        }
        for rel in snapshot["relationships"]
    ]


def node_label(snapshot: Dict[str, Any], node_id: str) -> str:
    if node_id in snapshot["parties"]:
        identity = snapshot["parties"][node_id].get("identity", {})
        return f"{identity.get('first_name', '')} {identity.get('last_name', '')}".strip() or node_id
    if node_id in snapshot["policies"]:
        policy = snapshot["policies"][node_id]
        return f"{policy.get('product_type', 'policy').title()} {node_id}"
    if node_id in snapshot["assets"]:
        asset = snapshot["assets"][node_id]
        spec = asset.get("specification", {})
        ident = asset.get("identification", {})
        return spec.get("model") or spec.get("property_style") or ident.get("registration_number") or node_id
    return node_id


def evenly_spaced_positions(node_ids: List[str], x: int, top: int, bottom: int) -> Dict[str, tuple[int, int]]:
    if not node_ids:
        return {}
    if len(node_ids) == 1:
        return {node_ids[0]: (x, (top + bottom) // 2)}
    gap = (bottom - top) / (len(node_ids) - 1)
    return {
        node_id: (x, int(top + idx * gap))
        for idx, node_id in enumerate(node_ids)
    }


def build_relationship_svg(snapshot: Dict[str, Any], title: str) -> str:
    parties = list(snapshot["parties"].keys())
    policies = list(snapshot["policies"].keys())
    assets = list(snapshot["assets"].keys())
    height = max(420, 170 + max(len(parties), len(policies), len(assets), 1) * 110)
    width = 1100
    node_width = 180
    node_height = 54
    top = 100
    bottom = height - 70

    party_pos = evenly_spaced_positions(parties, 150, top, bottom)
    policy_pos = evenly_spaced_positions(policies, 550, top, bottom)
    asset_pos = evenly_spaced_positions(assets, 950, top, bottom)
    positions = {**party_pos, **policy_pos, **asset_pos}

    def line_markup(x1: int, y1: int, x2: int, y2: int, color: str, label: str, dashed: bool = False, bend: int = 0) -> str:
        if bend:
            cx1 = x1 + bend
            cx2 = x2 - bend
            path = f"M{x1},{y1} C{cx1},{y1} {cx2},{y2} {x2},{y2}"
            line = f"<path d='{path}' fill='none' stroke='{color}' stroke-width='2.5' {'stroke-dasharray=\"7,5\"' if dashed else ''} opacity='0.88'/>"
            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2 - 10
        else:
            line = f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color}' stroke-width='2.5' {'stroke-dasharray=\"7,5\"' if dashed else ''} opacity='0.88'/>"
            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2 - 10
        label_markup = f"""
        <rect x='{label_x - 48}' y='{label_y - 12}' width='96' height='20' rx='10'
              fill='rgba(255,255,255,0.86)' stroke='rgba(30,54,78,0.10)' />
        <text x='{label_x}' y='{label_y + 2}' text-anchor='middle' font-size='11' fill='#243649'>{escape(label[:18])}</text>
        """
        return line + label_markup

    lines: List[str] = []
    for idx, rel in enumerate(snapshot["relationships"]):
        from_id = rel["from_node_id"]
        to_id = rel["to_node_id"]
        if from_id not in positions or to_id not in positions:
            continue
        x1, y1 = positions[from_id]
        x2, y2 = positions[to_id]
        if from_id in party_pos:
            x1 += node_width // 2
        elif from_id in policy_pos:
            x1 += node_width // 2
        else:
            x1 -= node_width // 2
        if to_id in party_pos:
            x2 += node_width // 2
        elif to_id in policy_pos:
            x2 -= node_width // 2
        else:
            x2 -= node_width // 2

        color = {
            "party_to_policy": "#3d6fb6",
            "party_to_asset": "#b86d2f",
            "party_to_party": "#7a4ea3",
            "policy_to_asset": "#2f8f6a",
        }.get(rel["relationship_type"], "#557085")

        bend = 0
        if rel["relationship_type"] == "party_to_party":
            bend = 90 + (idx % 3) * 25
        elif rel["relationship_type"] == "party_to_asset":
            bend = 30 if abs(y2 - y1) < 45 else 0

        lines.append(line_markup(x1, y1, x2, y2, color, rel["role"], bend=bend))

    for idx, (policy_id, policy) in enumerate(snapshot["policies"].items()):
        asset_id = policy.get("asset_id")
        if not asset_id or policy_id not in policy_pos or asset_id not in asset_pos:
            continue
        x1, y1 = policy_pos[policy_id]
        x2, y2 = asset_pos[asset_id]
        lines.append(
            line_markup(
                x1 + node_width // 2,
                y1 + (idx % 2) * 6,
                x2 - node_width // 2,
                y2 + (idx % 2) * 6,
                "#2f8f6a",
                "Covers",
                dashed=True,
            )
        )

    def node_markup(node_id: str, x: int, y: int, fill: str, subtitle: str) -> str:
        return f"""
        <g>
            <rect x='{x - node_width / 2}' y='{y - node_height / 2}' width='{node_width}' height='{node_height}'
                  rx='18' fill='{fill}' stroke='rgba(18,32,43,0.12)' stroke-width='1.2'/>
            <text x='{x}' y='{y - 3}' text-anchor='middle' font-size='13' font-weight='600' fill='#13212e'>{escape(node_label(snapshot, node_id)[:28])}</text>
            <text x='{x}' y='{y + 15}' text-anchor='middle' font-size='11' fill='#4b6274'>{escape(subtitle)}</text>
        </g>
        """

    nodes: List[str] = []
    for node_id, (x, y) in party_pos.items():
        nodes.append(node_markup(node_id, x, y, "#f5dfc6", node_id))
    for node_id, (x, y) in policy_pos.items():
        product = snapshot["policies"][node_id].get("product_type", "policy").title()
        nodes.append(node_markup(node_id, x, y, "#dceaf7", f"{product} · {node_id}"))
    for node_id, (x, y) in asset_pos.items():
        asset_type = snapshot["assets"][node_id].get("asset_type", "asset").title()
        nodes.append(node_markup(node_id, x, y, "#dcefe5", f"{asset_type} · {node_id}"))

    svg = f"""
    <svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="{width}" height="{height}" rx="28" fill="rgba(255,255,255,0.72)" stroke="rgba(19,33,46,0.08)"/>
        <text x="42" y="44" font-size="24" font-weight="700" fill="#14212d">{escape(title)}</text>
        <text x="150" y="78" text-anchor="middle" font-size="14" font-weight="700" fill="#8c4f20">Parties</text>
        <text x="550" y="78" text-anchor="middle" font-size="14" font-weight="700" fill="#29598f">Policies</text>
        <text x="950" y="78" text-anchor="middle" font-size="14" font-weight="700" fill="#2b7b5c">Assets</text>
        {''.join(lines)}
        {''.join(nodes)}
    </svg>
    """
    return svg


def render_relationship_map(snapshot: Dict[str, Any], title: str, height: int = 620) -> None:
    components.html(build_relationship_svg(snapshot, title), height=height, scrolling=False)


def activity_rows(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for policy_id, policy in snapshot["policies"].items():
        for event in policy.get("mta_log", []):
            rows.append(
                {
                    "when": event.get("effective_from"),
                    "source": policy_id,
                    "event": event.get("event_type"),
                    "detail": event.get("reason") or event.get("status") or event.get("new_total") or event.get("asset_id"),
                }
            )
    for rel in snapshot["relationships"]:
        rows.append(
            {
                "when": rel.get("effective_from"),
                "source": rel["relationship_id"],
                "event": "RelationshipStarted",
                "detail": f"{rel['from_node_id']} -> {rel['to_node_id']} ({rel['role']})",
            }
        )
        if rel.get("effective_to"):
            rows.append(
                {
                    "when": rel.get("effective_to"),
                    "source": rel["relationship_id"],
                    "event": "RelationshipEnded",
                    "detail": f"{rel['from_node_id']} -> {rel['to_node_id']} ({rel['role']})",
                }
            )
    return sorted(rows, key=lambda row: row["when"] or "", reverse=True)


def render_dashboard(snapshot: Dict[str, Any], container_uuid: UUID) -> None:
    st.subheader("Dashboard")
    top_left, top_right = st.columns([1.1, 0.9])
    with top_left:
        st.markdown("**Container**")
        st.write(f"Code: `{snapshot['container_id']}`")
        st.write(f"Account holder: `{snapshot['account_holder_id']}`")
        st.write(f"Container version: `{snapshot['version']}`")
        st.write(f"Aggregate UUID: `{container_uuid}`")
    with top_right:
        st.markdown("**What is in this scenario?**")
        st.write(f"{len(snapshot['portfolios'])} portfolios")
        st.write(f"{len(snapshot['policies'])} policies")
        st.write(f"{len(snapshot['parties'])} parties")
        st.write(f"{len(snapshot['assets'])} assets")
        st.write(f"{len(snapshot['relationships'])} relationships")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**Policies**")
        st.dataframe(policy_rows(snapshot), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("**Relationships**")
        st.dataframe(relationship_rows(snapshot), use_container_width=True, hide_index=True)

    bottom_left, bottom_right = st.columns([1, 1])
    with bottom_left:
        st.markdown("**Portfolios**")
        st.dataframe(portfolio_rows(snapshot), use_container_width=True, hide_index=True)
    with bottom_right:
        st.markdown("**Recent Activity**")
        st.dataframe(activity_rows(snapshot)[:12], use_container_width=True, hide_index=True)

    st.markdown("**Relationship Map**")
    render_relationship_map(snapshot, "Current Relationship Graph")

    blueprint = get_last_generated_scenario(container_uuid)
    with st.expander("Raw JSON", expanded=False):
        st.json(
            {
                "container_summary": {
                    "container_id": snapshot["container_id"],
                    "account_holder_id": snapshot["account_holder_id"],
                    "version": snapshot["version"],
                },
                "generated_blueprint": blueprint,
                "current_snapshot": snapshot,
            },
            expanded=False,
        )


def render_explorer(snapshot: Dict[str, Any]) -> None:
    st.subheader("Explore")
    st.caption("Pick one entity at a time instead of reading the whole snapshot.")
    explorer_left, explorer_right = st.columns([0.55, 1.45])

    entity_type = explorer_left.radio(
        "Entity Type",
        options=["Policy", "Party", "Asset", "Relationship"],
        key="explore_entity_type",
    )

    entity_maps = {
        "Policy": snapshot["policies"],
        "Party": snapshot["parties"],
        "Asset": snapshot["assets"],
        "Relationship": {rel["relationship_id"]: rel for rel in snapshot["relationships"]},
    }
    selected_map = entity_maps[entity_type]
    selected_options = list(selected_map.keys())
    if not selected_options:
        explorer_left.info(f"No {entity_type.lower()} records available in this container.")
        return
    current_selected_id = st.session_state.get("explore_entity_id")
    if current_selected_id not in selected_options:
        st.session_state["explore_entity_id"] = selected_options[0]
    selected_id = explorer_left.selectbox(
        f"{entity_type} ID",
        options=selected_options,
        key="explore_entity_id",
    )
    explorer_left.markdown("**Collection View**")
    if entity_type == "Policy":
        explorer_left.dataframe(policy_rows(snapshot), use_container_width=True, hide_index=True)
    elif entity_type == "Party":
        explorer_left.dataframe(party_rows(snapshot), use_container_width=True, hide_index=True)
    elif entity_type == "Asset":
        explorer_left.dataframe(asset_rows(snapshot), use_container_width=True, hide_index=True)
    else:
        explorer_left.dataframe(relationship_rows(snapshot), use_container_width=True, hide_index=True)

    explorer_right.markdown(f"**{entity_type} Detail: {selected_id}**")
    explorer_right.json(selected_map.get(selected_id, {}), expanded=True)
    explorer_right.markdown("**Relationship Map**")
    render_relationship_map(snapshot, "Graph Context For Current Container", height=560)


def render_actions(container_uuid: UUID, snapshot: Dict[str, Any]) -> None:
    st.subheader("Actions")
    st.caption("Build structure on the left. Change existing data on the right.")
    portfolios = list(snapshot["portfolios"].keys())
    assets = list(snapshot["assets"].keys())
    policies = list(snapshot["policies"].keys())
    parties = list(snapshot["parties"].keys())
    relationship_ids = [relationship["relationship_id"] for relationship in snapshot["relationships"]]
    node_options = parties + assets + policies

    left, right = st.columns(2)
    with left:
        with st.expander("1. Add Portfolio Or Party", expanded=True):
            portfolio_col, party_col = st.columns(2)
            with portfolio_col:
                with st.form("portfolio_form", clear_on_submit=True):
                    portfolio_id = st.text_input("Portfolio ID", key="portfolio_id")
                    portfolio_type = st.selectbox("Portfolio Type", options=["motor", "motorcycle", "home", "contents", "mixed"], key="portfolio_type")
                    display_name = st.text_input("Display Name", key="portfolio_display_name")
                    if st.form_submit_button("Add Portfolio", use_container_width=True):
                        get_app().add_portfolio(container_uuid, portfolio_id, portfolio_type, display_name or None)
                        st.success(f"Added portfolio {portfolio_id}.")
            with party_col:
                with st.form("party_form", clear_on_submit=True):
                    party_id = st.text_input("Party ID", key="party_id")
                    party_type = st.selectbox("Party Type", options=["Individual", "Company"], key="party_type")
                    first_name = st.text_input("First Name", key="party_first_name")
                    last_name = st.text_input("Last Name", key="party_last_name")
                    dob = st.date_input("Date of Birth", value=date(1985, 5, 5), key="party_dob")
                    email = st.text_input("Email", key="party_email")
                    phone = st.text_input("Phone", key="party_phone")
                    licence_points = st.number_input("Licence Points", min_value=0, step=1, key="party_licence_points")
                    if st.form_submit_button("Register Party", use_container_width=True):
                        get_app().register_party(
                            container_id=container_uuid,
                            party_id=party_id,
                            identity={"first_name": first_name, "last_name": last_name, "dob": dob.isoformat()},
                            contact_details={"email": email, "phone": phone},
                            risk_profile={"licence_points": int(licence_points)},
                            party_type=party_type,
                        )
                        st.success(f"Registered party {party_id}.")

        with st.expander("2. Add Asset Or Policy", expanded=True):
            asset_col, policy_col = st.columns(2)
            with asset_col:
                with st.form("asset_form", clear_on_submit=True):
                    asset_id = st.text_input("Asset ID", key="asset_id")
                    asset_type = st.selectbox("Asset Type", options=["vehicle", "motorcycle", "home"], key="asset_type")
                    vin_or_ref = st.text_input("VIN / UPRN", key="asset_identifier")
                    registration = st.text_input("Registration", key="asset_registration")
                    make = st.text_input("Make", key="asset_make")
                    model = st.text_input("Model", key="asset_model")
                    engine_cc = st.number_input("Engine CC", min_value=0, step=50, key="asset_engine_cc")
                    address = st.text_input("Property Address", key="asset_address")
                    garaging_postcode = st.text_input("Garaging / Risk Postcode", key="asset_postcode")
                    if st.form_submit_button("Register Asset", use_container_width=True):
                        get_app().register_asset(
                            container_id=container_uuid,
                            asset_id=asset_id,
                            asset_type=asset_type,
                            identification={"primary_reference": vin_or_ref, "registration_number": registration},
                            specification={k: v for k, v in {"make": make, "model": model, "engine_cc": int(engine_cc) if engine_cc else None, "address": address}.items() if v not in ("", None)},
                            risk_attributes={k: v for k, v in {"location_postcode": garaging_postcode}.items() if v},
                        )
                        st.success(f"Registered asset {asset_id}.")
            with policy_col:
                with st.form("policy_form", clear_on_submit=True):
                    policy_id = st.text_input("Policy ID", key="policy_id")
                    portfolio_id = st.selectbox("Portfolio", options=portfolios if portfolios else ["<create portfolio first>"], key="policy_portfolio_id")
                    asset_id = st.selectbox("Linked Asset", options=assets if assets else ["<register asset first>"], key="policy_asset_id")
                    product_type = st.selectbox("Product Type", options=["motor", "motorcycle", "home", "contents"], key="policy_product_type")
                    start = st.date_input("Start Date", value=date.today(), key="policy_start")
                    end = st.date_input("End Date", value=one_year_from_today(), key="policy_end")
                    duration_months = st.number_input("Duration (Months)", min_value=1, step=1, value=12, key="policy_duration")
                    premium_amount = st.number_input("Premium", min_value=0.0, step=25.0, value=900.0, key="policy_premium")
                    ipt_amount = st.number_input("IPT", min_value=0.0, step=5.0, value=90.0, key="policy_ipt")
                    excess_amount = st.number_input("Excess", min_value=0.0, step=50.0, value=250.0, key="policy_excess")
                    ncd_years = st.number_input("NCD Years", min_value=0, step=1, value=0, key="policy_ncd")
                    legal_protection = st.checkbox("Legal Protection", key="policy_legal_protection")
                    if st.form_submit_button("Create Policy", use_container_width=True):
                        if not portfolios or portfolio_id.startswith("<"):
                            st.error("Create a portfolio first.")
                        elif not assets or asset_id.startswith("<"):
                            st.error("Register an asset first.")
                        else:
                            app = get_app()
                            effective = iso_from_date(start, hour=9)
                            app.create_policy(
                                container_id=container_uuid,
                                policy_id=policy_id,
                                portfolio_id=portfolio_id,
                                product_type=product_type,
                                start_date=effective,
                                end_date=iso_from_date(end, hour=23),
                                duration_months=int(duration_months),
                                premium_amount=float(premium_amount),
                                ipt_amount=float(ipt_amount),
                                excess_amount=float(excess_amount),
                                ncd_years=int(ncd_years),
                                legal_protection=legal_protection,
                            )
                            app.link_policy_to_asset(container_uuid, policy_id, asset_id, effective)
                            st.success(f"Created policy {policy_id}.")

    with right:
        with st.expander("3. Start Or End Relationship", expanded=True):
            rel_start, rel_end = st.columns(2)
            with rel_start:
                with st.form("start_relationship_form", clear_on_submit=True):
                    relationship_id = st.text_input("Relationship ID", key="relationship_id")
                    relationship_type = st.selectbox("Relationship Type", options=["party_to_policy", "party_to_asset", "party_to_party", "policy_to_asset"], key="relationship_type")
                    from_node_id = st.selectbox("From Node", options=node_options or ["<create nodes first>"], key="relationship_from")
                    to_node_id = st.selectbox("To Node", options=node_options or ["<create nodes first>"], key="relationship_to")
                    role = st.text_input("Role", value="NamedDriver", key="relationship_role")
                    context_policy_id = st.selectbox("Context Policy", options=[""] + policies, key="relationship_policy_context")
                    effective_from = st.date_input("Effective From", value=date.today(), key="relationship_effective_from")
                    if st.form_submit_button("Start", use_container_width=True):
                        if not node_options:
                            st.error("Create parties, assets, or policies first.")
                        else:
                            get_app().start_relationship(
                                container_id=container_uuid,
                                relationship_id=relationship_id,
                                relationship_type=relationship_type,
                                from_node_id=from_node_id,
                                to_node_id=to_node_id,
                                role=role,
                                effective_from=iso_from_date(effective_from, hour=9),
                                context_policy_id=context_policy_id or None,
                            )
                            st.success(f"Started relationship {relationship_id}.")
            with rel_end:
                with st.form("end_relationship_form", clear_on_submit=True):
                    relationship_id = st.selectbox("Relationship To End", options=relationship_ids if relationship_ids else ["<no relationships yet>"], key="relationship_end_id")
                    effective_to = st.date_input("Effective To", value=date.today(), key="relationship_effective_to")
                    if st.form_submit_button("End", use_container_width=True):
                        if not relationship_ids:
                            st.error("No relationships available.")
                        else:
                            get_app().end_relationship(
                                container_id=container_uuid,
                                relationship_id=relationship_id,
                                effective_to=iso_from_date(effective_to, hour=18),
                            )
                            st.success(f"Ended relationship {relationship_id}.")

        with st.expander("4. Apply Policy MTA", expanded=True):
            with st.form("premium_mta_form", clear_on_submit=True):
                policy_id = st.selectbox("Policy", options=policies if policies else ["<create a policy first>"], key="mta_policy_id")
                effective_from = st.date_input("MTA Date", value=date.today(), key="mta_date")
                new_premium = st.number_input("New Premium", min_value=0.0, step=25.0, value=1000.0, key="mta_new_premium")
                new_ipt = st.number_input("New IPT", min_value=0.0, step=5.0, value=100.0, key="mta_new_ipt")
                legal_protection = st.checkbox("Enable Legal Protection", key="mta_legal_protection")
                ncd_years = st.number_input("Updated NCD Years", min_value=0, step=1, value=0, key="mta_ncd_years")
                new_status = st.selectbox("Status", options=["active", "pending", "cancelled", "lapsed", "renewed"], key="mta_status")
                reason = st.text_input("Reason", value="User-driven MTA", key="mta_reason")
                if st.form_submit_button("Apply MTA", use_container_width=True):
                    if not policies:
                        st.error("Create a policy first.")
                    else:
                        app = get_app()
                        effective = iso_from_date(effective_from, hour=10)
                        app.adjust_policy_premium(container_uuid, policy_id, float(new_premium), float(new_ipt), effective, reason)
                        app.change_policy_legal_protection(container_uuid, policy_id, legal_protection, effective, reason)
                        app.change_policy_no_claims_discount(container_uuid, policy_id, int(ncd_years), effective, reason)
                        app.change_policy_status(container_uuid, policy_id, new_status, effective, reason)
                        st.success(f"Applied MTA to {policy_id}.")


def render_history(snapshot: Dict[str, Any], container_uuid: UUID) -> None:
    st.subheader("Historical Views")
    policies = snapshot["policies"]
    app = get_app()
    blueprint = get_last_generated_scenario(container_uuid)

    left, right = st.columns([0.9, 1.1])
    with left:
        timeline_markers = []
        if blueprint:
            timeline_markers = blueprint.get("meta", {}).get("timeline_markers", [])
        if timeline_markers:
            selected_marker = st.selectbox(
                "Scenario Timeline Marker",
                options=timeline_markers,
                index=max(0, len(timeline_markers) - 1),
                key="history_timeline_marker",
            )
            default_as_at = date.fromisoformat(selected_marker)
            st.caption("Use the marker dates to see relationship changes across the seeded scenario.")
        else:
            default_as_at = date.today()

        as_at = st.date_input("Graph As-At Date", value=default_as_at, key="as_at_date")
        as_at_snapshot = app.get_graph_as_of(container_uuid, iso_from_date(as_at, hour=12))
        st.markdown("**As-At Relationship Map**")
        render_relationship_map(as_at_snapshot, f"Relationship Graph As At {as_at.isoformat()}", height=560)
        st.markdown("**Active Relationships As At Date**")
        st.dataframe(relationship_rows(as_at_snapshot), use_container_width=True, hide_index=True)
        st.markdown("**All Relationship Edges**")
        st.dataframe(relationship_rows(snapshot), use_container_width=True, hide_index=True)

    with right:
        policy_ids = list(policies.keys())
        if not policy_ids:
            st.info("Create a policy to inspect its historical versions.")
            return
        selected_policy_id = st.selectbox("Policy For Version Inspection", options=policy_ids, key="history_policy_select")
        current_policy = app.get_policy(container_uuid, selected_policy_id)
        version = st.number_input(
            "Historical Version",
            min_value=1,
            max_value=int(current_policy.version),
            value=int(current_policy.version),
            step=1,
            key="history_policy_version",
        )
        historical_policy = app.get_policy(container_uuid, selected_policy_id, version=int(version))
        current_payload = app._serialize_policy(current_policy)  # noqa: SLF001
        historical_payload = app._serialize_policy(historical_policy)  # noqa: SLF001
        st.markdown("**Current Policy**")
        st.json(current_payload, expanded=False)
        st.markdown("**Selected Historical Version**")
        st.json(historical_payload, expanded=False)
        st.markdown("**Policy Event Timeline**")
        st.dataframe(current_policy.mta_log, use_container_width=True)


def main() -> None:
    configure_page()
    current_uuid = sidebar_controls()
    snapshot = safe_snapshot(current_uuid)
    render_hero(snapshot)

    if not current_uuid or not snapshot:
        return

    tabs = st.tabs(
        [
            "Dashboard",
            "Explore",
            "Actions",
            "History",
        ]
    )
    with tabs[0]:
        render_dashboard(snapshot, current_uuid)
    with tabs[1]:
        render_explorer(snapshot)
    with tabs[2]:
        render_actions(current_uuid, snapshot)
    with tabs[3]:
        render_history(snapshot, current_uuid)


if __name__ == "__main__":
    main()
