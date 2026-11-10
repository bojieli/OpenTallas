#!/usr/bin/env python3
"""S81 svc_rs v5: ONE outline per provider box master (S81-SVCRS-3, 11-10).

v5 gives each provider box module one LEF path but 2-3 outlines across its slots (svc_hi 259.2 bands, svc_lo
276.48 / 285.12 bands, and different widths per side).  A hard macro has one outline, so per physical master
(TRX per XOFF master) the outline becomes (min width, min height) over all its slots in the 14 svc_rs types; the
origin is unchanged (the box sits at the slot's lower-left corner inside its old slot, so no new overlap can appear).
Fill is re-computed with the v5 measured box area and the event's 4.32 halo.  Asserts one outline per master.

usage: svc_v5_one_outline_1110.py V5_PLAN(.json|.gz) V5_EVENT.json OUT_PLAN.json OUT_TABLE.json
"""
import gzip, json, sys

HALO = 4.32
PREFIX = "physical/die_plan/s81/cores/svc/prov_1109/"


def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))


def master(h):
    return h.get("physical_master", h["module"])


def main(plan_p, event_p, out_p, table_p):
    P, E = load(plan_p), load(event_p)
    names = sorted(n for n in P["partition_types"] if "svc_rs" in n)
    assert len(names) == 14
    boxes = [h for n in names for h in P["partition_types"][n]["hard_cores"] if h["lef"].startswith(PREFIX)]
    dims = {}
    for h in boxes:
        dims.setdefault(master(h), set()).add(tuple(h["outline_um"]))
    one = {m: [min(w for w, _ in s), min(hh for _, hh in s)] for m, s in dims.items()}
    area = {}
    for n in names:
        for b in E["types"][n]["boxes"]:
            area.setdefault(b.get("physical_master", b["module"]), set()).add(b["area_um2"])
    for h in boxes:
        h["outline_um"] = list(one[master(h)])
    for n in names:
        for h in P["partition_types"][n]["hard_cores"]:
            if h["lef"].startswith(PREFIX):
                h["note"] = h["note"] + f" | S81-SVCRS-3 11-10 one outline per master: {one[master(h)][0]} x {one[master(h)][1]} (origin unchanged)"
    after = {}
    for h in boxes:
        after.setdefault(master(h), set()).add(tuple(h["outline_um"]))
    assert all(len(s) == 1 for s in after.values()), after
    table = {}
    for m, (w, hh) in sorted(one.items()):
        a = max(area[m])
        table[m] = dict(outline_um=[w, hh], slots_before=sorted(map(list, dims[m])), instances=sum(1 for h in boxes if master(h) == m),
                        area_um2=a, fill=round(a / ((w - 2 * HALO) * (hh - 2 * HALO)), 3))
    open(out_p, "w").write(json.dumps(P, indent=1) + "\n")
    json.dump(table, open(table_p, "w"), indent=1)
    for m, r in table.items():
        print(m, r["outline_um"], "fill", r["fill"], "x", r["instances"])


if __name__ == "__main__":
    main(*sys.argv[1:5])
