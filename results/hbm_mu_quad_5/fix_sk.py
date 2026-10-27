#!/usr/bin/env python3
"""HBM-MU-QUAD-5 delta B1 (COORD 03:02 ruling GEOM-18 (a)): tail_sink_clk div-7 GENERATED clock -> div-7 CLOCK ENABLE.
The sk cores take the die clock at their own centre entries; rest drives a registered 1-bit enable (flop -> flop data
net).  RTL + LEC: rtl/hbm_accel/cores_split/sk_en_q4 (results/hbm_mu_quad_5/sk_en).  Usage: fix_sk.py IN OUT"""
import json, sys, shutil, copy, hashlib
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out, symlinks=True)
raw = json.loads((out / "die_plan.json").read_text()); t = raw["partition_types"]["root"]
H = {h["inst"]: h for h in t["hard_cores"]}
rep = dict(tables=[], taps=[], conns=[])
NOTE = " | QUAD-5 B1: sk on the die clock at the centre entry + registered div-7 enable sk_en (RTL sk_en_q4, LEC PASS results/hbm_mu_quad_5/sk_en)"
CTR = {"sk_step0": (77.784, 120.96), "sk_steady": (77.784, 99.36), "rest": (77.784, 86.4)}


def load(f):
    d = json.loads((out / f).read_text()); return d.get("pins", d) if isinstance(d, dict) else d


done = set()
for n in range(2):
    rest, sks = H[f"u_hc_eng_tail{n}_rest"], [H[f"u_hc_eng_tail{n}_sk_step0"], H[f"u_hc_eng_tail{n}_sk_steady"]]
    # rest table (one per tail): sink_clk -> sk_en_sk (same site, now a flop output), clk -> centre entry
    ps = load(rest["pins_file"]); old = f"x_g_tail_{n}_u_t_u_tail_sink_clk"; new = f"x_g_tail_{n}_u_t_u_tail_sk_en_sk"
    for p in ps:
        if p.get("name") == old:
            p["name"] = new
        elif p.get("name") == "clk":
            p.update(layer="M5", x=CTR["rest"][0], y=CTR["rest"][1])
    (out / rest["pins_file"]).write_text(json.dumps(ps) + "\n"); rep["tables"].append(rest["pins_file"])
    rest["note"] = rest.get("note", "") + NOTE
    for sk in sks:
        kind = "sk_step0" if "step0" in sk["inst"] else "sk_steady"
        sk["note"] = sk.get("note", "") + NOTE
        if sk["pins_file"] not in done:     # shared canonical table of tail0/tail1: edit once
            ps = load(sk["pins_file"]); w, h = sk["outline_um"]
            for p in ps:
                if p.get("name") == "clk":
                    p.update(layer="M5", x=CTR[kind][0], y=CTR[kind][1])
            # sk_en_i on the W face (toward rest for tail0; core_faces re-check adds a superset copy if needed)
            used = {round((p["y"] - 0.024) / 0.048) for p in ps if p["x"] < 1}
            k = round((h / 2 - 0.024) / 0.048)
            while k in used:
                k += 1
            ps.append(dict(name="sk_en_i", layer="M4", x=0.019, y=round(0.024 + k * 0.048, 6)))
            (out / sk["pins_file"]).write_text(json.dumps(ps) + "\n"); done.add(sk["pins_file"]); rep["tables"].append(sk["pins_file"])
# taps: one centre-entry tap per sk core (cloned from the rest tap)
taps = t["clock"]["taps"]
for n in range(2):
    base = next(tp for tp in taps if tp["name"] == f"u_hc_eng_tail{n}_rest")
    for kind in ("sk_step0", "sk_steady"):
        nm = f"u_hc_eng_tail{n}_{kind}"
        if any(tp["name"] == nm for tp in taps):
            continue
        h = H[nm]; q = copy.deepcopy(base); q["name"] = nm
        q["xy"] = [round(h["origin_um"][0] + 77.76, 4), round(h["origin_um"][1] + CTR[kind][1], 4)]
        q["budget_owner"] = h["module"]
        q["note"] = "QUAD-5 B1: sk core on the die clock at its plan centre entry (12.8a); replaces the exported div-7 generated clock"
        taps.append(q); rep["taps"].append((nm, q["xy"]))
(out / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
# entries
E = json.loads((out / "clock_entries.json").read_text())
for n in range(2):
    for kind, y in (("sk_step0", 120.96), ("sk_steady", 99.36)):
        e = E["root"][f"u_hc_eng_tail{n}_{kind}"]; e["xy_um"] = [77.76, y]; e["island_um"] = [73.44, y - 4.32, 82.08, y + 4.32]; e["port"] = "clk"
(out / "clock_entries.json").write_text(json.dumps(E, indent=1) + "\n")
(out / "generated_clocks.json").write_text("[]\n")
# core_conns
C = json.loads((out / "core_conns.json").read_text()); r = C["root"]
for n in range(2):
    rn = f"u_hc_eng_tail{n}_rest"; old = f"x_g_tail_{n}_u_t_u_tail_sink_clk"; new = f"x_g_tail_{n}_u_t_u_tail_sk_en_sk"
    if old in r[rn]:
        r[rn][new] = r[rn].pop(old)
    for kind in ("sk_step0", "sk_steady"):
        sk = f"u_hc_eng_tail{n}_{kind}"
        r[sk]["clk"] = [f"tap:{sk}"]; r[sk]["sk_en_i"] = [f"core:{rn}"]
    rep["conns"].append(rn)
(out / "core_conns.json").write_text(json.dumps(C, indent=1) + "\n")
print(json.dumps(rep)); print("sha", hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()[:12])
