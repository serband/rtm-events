from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from application import InsuranceGraphApplication


FIRST_NAMES = [
    "Amelia",
    "Oliver",
    "George",
    "Grace",
    "Luca",
    "Freya",
    "Maya",
    "Theo",
    "Eleanor",
    "Noah",
]

LAST_NAMES = [
    "Carter",
    "Patel",
    "Hughes",
    "Khan",
    "Morgan",
    "Davies",
    "Clarke",
    "Shaw",
    "Edwards",
    "Turner",
]

STREETS = [
    "Station Road",
    "Park View",
    "Willow Close",
    "Hawthorn Avenue",
    "Rectory Lane",
    "Mill Rise",
]

TOWNS = [
    ("Bristol", "BS1"),
    ("Leeds", "LS1"),
    ("Manchester", "M1"),
    ("Cardiff", "CF10"),
    ("Nottingham", "NG1"),
    ("Southampton", "SO14"),
]

CAR_MODELS = [
    ("Volkswagen", "Golf", 1.6),
    ("Tesla", "Model 3", 0),
    ("BMW", "320i", 2.0),
    ("Ford", "Focus", 1.5),
    ("Audi", "A4", 2.0),
]

MOTORCYCLE_MODELS = [
    ("Triumph", "Street Triple", 765),
    ("Yamaha", "MT-07", 689),
    ("Honda", "CB650R", 649),
    ("BMW", "F 900 R", 895),
]

HOME_STYLES = [
    "Victorian terrace",
    "Detached house",
    "Semi-detached house",
    "Converted flat",
]

OCCUPATIONS = [
    "Project Manager",
    "Teacher",
    "Operations Analyst",
    "Paramedic",
    "Quantity Surveyor",
    "Graphic Designer",
]


def iso_at(value: date, hour: int) -> str:
    return datetime.combine(value, time(hour=hour, tzinfo=timezone.utc)).isoformat()


def make_id(prefix: str, rng: random.Random, size: int = 5) -> str:
    return f"{prefix}-{rng.randint(10 ** (size - 1), (10 ** size) - 1)}"


def choose_address(rng: random.Random) -> Dict[str, str]:
    town, area = rng.choice(TOWNS)
    street = rng.choice(STREETS)
    house_number = rng.randint(1, 90)
    return {
        "line_1": f"{house_number} {street}",
        "city": town,
        "postcode": f"{area} {rng.randint(1, 9)}{rng.choice(['AA', 'AB', 'CD', 'EF'])}",
    }


def generate_party_json(
    party_id: str,
    rng: random.Random,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    birth_year: Optional[int] = None,
    party_type: str = "Individual",
    relationship_to_holder: Optional[str] = None,
) -> Dict[str, Any]:
    first_name = first_name or rng.choice(FIRST_NAMES)
    last_name = last_name or rng.choice(LAST_NAMES)
    birth_year = birth_year or rng.randint(1965, 2004)
    address = choose_address(rng)
    identity = {
        "first_name": first_name,
        "last_name": last_name,
        "dob": date(birth_year, rng.randint(1, 12), rng.randint(1, 26)).isoformat(),
        "relationship_to_holder": relationship_to_holder or "self",
    }
    contact_details = {
        "email": f"{first_name.lower()}.{last_name.lower()}@example.co.uk",
        "phone": f"07{rng.randint(100000000, 999999999)}",
        "address": address,
    }
    risk_profile = {
        "occupation": rng.choice(OCCUPATIONS),
        "licence_points": rng.randint(0, 6),
        "residency_years": rng.randint(1, 18),
        "claims_last_5_years": rng.randint(0, 2),
    }
    return {
        "party_id": party_id,
        "party_type": party_type,
        "identity": identity,
        "contact_details": contact_details,
        "risk_profile": risk_profile,
    }


def generate_vehicle_asset_json(asset_id: str, rng: random.Random) -> Dict[str, Any]:
    make, model, engine_size = rng.choice(CAR_MODELS)
    registration_letters = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(3))
    address = choose_address(rng)
    return {
        "asset_id": asset_id,
        "asset_type": "vehicle",
        "identification": {
            "vin": f"VIN{rng.randint(1000000, 9999999)}",
            "registration_number": f"{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{rng.randint(10,99)} {registration_letters}",
        },
        "specification": {
            "make": make,
            "model": model,
            "engine_litres": engine_size,
            "year_of_manufacture": rng.randint(2019, 2025),
            "colour": rng.choice(["Blue", "Grey", "Black", "Silver", "Red"]),
        },
        "risk_attributes": {
            "garaging_postcode": address["postcode"],
            "annual_mileage": rng.randint(5000, 18000),
            "overnight_location": rng.choice(["Driveway", "Street", "Garage"]),
        },
    }


def generate_motorcycle_asset_json(asset_id: str, rng: random.Random) -> Dict[str, Any]:
    make, model, engine_cc = rng.choice(MOTORCYCLE_MODELS)
    address = choose_address(rng)
    return {
        "asset_id": asset_id,
        "asset_type": "motorcycle",
        "identification": {
            "vin": f"MC{rng.randint(100000000, 999999999)}",
            "registration_number": f"{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{rng.randint(10,99)} {''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(3))}",
        },
        "specification": {
            "make": make,
            "model": model,
            "engine_cc": engine_cc,
            "year_of_manufacture": rng.randint(2020, 2025),
            "style": rng.choice(["Naked", "Adventure", "Sport", "Roadster"]),
        },
        "risk_attributes": {
            "garaging_postcode": address["postcode"],
            "security_devices": rng.sample(["immobiliser", "tracker", "disc_lock"], k=rng.randint(1, 3)),
            "annual_mileage": rng.randint(2000, 9000),
        },
    }


def generate_home_asset_json(asset_id: str, rng: random.Random) -> Dict[str, Any]:
    address = choose_address(rng)
    return {
        "asset_id": asset_id,
        "asset_type": "home",
        "identification": {
            "uprn": f"UPRN{rng.randint(100000, 999999)}",
            "address_key": f"{address['line_1']}, {address['city']}",
        },
        "specification": {
            "address": address,
            "property_style": rng.choice(HOME_STYLES),
            "bedrooms": rng.randint(2, 5),
            "rebuild_cost": rng.randint(220000, 550000),
            "contents_sum_insured": rng.randint(45000, 120000),
        },
        "risk_attributes": {
            "occupancy": rng.choice(["owner_occupied", "family_home"]),
            "alarm_installed": rng.choice([True, False]),
            "previous_subsidence": False,
        },
    }


def generate_asset_json(asset_id: str, asset_type: str, rng: random.Random) -> Dict[str, Any]:
    if asset_type == "vehicle":
        return generate_vehicle_asset_json(asset_id, rng)
    if asset_type == "motorcycle":
        return generate_motorcycle_asset_json(asset_id, rng)
    if asset_type == "home":
        return generate_home_asset_json(asset_id, rng)
    raise ValueError(f"Unsupported asset type: {asset_type}")


def calculate_policy_financials(product_type: str, rng: random.Random) -> Dict[str, float]:
    base = {
        "motor": rng.randint(780, 1450),
        "motorcycle": rng.randint(420, 980),
        "home": rng.randint(310, 880),
        "contents": rng.randint(120, 360),
    }[product_type]
    ipt_amount = round(base * 0.12, 2)
    excess_amount = {
        "motor": rng.choice([250.0, 350.0, 500.0]),
        "motorcycle": rng.choice([300.0, 400.0]),
        "home": rng.choice([100.0, 250.0, 500.0]),
        "contents": rng.choice([75.0, 100.0, 150.0]),
    }[product_type]
    return {
        "premium_amount": float(base),
        "ipt_amount": float(ipt_amount),
        "excess_amount": float(excess_amount),
    }


def generate_policy_json(
    policy_id: str,
    portfolio_id: str,
    product_type: str,
    asset_id: str,
    start_date: date,
    rng: random.Random,
) -> Dict[str, Any]:
    financials = calculate_policy_financials(product_type, rng)
    return {
        "policy_id": policy_id,
        "portfolio_id": portfolio_id,
        "product_type": product_type,
        "linked_asset_id": asset_id,
        "start_date": iso_at(start_date, 9),
        "end_date": iso_at(start_date + timedelta(days=364), 23),
        "duration_months": 12,
        "status": "active",
        "ncd_years": rng.randint(0, 9) if product_type in {"motor", "motorcycle"} else 0,
        "legal_protection": rng.choice([True, False]),
        **financials,
    }


def generate_relationship_json(
    relationship_id: str,
    relationship_type: str,
    from_node_id: str,
    to_node_id: str,
    role: str,
    effective_from: str,
    context_policy_id: Optional[str] = None,
    effective_to: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "relationship_id": relationship_id,
        "relationship_type": relationship_type,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "role": role,
        "context_policy_id": context_policy_id,
        "effective_from": effective_from,
        "effective_to": effective_to,
    }


def generate_complex_scenario(seed: Optional[int] = None) -> Dict[str, Any]:
    rng = random.Random(seed if seed is not None else random.randrange(1, 10_000_000))
    family_name = rng.choice(LAST_NAMES)
    household_town, _ = rng.choice(TOWNS)
    scenario_seed = rng.randint(100_000, 999_999)
    start_base = date.today() - timedelta(days=rng.randint(90, 220))

    holder_id = make_id("PTY", rng)
    spouse_id = make_id("PTY", rng)
    child_id = make_id("PTY", rng)
    friend_id = make_id("PTY", rng)

    car_asset_id = make_id("AST", rng)
    bike_asset_id = make_id("AST", rng)
    home_asset_id = make_id("AST", rng)

    motor_portfolio_id = make_id("PORT", rng)
    home_portfolio_id = make_id("PORT", rng)

    motor_policy_id = make_id("POL", rng)
    bike_policy_id = make_id("POL", rng)
    home_policy_id = make_id("POL", rng)

    container_code = f"CONT-{household_town[:3].upper()}-{scenario_seed}"

    parties = [
        generate_party_json(holder_id, rng, first_name=rng.choice(FIRST_NAMES), last_name=family_name, birth_year=1981),
        generate_party_json(spouse_id, rng, first_name=rng.choice(FIRST_NAMES), last_name=family_name, birth_year=1984, relationship_to_holder="spouse"),
        generate_party_json(child_id, rng, first_name=rng.choice(FIRST_NAMES), last_name=family_name, birth_year=2003, relationship_to_holder="child"),
        generate_party_json(friend_id, rng, first_name=rng.choice(FIRST_NAMES), last_name=rng.choice(LAST_NAMES), birth_year=1990, relationship_to_holder="friend"),
    ]

    home_address = choose_address(rng)
    for party in parties[:3]:
        party["contact_details"]["address"] = home_address

    assets = [
        generate_vehicle_asset_json(car_asset_id, rng),
        generate_motorcycle_asset_json(bike_asset_id, rng),
        generate_home_asset_json(home_asset_id, rng),
    ]
    assets[2]["specification"]["address"] = home_address

    portfolios = [
        {
            "portfolio_id": motor_portfolio_id,
            "portfolio_type": "motor",
            "display_name": f"{family_name} Mobility Portfolio",
        },
        {
            "portfolio_id": home_portfolio_id,
            "portfolio_type": "home",
            "display_name": f"{family_name} Household Portfolio",
        },
    ]

    policies = [
        generate_policy_json(motor_policy_id, motor_portfolio_id, "motor", car_asset_id, start_base, rng),
        generate_policy_json(bike_policy_id, motor_portfolio_id, "motorcycle", bike_asset_id, start_base + timedelta(days=14), rng),
        generate_policy_json(home_policy_id, home_portfolio_id, "home", home_asset_id, start_base - timedelta(days=20), rng),
    ]

    relationships = [
        generate_relationship_json(make_id("REL", rng), "party_to_policy", holder_id, motor_policy_id, "Policyholder", policies[0]["start_date"], motor_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_policy", holder_id, motor_policy_id, "Payer", policies[0]["start_date"], motor_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_asset", holder_id, car_asset_id, "RegisteredKeeper", policies[0]["start_date"], motor_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_asset", spouse_id, car_asset_id, "MainDriver", policies[0]["start_date"], motor_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_asset", child_id, car_asset_id, "NamedDriver", iso_at(start_base + timedelta(days=45), 9), motor_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_policy", holder_id, bike_policy_id, "Policyholder", policies[1]["start_date"], bike_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_asset", holder_id, bike_asset_id, "MainRider", policies[1]["start_date"], bike_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_policy", holder_id, home_policy_id, "Policyholder", policies[2]["start_date"], home_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_policy", spouse_id, home_policy_id, "JointPolicyholder", policies[2]["start_date"], home_policy_id),
        generate_relationship_json(make_id("REL", rng), "party_to_party", holder_id, spouse_id, "Spouse", policies[2]["start_date"]),
        generate_relationship_json(make_id("REL", rng), "party_to_party", holder_id, child_id, "Child", policies[2]["start_date"]),
        generate_relationship_json(make_id("REL", rng), "party_to_asset", friend_id, car_asset_id, "OccasionalDriver", iso_at(start_base + timedelta(days=70), 9), motor_policy_id),
    ]

    history = [
        {
            "event_type": "PolicyPremiumAdjusted",
            "policy_id": motor_policy_id,
            "effective_from": iso_at(start_base + timedelta(days=32), 10),
            "reason": "Added young driver load",
            "premium_amount": policies[0]["premium_amount"] + 145.0,
            "ipt_amount": round((policies[0]["premium_amount"] + 145.0) * 0.12, 2),
        },
        {
            "event_type": "PolicyLegalProtectionChanged",
            "policy_id": motor_policy_id,
            "effective_from": iso_at(start_base + timedelta(days=32), 10),
            "reason": "Legal protection added during MTA",
            "enabled": True,
        },
        {
            "event_type": "PolicyNoClaimsDiscountChanged",
            "policy_id": motor_policy_id,
            "effective_from": iso_at(start_base + timedelta(days=32), 10),
            "reason": "NCD recalculated after driver change",
            "ncd_years": max(0, policies[0]["ncd_years"] - 1),
        },
        {
            "event_type": "PolicyPremiumAdjusted",
            "policy_id": bike_policy_id,
            "effective_from": iso_at(start_base + timedelta(days=58), 10),
            "reason": "Security tracker installed",
            "premium_amount": max(250.0, policies[1]["premium_amount"] - 60.0),
            "ipt_amount": round(max(250.0, policies[1]["premium_amount"] - 60.0) * 0.12, 2),
        },
        {
            "event_type": "PolicyStatusChanged",
            "policy_id": home_policy_id,
            "effective_from": iso_at(start_base + timedelta(days=12), 10),
            "reason": "Pending documentation resolved",
            "new_status": "active",
        },
        {
            "event_type": "PartyRiskProfileUpdated",
            "party_id": child_id,
            "risk_updates": {"licence_points": rng.randint(0, 3), "telematics_score": rng.randint(620, 780)},
        },
        {
            "event_type": "AssetRiskAttributesUpdated",
            "asset_id": home_asset_id,
            "risk_updates": {"alarm_installed": True, "recent_renovation": True},
        },
        {
            "event_type": "RelationshipEnded",
            "relationship_id": relationships[-1]["relationship_id"],
            "effective_to": iso_at(start_base + timedelta(days=122), 18),
        },
    ]

    return {
        "meta": {
            "seed": scenario_seed,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": "Cross-product household with motor, motorcycle, and home coverage.",
        },
        "container": {
            "container_id": container_code,
            "account_holder_id": holder_id,
        },
        "portfolios": portfolios,
        "parties": parties,
        "assets": assets,
        "policies": policies,
        "relationships": relationships,
        "history": history,
    }


def apply_scenario(app: InsuranceGraphApplication, scenario: Dict[str, Any]) -> UUID:
    container = scenario["container"]
    container_uuid = app.open_policy_container(
        container_id=container["container_id"],
        account_holder_id=container["account_holder_id"],
    )

    for portfolio in scenario["portfolios"]:
        app.add_portfolio(
            container_uuid,
            portfolio["portfolio_id"],
            portfolio["portfolio_type"],
            portfolio["display_name"],
        )

    for party in scenario["parties"]:
        app.register_party(
            container_id=container_uuid,
            party_id=party["party_id"],
            identity=party["identity"],
            contact_details=party["contact_details"],
            risk_profile=party["risk_profile"],
            party_type=party["party_type"],
        )

    for asset in scenario["assets"]:
        app.register_asset(
            container_id=container_uuid,
            asset_id=asset["asset_id"],
            asset_type=asset["asset_type"],
            identification=asset["identification"],
            specification=asset["specification"],
            risk_attributes=asset["risk_attributes"],
        )

    for policy in scenario["policies"]:
        app.create_policy(
            container_id=container_uuid,
            policy_id=policy["policy_id"],
            portfolio_id=policy["portfolio_id"],
            product_type=policy["product_type"],
            start_date=policy["start_date"],
            end_date=policy["end_date"],
            duration_months=policy["duration_months"],
            premium_amount=policy["premium_amount"],
            ipt_amount=policy["ipt_amount"],
            excess_amount=policy["excess_amount"],
            ncd_years=policy["ncd_years"],
            legal_protection=policy["legal_protection"],
            status=policy["status"],
        )
        app.link_policy_to_asset(
            container_id=container_uuid,
            policy_id=policy["policy_id"],
            asset_id=policy["linked_asset_id"],
            effective_from=policy["start_date"],
        )

    for relationship in scenario["relationships"]:
        app.start_relationship(
            container_id=container_uuid,
            relationship_id=relationship["relationship_id"],
            relationship_type=relationship["relationship_type"],
            from_node_id=relationship["from_node_id"],
            to_node_id=relationship["to_node_id"],
            role=relationship["role"],
            effective_from=relationship["effective_from"],
            context_policy_id=relationship.get("context_policy_id"),
            effective_to=relationship.get("effective_to"),
        )

    for event in scenario.get("history", []):
        event_type = event["event_type"]
        if event_type == "PolicyPremiumAdjusted":
            app.adjust_policy_premium(
                container_id=container_uuid,
                policy_id=event["policy_id"],
                premium_amount=event["premium_amount"],
                ipt_amount=event["ipt_amount"],
                effective_from=event["effective_from"],
                reason=event["reason"],
            )
        elif event_type == "PolicyLegalProtectionChanged":
            app.change_policy_legal_protection(
                container_id=container_uuid,
                policy_id=event["policy_id"],
                enabled=event["enabled"],
                effective_from=event["effective_from"],
                reason=event["reason"],
            )
        elif event_type == "PolicyNoClaimsDiscountChanged":
            app.change_policy_no_claims_discount(
                container_id=container_uuid,
                policy_id=event["policy_id"],
                ncd_years=event["ncd_years"],
                effective_from=event["effective_from"],
                reason=event["reason"],
            )
        elif event_type == "PolicyStatusChanged":
            app.change_policy_status(
                container_id=container_uuid,
                policy_id=event["policy_id"],
                new_status=event["new_status"],
                effective_from=event["effective_from"],
                reason=event["reason"],
            )
        elif event_type == "PartyRiskProfileUpdated":
            app.update_party_risk_profile(
                container_id=container_uuid,
                party_id=event["party_id"],
                risk_updates=event["risk_updates"],
            )
        elif event_type == "AssetRiskAttributesUpdated":
            app.update_asset_risk_attributes(
                container_id=container_uuid,
                asset_id=event["asset_id"],
                risk_updates=event["risk_updates"],
            )
        elif event_type == "RelationshipEnded":
            app.end_relationship(
                container_id=container_uuid,
                relationship_id=event["relationship_id"],
                effective_to=event["effective_to"],
            )
        else:
            raise ValueError(f"Unsupported history event: {event_type}")

    return container_uuid
