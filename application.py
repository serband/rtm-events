"""
Application service for the RTM replacement POC.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from eventsourcing.application import Application

from domain import Asset, Party, Policy, PolicyContainer, Relationship


def parse_iso_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class InsuranceGraphApplication(Application):
    """
    Uses eventsourcing with SQLAlchemy persistence. PostgreSQL can be used by
    setting SQLALCHEMY_URL to a PostgreSQL connection string.
    """

    def __init__(self, **kwargs: Any) -> None:
        if "env" not in kwargs:
            kwargs["env"] = {}

        sqlalchemy_url = os.getenv("SQLALCHEMY_URL", "sqlite:///insurance_graph_events.db")
        kwargs["env"].update(
            {
                "PERSISTENCE_MODULE": "eventsourcing_sqlalchemy",
                "SQLALCHEMY_URL": sqlalchemy_url,
                "CREATE_TABLE": "true",
            }
        )
        super().__init__(**kwargs)

    def open_policy_container(self, container_id: str, account_holder_id: str) -> UUID:
        container = PolicyContainer(container_id=container_id, account_holder_id=account_holder_id)
        self.save(container)
        return container.id

    def add_portfolio(
        self,
        container_id: UUID,
        portfolio_id: str,
        portfolio_type: str,
        display_name: Optional[str] = None,
    ) -> None:
        container = self.repository.get(container_id)
        container.add_portfolio(
            portfolio_id=portfolio_id,
            portfolio_type=portfolio_type,
            display_name=display_name,
        )
        self.save(container)

    def register_party(
        self,
        container_id: UUID,
        party_id: str,
        identity: Dict[str, Any],
        contact_details: Optional[Dict[str, Any]] = None,
        risk_profile: Optional[Dict[str, Any]] = None,
        party_type: str = "Individual",
    ) -> UUID:
        party = Party(
            party_id=party_id,
            party_type=party_type,
            identity=identity,
            contact_details=contact_details,
            risk_profile=risk_profile,
        )
        container = self.repository.get(container_id)
        container.register_party(party_id=party_id, aggregate_id=str(party.id))
        self.save(party, container)
        return party.id

    def register_asset(
        self,
        container_id: UUID,
        asset_id: str,
        asset_type: str,
        identification: Dict[str, Any],
        specification: Dict[str, Any],
        risk_attributes: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        asset = Asset(
            asset_id=asset_id,
            asset_type=asset_type,
            identification=identification,
            specification=specification,
            risk_attributes=risk_attributes,
        )
        container = self.repository.get(container_id)
        container.register_asset(asset_id=asset_id, aggregate_id=str(asset.id))
        self.save(asset, container)
        return asset.id

    def create_policy(
        self,
        container_id: UUID,
        policy_id: str,
        portfolio_id: str,
        product_type: str,
        start_date: str,
        end_date: str,
        duration_months: int,
        premium_amount: float,
        ipt_amount: float,
        excess_amount: float,
        ncd_years: int = 0,
        legal_protection: bool = False,
        status: str = "active",
    ) -> UUID:
        container = self.repository.get(container_id)
        policy = Policy(
            policy_id=policy_id,
            container_id=container.container_id,
            portfolio_id=portfolio_id,
            product_type=product_type,
            start_date=start_date,
            end_date=end_date,
            duration_months=duration_months,
            premium_amount=premium_amount,
            ipt_amount=ipt_amount,
            excess_amount=excess_amount,
            ncd_years=ncd_years,
            legal_protection=legal_protection,
            status=status,
        )
        container.register_policy(
            policy_id=policy_id,
            aggregate_id=str(policy.id),
            portfolio_id=portfolio_id,
            product_type=product_type,
        )
        self.save(policy, container)
        return policy.id

    def link_policy_to_asset(
        self,
        container_id: UUID,
        policy_id: str,
        asset_id: str,
        effective_from: str,
    ) -> None:
        policy = self.get_policy(container_id, policy_id)
        policy.link_asset(asset_id=asset_id, effective_from=effective_from)
        self.save(policy)

    def start_relationship(
        self,
        container_id: UUID,
        relationship_id: str,
        relationship_type: str,
        from_node_id: str,
        to_node_id: str,
        role: str,
        effective_from: str,
        context_policy_id: Optional[str] = None,
        effective_to: Optional[str] = None,
    ) -> UUID:
        relationship = Relationship(
            relationship_id=relationship_id,
            relationship_type=relationship_type,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            role=role,
            context_policy_id=context_policy_id,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        container = self.repository.get(container_id)
        container.register_relationship(relationship_id=relationship_id, aggregate_id=str(relationship.id))
        self.save(relationship, container)
        return relationship.id

    def end_relationship(
        self,
        container_id: UUID,
        relationship_id: str,
        effective_to: str,
    ) -> None:
        relationship = self.get_relationship(container_id, relationship_id)
        relationship.end(effective_to=effective_to)
        self.save(relationship)

    def update_party_identity(
        self,
        container_id: UUID,
        party_id: str,
        identity_updates: Dict[str, Any],
    ) -> None:
        party = self.get_party(container_id, party_id)
        party.update_identity(identity_updates)
        self.save(party)

    def update_party_risk_profile(
        self,
        container_id: UUID,
        party_id: str,
        risk_updates: Dict[str, Any],
    ) -> None:
        party = self.get_party(container_id, party_id)
        party.update_risk_profile(risk_updates)
        self.save(party)

    def update_asset_specification(
        self,
        container_id: UUID,
        asset_id: str,
        specification_updates: Dict[str, Any],
    ) -> None:
        asset = self.get_asset(container_id, asset_id)
        asset.update_specification(specification_updates)
        self.save(asset)

    def update_asset_risk_attributes(
        self,
        container_id: UUID,
        asset_id: str,
        risk_updates: Dict[str, Any],
    ) -> None:
        asset = self.get_asset(container_id, asset_id)
        asset.update_risk_attributes(risk_updates)
        self.save(asset)

    def adjust_policy_premium(
        self,
        container_id: UUID,
        policy_id: str,
        premium_amount: float,
        ipt_amount: float,
        effective_from: str,
        reason: str,
    ) -> None:
        policy = self.get_policy(container_id, policy_id)
        policy.adjust_premium(
            premium_amount=premium_amount,
            ipt_amount=ipt_amount,
            effective_from=effective_from,
            reason=reason,
        )
        self.save(policy)

    def change_policy_legal_protection(
        self,
        container_id: UUID,
        policy_id: str,
        enabled: bool,
        effective_from: str,
        reason: str,
    ) -> None:
        policy = self.get_policy(container_id, policy_id)
        policy.change_legal_protection(
            enabled=enabled,
            effective_from=effective_from,
            reason=reason,
        )
        self.save(policy)

    def change_policy_no_claims_discount(
        self,
        container_id: UUID,
        policy_id: str,
        ncd_years: int,
        effective_from: str,
        reason: str,
    ) -> None:
        policy = self.get_policy(container_id, policy_id)
        policy.change_no_claims_discount(
            ncd_years=ncd_years,
            effective_from=effective_from,
            reason=reason,
        )
        self.save(policy)

    def change_policy_status(
        self,
        container_id: UUID,
        policy_id: str,
        new_status: str,
        effective_from: str,
        reason: str,
    ) -> None:
        policy = self.get_policy(container_id, policy_id)
        policy.change_status(
            new_status=new_status,
            effective_from=effective_from,
            reason=reason,
        )
        self.save(policy)

    def cancel_policy(
        self,
        container_id: UUID,
        policy_id: str,
        effective_from: str,
        reason: str,
    ) -> None:
        self.change_policy_status(
            container_id=container_id,
            policy_id=policy_id,
            new_status="cancelled",
            effective_from=effective_from,
            reason=reason,
        )
        self._end_policy_context_relationships(
            container_id=container_id,
            policy_id=policy_id,
            effective_to=effective_from,
        )

    def create_policy_renewal(
        self,
        container_id: UUID,
        source_policy_id: str,
        new_policy_id: str,
        renewal_start_date: str,
        renewal_end_date: str,
        premium_amount: float,
        ipt_amount: float,
        excess_amount: float,
        ncd_years: int,
        legal_protection: bool,
        reason: str,
    ) -> UUID:
        source_policy = self.get_policy(container_id, source_policy_id)
        source_snapshot = self.get_container_snapshot(container_id)
        active_context_relationships = [
            rel
            for rel in source_snapshot["relationships"]
            if rel.get("context_policy_id") == source_policy_id
            and (rel.get("effective_to") is None or parse_iso_date(rel["effective_to"]) > parse_iso_date(renewal_start_date))
        ]

        self.change_policy_status(
            container_id=container_id,
            policy_id=source_policy_id,
            new_status="renewed",
            effective_from=renewal_start_date,
            reason=reason,
        )
        self._end_policy_context_relationships(
            container_id=container_id,
            policy_id=source_policy_id,
            effective_to=renewal_start_date,
        )

        new_policy_uuid = self.create_policy(
            container_id=container_id,
            policy_id=new_policy_id,
            portfolio_id=source_policy.portfolio_id,
            product_type=source_policy.product_type,
            start_date=renewal_start_date,
            end_date=renewal_end_date,
            duration_months=source_policy.terms["duration_months"],
            premium_amount=premium_amount,
            ipt_amount=ipt_amount,
            excess_amount=excess_amount,
            ncd_years=ncd_years,
            legal_protection=legal_protection,
            status="active",
        )

        if source_policy.asset_id:
            self.link_policy_to_asset(
                container_id=container_id,
                policy_id=new_policy_id,
                asset_id=source_policy.asset_id,
                effective_from=renewal_start_date,
            )

        for rel in active_context_relationships:
            to_node_id = rel["to_node_id"]
            if rel["relationship_type"] == "party_to_policy" and to_node_id == source_policy_id:
                to_node_id = new_policy_id
            self.start_relationship(
                container_id=container_id,
                relationship_id=f"REL-{uuid4().hex[:10].upper()}",
                relationship_type=rel["relationship_type"],
                from_node_id=rel["from_node_id"],
                to_node_id=to_node_id,
                role=rel["role"],
                effective_from=renewal_start_date,
                context_policy_id=new_policy_id,
            )

        return new_policy_uuid

    def get_container(self, container_id: UUID, version: Optional[int] = None) -> PolicyContainer:
        return self.repository.get(container_id, version=version)

    def get_policy(
        self,
        container_id: UUID,
        policy_id: str,
        version: Optional[int] = None,
    ) -> Policy:
        container = self.get_container(container_id)
        return self.repository.get(UUID(container.policy_refs[policy_id]), version=version)

    def get_party(
        self,
        container_id: UUID,
        party_id: str,
        version: Optional[int] = None,
    ) -> Party:
        container = self.get_container(container_id)
        return self.repository.get(UUID(container.party_refs[party_id]), version=version)

    def get_asset(
        self,
        container_id: UUID,
        asset_id: str,
        version: Optional[int] = None,
    ) -> Asset:
        container = self.get_container(container_id)
        return self.repository.get(UUID(container.asset_refs[asset_id]), version=version)

    def get_relationship(
        self,
        container_id: UUID,
        relationship_id: str,
        version: Optional[int] = None,
    ) -> Relationship:
        container = self.get_container(container_id)
        return self.repository.get(UUID(container.relationship_refs[relationship_id]), version=version)

    def get_container_snapshot(self, container_id: UUID) -> Dict[str, Any]:
        container = self.get_container(container_id)
        return self._build_snapshot(container)

    def get_graph_as_of(self, container_id: UUID, as_of_date: str) -> Dict[str, Any]:
        snapshot = self.get_container_snapshot(container_id)
        as_of = parse_iso_date(as_of_date)
        snapshot["relationships"] = [
            rel
            for rel in snapshot["relationships"]
            if parse_iso_date(rel["effective_from"]) <= as_of
            and (
                rel["effective_to"] is None
                or parse_iso_date(rel["effective_to"]) > as_of
            )
        ]
        snapshot["as_of_date"] = as_of_date
        return snapshot

    def _end_policy_context_relationships(
        self,
        container_id: UUID,
        policy_id: str,
        effective_to: str,
    ) -> None:
        snapshot = self.get_container_snapshot(container_id)
        active_relationships = [
            rel
            for rel in snapshot["relationships"]
            if rel.get("context_policy_id") == policy_id
            and (rel.get("effective_to") is None or parse_iso_date(rel["effective_to"]) > parse_iso_date(effective_to))
        ]
        for rel in active_relationships:
            self.end_relationship(
                container_id=container_id,
                relationship_id=rel["relationship_id"],
                effective_to=effective_to,
            )

    def _build_snapshot(self, container: PolicyContainer) -> Dict[str, Any]:
        policies = {
            policy_id: self._serialize_policy(self.repository.get(UUID(aggregate_id)))
            for policy_id, aggregate_id in container.policy_refs.items()
        }
        parties = {
            party_id: self._serialize_party(self.repository.get(UUID(aggregate_id)))
            for party_id, aggregate_id in container.party_refs.items()
        }
        assets = {
            asset_id: self._serialize_asset(self.repository.get(UUID(aggregate_id)))
            for asset_id, aggregate_id in container.asset_refs.items()
        }
        relationships = [
            self._serialize_relationship(self.repository.get(UUID(aggregate_id)))
            for aggregate_id in container.relationship_refs.values()
        ]
        total_portfolio_premium = sum(
            policy["financials"]["total_payable"] for policy in policies.values()
        )
        return {
            "container_id": container.container_id,
            "account_holder_id": container.account_holder_id,
            "status": container.status,
            "portfolios": container.portfolios,
            "policies": policies,
            "parties": parties,
            "assets": assets,
            "relationships": relationships,
            "total_portfolio_premium": total_portfolio_premium,
            "version": container.version,
        }

    @staticmethod
    def _serialize_policy(policy: Policy) -> Dict[str, Any]:
        return {
            "policy_id": policy.policy_id,
            "container_id": policy.container_id,
            "portfolio_id": policy.portfolio_id,
            "product_type": policy.product_type,
            "asset_id": policy.asset_id,
            "status": policy.status,
            "terms": policy.terms,
            "financials": policy.financials,
            "mta_log": policy.mta_log,
            "version": policy.version,
        }

    @staticmethod
    def _serialize_party(party: Party) -> Dict[str, Any]:
        return {
            "party_id": party.party_id,
            "party_type": party.party_type,
            "identity": party.identity,
            "contact_details": party.contact_details,
            "risk_profile": party.risk_profile,
            "version": party.version,
        }

    @staticmethod
    def _serialize_asset(asset: Asset) -> Dict[str, Any]:
        return {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type,
            "identification": asset.identification,
            "specification": asset.specification,
            "risk_attributes": asset.risk_attributes,
            "version": asset.version,
        }

    @staticmethod
    def _serialize_relationship(relationship: Relationship) -> Dict[str, Any]:
        return {
            "relationship_id": relationship.relationship_id,
            "relationship_type": relationship.relationship_type,
            "from_node_id": relationship.from_node_id,
            "to_node_id": relationship.to_node_id,
            "role": relationship.role,
            "context_policy_id": relationship.context_policy_id,
            "effective_from": relationship.effective_from,
            "effective_to": relationship.effective_to,
            "status": relationship.status,
            "version": relationship.version,
        }


def create_sample_policy_data() -> Dict[str, Any]:
    return {
        "portfolio": {
            "portfolio_id": "PORT-MOTOR-001",
            "portfolio_type": "motor",
            "display_name": "Annual Motor",
        },
        "policy": {
            "policy_id": "POL-88293",
            "product_type": "motor",
            "start_date": "2026-04-13T09:00:00+00:00",
            "end_date": "2027-04-12T23:59:59+00:00",
            "duration_months": 12,
            "status": "active",
            "ncd_years": 5,
            "legal_protection": False,
            "premium_amount": 960.0,
            "ipt_amount": 102.0,
            "excess_amount": 250.0,
        },
        "parties": {
            "policyholder": {
                "party_id": "PRSN-001",
                "identity": {"first_name": "John", "last_name": "Doe", "dob": "1980-01-01"},
            },
            "driver": {
                "party_id": "PRSN-002",
                "identity": {"first_name": "Jane", "last_name": "Doe", "dob": "1985-05-05"},
            },
        },
        "asset": {
            "asset_id": "AST-MC-001",
            "asset_type": "motorcycle",
            "identification": {
                "vin": "SMTTC3367GT123456",
                "registration_number": "AB12CDE",
            },
            "specification": {
                "make": "Triumph",
                "model": "Street Triple",
                "engine_cc": 765,
                "year_of_manufacture": 2024,
            },
            "risk_attributes": {"garaging_postcode": "SW1A 1AA"},
        },
    }


def demonstrate_mta_time_travel() -> Dict[str, Any]:
    """
    Monday is 2026-04-13 and Tuesday is 2026-04-14.
    """

    app = InsuranceGraphApplication()
    sample = create_sample_policy_data()

    monday = "2026-04-13T09:00:00+00:00"
    tuesday = "2026-04-14T10:00:00+00:00"

    container_id = app.open_policy_container(
        container_id="CONT-001",
        account_holder_id=sample["parties"]["policyholder"]["party_id"],
    )
    app.add_portfolio(
        container_id=container_id,
        portfolio_id=sample["portfolio"]["portfolio_id"],
        portfolio_type=sample["portfolio"]["portfolio_type"],
        display_name=sample["portfolio"]["display_name"],
    )
    app.register_party(
        container_id=container_id,
        party_id=sample["parties"]["policyholder"]["party_id"],
        identity=sample["parties"]["policyholder"]["identity"],
    )
    app.register_party(
        container_id=container_id,
        party_id=sample["parties"]["driver"]["party_id"],
        identity=sample["parties"]["driver"]["identity"],
    )
    app.register_asset(
        container_id=container_id,
        asset_id=sample["asset"]["asset_id"],
        asset_type=sample["asset"]["asset_type"],
        identification=sample["asset"]["identification"],
        specification=sample["asset"]["specification"],
        risk_attributes=sample["asset"]["risk_attributes"],
    )
    app.create_policy(
        container_id=container_id,
        policy_id=sample["policy"]["policy_id"],
        portfolio_id=sample["portfolio"]["portfolio_id"],
        product_type=sample["policy"]["product_type"],
        start_date=sample["policy"]["start_date"],
        end_date=sample["policy"]["end_date"],
        duration_months=sample["policy"]["duration_months"],
        premium_amount=sample["policy"]["premium_amount"],
        ipt_amount=sample["policy"]["ipt_amount"],
        excess_amount=sample["policy"]["excess_amount"],
        ncd_years=sample["policy"]["ncd_years"],
        legal_protection=sample["policy"]["legal_protection"],
        status=sample["policy"]["status"],
    )
    app.link_policy_to_asset(
        container_id=container_id,
        policy_id=sample["policy"]["policy_id"],
        asset_id=sample["asset"]["asset_id"],
        effective_from=monday,
    )
    app.start_relationship(
        container_id=container_id,
        relationship_id="REL-PH-001",
        relationship_type="party_to_policy",
        from_node_id=sample["parties"]["policyholder"]["party_id"],
        to_node_id=sample["policy"]["policy_id"],
        role="Policyholder",
        effective_from=monday,
        context_policy_id=sample["policy"]["policy_id"],
    )

    monday_policy = app.get_policy(container_id, sample["policy"]["policy_id"])
    monday_policy_version = monday_policy.version
    monday_total = monday_policy.financials["total_payable"]

    app.adjust_policy_premium(
        container_id=container_id,
        policy_id=sample["policy"]["policy_id"],
        premium_amount=1060.0,
        ipt_amount=108.2,
        effective_from=tuesday,
        reason="Add legal protection MTA",
    )
    app.change_policy_legal_protection(
        container_id=container_id,
        policy_id=sample["policy"]["policy_id"],
        enabled=True,
        effective_from=tuesday,
        reason="Customer added legal protection",
    )
    app.start_relationship(
        container_id=container_id,
        relationship_id="REL-DRV-001",
        relationship_type="party_to_asset",
        from_node_id=sample["parties"]["driver"]["party_id"],
        to_node_id=sample["asset"]["asset_id"],
        role="NamedDriver",
        effective_from=tuesday,
        context_policy_id=sample["policy"]["policy_id"],
    )

    tuesday_policy = app.get_policy(container_id, sample["policy"]["policy_id"])
    monday_policy_restored = app.get_policy(
        container_id,
        sample["policy"]["policy_id"],
        version=monday_policy_version,
    )
    monday_graph = app.get_graph_as_of(container_id, monday)
    tuesday_graph = app.get_graph_as_of(container_id, tuesday)

    return {
        "container_id": container_id,
        "policy_id": sample["policy"]["policy_id"],
        "monday_policy_version": monday_policy_version,
        "monday_total": monday_total,
        "tuesday_total": tuesday_policy.financials["total_payable"],
        "monday_legal_protection": monday_policy_restored.terms["legal_protection"],
        "tuesday_legal_protection": tuesday_policy.terms["legal_protection"],
        "monday_named_driver_count": len(
            [rel for rel in monday_graph["relationships"] if rel["role"] == "NamedDriver"]
        ),
        "tuesday_named_driver_count": len(
            [rel for rel in tuesday_graph["relationships"] if rel["role"] == "NamedDriver"]
        ),
        "monday_restored_total": monday_policy_restored.financials["total_payable"],
        "policy_event_types": [entry["event_type"] for entry in tuesday_policy.mta_log],
        "current_policy_version": tuesday_policy.version,
    }


if __name__ == "__main__":
    result = demonstrate_mta_time_travel()
    print("MTA demo result:")
    for key, value in result.items():
        print(f"{key}: {value}")
