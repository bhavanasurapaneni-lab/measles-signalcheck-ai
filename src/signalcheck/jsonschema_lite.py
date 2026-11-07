"""Minimal JSON Schema validator (no third-party dependency).

Supports the subset used by ``schemas/evidence_packet.schema.json``: type (single or
list), enum, required, properties, additionalProperties=false, items, pattern,
minItems, maxItems. Unsupported keywords in a schema raise, so the subset cannot
silently drift from the documented schema.
"""
from __future__ import annotations

import re

SUPPORTED = {"$schema", "$id", "title", "description", "type", "enum", "required",
             "properties", "additionalProperties", "items", "pattern", "minItems", "maxItems"}
TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "integer": int, "number": (int, float), "null": type(None),
}


class SchemaViolation(ValueError):
    pass


def _type_ok(value, t: str) -> bool:
    if t in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, TYPES[t])


def validate(value, schema: dict, path: str = "$") -> None:
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise SchemaViolation(f"{path}: unsupported schema keyword(s) {sorted(unknown)}")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            raise SchemaViolation(f"{path}: expected {types}, got {type(value).__name__}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaViolation(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        raise SchemaViolation(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise SchemaViolation(f"{path}: missing required {key!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            if extra:
                raise SchemaViolation(f"{path}: unexpected properties {sorted(extra)}")
        for key, sub in props.items():
            if key in value:
                validate(value[key], sub, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise SchemaViolation(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise SchemaViolation(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(value):
                validate(item, schema["items"], f"{path}[{i}]")
