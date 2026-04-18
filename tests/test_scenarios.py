import os

import pytest

from application import InsuranceGraphApplication


@pytest.fixture
def app(tmp_path):
    os.environ["SQLALCHEMY_URL"] = f"sqlite:///{tmp_path / 'scenarios.db'}"
    return InsuranceGraphApplication()


def test_one_party_can_span_multiple_policies_and_portfolios(app: InsuranceGraphApplication) -> None:
    container_id = app.open_policy_container("CONT-SCEN-001", "PTY-JOHN-DOE")
    app.add_portfolio(container_id, "PORT-MOTOR", "motor", "Motor Portfolio")
    app.add_portfolio(container_id, "PORT-HOME", "home", "Home Portfolio")

    app.register_party(
        container_id,
        "PTY-JOHN-DOE",
        identity={"first_name": "John", "last_name": "Doe", "dob": "1980-01-01"},
    )
    app.register_asset(
        container_id,
        "AST-CAR-001",
        "vehicle",
        identification={"vin": "CAR-001"},
        specification={"make": "Ford", "model": "Focus"},
        risk_attributes={"garaging_postcode": "SW1A 1AA"},
    )
    app.register_asset(
        container_id,
        "AST-HOME-001",
        "home",
        identification={"uprn": "HOME-001"},
        specification={"address": "1 High Street", "sum_insured": 300000},
        risk_attributes={"occupancy": "owner_occupied"},
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-MOTOR-001",
        portfolio_id="PORT-MOTOR",
        product_type="motor",
        start_date="2026-01-01T00:00:00+00:00",
        end_date="2026-12-31T23:59:59+00:00",
        duration_months=12,
        premium_amount=900.0,
        ipt_amount=90.0,
        excess_amount=250.0,
        ncd_years=4,
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-HOME-001",
        portfolio_id="PORT-HOME",
        product_type="home",
        start_date="2026-01-01T00:00:00+00:00",
        end_date="2026-12-31T23:59:59+00:00",
        duration_months=12,
        premium_amount=700.0,
        ipt_amount=84.0,
        excess_amount=500.0,
        legal_protection=True,
    )
    app.link_policy_to_asset(container_id, "POL-MOTOR-001", "AST-CAR-001", "2026-01-01T00:00:00+00:00")
    app.link_policy_to_asset(container_id, "POL-HOME-001", "AST-HOME-001", "2026-01-01T00:00:00+00:00")
    app.start_relationship(
        container_id,
        relationship_id="REL-MOTOR-PH",
        relationship_type="party_to_policy",
        from_node_id="PTY-JOHN-DOE",
        to_node_id="POL-MOTOR-001",
        role="Policyholder",
        effective_from="2026-01-01T00:00:00+00:00",
        context_policy_id="POL-MOTOR-001",
    )
    app.start_relationship(
        container_id,
        relationship_id="REL-HOME-PH",
        relationship_type="party_to_policy",
        from_node_id="PTY-JOHN-DOE",
        to_node_id="POL-HOME-001",
        role="Policyholder",
        effective_from="2026-01-01T00:00:00+00:00",
        context_policy_id="POL-HOME-001",
    )

    snapshot = app.get_container_snapshot(container_id)

    assert snapshot["container_id"] == "CONT-SCEN-001"
    assert len(snapshot["policies"]) == 2
    assert len(snapshot["assets"]) == 2
    assert len(snapshot["parties"]) == 1
    assert len(snapshot["relationships"]) == 2
    assert snapshot["policies"]["POL-MOTOR-001"]["asset_id"] == "AST-CAR-001"
    assert snapshot["policies"]["POL-HOME-001"]["asset_id"] == "AST-HOME-001"


def test_relationship_temporal_filtering(app: InsuranceGraphApplication) -> None:
    container_id = app.open_policy_container("CONT-SCEN-002", "PRSN-001")
    app.add_portfolio(container_id, "PORT-MOTOR", "motor", "Motor Portfolio")
    app.register_party(
        container_id,
        "PRSN-001",
        identity={"first_name": "John", "last_name": "Doe"},
    )
    app.register_party(
        container_id,
        "PRSN-002",
        identity={"first_name": "Jane", "last_name": "Doe"},
    )
    app.register_asset(
        container_id,
        "AST-001",
        "vehicle",
        identification={"vin": "VIN-001"},
        specification={"make": "Tesla", "model": "Model 3"},
        risk_attributes={},
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-001",
        portfolio_id="PORT-MOTOR",
        product_type="motor",
        start_date="2026-04-13T09:00:00+00:00",
        end_date="2027-04-12T23:59:59+00:00",
        duration_months=12,
        premium_amount=950.0,
        ipt_amount=95.0,
        excess_amount=300.0,
        ncd_years=5,
    )
    app.link_policy_to_asset(container_id, "POL-001", "AST-001", "2026-04-13T09:00:00+00:00")
    app.start_relationship(
        container_id,
        relationship_id="REL-001",
        relationship_type="party_to_asset",
        from_node_id="PRSN-002",
        to_node_id="AST-001",
        role="NamedDriver",
        effective_from="2026-04-14T10:00:00+00:00",
        context_policy_id="POL-001",
    )

    monday = app.get_graph_as_of(container_id, "2026-04-13T12:00:00+00:00")
    tuesday = app.get_graph_as_of(container_id, "2026-04-14T12:00:00+00:00")

    assert len(monday["relationships"]) == 0
    assert len(tuesday["relationships"]) == 1
    assert tuesday["relationships"][0]["role"] == "NamedDriver"
