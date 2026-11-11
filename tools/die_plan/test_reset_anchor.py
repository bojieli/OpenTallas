"""RELAY-ANCHOR (DIE-QC-97 11-10): plan relay names re-picked by recorded site when a reset-tree input renumbers the
tree (TAPREACH-1 sle_ctl__cl67434795 rst_rl_228; cand16 slw_sc_v1 rst_rl_97)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_anchor as RA  # noqa: E402
import schema  # noqa: E402

FIX = HERE / "examples" / "reset_anchor" / "sle_ctl_tapreach.json"


def _tree(rows):
    return {"relays": [dict(q=q, depth=d, xy=list(xy)) for q, d, xy in rows]}


def _type(*names):
    stages = [dict(xy_um=[10.0 * i, 0.0], raw_reset=n) for i, n in enumerate(names)]
    return {"clock": {"landing_writer_start": {"depth": len(stages), "branches": {"b_o": {"stages": stages}}},
                      "landing_local_resets": [dict(name="l0", raw=names[0], xy_um=[1.0, 1.0],
                                                    consumers=["u_cland_x"])]}}


OLD = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 2, (100, 0)), ("rst_rl_2", 2, (0, 100)), ("rst_rl_3", 3, (100, 100))])
# the same sites after an input change re-ordered the build (a new relay rst_rl_1 at depth 1 in front)
NEW = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 1, (300, 0)), ("rst_rl_2", 2, (100, 0)),
             ("rst_rl_3", 2, (0, 100)), ("rst_rl_4", 3, (100, 104))])
NOPORT = lambda tree: set()  # noqa: E731


def _anchored(*names, tree=OLD, tol=50.0):
    t = _type(*names)
    t["clock"][RA.KEY] = RA.record(t, tree, HERE, tol)
    return t


def _names(t):
    return [c[k] for c, k in RA.refs(t)]


def test_renumbered_tree_is_repicked_by_site():
    t = _anchored("rst_rl_1", "rst_rl_2", "rst_rl_3")
    # without the anchor the plan names point at the wrong relays (rst_rl_1 is now depth 1 at 300,0)
    by = {r["q"]: r for r in NEW["relays"]}
    assert by["rst_rl_1"]["depth"] != t["clock"][RA.KEY]["relays"]["rst_rl_1"]["depth"]
    rec = RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)
    assert _names(t) == ["rst_rl_2", "rst_rl_3", "rst_rl_4", "rst_rl_2"]
    assert [(m["name"], m["to"]) for m in rec["remaps"]] == [("rst_rl_1", "rst_rl_2"), ("rst_rl_2", "rst_rl_3"),
                                                              ("rst_rl_3", "rst_rl_4")]
    assert rec["remaps"][2]["moved_um"] == 4.0 and rec["refs_rewritten"] == 4
    # idempotent: the in-memory anchor follows the new names
    assert RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)["remaps"] == []


def test_unchanged_tree_is_byte_identical():
    t = _anchored("rst_rl_1", "rst_rl_3")
    before = hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()
    rec = RA.resolve("T", t, copy.deepcopy(OLD), HERE, ported_fn=lambda tr: pytest.fail("no re-pick expected"))
    assert rec["remaps"] == [] and rec["kept"] == 2
    assert hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest() == before


def test_no_anchor_is_untouched():
    t = _type("rst_rl_1")
    snap = copy.deepcopy(t)
    assert RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT) is None and t == snap
    raw = {"partition_types": {"T": t}}
    assert RA.resolve_plan(raw, None, HERE, tree_fn=lambda tn: pytest.fail("no tree for unanchored plans")) == ([], [])


def test_no_relay_within_tolerance_fails_closed():
    t = _anchored("rst_rl_3", tol=2.0)          # rst_rl_3 moved 4 um in NEW
    with pytest.raises(RA.AnchorError, match="no relay within the recorded site tolerance"):
        RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)
    t = _anchored("rst_rl_3")
    gone = _tree([(r["q"], r["depth"], r["xy"]) for r in NEW["relays"] if r["depth"] != 3])
    with pytest.raises(RA.AnchorError, match="no same-depth relay"):
        RA.resolve("T", t, gone, HERE, ported_fn=NOPORT)
    raw = {"partition_types": {"T": _anchored("rst_rl_3", tol=2.0)}}
    rec, err = RA.resolve_plan(raw, None, HERE, tree_fn=lambda tn: NEW, ported_fn=NOPORT)
    assert rec == [] and len(err) == 1 and err[0].startswith("RESET_ANCHOR T:")


def test_ported_relay_is_never_a_target_and_unanchored_name_fails():
    t = _anchored("rst_rl_1", tol=250.0)
    rec = RA.resolve("T", t, NEW, HERE, ported_fn=lambda tr: {"rst_rl_2"})
    assert rec["remaps"][0]["to"] == "rst_rl_3" and rec["remaps"][0]["moved_um"] == 200.0
    with pytest.raises(RA.AnchorError):                # the same with tol 50: the only free relay is too far
        RA.resolve("T", _anchored("rst_rl_1"), NEW, HERE, ported_fn=lambda tr: {"rst_rl_2"})
    t = _anchored("rst_rl_1")
    t["clock"]["landing_local_resets"][0]["raw"] = "rst_rl_0"
    with pytest.raises(RA.AnchorError, match="lacks referenced relay"):
        RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)


def test_record_rejects_names_not_in_tree():
    with pytest.raises(RA.AnchorError, match="not in the tree"):
        RA.record(_type("rst_rl_9"), OLD, HERE, 10)


def test_schema_accepts_anchor_and_rejects_unknown_key():
    s = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    anc = _anchored("rst_rl_1")["clock"][RA.KEY]
    errs = []
    schema._check(anc, s[RA.KEY], "$", errs)
    assert errs == []
    schema._check(dict(anc, extra=1), s[RA.KEY], "$", errs)
    assert errs == ["$: unknown key 'extra'"]


def test_sle_ctl_tapreach_matches_the_cand12_hand_repick():
    """MEASURED fixture: plan_pv sle_ctl__cl67434795 references, anchored on the 11-06 bins tree (501 relays), resolved on
    the TAPREACH-1 bins tree (513).  Before: rst_rl_228 is not even a relay; after: every name equals RELAY-REMAP-1."""
    fx = json.loads(FIX.read_text())
    t = {"clock": copy.deepcopy(fx["clock"])}
    t["clock"][RA.KEY] = fx["anchor"]
    tree = fx["tree_B"]
    by = {r["q"]: r for r in tree["relays"]}
    assert "rst_rl_228" in _names(t) and "rst_rl_228" not in by
    rec = RA.resolve(fx["type"], t, tree, HERE, ported_fn=lambda tr: set(fx["ported_B"]))
    assert "sink_bins" in rec["changed_inputs"]
    got = {n: next((m["to"] for m in rec["remaps"] if m["name"] == n), n) for n in fx["anchor"]["relays"]}
    assert got == {n: fx["expect_map"][n] for n in got}
    assert got["rst_rl_228"] == "rst_rl_211"
    assert all(n in by and by[n]["depth"] == fx["anchor"]["relays"][o]["depth"]
               for o, n in got.items())
