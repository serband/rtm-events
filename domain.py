"""
Insurance PAS domain model based on explicit aggregates and business events.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from eventsourcing.domain import Aggregate, event


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def copy_data(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return deepcopy(data) if data else {}


class PolicyContainer(Aggregate):
    """
    Root account envelope. It tracks membership references across portfolios,
    policies, parties, assets, and relationships.
    """

    @event("ContainerOpened")
    def __init__(self, container_id: str, account_holder_id: str) -> None:
        self.container_id = container_id
        self.account_holder_id = account_holder_id
        self.status = "active"
        self.created_at = utc_now()
        self.portfolios: Dict[str, Dict[str, Any]] = {}
        self.policy_refs: Dict[str, str] = {}
        self.party_refs: Dict[str, str] = {}
        self.asset_refs: Dict[str, str] = {}
        self.relationship_refs: Dict[str, str] = {}

    @event("PortfolioAddedToContainer")
    def add_portfolio(
        self,
        portfolio_id: str,
        portfolio_type: str,
        display_name: Optional[str] = None,
    ) -> None:
        self.portfolios[portfolio_id] = {
            "portfolio_id": portfolio_id,
            "portfolio_type": portfolio_type,
            "display_name": display_name or portfolio_type,
            "created_at": utc_now(),
        }

    @event("PolicyRegisteredInContainer")
    def register_policy(
        self,
        policy_id: str,
        aggregate_id: str,
        portfolio_id: str,
        product_type: str,
    ) -> None:
        self.policy_refs[policy_id] = aggregate_id
        if portfolio_id in self.portfolios:
            self.portfolios[portfolio_id].setdefault("policy_ids", [])
            if policy_id not in self.portfolios[portfolio_id]["policy_ids"]:
                self.portfolios[portfolio_id]["policy_ids"].append(policy_id)
        self.portfolios.setdefault(
            portfolio_id,
            {
                "portfolio_id": portfolio_id,
                "portfolio_type": product_type,
                "display_name": portfolio_id,
                "created_at": utc_now(),
                "policy_ids": [],
            },
        )
        if policy_id not in self.portfolios[portfolio_id].setdefault("policy_ids", []):
            self.portfolios[portfolio_id]["policy_ids"].append(policy_id)

    @event("PartyRegisteredInContainer")
    def register_party(self, party_id: str, aggregate_id: str) -> None:
        self.party_refs[party_id] = aggregate_id

    @event("AssetRegisteredInContainer")
    def register_asset(self, asset_id: str, aggregate_id: str) -> None:
        self.asset_refs[asset_id] = aggregate_id

    @event("RelationshipRegisteredInContainer")
    def register_relationship(self, relationship_id: str, aggregate_id: str) -> None:
        self.relationship_refs[relationship_id] = aggregate_id


class Policy(Aggregate):
    """
    Insurance contract aggregate. MTAs are modeled as explicit business events.
    """

    @event("PolicyCreated")
    def __init__(
        self,
        policy_id: str,
        container_id: str,
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
    ) -> None:
        self.policy_id = policy_id
        self.container_id = container_id
        self.portfolio_id = portfolio_id
        self.product_type = product_type
        self.asset_id: Optional[str] = None
        self.status = status
        self.terms = {
            "start_date": start_date,
            "end_date": end_date,
            "duration_months": duration_months,
            "ncd_years": ncd_years,
            "legal_protection": legal_protection,
        }
        self.financials = {
            "premium_amount": premium_amount,
            "ipt_amount": ipt_amount,
            "total_payable": premium_amount + ipt_amount,
            "excess_amount": excess_amount,
        }
        self.mta_log = [
            {
                "event_type": "PolicyCreated",
                "recorded_at": utc_now(),
                "effective_from": start_date,
                "status": status,
                "premium_amount": premium_amount,
                "ipt_amount": ipt_amount,
                "legal_protection": legal_protection,
                "ncd_years": ncd_years,
            }
        ]
        self.created_at = utc_now()

    @event("PolicyAssetLinked")
    def link_asset(self, asset_id: str, effective_from: str) -> None:
        if self.asset_id and self.asset_id != asset_id:
            raise ValueError("A policy can only be linked to one asset.")
        self.asset_id = asset_id
        self.mta_log.append(
            {
                "event_type": "PolicyAssetLinked",
                "recorded_at": utc_now(),
                "effective_from": effective_from,
                "asset_id": asset_id,
            }
        )

    @event("PolicyPremiumAdjusted")
    def adjust_premium(
        self,
        premium_amount: float,
        ipt_amount: float,
        effective_from: str,
        reason: str,
    ) -> None:
        previous_total = self.financials["total_payable"]
        self.financials["premium_amount"] = premium_amount
        self.financials["ipt_amount"] = ipt_amount
        self.financials["total_payable"] = premium_amount + ipt_amount
        self.mta_log.append(
            {
                "event_type": "PolicyPremiumAdjusted",
                "recorded_at": utc_now(),
                "effective_from": effective_from,
                "reason": reason,
                "previous_total": previous_total,
                "new_total": self.financials["total_payable"],
            }
        )

    @event("PolicyLegalProtectionChanged")
    def change_legal_protection(
        self,
        enabled: bool,
        effective_from: str,
        reason: str,
    ) -> None:
        self.terms["legal_protection"] = enabled
        self.mta_log.append(
            {
                "event_type": "PolicyLegalProtectionChanged",
                "recorded_at": utc_now(),
                "effective_from": effective_from,
                "reason": reason,
                "legal_protection": enabled,
            }
        )

    @event("PolicyNoClaimsDiscountChanged")
    def change_no_claims_discount(
        self,
        ncd_years: int,
        effective_from: str,
        reason: str,
    ) -> None:
        self.terms["ncd_years"] = ncd_years
        self.mta_log.append(
            {
                "event_type": "PolicyNoClaimsDiscountChanged",
                "recorded_at": utc_now(),
                "effective_from": effective_from,
                "reason": reason,
                "ncd_years": ncd_years,
            }
        )

    @event("PolicyStatusChanged")
    def change_status(self, new_status: str, effective_from: str, reason: str) -> None:
        self.status = new_status
        self.mta_log.append(
            {
                "event_type": "PolicyStatusChanged",
                "recorded_at": utc_now(),
                "effective_from": effective_from,
                "reason": reason,
                "status": new_status,
            }
        )


class Party(Aggregate):
    @event("PartyCreated")
    def __init__(
        self,
        party_id: str,
        party_type: str = "Individual",
        identity: Optional[Dict[str, Any]] = None,
        contact_details: Optional[Dict[str, Any]] = None,
        risk_profile: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.party_id = party_id
        self.party_type = party_type
        self.identity = copy_data(identity)
        self.contact_details = copy_data(contact_details)
        self.risk_profile = copy_data(risk_profile)
        self.created_at = utc_now()

    @event("PartyIdentityUpdated")
    def update_identity(self, identity_updates: Dict[str, Any]) -> None:
        self.identity.update(copy_data(identity_updates))

    @event("PartyContactUpdated")
    def update_contact(self, contact_updates: Dict[str, Any]) -> None:
        self.contact_details.update(copy_data(contact_updates))

    @event("PartyRiskProfileUpdated")
    def update_risk_profile(self, risk_updates: Dict[str, Any]) -> None:
        self.risk_profile.update(copy_data(risk_updates))


class Asset(Aggregate):
    @event("AssetCreated")
    def __init__(
        self,
        asset_id: str,
        asset_type: str,
        identification: Optional[Dict[str, Any]] = None,
        specification: Optional[Dict[str, Any]] = None,
        risk_attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.asset_id = asset_id
        self.asset_type = asset_type
        self.identification = copy_data(identification)
        self.specification = copy_data(specification)
        self.risk_attributes = copy_data(risk_attributes)
        self.created_at = utc_now()

    @event("AssetSpecificationUpdated")
    def update_specification(self, specification_updates: Dict[str, Any]) -> None:
        self.specification.update(copy_data(specification_updates))

    @event("AssetRiskAttributesUpdated")
    def update_risk_attributes(self, risk_updates: Dict[str, Any]) -> None:
        self.risk_attributes.update(copy_data(risk_updates))


class Relationship(Aggregate):
    @event("RelationshipStarted")
    def __init__(
        self,
        relationship_id: str,
        relationship_type: str,
        from_node_id: str,
        to_node_id: str,
        role: str,
        context_policy_id: Optional[str] = None,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
    ) -> None:
        self.relationship_id = relationship_id
        self.relationship_type = relationship_type
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.role = role
        self.context_policy_id = context_policy_id
        self.effective_from = effective_from or utc_now()
        self.effective_to = effective_to
        self.status = "active"
        self.created_at = utc_now()

    @event("RelationshipEnded")
    def end(self, effective_to: str) -> None:
        self.effective_to = effective_to
        self.status = "inactive"
