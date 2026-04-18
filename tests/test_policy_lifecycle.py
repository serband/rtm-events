import os

import pytest

from application import InsuranceGraphApplication


@pytest.fixture
def app(tmp_path):
    os.environ["SQLALCHEMY_URL"] = f"sqlite:///{tmp_path / 'policy_lifecycle.db'}"
    return InsuranceGraphApplication()


def test_policy_mta_preserves_monday_version(app: InsuranceGraphApplication) -> None:
    container_id = app.open_policy_container("CONT-LIFE-001", "PRSN-001")
    app.add_portfolio(container_id, "PORT-MOTOR-001", "motor", "Annual Motor")
    app.create_policy(
        container_id=container_id,
        policy_id="POL-AUTO-001",
        portfolio_id="PORT-MOTOR-001",
        product_type="motor",
        start_date="2026-04-13T09:00:00+00:00",
        end_date="2027-04-12T23:59:59+00:00",
        duration_months=12,
        premium_amount=1000.0,
        ipt_amount=100.0,
        excess_amount=250.0,
        ncd_years=5,
        legal_protection=False,
    )

    monday_policy = app.get_policy(container_id, "POL-AUTO-001")
    monday_version = monday_policy.version

    app.adjust_policy_premium(
        container_id,
        "POL-AUTO-001",
        premium_amount=1100.0,
        ipt_amount=110.0,
        effective_from="2026-04-14T10:00:00+00:00",
        reason="Vehicle change MTA",
    )
    app.change_policy_legal_protection(
        container_id,
        "POL-AUTO-001",
        enabled=True,
        effective_from="2026-04-14T10:00:00+00:00",
        reason="Customer added legal protection",
    )

    current_policy = app.get_policy(container_id, "POL-AUTO-001")
    restored_policy = app.get_policy(container_id, "POL-AUTO-001", version=monday_version)

    assert current_policy.financials["total_payable"] == 1210.0
    assert current_policy.terms["legal_protection"] is True
    assert restored_policy.financials["total_payable"] == 1100.0
    assert restored_policy.terms["legal_protection"] is False


def test_policy_links_to_exactly_one_asset(app: InsuranceGraphApplication) -> None:
    container_id = app.open_policy_container("CONT-LIFE-002", "PRSN-001")
    app.add_portfolio(container_id, "PORT-MOTOR-001", "motor", "Annual Motor")
    app.register_asset(
        container_id,
        asset_id="AST-001",
        asset_type="vehicle",
        identification={"vin": "VIN-001"},
        specification={"make": "Toyota", "model": "Yaris"},
        risk_attributes={},
    )
    app.register_asset(
        container_id,
        asset_id="AST-002",
        asset_type="vehicle",
        identification={"vin": "VIN-002"},
        specification={"make": "Ford", "model": "Focus"},
        risk_attributes={},
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-AUTO-002",
        portfolio_id="PORT-MOTOR-001",
        product_type="motor",
        start_date="2026-04-13T09:00:00+00:00",
        end_date="2027-04-12T23:59:59+00:00",
        duration_months=12,
        premium_amount=800.0,
        ipt_amount=80.0,
        excess_amount=350.0,
        ncd_years=3,
    )

    app.link_policy_to_asset(container_id, "POL-AUTO-002", "AST-001", "2026-04-13T09:00:00+00:00")

    with pytest.raises(ValueError):
        app.link_policy_to_asset(container_id, "POL-AUTO-002", "AST-002", "2026-04-14T10:00:00+00:00")


def test_policy_cancellation_ends_policy_context_relationships(app: InsuranceGraphApplication) -> None:
    container_id = app.open_policy_container("CONT-LIFE-003", "PRSN-001")
    app.add_portfolio(container_id, "PORT-MOTOR-001", "motor", "Annual Motor")
    app.register_party(
        container_id,
        "PRSN-001",
        identity={"first_name": "John", "last_name": "Doe", "dob": "1980-01-01"},
    )
    app.register_asset(
        container_id,
        asset_id="AST-001",
        asset_type="vehicle",
        identification={"vin": "VIN-001"},
        specification={"make": "Toyota", "model": "Yaris"},
        risk_attributes={},
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-AUTO-003",
        portfolio_id="PORT-MOTOR-001",
        product_type="motor",
        start_date="2026-04-13T09:00:00+00:00",
        end_date="2027-04-12T23:59:59+00:00",
        duration_months=12,
        premium_amount=800.0,
        ipt_amount=80.0,
        excess_amount=250.0,
        ncd_years=3,
    )
    app.link_policy_to_asset(container_id, "POL-AUTO-003", "AST-001", "2026-04-13T09:00:00+00:00")
    app.start_relationship(
        container_id,
        relationship_id="REL-CANCEL-001",
        relationship_type="party_to_policy",
        from_node_id="PRSN-001",
        to_node_id="POL-AUTO-003",
        role="Policyholder",
        effective_from="2026-04-13T09:00:00+00:00",
        context_policy_id="POL-AUTO-003",
    )

    app.cancel_policy(
        container_id=container_id,
        policy_id="POL-AUTO-003",
        effective_from="2026-05-10T12:00:00+00:00",
        reason="Customer requested cancellation",
    )

    policy = app.get_policy(container_id, "POL-AUTO-003")
    snapshot = app.get_container_snapshot(container_id)
    matching_rels = [
        rel for rel in snapshot["relationships"] if rel["relationship_id"] == "REL-CANCEL-001"
    ]

    assert policy.status == "cancelled"
    assert matching_rels[0]["effective_to"] == "2026-05-10T12:00:00+00:00"


def test_policy_renewal_creates_new_policy_and_rehomes_context(app: InsuranceGraphApplication) -> None:
    container_id = app.open_policy_container("CONT-LIFE-004", "PRSN-001")
    app.add_portfolio(container_id, "PORT-MOTOR-001", "motor", "Annual Motor")
    app.register_party(
        container_id,
        "PRSN-001",
        identity={"first_name": "John", "last_name": "Doe", "dob": "1980-01-01"},
    )
    app.register_asset(
        container_id,
        asset_id="AST-001",
        asset_type="vehicle",
        identification={"vin": "VIN-001"},
        specification={"make": "Toyota", "model": "Yaris"},
        risk_attributes={},
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-AUTO-004",
        portfolio_id="PORT-MOTOR-001",
        product_type="motor",
        start_date="2026-04-13T09:00:00+00:00",
        end_date="2027-04-12T23:59:59+00:00",
        duration_months=12,
        premium_amount=900.0,
        ipt_amount=90.0,
        excess_amount=250.0,
        ncd_years=5,
        legal_protection=True,
    )
    app.link_policy_to_asset(container_id, "POL-AUTO-004", "AST-001", "2026-04-13T09:00:00+00:00")
    app.start_relationship(
        container_id,
        relationship_id="REL-REN-001",
        relationship_type="party_to_policy",
        from_node_id="PRSN-001",
        to_node_id="POL-AUTO-004",
        role="Policyholder",
        effective_from="2026-04-13T09:00:00+00:00",
        context_policy_id="POL-AUTO-004",
    )

    app.create_policy_renewal(
        container_id=container_id,
        source_policy_id="POL-AUTO-004",
        new_policy_id="POL-AUTO-004-REN",
        renewal_start_date="2027-04-13T00:00:00+00:00",
        renewal_end_date="2028-04-12T23:00:00+00:00",
        premium_amount=980.0,
        ipt_amount=98.0,
        excess_amount=300.0,
        ncd_years=6,
        legal_protection=True,
        reason="Annual renewal created",
    )

    old_policy = app.get_policy(container_id, "POL-AUTO-004")
    new_policy = app.get_policy(container_id, "POL-AUTO-004-REN")
    snapshot = app.get_container_snapshot(container_id)
    renewed_relationships = [
        rel for rel in snapshot["relationships"] if rel.get("context_policy_id") == "POL-AUTO-004-REN"
    ]

    assert old_policy.status == "renewed"
    assert new_policy.asset_id == "AST-001"
    assert new_policy.financials["total_payable"] == 1078.0
    assert any(rel["to_node_id"] == "POL-AUTO-004-REN" for rel in renewed_relationships)
