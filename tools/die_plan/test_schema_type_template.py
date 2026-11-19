"""TYPE-TEMPLATE (OWNER 11-19): partition_types[T].type_template is a schema key (a type entry refuses unknown keys)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402


def test_type_template_is_a_boolean_type_key():
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]
    assert props["properties"]["type_template"] == {"type": "boolean"}
    assert props.get("additionalProperties") is False        # so the key must be declared
