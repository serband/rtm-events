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
