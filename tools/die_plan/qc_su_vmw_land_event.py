#!/usr/bin/env python3
"""QC SU VM-write landing event (DIE-QC-95 11-08): land the writes of lanes 0-3 (su_l0) and 4-7 (su_l1) on one edge.

R8 equalises per (sink, source partition) and per source pin, so su_l0's class settles on x_su_l0_ctl (18) and su_l1's on
x_su_l1_ctl (19) and one VM write port takes lanes 0-3 and 4-7 on edges 18 and 19, which vm8x w_bad_r faults (bench 64/128
data errors, vm_fault).  This adds one R8 bus group per slice {x_su_l0_ctl, x_su_l1_ctl}, so x_su_l0_ctl pads +1.  After the
event the R8 table must be re-derived from a first bind's bus_groups (tools/die_plan/r8.py pads), then strict bind.
    qc_su_vmw_land_event.py PLAN.json OUT.json   -> prints {n_groups, lanes_padded, sha256}
"""
import argparse, hashlib, json, re
from pathlib import Path

CTL = re.compile(r"sl_([EW]\d+)_su_l0__x_su_l0_ctl$")
N_SLICES = 12


def groups(lanes):
    """One R8 bus group per slice; refuses a slice set or depth order this event was not derived for."""
    slices = sorted(m[1] for k in lanes if (m := CTL.match(k)))
    if len(slices) != N_SLICES:
        raise SystemExit(f"expected {N_SLICES} slices, got {slices}")
    out = []
    for s in slices:
        x0, x1 = f"sl_{s}_su_l0__x_su_l0_ctl", f"sl_{s}_su_l1__x_su_l1_ctl"
        if x1 not in lanes:
            raise SystemExit(f"{s}: no {x1}")
        if lanes[x0]["cycles"] > lanes[x1]["cycles"]:
            raise SystemExit(f"{s}: su_l0 ctl lane slower than su_l1, event not derived for this plan")
        out.append(dict(name=f"su_vmw_ctl_{s}", kind="bus", lanes=[x0, x1], source="DIE-QC-95 11-08 VM write landing"))
    return out


def main(argv=None):
    import schema, gen
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"refusing to overwrite {a.out}")
    d = json.loads(a.plan.read_text())
    lanes = d["latency"]["lanes"]
    g = groups(lanes)
    d.setdefault("latency_groups", [])
    if any(x["name"].startswith("su_vmw_ctl_") for x in d["latency_groups"]):
        raise SystemExit("already applied")
    d["latency_groups"].extend(g)
    new = gen.latency_table(schema.Plan(d))
    changed = {k: (lanes[k], new[k]) for k in new if k in lanes and lanes[k] != new[k]}
    for k, (o, n) in changed.items():
        if not re.search(r"__x_su_l0_ctl$", k):
            raise SystemExit(f"unexpected lane change {k}: {o} -> {n}")
    d["latency"]["lanes"] = new
    out = json.dumps(d, indent=1) + "\n"
    a.out.write_text(out)
    print(json.dumps(dict(n_groups=len(g), lanes_padded=len(changed), sha256=hashlib.sha256(out.encode()).hexdigest())))


if __name__ == "__main__":
    main()
