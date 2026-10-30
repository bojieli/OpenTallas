#!/usr/bin/env python3
"""HBM-CORES-KITS-24/OPSTORE-A: net-identity check of the 4 split_bitmap UNPROVEN opstore_a buses.
Plan bit identity = the cut record split/wip_unverified/<piece>.map.json (plan bus bit i -> master net name, convention
of the HBM-P5 netcut). Each name is resolved in the elaborated master (split3_master_elab.ys) to its sigbit; the
candidate RTL bit (split_bitmap slices) must carry the SAME sigbit (through the rest_wrap u_x connections).
Constant plan bits (0/1) must map to RTL bits whose master net is the same constant."""
import json, re, sys
sys.path.insert(0, sys.argv[1])
import split_bitmap as S
mj = json.load(open(sys.argv[2])); wip = json.load(open(sys.argv[3]))["buses"]; bm = json.load(open(sys.argv[4]))
rest = open(sys.argv[5]).read(); rtop = sys.argv[6]
names = S.master_index(mj, "ot_hgi_sfu_core_split3")
byclean = {}
for n in names: byclean.setdefault(S.clean(n), []).append(n)
ports, rtl2h = S.rest_ports(rest, rtop)
def master_bit(h, i):
    rec = names.get(h)
    if rec is None:
        c = byclean.get(S.clean(h), []); rec = names[c[0]] if len(c) == 1 else None
    return S.bit_of(rec, i) if rec else None
def name_bit(nm):
    if nm in ("0", "1", "x"): return nm
    m = re.match(r"^(.*)\[(\d+)\]$", nm)
    h, i = (m.group(1), int(m.group(2))) if m else (nm, 0)
    if h not in names:
        c = byclean.get(S.clean(h), [])
        if len(c) != 1: return None
    return master_bit(h, i)
out = {}
for bus in sys.argv[7].split(","):
    sl = bm["slices"][bus]; plan = wip[bus]; ok = bad = unres = 0; ex = []
    for p, k, pb, n in sl:
        for t in range(n):
            want = name_bit(plan[pb + t])
            h = rtl2h.get((p, k + t)); got = master_bit(*h) if h else None
            if want is None or got is None: unres += 1; ex.append((bus, pb + t, plan[pb + t], p, k + t, h, "UNRESOLVED")); continue
            if want == got: ok += 1
            else: bad += 1; ex.append((bus, pb + t, plan[pb + t], want, p, k + t, h, got))
    out[bus] = dict(width=len(plan), same_net=ok, differ=bad, unresolved=unres, verdict="PROVED" if ok == len(plan) else "NOT_PROVED", examples=ex[:6])
    print(bus, out[bus]["verdict"], ok, "/", len(plan), "differ", bad, "unres", unres, ex[:3])
json.dump(out, open(sys.argv[8], "w"), indent=1, default=str)
