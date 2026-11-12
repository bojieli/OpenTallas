#!/usr/bin/env python3
"""HBM-VSN-XTAP-2 11-12 generalised form A' plan delta against d53b (DIE-HBM-100 / COORD NW_iorly ruling).
mk_d12.py D53B_PLAN T12_BASE_PLAN D9_DELTA D11_DELTA PAPER_TSV OUT_DELTA OUT_PLAN_DIR
ops: del clock.ft_hop_lockup.xtap_flop; types = existing U every type with a cross-port station hop;
tap / latch_frac = vsN4 measured map of d11 + every plan-paper hop whose best form differs from the generator default
(dtap, f 0.5); revert the d9 xtap latency rows (d53b value - (d9 new - t12 base)); note."""
import copy, csv, hashlib, json, sys
from pathlib import Path

d53p, t12p, d9p, d11p, paperp, outd, outdir = sys.argv[1:8]
base = json.loads(Path(d53p).read_text())
t12 = json.loads(Path(t12p).read_text())
d9 = json.loads(Path(d9p).read_text())
d11 = json.loads(Path(d11p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(o, path):
    for k in path:
        o = o[k]
    return o


lk = base["clock"]["ft_hop_lockup"]
assert "xtap_flop" in lk and "tap" not in lk and "latch_frac" not in lk
d11ops = {tuple(p[-1:]): v for p, op, v in d11["files"]["die_plan.json"]["ops"] if p[:2] == ["clock", "ft_hop_lockup"]}
tap = copy.deepcopy(d11ops[("tap",)])
frac = copy.deepcopy(d11ops[("latch_frac",)])
rows = list(csv.DictReader(open(paperp), delimiter="\t"))
xtypes = sorted({r["type"] for r in rows})
bad = [r for r in rows if r["verdict"] in ("FAIL", "UNKNOWN_SITES") and r["basis"] == "plan"]
nkey = 0
for r in rows:
    if r["basis"] != "plan" or r["tap"] == "?":
        continue
    t, s, k = r["type"], r["slot"], r["k"]
    if r["tap"] != r["dtap"]:
        # "launch" over a die-default capture regex (u_fl_L201x) needs gen_phys 11-12 (claude/hbm-xtap-all-1112)
        tap.setdefault(t, {}).setdefault(s, {})[k] = "launch" if r["tap"] == "L" else "capture"; nkey += 1
    if r["f"] != "0.50":
        frac.setdefault(t, {}).setdefault(s, {})[k] = float(r["f"]); nkey += 1
types = sorted(set(lk["types"]) | set(xtypes))
ops = [[["clock", "ft_hop_lockup", "xtap_flop"], "del", None],
       [["clock", "ft_hop_lockup", "types"], "set", types],
       [["clock", "ft_hop_lockup", "tap"], "set", tap],
       [["clock", "ft_hop_lockup", "latch_frac"], "set", frac]]
note = ("HBM-VSN-XTAP-2 11-12 generalised form A' on d53b (COORD NW_iorly ruling via DIE-HBM-100; criterion by intent: "
        "every station hop whose two stations land on DIFFERENT kit tap ports carries the plan tap window W, early -W / "
        "late 0 on every port, no CRPR across ports).  Every type with such a hop is on ft_hop_lockup (ot_dp_lk latch on "
        "every station hop, 0 cycles); xtap_flop REMOVED (full-cycle hop flop cannot close FF hold; its +1 latency rows "
        "reverted).  tap / latch_frac: vsN4 from the routed per-pair check (d11); every other cross-port hop latch_frac "
        "0.95 on its launch tap (vsN1/vsN2 L201 hops: tap launch over the die-default capture regex, gen_phys 11-12): the "
        "cross-port leg becomes the short latch -> capture leg, ~206 ps (W 160) / ~248 ps (W 120) of real tap skew "
        "tolerated either sign on paper; on the routed vsN4 STA launch+0.95 passes all 36 cross-tap hops (min S +6.0, "
        "H +39.2 ps) where the midpoint fails 11.  Physical only; DO_NOT_COUNT.")
ops.append([["clock", "ft_hop_lockup", "note"], "set", note])
nrow = 0
for f, v in d9["files"].items():
    for path, op, val in v["ops"]:
        if path[0] != "latency":
            continue
        cur, b12 = get(base, path), get(t12, path)
        want = cur - (val - b12)
        if want != cur:
            ops.append([path, "set", want]); nrow += 1
delta = {"name": "d12_formAp_all_types_1112", "source": "HBM-VSN-XTAP-2 (DIE-HBM-100 11-12, COORD NW_iorly ruling)",
         "base": {"die_plan.json": sha(d53p)}, "files": {"die_plan.json": {"kind": "json", "ops": ops}}}
Path(outd).write_text(json.dumps(delta, indent=1) + "\n")
new = copy.deepcopy(base)
for path, op, val in ops:
    o = get(new, path[:-1])
    if op == "del":
        del o[path[-1]]
    else:
        o[path[-1]] = val
od = Path(outdir); od.mkdir(parents=True, exist_ok=True)
(od / "die_plan.json").write_text(json.dumps(new, indent=1) + "\n")
print(f"types {len(lk['types'])} -> {len(types)} (+{len(set(types) - set(lk['types']))}: "
      f"{','.join(sorted(set(types) - set(lk['types'])))})")
print(f"ops {len(ops)} latency rows {nrow} plan-paper keys {nkey} tap entries "
      f"{sum(len(m) for t in tap.values() for m in t.values())} frac entries "
      f"{sum(len(m) for t in frac.values() for m in t.values())} paper FAIL/UNKNOWN {len(bad)}")
print("delta", sha(outd)[:12], "plan", sha(od / "die_plan.json")[:12])
