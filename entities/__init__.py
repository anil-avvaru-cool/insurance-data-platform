from __future__ import annotations

from entities.entity_vehicle import resolve_vehicles
from entities.entity_person import resolve_persons
from entities.entity_address import resolve_addresses
from entities.entity_phone import resolve_phones
from entities.entity_policy import resolve_policies

__all__ = [
    "resolve_vehicles",
    "resolve_persons",
    "resolve_addresses",
    "resolve_phones",
    "resolve_policies",
]
