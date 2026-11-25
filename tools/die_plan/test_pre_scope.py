"""FP-CONVERGE-S81 11-25: plan_gate_pre --types (scoped PRE): scoped == full PRE filtered to the types; excluded findings vanish, included stay."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402
import pre_diff as PD  # noqa: E402

NAMES = {"leaf__t10", "leaf__t15", "col_h9_r1__t1", "svc_lo__t5"}
FULL = ["FAIL INOUTLINE leaf__t10: station reg (160, 60) +60",
        "FAIL REACH leaf__t15: hop 500",
        "WARN ADV-X col_h9_r1__t1 and svc_lo__t5: shared",
        "FAIL SCHEMA-LOAD whole plan finding",
        "LIST PRE-TIME 12 s: RESETWARM 5s"]


def test_parse_types_globs_list_and_file(tmp_path):
    assert G.parse_types("leaf__*", NAMES) == {"leaf__t10", "leaf__t15"}
    assert G.parse_types("leaf__t10,svc_lo__t5", NAMES) == {"leaf__t10", "svc_lo__t5"}
    f = tmp_path / "t.txt"
    f.write_text("col_h9_r1__t1\nsvc_lo__t5\n")
    assert G.parse_types("@" + str(f), NAMES) == {"col_h9_r1__t1", "svc_lo__t5"}


def test_parse_types_unmatched_glob_is_an_error():
    with pytest.raises(ValueError):
        G.parse_types("nosuch*", NAMES)


def test_scope_lines_equals_full_filtered():
    scope = {"leaf__t10"}
    out = G.scope_lines(FULL, scope, NAMES)
    assert out == [FULL[0], FULL[3], FULL[4]]                     # leaf__t15 and the col/svc line (neither in scope) drop; whole-plan lines stay
    both = G.scope_lines(FULL, {"col_h9_r1__t1"}, NAMES)
    assert FULL[2] in both and FULL[0] not in both              # a line naming an in-scope type with an out-of-scope one stays


def test_mutant_included_finding_must_appear_excluded_must_not():
    out = G.scope_lines(FULL, {"leaf__t15"}, NAMES)
    assert FULL[1] in out and FULL[0] not in out


def test_check_scopes_and_resets_global(tmp_path, monkeypatch):
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps({"partition_types": {n: {} for n in NAMES}}))
    seen = {}

    def fake(*a, **k):
        seen["scope"] = set(G._SCOPE) if G._SCOPE is not None else None
        return list(FULL)
    monkeypatch.setattr(G, "_check_unscoped", fake)
    out = G.check("tree", str(plan), types="leaf__t10")
    assert seen["scope"] == {"leaf__t10"} and G._SCOPE is None
    assert FULL[0] in out and FULL[1] not in out and out[-1] == "LIST PRE-SCOPE 1 of 4 types"
    assert G.check("tree", str(plan)) == FULL and seen["scope"] is None      # no types: unscoped, untouched


def test_base_cmd_and_cache_key_carry_types(tmp_path):
    cmd = PD.base_cmd("b.json", "tree", types="leaf__*")
    assert cmd[cmd.index("--types") + 1] == "leaf__*"
    assert "--types" not in PD.base_cmd("b.json", "tree")
    b = tmp_path / "b.json"
    b.write_text("{}")
    assert PD.cache_key(str(b), str(tmp_path), types="a") != PD.cache_key(str(b), str(tmp_path), types="b")
