#!/usr/bin/env python3
"""S81-RF1 block / S81-071 (DIE-S81-51/PLAN 11-03): class split of ot_s81sl_leaf__t40__cl86ea32b3.

kit_rtl FAIL (kit-wave b1a2125433d0 attempt_2): the type's two instances s_4N_L4 / s_5S_L4 differ in the logic parameter
S_u_lf4_u_vq_sid (TYPE-DEDUP merged t49 into t40), so one kit cannot serve both.  Split: s_4N_L4 keeps the type,
s_5S_L4 gets an exact clone NEW (module = NEW, landing_base_type unchanged, note += split).  Every plan reference to the
type that is per-type (partition_types key + module, clock.landing_contract.collector_tree.type, reset.in_sites) is
cloned; the partition's .type moves; the bind clock landing table (h2_2249/landed_sidecar_h2.json collector.types) gets the
same clone.  Nothing else changes (check_equal).  Writes with pin_template.dumps.

    delta_t40split_1103.py PLAN_IN PLAN_OUT SIDECAR_IN SIDECAR_OUT
"""
import copy, json, sys
from pathlib import Path
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools" / "die_plan"))
import pin_template as PT  # noqa: E402

OLD = "ot_s81sl_leaf__t40__cl86ea32b3"
NEW = OLD + "__sid5S"
MOVE = "s_5S_L4"
KEEP = "s_4N_L4"
NOTE = ";S81-071 class split (DIE-S81-51/PLAN 11-03, delta_t40split_1103.py): instance %s, own S_u_lf4_u_vq_sid image"


def apply(raw, side):
    ts = raw["partition_types"]
    assert OLD in ts and NEW not in ts
    names = sorted(p["name"] for p in raw["partitions"] if p["type"] == OLD)
    assert names == sorted([KEEP, MOVE]), names
    t = copy.deepcopy(ts[OLD])
    assert t["module"] == OLD
    t["module"] = NEW
    t["note"] = t.get("note", "") + NOTE % MOVE
    ct = t.get("clock", {}).get("landing_contract", {}).get("collector_tree", {})
    if ct.get("type") == OLD:
        ct["type"] = NEW
    ts[OLD]["note"] = ts[OLD].get("note", "") + NOTE % KEEP
    # keep partition_types order: NEW right after OLD
    items = list(ts.items())
    i = [k for k, _ in items].index(OLD)
    items.insert(i + 1, (NEW, t))
    raw["partition_types"] = dict(items)
    for p in raw["partitions"]:
        if p["name"] == MOVE:
            p["type"] = NEW
    ins = raw.get("reset", {}).get("in_sites", {})
    if OLD in ins:
        it = list(ins.items()); j = [k for k, _ in it].index(OLD)
        it.insert(j + 1, (NEW, copy.deepcopy(ins[OLD]))); raw["reset"]["in_sites"] = dict(it)
    ct_ = side["collector"]["types"]
    assert OLD in ct_ and NEW not in ct_
    it = list(ct_.items()); j = [k for k, _ in it].index(OLD)
    it.insert(j + 1, (NEW, copy.deepcopy(ct_[OLD]))); side["collector"]["types"] = dict(it)
    return raw, side


def check_equal(a, b):
    """b minus the split == a"""
    b = copy.deepcopy(b)
    t = b["partition_types"].pop(NEW)
    assert t["module"] == NEW
    b["partition_types"][OLD]["note"] = b["partition_types"][OLD]["note"].replace(NOTE % KEEP, "")
    for p in b["partitions"]:
        if p["name"] == MOVE:
            p["type"] = OLD
    b.get("reset", {}).get("in_sites", {}).pop(NEW, None)
    assert a == b, "unexpected plan edit"
    t2 = copy.deepcopy(a["partition_types"][OLD]); t["module"] = OLD
    t["note"] = t["note"].replace(NOTE % MOVE, "")
    ct = t.get("clock", {}).get("landing_contract", {}).get("collector_tree", {})
    if ct.get("type") == NEW:
        ct["type"] = OLD
    assert t == t2, "clone differs from the base type"


if __name__ == "__main__":
    pi, po, si, so = sys.argv[1:5]
    a = json.loads(Path(pi).read_text()); s = json.loads(Path(si).read_text())
    raw, side = apply(copy.deepcopy(a), copy.deepcopy(s))
    check_equal(a, raw)
    Path(po).write_text(PT.dumps(raw))
    assert json.dumps(s, separators=(",", ":")) == Path(si).read_text(), "sidecar format"
    Path(so).write_text(json.dumps(side, separators=(",", ":")))
    print("split", OLD, "->", NEW, "for", MOVE)
