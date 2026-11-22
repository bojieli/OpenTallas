"""PORTPAD-1122 (FLOW-OPS-R2, COORD; OPUS-FIX-KV-HGI-R6 padremap.py): landing_remap rewrites landing references to the port-pad
relay chain by identity (depth, site, kind), also when reset_resel refuses the branch ("tree relay after a non-tree stage")."""
import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_remap as LR  # noqa: E402

PORT = (1274.4, 1241.82)
# R6 hgi_v2: the core move renumbers the pad chain at the east reset port by -4
OLD = {f"rst_rl_{322 + i}": (2 + i, PORT, "pad") for i in range(4)}
OLD.update({"rst_rl_326": (6, PORT, "wire"), "rst_rl_327": (7, (1274.4, 966.82), "wire")})
NEW = {f"rst_rl_{318 + i}": (2 + i, PORT, "pad") for i in range(4)}
NEW.update({"rst_rl_322": (6, PORT, "wire"), "rst_rl_323": (7, (1274.4, 966.82), "wire"), "rst_rl_324": (8, (0, 0), "wire"),
            "rst_rl_325": (9, (0, 0), "wire"), "rst_rl_326": (10, (0, 0), "wire"), "rst_rl_327": (11, (0, 0), "wire")})


def plan():
    br = {"name": "fs_ft0_o", "base": "rst_rl_322",
          "stages": [{"original": f"rst_rl_{323 + i}"} for i in range(5)] + [{"original": "cland_reset_ft0_i"}]}
    return {"partition_types": {"T": {"clock": {"landing_raw_branches": [br]}}}}


def ident(old):
    return lambda raw, tn: OLD if raw is old else NEW


def test_port_pad_chain_by_identity_after_resel_refused():
    old, new = plan(), plan()
    rec = LR.remap_plan(old, new, HERE, HERE, resets="resel", adopt=False, keep_xy=False, ident_fn=ident(old),
                        resel_fn=lambda *a: {"T": {"error": "landing_raw_branches.0 (o): tree relay after a non-tree stage"}},
                        tree_fn=lambda raw, tn: {"relays": []})
    br = new["partition_types"]["T"]["clock"]["landing_raw_branches"][0]
    assert br["base"] == "rst_rl_318" and [s["original"] for s in br["stages"]] == \
        ["rst_rl_319", "rst_rl_320", "rst_rl_321", "rst_rl_322", "rst_rl_323", "cland_reset_ft0_i"]
    assert "T" in rec["resel_fallback"] and len(rec["identity"]) == 6


def test_other_resel_error_still_fails_closed_and_unplaceable_identity_raises():
    old, new = plan(), plan()
    with pytest.raises(LR.RemapError, match="reset_resel"):
        LR.remap_plan(old, new, HERE, HERE, resets="resel", adopt=False, ident_fn=ident(old),
                      resel_fn=lambda *a: {"T": {"error": "plan load: x"}})
    gone = dict(NEW); del gone["rst_rl_318"]
    old, new = plan(), plan()
    with pytest.raises(LR.RemapError, match="needs a plan row"):
        LR.identity_remap(old, new, ["T"], lambda raw, tn: OLD if raw is old else gone)


def test_after_successful_resel_leftovers_are_taken_and_unchanged_types_untouched():
    old, new = plan(), plan()
    LR.remap_plan(old, new, HERE, HERE, resets="resel", adopt=False, keep_xy=False, ident_fn=ident(old),
                  resel_fn=lambda *a: {"T": dict(exports=[], raw=[], skipped=["landing_raw_branches.0 (fs_ft0_o): chain ends"])},
                  tree_fn=lambda raw, tn: {"relays": []})
    assert new["partition_types"]["T"]["clock"]["landing_raw_branches"][0]["base"] == "rst_rl_318"
    old, new = plan(), plan()
    same = copy.deepcopy(new)
    LR.identity_remap(old, new, ["T"], lambda raw, tn: OLD)
    assert new == same
