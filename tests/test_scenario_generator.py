import os

from application import InsuranceGraphApplication
from scenario_generator import apply_scenario, generate_complex_scenario


def test_generate_complex_scenario_returns_rich_blueprint() -> None:
    scenario = generate_complex_scenario(seed=12345)

    assert scenario["container"]["container_id"].startswith("CONT-")
    assert len(scenario["portfolios"]) >= 2
    assert len(scenario["parties"]) >= 4
    assert len(scenario["assets"]) >= 3
    assert len(scenario["policies"]) >= 3
    assert len(scenario["relationships"]) >= 8
    assert len(scenario["history"]) >= 5
    assert len(scenario["meta"]["timeline_markers"]) >= 6

    policy_asset_ids = {policy["linked_asset_id"] for policy in scenario["policies"]}
    asset_ids = {asset["asset_id"] for asset in scenario["assets"]}
    assert policy_asset_ids.issubset(asset_ids)


def test_apply_generated_scenario_creates_complex_snapshot(tmp_path) -> None:
    os.environ["SQLALCHEMY_URL"] = f"sqlite:///{tmp_path / 'generated_scenario.db'}"
    app = InsuranceGraphApplication()
    scenario = generate_complex_scenario(seed=54321)

    container_uuid = apply_scenario(app, scenario)
    snapshot = app.get_container_snapshot(container_uuid)
    relationship_starts_in_history = sum(
        1 for event in scenario["history"] if event["event_type"] == "RelationshipStarted"
    )

    assert snapshot["container_id"] == scenario["container"]["container_id"]
    assert len(snapshot["policies"]) == len(scenario["policies"])
    assert len(snapshot["assets"]) == len(scenario["assets"])
    assert len(snapshot["parties"]) == len(scenario["parties"])
    assert len(snapshot["relationships"]) == len(scenario["relationships"]) + relationship_starts_in_history
    assert any(policy["version"] > 1 for policy in snapshot["policies"].values())

    early_graph = app.get_graph_as_of(container_uuid, f"{scenario['meta']['timeline_markers'][1]}T12:00:00+00:00")
    late_graph = app.get_graph_as_of(container_uuid, f"{scenario['meta']['timeline_markers'][-1]}T12:00:00+00:00")

    early_relationship_ids = {rel["relationship_id"] for rel in early_graph["relationships"]}
    late_relationship_ids = {rel["relationship_id"] for rel in late_graph["relationships"]}
    assert early_relationship_ids != late_relationship_ids
