#!/usr/bin/env python3
"""FTRES-FIX 11-10 addendum (COORD fail_watch q_spu1__physical_v1 GRT-0183 on u_bound.u_ft_L40x1_o_4): ftres rule
'cut the die reservation to the measured need' on the two transit-only q_spu1 types (no hard cores, so not in the
over-core table). Their NS die band [276.48,786.24] (L2 N->W 2999 b die bundle) reserves M7 1.0 / M5 0.5 while own
S/N slot windows (L40x1, L87x1, L722x3, L723x3, L49x1, L1273x1, L507x...) sit inside it; o_4 enters at S x~769 on M7/M5
inside the band and is boxed in. New die_share (both layers) = bundle bits / band tracks (M5+M7) at 0.6 use, rounded up
to 0.05. Span, layers, stations and windows unchanged. usage: mk_plan_spu1.py BASE OUT_DIR"""
import hashlib, json, math, os, re, sys
BASE, OUT = sys.argv[1:3]
EXP = "29333b2b19c99251"
raw = open(BASE, "rb").read(); sha = hashlib.sha256(raw).hexdigest()
assert sha.startswith(EXP), sha
P = json.loads(raw); T = P["partition_types"]
PITCH = {"M4": .048, "M5": .048, "M6": .064, "M7": .064}; USE = 0.6
led = []
for tn in ("q_spu1", "q_spu1__physical_v1"):
    t = T[tn]; assert not t.get("hard_cores"), tn
    grp = {}
    for i, b in enumerate(t["die_ft_bands"]):
        grp.setdefault((b["dir"], tuple(b["span_um"])), []).append(i)
    for (d, sp), idx in grp.items():
        bits = [int(m) for i in idx for m in re.findall(r"(\d+) b bundle", t["die_ft_bands"][i].get("note", ""))]
        if not bits: continue
        nb = max(bits); wd = sp[1] - sp[0]
        tracks = sum(wd / PITCH[L] for i in idx for L in t["die_ft_bands"][i]["layers"])
        ds = round(min(1.0, math.ceil(nb / (USE * tracks) * 20 - 1e-9) / 20), 2)
        for i in idx:
            b = t["die_ft_bands"][i]; old = b.get("die_share", 1.0)
            b["die_share"] = ds
            b["note"] = b.get("note", "") + (f" | FTRES-FIX 11-10 (q_spu1 GRT-0183 L40x1_o_4): die_share {old:g} -> {ds:g}"
                                              f" = {nb} b / {tracks:.0f} band tracks (M5+M7) at {USE} use")
            led.append(dict(type=tn, band=i, dir=d, span_um=list(sp), layers=b["layers"], bits=nb,
                            tracks=round(tracks), old_die_share=old, new_die_share=ds))
os.makedirs(OUT, exist_ok=True)
body = json.dumps(P, indent=1, sort_keys=False) + "\n"
open(os.path.join(OUT, "die_plan.json"), "w").write(body)
nsha = hashlib.sha256(body.encode()).hexdigest()
json.dump(dict(event="ftres-fix-1110-spu1", base_plan=BASE, base_sha256=sha, out_sha256=nsha, ledger=led),
          open(os.path.join(OUT, "spu1_event.json"), "w"), indent=1)
print(nsha); print(json.dumps(led, indent=0))
