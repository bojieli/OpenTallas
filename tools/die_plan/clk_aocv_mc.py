#!/usr/bin/env python3
"""Monte Carlo of ASAP7 clock-buffer chains for the CLK-AOCV depth table (METHODOLOGY 12.4a b1).

The ASAP7 PDK (asap7_pdk_r1p7 models/hspice 7nm_{TT,SS,FF}.pm, BSIM-CMG level 72) ships global corners only: no
mismatch / statistical blocks; ASAP7 authors (Clark et al., MSE 2017) state "variation modeling is not directly
supported by the ASAP7 PDK" and add mismatch from an assumed Pelgrom A_VT = 1.2 mV.um (Intel 14 nm, Giles et al.,
VLSI 2015: 1.07 n / 1.23 p).  We do the same: every transistor of every MC buffer gets an independent BSIM-CMG 111
instance parameter DELVTRAND ~ N(0, A_VT / sqrt(nfin * Weff_fin * L)), Weff_fin = 2 HFIN + TFIN of the ASAP7 card.

    clk_aocv_mc.py gen  --lib LIBDIR --osdi OSDI --out DECKDIR --chain A|B --corner TT|FF --samples N --seed S
    clk_aocv_mc.py parse DECKDIR... --out mc.json

Chain A (die tree stage): BUFx24 -> 450 um clock wire (10 pi segments, NDR M8/M9) -> next BUFx24.
Chain B (core tree stage): BUFx8 -> 40 um M5 wire -> next BUFx8 + 3 nominal BUFx8 sibling loads (fanout 4).
Sample 0 of every deck set is nominal (all DELVTRAND = 0).  Rising input edge (non-inverting buffers: rise->rise).
Per stage i the deck measures the 50 % crossing at the cell input n<i> and output o<i>.
"""
import argparse
import json
import math
import random
import re
import sys
from pathlib import Path

DEPTH = 4                  # simulated chain length (minimum component); depth 1..80 is composed analytically
AVT_MV_UM = 1.2
HFIN_NM, TFIN_NM, L_NM = 32.0, 6.5, 20.0          # ASAP7 card hfin=3.2e-8, tfin=6.5e-9; instance L=2e-08
CORNER = {"TT": dict(vdd=0.70, temp=25), "FF": dict(vdd=0.77, temp=0)}
CHAIN = {
    "A": dict(cell="BUFx24_ASAP7_75t_R", wire_um=450.0, r_ohm_um=4.45, c_ff_um=0.11, nseg=10, sib=0,
              note="die tree stage: BUFx24 + 450 um NDR M8/M9 (R = M9 8.9 ohm/um at 2x width, C 0.11 fF/um)"),
    "B": dict(cell="BUFx8_ASAP7_75t_R", wire_um=40.0, r_ohm_um=19.0, c_ff_um=0.164, nseg=4, sib=3,
              note="core tree stage: BUFx8 + 40 um M5 (setRC 19 ohm/um, 0.164 fF/um) + 3 sibling BUFx8 loads"),
}


def sigma_vt_v(nfin):
    a_um2 = nfin * (2 * HFIN_NM + TFIN_NM) * 1e-3 * L_NM * 1e-3
    return AVT_MV_UM / math.sqrt(a_um2) * 1e-3


def subckt(cells_sp, name):
    txt = Path(cells_sp).read_text().splitlines()
    out, on = [], False
    for ln in txt:
        if ln.lower().startswith(".subckt") and ln.split()[1] == name:
            on = True
        if on:
            out.append(ln)
            if ln.lower().startswith(".ends"):
                break
    if not out:
        raise SystemExit(f"{name} not in {cells_sp}")
    return out


def mc_subckt(lines, new):
    """parameterised copy: every OSDI device N.. gets delvtrand={dk}; returns (text, [nfin per device])."""
    body, nf, k = [], [], 0
    for ln in lines:
        if ln.lower().startswith(".subckt"):
            f = ln.split()
            continue
        if ln[:1] == "N":
            m = re.search(r"nfin=(\d+)", ln)
            nf.append(int(m.group(1)))
            ln = f"{ln} delvtrand={{d{k}}}"
            k += 1
        body.append(ln)
    head = f".subckt {new} {' '.join(f[2:])} " + " ".join(f"d{i}=0" for i in range(k))
    return "\n".join([head] + body[:-1] + [".ends"]), nf


def gen(a):
    global DEPTH
    DEPTH = a.depth
    ch, co = CHAIN[a.chain], CORNER[a.corner]
    lib = Path(a.lib) / a.corner
    sc, nf = mc_subckt(subckt(lib / "cells.sp", ch["cell"]), "MCBUF")
    sig = [sigma_vt_v(n) for n in nf]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    rs = ch["r_ohm_um"] * ch["wire_um"] / ch["nseg"]
    cs = ch["c_ff_um"] * ch["wire_um"] / ch["nseg"]
    vdd = co["vdd"]
    meta = dict(chain=a.chain, corner=a.corner, cell=ch["cell"], depth=DEPTH, samples=a.samples, seed=a.seed,
                avt_mv_um=AVT_MV_UM, weff_fin_nm=2 * HFIN_NM + TFIN_NM, l_nm=L_NM,
                sigma_vt_mv={str(n): round(sigma_vt_v(n) * 1e3, 3) for n in sorted(set(nf))}, chain_def=ch,
                corner_def=co, devices_per_cell=len(nf))
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    for s in range(a.samples):
        L = [f"* CLK-AOCV MC chain {a.chain} {a.corner} sample {s}", ".control", f"pre_osdi {a.osdi}",
             "set noaskquit", "run", f"wrdata /w/run/{out.name}/s{s:04d}.dat " +
             " ".join(f"v(n{i}) v(o{i})" for i in range(1, DEPTH + 1)) + f" v(n{DEPTH + 1})", "quit", ".endc",
             ".options klu", ".save " + " ".join(f"v(n{i}) v(o{i})" for i in range(1, DEPTH + 1)) + f" v(n{DEPTH + 1})",
             f".temp {co['temp']}", f".include {a.libw}/{a.corner}/models.sp",
             f".include {a.libw}/{a.corner}/cells.sp", sc,
             f"Vdd vdd 0 {vdd}", "Vss vss 0 0", f"Vin in 0 PWL(0 0 100p 0 140p {vdd})",
             # two nominal pre-drivers give a realistic input slew
             f"Xp1 vss vdd in p1 {ch['cell']}", f"Xp2 vss vdd p1 n1 {ch['cell']}"]
        for i in range(1, DEPTH + 1):
            d = [0.0] * len(nf) if s == 0 else [rng.gauss(0.0, sg) for sg in sig]
            L.append(f"X{i} vss vdd n{i} o{i} MCBUF " + " ".join(f"d{k}={v:.6e}" for k, v in enumerate(d)))
            prev = f"o{i}"
            for j in range(ch["nseg"]):
                nx = f"w{i}_{j}" if j < ch["nseg"] - 1 else f"n{i + 1}"
                L.append(f"Cw{i}_{j}a {prev} 0 {cs / 2:.4f}f")
                L.append(f"Rw{i}_{j} {prev} {nx} {rs:.3f}")
                L.append(f"Cw{i}_{j}b {nx} 0 {cs / 2:.4f}f")
                prev = nx
            for k in range(ch["sib"]):
                L.append(f"Xs{i}_{k} vss vdd n{i + 1} sib{i}_{k} {ch['cell']}")
        L.append(f"Xend vss vdd n{DEPTH + 1} oend {ch['cell']}")
        L.append(f".tran 1p {140 + 250 + DEPTH * (110 if a.chain == 'A' else 45) + 100}p 0 1p")
        L.append(".end")
        (out / f"s{s:04d}.sp").write_text("\n".join(L) + "\n")
    print(out, a.samples, "decks", len(nf), "devices/cell", meta["sigma_vt_mv"])


def crossings(path, vh):
    """wrdata: pairs of (time, value) columns per vector -> first rising 50 % crossing per vector."""
    rows = [list(map(float, ln.split())) for ln in Path(path).read_text().splitlines() if ln.strip()]
    nv = len(rows[0]) // 2
    res = []
    for v in range(nv):
        t_prev = x_prev = None
        hit = None
        for r in rows:
            t, x = r[2 * v], r[2 * v + 1]
            if x_prev is not None and x_prev < vh <= x:
                hit = t_prev + (vh - x_prev) * (t - t_prev) / (x - x_prev)
                break
            t_prev, x_prev = t, x
        res.append(hit)
    return res


def parse(a):
    global DEPTH
    out = {}
    for dd in a.decks:
        dd = Path(dd)
        meta = json.loads((dd / "meta.json").read_text())
        vh = meta["corner_def"]["vdd"] / 2
        DEPTH = meta["depth"]
        S = []
        for f in sorted(dd.glob("s*.dat")):
            c = crossings(f, vh)
            if any(x is None for x in c):
                continue
            n, o = c[0:2 * DEPTH:2] + [c[2 * DEPTH]], c[1:2 * DEPTH:2]
            S.append(dict(s=int(f.stem[1:]), cell=[(o[i] - n[i]) * 1e12 for i in range(DEPTH)],
                          stage=[(n[i + 1] - n[i]) * 1e12 for i in range(DEPTH)]))
        out[f"{meta['chain']}_{meta['corner']}"] = dict(meta=meta, samples=S)
    Path(a.out).write_text(json.dumps(out) + "\n")
    print({k: len(v["samples"]) for k, v in out.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen")
    g.add_argument("--lib", required=True, help="host dir holding TT/ FF/ {models,cells}.sp (read for the subckt)")
    g.add_argument("--libw", default="/w/lib", help="same dir as seen inside the container")
    g.add_argument("--osdi", default="/w/osdi/bsimcmg23.osdi")
    g.add_argument("--out", required=True)
    g.add_argument("--chain", choices=sorted(CHAIN), required=True)
    g.add_argument("--corner", choices=sorted(CORNER), required=True)
    g.add_argument("--samples", type=int, default=200)
    g.add_argument("--seed", type=int, default=1)
    g.add_argument("--depth", type=int, default=DEPTH)
    p = sp.add_parser("parse")
    p.add_argument("decks", nargs="+")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return gen(a) if a.cmd == "gen" else parse(a)


if __name__ == "__main__":
    sys.exit(main())
