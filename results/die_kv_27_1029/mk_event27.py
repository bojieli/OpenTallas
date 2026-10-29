#!/usr/bin/env python3
"""DIE-KV-27 plan event27 = event26a + ASK-C gate-failure pin/port delta (COORD 06:14 YES; KV-007/KV-008 GEOM FAIL fixes).
No die-tree change: the new ahub clock entries are hub_C PARTITION tree leaves (core_taps internal), die tree c unchanged.
 (1) qkd_kvs_pc (R0 + fMX pin files): pc__land_es[287:0] moves S face -> W face directly below the chain block
     (pc__fi/fo/ki/ko/x__est stay at y 343.75..360.6). W face re-spread at 4 M4 tracks (0.192 um), land_es y 288..343,
     i_prev/o_next/o_prev compressed into y 2.5..267. Fixes KV-KITS-20 root cause (a): chain c[F_V] (W top) -> land_es
     (S face x270-331) one-edge path >= 608 um. 0 cycles. h_head_p variant unchanged (its land_es is already on the W face).
 (2) qkd_ahub: ck widened 3 -> 7: ck[3]=S-W, ck[4]=S-E, ck[5]=E-S, ck[6]=E-N interior M5 entries (KV-KITS-20 5-entry
     estimate, reach <= ~200 um); hub_C partition taps ahub.ck[3..6] at common latency 250 TT / 202.5 FF (12.3).
     ck[0] keeps the centre cluster; ck[1]/ck[2] (zh macro clocks) unchanged. RTL: qkd_ahub port ck[2:0] -> ck[6:0],
     same clock domain, sink split by region = KV-KITS-21 (kit/RTL owner); strict bind needs that RTL.
usage: mk_event27.py PLAN_E26A PINS_DIR OUT_DIR"""
import json, sys, hashlib, copy, re
from pathlib import Path
src, pdir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
raw = src.read_bytes(); P = json.loads(raw)
H, TRK, OFF, PITCH = 362.88, 0.048, 0.024, 0.192
snap = lambda y: round(OFF + TRK * round((y - OFF) / TRK), 3)

def repack_kvspc(doc):
    pins = doc["pins"]; W = [p for p in pins if p["x"] < 0.2]
    fam = lambda p: re.sub(r"\[.*", "", p["name"])
    top = [p for p in W if p["y"] >= 343.7]                     # fi/fo/ki/ko/x__est: unchanged
    low = sorted([p for p in W if p["y"] < 343.7], key=lambda p: p["y"])   # i_prev, o_next, o_prev (order kept)
    les = sorted([p for p in pins if fam(p) == "pc__land_es"], key=lambda p: int(p["name"].split("[")[1][:-1]))
    assert len(les) == 288 and len(top) == 69 and len(low) == 1378, (len(les), len(top), len(low))
    y = snap(343.75 - PITCH)
    for p in reversed(les):                                      # bit 287 highest... bit 0 lowest
        p.update(x=0.096, y=y, layer="M4"); y = snap(y - PITCH)
    les_lo = les[0]["y"]
    y0 = snap(2.52); assert y0 + PITCH * (len(low) - 1) < les_lo - PITCH, "W face overflow"
    for i, p in enumerate(low): p["y"] = snap(y0 + PITCH * i)
    ys = sorted(p["y"] for p in pins if p["x"] < 0.2)
    assert all(b - a >= PITCH - 1e-6 for a, b in zip(ys, ys[1:])), "W pin spacing < 4 tracks"
    doc["faces"]["W"]["pins"] += 288; doc["faces"]["S"]["pins"] -= 288
    doc["source"] += " | DIE-KV-27 event27 (ASK-C, KV-008 root cause a): pc__land_es S->W face below the chain block, W re-spread 0.192"
    return doc

stats = {}
for fn, mirror in (("qkd_kvs_pc_pins_r25.json", False), ("qkd_kvs_pc_pins_fMX_r25.json", True)):
    d = json.load(open(pdir / "qkd_kvs_pc_pins_r25.json"))
    d = repack_kvspc(d)
    if mirror:
        for p in d["pins"]: p["y"] = round(H - p["y"], 3)
        d["frame"] = json.load(open(pdir / fn))["frame"]
        if d.get("island_ft"): d["island_ft"] = json.load(open(pdir / fn))["island_ft"]
    o = fn.replace("_r25.json", "_r27.json"); json.dump(d, open(out / o, "w"), indent=1); stats[o] = len(d["pins"])

A = json.load(open(pdir / "qkd_ahub_pins_r26q5.json"))
NEW = {3: (150.0, 50.0, "S-W"), 4: (450.0, 50.0, "S-E"), 5: (580.0, 110.0, "E-S"), 6: (580.0, 330.0, "E-N")}
for i, (x, y, tag) in NEW.items():
    A["pins"].append(dict(name=f"ck[{i}]", layer="M5", x=x, y=y, note=f"DIE-KV-27 event27 ASK-C: {tag} clock entry (KV-007), interior; kit may slide <=20 um off macros"))
A["source"] += " | DIE-KV-27 event27 (ASK-C, KV-007): ck[3..6] S-W/S-E/E-S/E-N interior clock entries"
json.dump(A, open(out / "qkd_ahub_pins_r27.json", "w"), indent=1)

repoint = 0
for tn, t in P["partition_types"].items():
    for h in t.get("hard_cores", []):
        f = h.get("pins_file", "")
        for a, b in (("qkd_kvs_pc_pins_r25.json", "qkd_kvs_pc_pins_r27.json"), ("qkd_kvs_pc_pins_fMX_r25.json", "qkd_kvs_pc_pins_fMX_r27.json"),
                     ("qkd_ahub_pins_r26q5.json", "qkd_ahub_pins_r27.json")):
            if f.endswith("/" + a):
                h["pins_file"] = str(out / b); h["note"] = h.get("note", "") + " | DIE-KV-27 event27 pins " + b; repoint += 1
hc = P["partition_types"]["kv3_hub_C"]; ah = [h for h in hc["hard_cores"] if h["inst"] == "ahub"][0]
ox, oy = ah["origin_um"]; assert ah["orient"] == "R0"
for i, (x, y, tag) in NEW.items():
    hc["clock"]["taps"].append(dict(name=f"ahub.ck[{i}]", kind="core", xy=[round(ox + x, 3), round(oy + y, 3)], insertion_ps=250.0,
        insertion_ff_ps=202.5, budget_owner="qkd_ahub", note=f"DIE-KV-27 event27 ASK-C (KV-007): {tag} ahub clock entry; hub_C partition tree leaf, common latency 12.3 (core_taps internal)"))
P["note"] = P.get("note", "") + " | DIE-KV-27 event27: ASK-C gate-fix pin/port delta (kvs_pc land_es W face; ahub ck[3..6] + hub_C taps)"
json.dump(P, open(out / "plan_e27.json", "w"), indent=1)
json.dump(dict(schema="kv_event27/1", src=str(src), src_sha256=hashlib.sha256(raw).hexdigest(), pins_files=stats, repointed_hard_cores=repoint,
               ahub_new_ports={f"ck[{i}]": dict(core_xy_um=[x, y], hub_C_xy_um=[round(ox + x, 3), round(oy + y, 3)], entry=tag) for i, (x, y, tag) in NEW.items()},
               rtl_delta="qkd_ahub: ck[2:0] -> ck[6:0] (same clock), sinks by region: S band x<300 -> ck[3], S band x>=300 -> ck[4], E column y<220 -> ck[5], y>=220 -> ck[6], centre -> ck[0]; ck[1]/ck[2] unchanged",
               die_tree="unchanged (tree c, 1920 taps): new entries are hub_C partition-internal leaves"), open(out / "event27.json", "w"), indent=1)
print("repointed", repoint, stats)
