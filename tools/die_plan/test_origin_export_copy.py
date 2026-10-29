"""Export fanout copies are explicit, optional existing-state replicas."""
from clock_landings import Landings


def emitted(enable=None):
    c = Landings.__new__(Landings)
    c.reset_placements = {}
    c.types = {"B": {"clock": {}}}
    if enable is not None:
        c.types["B"]["clock"]["landing_origin_export_copy"] = enable
    logic, _ = c._origin_strap_rtl("B", ("strap", ["y", "z"], 1, 64, False),
                                  {"y": "raw_y", "z": "raw_z"}, [], lambda _: "raw")
    return "\n".join(logic)


def test_export_copy_default_byte_identical_and_optin_per_sampler():
    assert emitted() == emitted(False)
    old = emitted()
    new = emitted(True)
    assert old.replace("#(.PADW(1))", "#(.PADW(1), .FWD_COPY(1))") == new
    assert new.count(".FWD_COPY(1)") == 2
    assert "assign cland_start_d" in new


def test_export_copy_schema_is_explicit_boolean():
    import schema
    prop = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert prop["landing_origin_export_copy"] == {"type": "boolean"}
