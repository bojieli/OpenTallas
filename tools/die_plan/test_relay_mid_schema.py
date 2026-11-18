"""FABLE-FIX-KV-HG 11-18: the plan form of the relay_mid siting keys (budgets.relay_mid_re_types / _tail_types /
_soft_frac_types and their plan-wide forms) passes the plan schema and reaches gen_phys; a bad value fails closed.
    python3 -m pytest -q tools/die_plan/test_relay_mid_schema.py"""
import gen_phys
import schema

RE = gen_phys.RELAY_MID_RE_KV if hasattr(gen_phys, "RELAY_MID_RE_KV") else r"^(.*[._]u_hst[0-9]+_(?:g|t[0-9]+))[.]"


def test_keys_declared_and_read():
    props = schema.SCHEMA["properties"]["budgets"]["properties"]
    for k in ("relay_mid_re", "relay_mid_re_types", "relay_mid_tail", "relay_mid_tail_types", "relay_mid_soft_frac",
              "relay_mid_soft_frac_types"):
        assert k in props, k
    b = dict(relay_mid_re_types={"kv3_hgi_v1": RE}, relay_mid_tail_types=["kv3_hgi_v1"],
             relay_mid_soft_frac_types={"kv3_hgi_v1": 0.05})
    assert gen_phys._relay_mid_re(b, "kv3_hgi_v1__cl0") == RE
    assert gen_phys._relay_mid_tail(b, "kv3_hgi_v1") and not gen_phys._relay_mid_tail(b, "kv3_hg")
    assert gen_phys._relay_mid_soft_frac(b, "kv3_hgi_v1") == 0.05


def test_schema_json_matches():
    import json
    from pathlib import Path
    on_disk = json.loads((Path(schema.__file__).with_name("die_plan.schema.json")).read_text())
    assert on_disk["properties"]["budgets"]["properties"]["relay_mid_soft_frac_types"] == \
        schema.SCHEMA["properties"]["budgets"]["properties"]["relay_mid_soft_frac_types"]
