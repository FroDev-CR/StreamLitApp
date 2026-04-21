import re
from datetime import datetime, timezone


def parse_total(raw: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", str(raw))
    if not cleaned:
        raise ValueError(f"No se pudo parsear el total: {repr(raw)}")
    return float(cleaned)


def parse_date_only(raw: str) -> str:
    raw   = str(raw).strip()
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if not match:
        return ""
    m, d, y = match.groups()
    return f"{y}-{int(m):02d}-{int(d):02d}"


def parse_address(raw: str) -> dict:
    raw   = str(raw).strip()
    parts = [p.strip() for p in raw.split(",")]
    street   = parts[0] if len(parts) > 0 else raw
    city     = parts[1] if len(parts) > 1 else ""
    province = ""
    postal   = ""
    if len(parts) > 2:
        state_zip = parts[-1].strip().split()
        province  = state_zip[0] if state_zip else ""
        postal    = state_zip[1] if len(state_zip) > 1 else ""
    return {"street": street, "city": city, "province": province, "postalCode": postal, "country": "US"}


def addresses_match(stored: dict, candidate: str) -> bool:
    stored_street    = (stored.get("street1") or "").strip().lower()
    candidate_street = parse_address(candidate).get("street", "").strip().lower()
    return stored_street == candidate_street


def build_property_input(address_str: str) -> dict:
    addr = parse_address(address_str)
    return {
        "address": {
            "street1":    addr["street"],
            "city":       addr["city"],
            "province":   addr["province"],
            "postalCode": addr["postalCode"],
            "country":    addr["country"],
        }
    }


def map_row_to_job_input(row: dict, property_id: str) -> dict:
    unit_price = parse_total(row["total"])
    start_date = parse_date_only(row["Start Date"])

    attributes: dict = {
        "propertyId": property_id,
        "title":      row["Job title Final"],
        "invoicing": {
            "invoicingType":     "FIXED_PRICE",
            "invoicingSchedule": "ON_COMPLETION",
        },
        "lineItems": [
            {
                "name":                      "Concrete Service",
                "description":               row["Job title Final"],
                "quantity":                  1,
                "unitPrice":                 unit_price,
                "saveToProductsAndServices": False,
            }
        ],
    }

    if start_date:
        attributes["timeframe"]  = {"startAt": start_date}
        attributes["scheduling"] = {"createVisits": True, "notifyTeam": False}

    return attributes


def validate_row(row: dict) -> str | None:
    try:
        parse_total(row["total"])
    except ValueError as e:
        return str(e)
    if not str(row.get("Full Property Address", "")).strip():
        return "Dirección vacía"
    if not str(row.get("Client Name", "")).strip():
        return "Cliente vacío"
    return None
