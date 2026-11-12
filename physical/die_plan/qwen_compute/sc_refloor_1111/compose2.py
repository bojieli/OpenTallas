"""SC-REFLOOR-1: compose a plan from BASE + per-type sources; DST<-SRC_TYPE@VARIANT copies the variant type's ft_slots and
landing band rects (sibling types share ft_slots, so a sibling takes its twin's form).  Only ft_slots and
clock.landing_contract band rect_um may change.  usage: compose2.py BASE OUT DST=SRCTYPE@VARIANT.json ..."""
import copy, json, sys
B = json.load(open(sys.argv[1])); T = B["partition_types"]; cache = {}
for a in sys.argv[3:]:
    dst, rhs = a.split("="); st, vp = rhs.split("@")
    V = cache.setdefault(vp, json.load(open(vp)))["partition_types"][st]
    d = T[dst]
    assert [s["name"] for s in d["ft_slots"]] == [s["name"] for s in V["ft_slots"]], dst
    for s0, s1 in zip(d["ft_slots"], V["ft_slots"]):
        for k in set(s0) | set(s1):
            if k not in ("regs_um", "bit_sites_um", "bit_site_cell_um", "stations"):
                assert s0.get(k) == s1.get(k), (dst, s0["name"], k)
    d["ft_slots"] = copy.deepcopy(V["ft_slots"])
    db, vb = d["clock"]["landing_contract"]["bands"], V["clock"]["landing_contract"]["bands"]
    n = 0
    for bn, bd in db.items():
        if bn in vb and vb[bn].get("rect_um") != bd.get("rect_um"):
            bd["rect_um"] = list(vb[bn]["rect_um"]); n += 1
    print(dst, "<-", st, vp.rsplit("/", 1)[-1], "bands moved", n,
          "stations", {s["name"]: s["stations"] for s in d["ft_slots"]} if "c1" in vp else "")
json.dump(B, open(sys.argv[2], "w"))
