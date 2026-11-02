#!/usr/bin/env python3
"""DIE-S81-47 11-01: physical type event for leaf40 SID9 / SID10 (COORD ruling Q13: adopt if G0C 0 new + bind 0).

The two leaf40 instances s_4N_L4 and s_5S_L4 share plan type ot_s81sl_leaf__t40__cl86ea32b3, but their as-built
contents differ in one static value: the parent ties the child ot_s81sl_vq.sid INPUT port to 9 (s_4N_L4) and 10
(s_5S_L4).  An input port is not a parameter, so the one-view (image-only) rule correctly refuses one shared view, and
the strict bind reports TYPE_SPLIT leaf40 (K80 strict bind FAIL 11-01).  This delta gives each instance its own
physical type, copied verbatim from the shared one:

  ot_s81sl_leaf__t40__cl86ea32b3 -> ot_s81sl_leaf__t40__cl86ea32b3__sid9   (s_4N_L4)
                                    ot_s81sl_leaf__t40__cl86ea32b3__sid10  (s_5S_L4)

Changed, and nothing else (asserted):
  plan partition_types: the old type is replaced by the two new ones; each differs from the old only in module,
      clock.landing_contract.collector_tree.type and an appended note.  landing_base_type stays ot_s81sl_leaf__t40,
      so geometry, buses/pins, macros, FT slots, clock taps/providers, reset and cores are identical.
  plan partitions: s_4N_L4 / s_5S_L4 .type.
  plan reset.in_sites: the old type key is replaced by the two new keys with the same site (the cohort generator
      clock_landing_plan.py copies in_sites the same way when it splits a type).
  landed sidecar collector.parts[s_4N_L4 / s_5S_L4].type and collector.types: the old entry is replaced by two
      copies whose tree.type names the new type.  collector.base_type_by_part stays ot_s81sl_leaf__t40.
No added port or cycle; 204 -> 205 types.

Generator logic follows Codex's prepare-only candidate coord/tmp/s81_leaf40_sid_split_1617/prepare_split.py
(type copy + cohort mapping + sidecar copy, payload-identity asserts).  This version also moves reset.in_sites (the
candidate left the old key, which no type owns after the split), keeps the file formats (plan in the
compact_plan layout with only the changed blocks re-serialized; sidecar one compact line) and runs on the current
base (svcrs3 + t28 tap fix).
usage (repo root): delta_leaf40sid_1101.py PLAN_IN PLAN_OUT SIDECAR_IN SIDECAR_OUT REPORT.json"""
import copy, json, re, sys
from pathlib import Path
import compact_plan as CP  # noqa: E402  physical/die_plan/s81/compact_plan.py (script dir)

OLD = "ot_s81sl_leaf__t40__cl86ea32b3"
COHORTS = {"s_4N_L4": 9, "s_5S_L4": 10}
NEW = {p: f"{OLD}__sid{s}" for p, s in COHORTS.items()}
NOTE = ";DIE-S81-47 11-01 physical SID type event: {p} ties child ot_s81sl_vq.sid = {s} (input port, not a parameter)"


def member(text, key, indent):
    """(start, end) of the unique '<indent>"key": value' member."""
    pat = r'^' + " " * indent + re.escape(json.dumps(key)) + r': '
    ms = list(re.finditer(pat, text, re.M))
    assert len(ms) == 1, (key, len(ms))
    _, j = json.JSONDecoder().raw_decode(text, ms[0].end())
    return ms[0].start(), j


def swap(d, old, items):
    """dict d with key old replaced in place by items (list of (k, v))."""
    return {k2: v2 for k, v in d.items() for k2, v2 in (items if k == old else [(k, v)])}


def main():
    pin, pout, sin, sout, rp = sys.argv[1:6]
    text = Path(pin).read_text(); raw = json.loads(text); orig = copy.deepcopy(raw)
    stext = Path(sin).read_text(); side = json.loads(stext); sorig = copy.deepcopy(side)
    assert json.dumps(sorig, separators=(",", ":")) + "\n" == stext  # sidecar is one compact line
    PT = raw["partition_types"]; T0 = PT[OLD]
    assert {p["name"] for p in raw["partitions"] if p["type"] == OLD} == set(COHORTS)
    assert T0["clock"]["landing_contract"]["collector_tree"]["type"] == OLD and T0["module"] == OLD
    assert all(n not in PT for n in NEW.values())
    C = side["collector"]; oc = C["types"][OLD]
    assert oc["tree"]["type"] == OLD and oc["tree"] == T0["clock"]["landing_contract"]["collector_tree"]
    same_inv = set(C["types"]) == set(PT)
    site = raw["reset"]["in_sites"][OLD]

    newT, newC = {}, {}
    for part, sid in COHORTS.items():
        nt = NEW[part]
        t = copy.deepcopy(T0); t["module"] = nt; t["clock"]["landing_contract"]["collector_tree"]["type"] = nt
        t["note"] = t.get("note", "") + NOTE.format(p=part, s=sid)
        back = copy.deepcopy(t); back["module"] = OLD; back["clock"]["landing_contract"]["collector_tree"]["type"] = OLD
        back["note"] = T0.get("note", ""); assert back == T0
        tc = copy.deepcopy(oc); tc["tree"]["type"] = nt
        back = copy.deepcopy(tc); back["tree"]["type"] = OLD; assert back == oc
        assert tc["tree"] == t["clock"]["landing_contract"]["collector_tree"]
        newT[nt], newC[nt] = t, tc
    raw["partition_types"] = swap(PT, OLD, list(newT.items()))
    for p in raw["partitions"]:
        if p["name"] in NEW:
            p["type"] = NEW[p["name"]]
    raw["reset"]["in_sites"] = swap(raw["reset"]["in_sites"], OLD, [(n, list(site)) for n in NEW.values()])
    for part, nt in NEW.items():
        assert C["parts"][part]["type"] == OLD; C["parts"][part]["type"] = nt
    C["types"] = swap(C["types"], OLD, list(newC.items()))

    # everything else unchanged
    for k in set(raw) | set(orig):
        if k not in ("partition_types", "partitions", "reset"):
            assert raw[k] == orig[k], k
    rs = lambda r: {k: v for k, v in r.items() if k != "in_sites"}
    assert rs(raw["reset"]) == rs(orig["reset"])
    assert {k: v for k, v in raw["reset"]["in_sites"].items() if k not in newT} == \
        {k: v for k, v in orig["reset"]["in_sites"].items() if k != OLD}
    assert {k: v for k, v in raw["partition_types"].items() if k not in newT} == \
        {k: v for k, v in orig["partition_types"].items() if k != OLD}
    assert len(raw["partition_types"]) == len(orig["partition_types"]) + 1
    assert len(raw["partitions"]) == len(orig["partitions"])
    for p, q in zip(raw["partitions"], orig["partitions"]):
        assert p == (dict(q, type=NEW[q["name"]]) if q["name"] in NEW else q), q["name"]
    for k in set(side) | set(sorig):
        if k != "collector":
            assert side[k] == sorig[k], k
    for k in set(C) | set(sorig["collector"]):
        if k not in ("parts", "types"):
            assert C[k] == sorig["collector"][k], k
    assert {k: v for k, v in C["parts"].items() if k not in NEW} == \
        {k: v for k, v in sorig["collector"]["parts"].items() if k not in NEW}
    assert {k: v for k, v in C["types"].items() if k not in newC} == \
        {k: v for k, v in sorig["collector"]["types"].items() if k != OLD}
    assert (set(C["types"]) == set(raw["partition_types"])) == same_inv

    # plan text: re-serialize only the changed members
    a, b = member(text, OLD, 2)
    text = text[:a] + ",\n".join("  " + json.dumps(n) + ": " + CP._d(t, 2) for n, t in newT.items()) + text[b:]
    for part, nt in NEW.items():
        pat = r'("name": ' + re.escape(json.dumps(part)) + r',\s*"type": )' + re.escape(json.dumps(OLD))
        ms = list(re.finditer(pat, text)); assert len(ms) == 1, (part, len(ms))
        text = text[:ms[0].start()] + ms[0].group(1) + json.dumps(nt) + text[ms[0].end():]
    a, b = member(text, OLD, 3)
    text = text[:a] + ",\n".join("   " + json.dumps(n) + ": " + CP._d(list(site), 3) for n in NEW.values()) + text[b:]
    assert json.dumps(OLD) not in text
    assert json.loads(text) == raw and list(json.loads(text)["partition_types"]) == list(raw["partition_types"])
    Path(pout).write_text(text)
    Path(sout).write_text(json.dumps(side, separators=(",", ":")) + "\n")
    assert json.loads(Path(sout).read_text()) == side
    rep = dict(old_type=OLD, new_types={nt: dict(part=p, sid=COHORTS[p]) for p, nt in NEW.items()},
               types=[len(orig["partition_types"]), len(raw["partition_types"])],
               sidecar_types=[len(sorig["collector"]["types"]), len(C["types"])], reset_in_site=site,
               changed_keys=["partition_types", "partitions[s_4N_L4,s_5S_L4].type", "reset.in_sites",
                             "sidecar collector.parts[s_4N_L4,s_5S_L4].type", "sidecar collector.types"],
               added_ports=0, added_cycles=0, geometry_identical=True,
               credit="type copy / cohort logic from Codex coord/tmp/s81_leaf40_sid_split_1617/prepare_split.py")
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
