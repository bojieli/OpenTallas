"""ROOT-RULETAG 10-19: the six helper-chain commits left unclassified after ROOT-UNBLOCK (03c544ca1, b7918e979 and four
tools/tt_views/view_export.py commits) are in helper_overlay.RULE_COMMITS; b7918e979 (child_lint (i) pin access) is a
tightening judged per kit by requires=child_pin_access."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2] / "closure_loop"))
import source_binding as SB  # noqa: E402
import helper_overlay as HO  # noqa: E402


def lef(obs, sig):
    """minimal hard-child LEF (same shape as tools/hier_contract/test_hier_contract.lef): signal pins 0.192 x 0.024"""
    out = ["VERSION 5.8 ;\nMACRO t\n  CLASS BLOCK ;\n  SIZE 20 BY 10 ;"]
    for n, ly, x, y in sig:
        out.append(f"  PIN {n}\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER {ly} ;\n"
                   f"        RECT {x} {y} {x + 0.192} {y + 0.024} ;\n    END\n  END {n}")
    out.append("  OBS\n" + "\n".join(f"    LAYER {ly} ;\n      RECT {a} {b} {c} {d} ;" for ly, a, b, c, d in obs)
               + "\n  END")
    out.append("END t\nEND LIBRARY\n")
    return "\n".join(out)

DF = "03c544ca1ab6f68f0d2a94bb2e7fb43751eedce7"
EC = "b7918e97926daf87d0edfee3e62f07322d62e96b"
VX = {"bb5e443cdb8423c7b3ad4fab6961c201bfeb9e1b": "neutral", "b8fa05678b7e74d2549d37a0d6c8a7608abc6731": "relaxing",
      "cdd8d92a84daa2bf1d60a08d9d8ba97be64c1488": "relaxing", "ff7aa2deb861035c309af48249284018f40718b0": "relaxing"}
APS = HERE.parents[2] / "hier_contract" / "abstract_pin_stub.py"


def test_registry_kinds():
    assert HO.RULE_COMMITS[DF]["kind"] == "neutral" and "requires" not in HO.RULE_COMMITS[DF]
    assert HO.RULE_COMMITS[EC]["kind"] == "tightening" and HO.RULE_COMMITS[EC]["requires"] == "child_pin_access"
    for c, k in VX.items():
        assert HO.RULE_COMMITS[c]["kind"] == k
    for rel in ("tools/hier_contract/abstract_pin_stub.py", "tools/hier_contract/child_lint.py"):
        assert HO.classify_commit(".", EC, rel, None, None)["kind"] == "tightening"
    assert HO.classify_commit(".", DF, "tools/hier_contract/abstract_pin_stub.py", None, None)["source"] == "registry"
    for c, k in VX.items():
        r = HO.classify_commit(".", c, "tools/tt_views/view_export.py", None, None)
        assert r["kind"] == k and r["source"] == "registry"


def test_bb5_trailer_is_not_vocabulary():
    # why bb5e443cd read unclassified: its trailer word is not relaxing|neutral|tightening
    assert HO.parse_rule_trailer("x\n\nGate-Rule: export-session reproduces verdict (no rule change)\n") is None


def kit(root, children):
    kd = root / "physical" / "ref_tile" / "k"
    kd.mkdir(parents=True)
    (kd / "spec.json").write_text(json.dumps(dict(kind="cluster", children=[dict(view=v) for v in children])))
    hc = root / "tools" / "hier_contract"
    hc.mkdir(parents=True)
    (hc / "abstract_pin_stub.py").write_text(APS.read_text())
    return dict(kit="k")


def view(root, name, obs):
    d = root / "views" / name
    d.mkdir(parents=True)
    (d / f"{name}.lef").write_text(lef(obs=obs, sig=(("p", "M5", 0.0, 4.5),)))
    return f"views/{name}"


def test_child_pin_access(tmp_path):
    a = tmp_path / "a"
    ok, rows = SB.relaxed_rule_requirement(["child_pin_access"], {}, kit(a, []), root=a)
    assert ok and "no hard children" in rows[0]["text"]
    b = tmp_path / "b"
    clean = view(b, "clean", [("M5", 6, 2, 8, 6)])
    ok, rows = SB.relaxed_rule_requirement(["child_pin_access"], {}, kit(b, [clean]), root=b)
    assert ok, rows
    c = tmp_path / "c"
    bad = view(c, "bad", [("M5", 0.24, 4.0, 1.0, 5.0)])   # wide M5 OBS one pitch beside the M5 pin
    ok, rows = SB.relaxed_rule_requirement(["child_pin_access"], {}, kit(c, [bad]), root=c)
    assert not ok and rows[0]["violations"].get("bad")
    d = tmp_path / "d"
    ok, _ = SB.relaxed_rule_requirement(["child_pin_access"], {}, kit(d, ["views/missing"]), root=d)
    assert not ok                                           # unreadable child view: strict
    assert not SB.relaxed_rule_requirement(["child_pin_access"], {}, None, root=tmp_path / "e")[0]
