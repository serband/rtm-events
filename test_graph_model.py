import os
from pathlib import Path

from application import (
    create_sample_policy_data,
    demonstrate_mta_time_travel,
    InsuranceGraphApplication,
)
from projector import GraphReadModel


def build_app(db_path: Path) -> InsuranceGraphApplication:
    os.environ["SQLALCHEMY_URL"] = f"sqlite:///{db_path}"
    return InsuranceGraphApplication()


def test_mta_demo_proves_time_travel(tmp_path) -> None:
    build_app(tmp_path / "graph_model_demo.db")
    result = demonstrate_mta_time_travel()

    assert result["tuesday_total"] > result["monday_total"]
    assert result["monday_restored_total"] == result["monday_total"]
    assert result["monday_legal_protection"] is False
    assert result["tuesday_legal_protection"] is True
    assert result["monday_named_driver_count"] == 0
    assert result["tuesday_named_driver_count"] == 1
    assert "PolicyPremiumAdjusted" in result["policy_event_types"]
    assert "PolicyLegalProtectionChanged" in result["policy_event_types"]


def test_read_model_projects_snapshot(tmp_path) -> None:
    app = build_app(tmp_path / "graph_model_projector.db")
    sample = create_sample_policy_data()
    container_id = app.open_policy_container("CONT-RM-001", "PRSN-001")
    app.add_portfolio(container_id, "PORT-MOTOR-001", "motor", "Annual Motor")
    app.register_party(container_id, "PRSN-001", sample["parties"]["policyholder"]["identity"])
    app.register_asset(
        container_id,
        asset_id=sample["asset"]["asset_id"],
        asset_type=sample["asset"]["asset_type"],
        identification=sample["asset"]["identification"],
        specification=sample["asset"]["specification"],
        risk_attributes=sample["asset"]["risk_attributes"],
    )
    app.create_policy(
        container_id=container_id,
        policy_id="POL-RM-001",
        portfolio_id="PORT-MOTOR-001",
        product_type="motorcycle",
        start_date="2026-04-13T09:00:00+00:00",
        end_date="2027-04-12T23:59:59+00:00",
        duration_months=12,
        premium_amount=900.0,
        ipt_amount=90.0,
        excess_amount=300.0,
        ncd_years=4,
        legal_protection=False,
    )
    app.link_policy_to_asset(container_id, "POL-RM-001", sample["asset"]["asset_id"], "2026-04-13T09:00:00+00:00")
    snapshot = app.get_container_snapshot(container_id)

    read_model = GraphReadModel(str(tmp_path / "graph_read_model.db"))
    read_model.project_snapshot(snapshot)
    projected = read_model.get_container_graph("CONT-RM-001")

    assert projected["container_id"] == "CONT-RM-001"
    assert projected["policies"]["POL-RM-001"]["asset_id"] == sample["asset"]["asset_id"]
    assert projected["assets"][sample["asset"]["asset_id"]]["asset_type"] == "motorcycle"
