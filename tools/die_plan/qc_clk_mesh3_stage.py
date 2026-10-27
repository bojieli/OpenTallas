#!/usr/bin/env python3
"""QC-CLK-MESH-3 S0: repeated-stage reach vs wire width (ngspice, ASAP7 BUFx24 transistor-level, per-instance DELVTRAND).

deck  OUT : one deck per (corner, width, mult, L): 9 independent 9-stage chains (chain 0 nominal, 1..8 MC: dvn/dvp
            N(0, 10 mV) per BUFx24 instance, wire N(1, 5 %) per 54-um piece) -> stage delay, far-end slew, sigma.
parse OUT : stage table + reach per (width, mult) = max L with far-end 10-90 slew <= 320 ps at TT and FF.
RC (QC-CLK-MESH-3, fd2d.py + asap7_m8m9_cal.json of CLOCK-128-R6, shield 0.04 @ 0.08 both sides): R = R6 rules R / w
(M9 2.228 ohm/um at 0.16 um, the higher of M8/M9); C = M8 over a full M7 plane (the higher of M8/M9), fF/um.
UNCHECKED vs a commercial field solver (fd2d reproduces the R6 0.16 um values to <1 %).
"""
import itertools
import json
import math
import random
import re
import sys
import zlib
from pathlib import Path

VDD = {"TT": 0.70, "FF": 0.77}
RC3 = {"4w": (2.228, 0.2465), "8w": (1.114, 0.3352), "16w": (0.557, 0.5022), "2x16w": (0.2785, 1.0044)}
WIDTHS = ["4w", "8w", "16w", "2x16w"]
MULTS = [1, 2]
LENS = [450, 900, 1350, 1800, 2400]
NCH = 5
NST = 7
SIG = dict(vt_mV=10.0, wire_rel=0.05, piece_um=54.0)


def deck(out):
    out = Path(out)
    cases = []
    for corner, w, mult, L in list(itertools.product(["TT", "FF"], WIDTHS, MULTS, LENS)) + list(itertools.product(["TT", "FF"], ["2x16w"], [3], LENS)):
        name = f"{corner}_{w}_m{mult}_L{L}"
        r, c = RC3[w]
        seg = max(15.0, L / 60.0)
        n = max(1, math.ceil(L / seg))
        dl = L / n
        rnd = random.Random(zlib.crc32(name.encode()))
        Ls = [f"* QC-CLK-MESH-3 stage {name}", f".param vdd={VDD[corner]}", ".temp %s" % ({"TT": 25.0, "FF": 0.0}[corner]),
              f".include /w/lib/{corner}/models.sp", f".include /w/lib/{corner}/cells_var.sp", "Vdd vdd 0 {vdd}", "Vss vss 0 0"]
        k = 0
        th = 300 + NST * (70 + 0.16 * L + 2.0e-5 * L * L) + 300
        for ch in range(NCH):
            Ls.append(f"Vin{ch} c{ch}s0 0 PWL(0 0 100p 0 150p {{vdd}} {th:.0f}p {{vdd}} {th + 50:.0f}p 0)")
            for s in range(NST):
                for q in range(mult):
                    dvn = rnd.gauss(0, SIG["vt_mV"] / 1e3) if ch else 0.0
                    dvp = rnd.gauss(0, SIG["vt_mV"] / 1e3) if ch else 0.0
                    Ls.append(f"Xb{ch}_{s}_{q} vss vdd c{ch}s{s} c{ch}o{s} BUFx24v dvn={dvn:.5f} dvp={dvp:.5f}")
                prev = f"c{ch}o{s}"
                npc = max(1, round(L / SIG["piece_um"]))
                fac = [rnd.gauss(1.0, SIG["wire_rel"]) if ch else 1.0 for _ in range(npc)]
                for j in range(n):
                    f = fac[min(npc - 1, int(j * dl / SIG["piece_um"]))]
                    nxt = f"c{ch}s{s + 1}" if j == n - 1 else f"c{ch}w{s}_{j}"
                    Ls.append(f"R{k} {prev} {nxt} {r * dl * f:.4f}")
                    Ls.append(f"Ca{k} {prev} 0 {c * dl / 2 * f:.5f}f")
                    Ls.append(f"Cb{k} {nxt} 0 {c * dl / 2 * f:.5f}f")
                    k += 1
                    prev = nxt
            Ls.append(f"Cl{ch} c{ch}s{NST} 0 {2.3 * mult:.2f}f")
            for s in range(2, NST + 1):
                Ls.append(f".meas tran r{ch}_{s} WHEN v(c{ch}s{s})={{vdd/2}} RISE=1")
                Ls.append(f".meas tran f{ch}_{s} WHEN v(c{ch}s{s})={{vdd/2}} FALL=1")
            for s in (4, 5):
                Ls.append(f".meas tran sr{ch}_{s} TRIG v(c{ch}s{s}) VAL={{0.1*vdd}} RISE=1 TARG v(c{ch}s{s}) VAL={{0.9*vdd}} RISE=1")
                Ls.append(f".meas tran sf{ch}_{s} TRIG v(c{ch}s{s}) VAL={{0.9*vdd}} FALL=1 TARG v(c{ch}s{s}) VAL={{0.1*vdd}} FALL=1")
                Ls.append(f".meas tran qr{ch}_{s} TRIG v(c{ch}s{s}) VAL={{0.2*vdd}} RISE=1 TARG v(c{ch}s{s}) VAL={{0.8*vdd}} RISE=1")
        tend = 2 * th
        Ls.append(".save " + " ".join(f"v(c{ch}s{s})" for ch in range(NCH) for s in range(2, NST + 1)))
        Ls += [".options method=gear reltol=1e-4", f".tran 1p {tend:.0f}p", ".control\npre_osdi /w/osdi/bsimcmg23.osdi\nrun\nquit\n.endc", ".end"]
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "deck.sp").write_text("\n".join(Ls) + "\n")
        cases.append(dict(name=name, corner=corner, w=w, mult=mult, L=L, r_ohm_um=r, c_fF_um=c))
    (out / "cases.json").write_text(json.dumps(dict(rc=RC3, sigma=SIG, cases=cases), indent=1))
    print(len(cases))


def parse(out):
    out = Path(out)
    meta = json.loads((out / "cases.json").read_text())
    rows = []
    for cs in meta["cases"]:
        f = out / cs["name"] / "sim.log"
        if not f.exists():
            continue
        v = {m.group(1): float(m.group(2)) * 1e12 for m in re.finditer(r"^(\w+)\s*=\s*([-+0-9.eE]+)", f.read_text(), re.M)}
        need = ["r0_3", "r0_6", "f0_3", "f0_6", "sr0_5", "sf0_5"] + [f"{e}{ch}_{k}" for ch in range(1, NCH) for e in "rf" for k in (3, 6)]
        if any(k not in v for k in need):
            rows.append(dict(cs, error="no meas"))
            continue
        # stage delay = (t(s6) - t(s3)) / 3, rise & fall averaged (an inverting-free buffer chain: rise stays rise)
        nom = ((v["r0_6"] - v["r0_3"]) + (v["f0_6"] - v["f0_3"])) / 6
        sl = max(v.get("sr0_5", 0), v.get("sf0_5", 0))
        sl28 = v.get("qr0_5", 0)
        # sigma of ONE stage: per chain and stage, d_s = t(s+1) - t(s), s = 3..6, rise and fall; MC chains 1..8
        ds = []
        for ch in range(1, NCH):
            for s in range(3, 6):
                for e in ("r", "f"):
                    a, b = v.get(f"{e}{ch}_{s}"), v.get(f"{e}{ch}_{s + 1}")
                    if a is not None and b is not None:
                        ds.append(b - a)
        mu = sum(ds) / len(ds)
        sd = (sum((x - mu) ** 2 for x in ds) / (len(ds) - 1)) ** 0.5
        # path sigma per stage from the 4-stage sums (includes stage-to-stage slew correlation)
        tot = [((v[f"r{ch}_6"] - v[f"r{ch}_3"]) + (v[f"f{ch}_6"] - v[f"f{ch}_3"])) / 2 for ch in range(1, NCH)]
        mt = sum(tot) / len(tot)
        sdt = (sum((x - mt) ** 2 for x in tot) / (len(tot) - 1)) ** 0.5 / 3 ** 0.5     # / sqrt(3 stages)
        rows.append(dict(cs, stage_ps=round(nom, 2), ps_per_mm=round(nom / cs["L"] * 1000, 2), slew1090_ps=round(sl, 1),
                         slew2080_ps=round(sl28, 1), sigma_stage_ps=round(sd, 3), sigma_path_per_sqrt_stage_ps=round(sdt, 3)))
    reach = {}
    for w, m in itertools.product(WIDTHS, MULTS):
        ok = [r["L"] for r in rows if r["w"] == w and r["mult"] == m and "error" not in r and r["corner"] == "TT" and
              any(q["corner"] == "FF" and q["w"] == w and q["mult"] == m and q["L"] == r["L"] and "error" not in q for q in rows) and
              all(q["slew1090_ps"] <= 320.0 for q in rows if q["w"] == w and q["mult"] == m and q["L"] == r["L"] and "error" not in q)]
        best = max(ok) if ok else None
        sel = {c: next((r for r in rows if r["w"] == w and r["mult"] == m and r["L"] == best and r["corner"] == c), None) for c in ("TT", "FF")}
        reach[f"{w}_m{m}"] = dict(reach_um=best, **{c: ({k: sel[c][k] for k in ("stage_ps", "ps_per_mm", "slew1090_ps", "sigma_stage_ps")} if sel[c] else None) for c in ("TT", "FF")})
    res = dict(schema="ot_qc_clk_mesh3_stage/1", rc=meta["rc"], sigma=meta["sigma"], slew_limit_ps="320 (10-90 far end, liberty convention)",
               rows=rows, reach=reach, checked="UNCHECKED")
    (out / "stage_table.json").write_text(json.dumps(res, indent=1))
    for k, v in reach.items():
        print(k, json.dumps(v))


if __name__ == "__main__" and sys.argv[1] in ("deck", "parse"):
    {"deck": deck, "parse": parse}[sys.argv[1]](sys.argv[2])


def slewdeck(out):
    """input-slew sensitivity of a BUFx24 stage (4W 450 um load): delay in50 -> far end 50 for input 10-90 slews."""
    out = Path(out)
    for corner in ("TT", "FF"):
        for sl in (40, 120, 200, 280, 360):
            name = f"slew_{corner}_{sl}"
            r, c = RC3["4w"]
            n = 30
            dl = 450 / n
            ramp = sl / 0.8
            Ls = [f"* slew {name}", f".param vdd={VDD[corner]}", ".temp %s" % ({"TT": 25.0, "FF": 0.0}[corner]),
                  f".include /w/lib/{corner}/models.sp", f".include /w/lib/{corner}/cells_var.sp", "Vdd vdd 0 {vdd}", "Vss vss 0 0",
                  f"Vin a 0 PWL(0 0 100p 0 {100 + ramp:.1f}p {{vdd}} 1000p {{vdd}} {1000 + ramp:.1f}p 0)",
                  "Xb vss vdd a o BUFx24v dvn=0 dvp=0"]
            prev = "o"
            for j in range(n):
                nxt = "e" if j == n - 1 else f"w{j}"
                Ls += [f"R{j} {prev} {nxt} {r * dl:.4f}", f"Ca{j} {prev} 0 {c * dl / 2:.5f}f", f"Cb{j} {nxt} 0 {c * dl / 2:.5f}f"]
                prev = nxt
            Ls += ["Xn vss vdd e z BUFx24v dvn=0 dvp=0", "Cz z 0 5f",
                   ".meas tran dr TRIG v(a) VAL={vdd/2} RISE=1 TARG v(e) VAL={vdd/2} RISE=1",
                   ".meas tran df TRIG v(a) VAL={vdd/2} FALL=1 TARG v(e) VAL={vdd/2} FALL=1",
                   ".meas tran so TRIG v(e) VAL={0.1*vdd} RISE=1 TARG v(e) VAL={0.9*vdd} RISE=1",
                   ".save v(a) v(e)", ".options method=gear reltol=1e-4", ".tran 0.5p 2000p",
                   ".control\npre_osdi /w/osdi/bsimcmg23.osdi\nrun\nquit\n.endc", ".end"]
            d = out / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "deck.sp").write_text("\n".join(Ls) + "\n")


def slewparse(out):
    res = {}
    for f in sorted(Path(out).glob("slew_*/sim.log")):
        v = {m.group(1): float(m.group(2)) * 1e12 for m in re.finditer(r"^(dr|df|so)\s*=\s*([-+0-9.eE]+)", f.read_text(), re.M)}
        _, c, sl = f.parent.name.split("_")
        res.setdefault(c, {})[int(sl)] = dict(delay_ps=round((v["dr"] + v["df"]) / 2, 2), out_slew_ps=round(v["so"], 1))
    for c, t in res.items():
        ks = sorted(t)
        t["sens_ps_per_ps"] = round((t[ks[-2]]["delay_ps"] - t[ks[1]]["delay_ps"]) / (ks[-2] - ks[1]), 4)
    (Path(out) / "slew_sens.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__" and sys.argv[1] in ("slewdeck", "slewparse"):
    {"slewdeck": slewdeck, "slewparse": slewparse}[sys.argv[1]](sys.argv[2])
