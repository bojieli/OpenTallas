#!/usr/bin/env python3
"""HBM-DIEGAP/SMHPARENT 10-21 (H.STA.BLK.14): tools/landed_parent/lp.py specs for the smh_attn parent built from the rp4a
hardened halves (flat input: rtl/hbm_accel/sm/attn/flat/ot_hbm_accel_smh_attn_rp4a.sv, smh_attn_rp4a_flat_gen.py).

Two forms, gate both (bind the first that closes):
  MAIN  per-HALF regions: t<c><p>n = u_t<c><p>_n, t<c><p>s = u_t<c><p>_s (+ u_gp<c> / u_be<c> for p 1).  The n -> s
        crossing (xo_b 2,069 + xo_g0 50 + xo_gp 100 b, u_xbo/u_xgo/u_xpo -> u_lands/u_xgi/u_xpi) is a LANDING (ring on the
        n root beside its S face, read on the s root beside u_lands), so no reg->reg path joins two halves' trees (SAFE-HBM
        parent note 10-21).  Rows / beat between columns, front -> columns, p0 -> p1 gather, gather -> BE, BE q chain and
        q -> front result are landed as HF-5c.
  FB    per-TILE regions: t<c><p> = both halves on ONE parent root (the crossing stays a direct reg->reg inside one
        region: the parent CTS balances both halves' clk pins from that root against their ETM insertions).  Fewer
        landings (no 16 x 2,219-b crossing rings), but closes only if the two halves' insertions match within the
        regional spread rule.
Floorplan centres (um, SM lower-left = 0,0; tile column pitch = half width + 86.4 landing channel; front column between
columns 3 and 4; p0 tiles on top, p1 below, BEs at the bottom; front result u_fr beside the BEs of columns 3 / 4).
    python3 tools/hbm_sm_attention/smh_attn_rp4a_lp_specs.py  -> results/arch/smh_attn_parent_1021/lp_spec_{main,fb}.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import smh_attn_rp4a_flat_gen as R  # noqa: E402

OUT = ROOT / "results/arch/smh_attn_parent_1021"
NC, NP, NL = R.NC, R.NP, R.NL
HN, HS = 1512.0, 1252.8             # r3 halves heights (n r1 frame, s r2 frame)
CH = 86.4                           # landing channel between tile columns / between row pairs
FW = 1036.8                         # front column width (u_fl + u_bc), estimate until the front cluster has a view
BEH = 302.4                         # BE row height (estimate: ot_hbm_sm_attn_be is soft, tree + stack + landings)


def child_sources():
    t = (ROOT / "tools/hbm_sm_attention/sm_elem_bench.py").read_text()
    src = re.findall(r'"([^"]+)"', re.search(r"^SRC = \[(.*?)\]", t, re.S | re.M).group(1))
    rp4a = re.findall(r'"([^"]+)"', re.search(r"^RP4A_SRC = \[(.*?)\]", t, re.S | re.M).group(1))
    out = []
    for s in src[:-1] + rp4a:          # drop the tb; the flat parent itself is "sources"
        if s.endswith("ot_hbm_accel_smh_attn_rp4a.sv") or s.endswith("ot_hbm_accel_smh_attn.sv") or s in out:
            continue
        out.append(s)
    return out


def defines():
    t = (ROOT / "tools/hbm_sm_attention/sm_elem_bench.py").read_text()
    return re.findall(r'"([^"]+)"', re.search(r"^RP4A_DEF = \[(.*?)\]", t, re.S | re.M).group(1))


def geometry(w, gap=CH):
    """column centre x, row centres y (um); gap = n/s channel (MAIN: 86.4 for the crossing landing, FB: 0 = abutted)."""
    pitch = w + CH
    tile_h = HN + gap + HS
    ybe = BEH / 2
    y1s = BEH + CH + HS / 2
    y1n = BEH + CH + HS + gap + HN / 2
    y0s = BEH + CH + tile_h + CH + HS / 2
    y0n = BEH + CH + tile_h + CH + HS + gap + HN / 2
    xs = {}
    for c in range(NC):
        k = (NL - 1 - c) if c < NL else (c - NL)             # hops from the front
        left = c < NL
        x0 = (NL * pitch) if left else (NL * pitch + FW)
        xs[c] = (x0 - CH / 2 - w / 2 - k * pitch) if left else (x0 + CH / 2 + w / 2 + k * pitch)
    xf = NL * pitch + FW / 2
    top = BEH + CH + 2 * tile_h + CH
    return dict(x=xs, xf=xf, y={"0n": y0n, "0s": y0s, "1n": y1n, "1s": y1s, "be": ybe}, w=2 * NL * pitch + FW, h=top,
                pitch=pitch, gap=gap)


def form_geometry(form):
    return geometry(691.2, CH) if form == "main" else geometry(734.4, 0.0)


def regions(form, w):
    g = form_geometry(form)
    rr = [dict(name="f", insts=["u_fl", "u_bc"], centre=[round(g["xf"], 1), round(g["h"] / 2, 1)],
               why="front launch (rows / beat for both row pairs of columns 3 / 4, request) + be_cmd glue: front column mid-height"),
          dict(name="fr", insts=["u_fr"], centre=[round(g["xf"], 1), round(g["y"]["be"], 1)],
               why="front result (ql/qr deskew -> rv/rrow/rdata/fault) at the bottom of the front column beside BEs 3 / 4")]
    for c in range(NC):
        x = round(g["x"][c], 1)
        for p in range(NP):
            extra = [f"u_gp{c}", f"u_be{c}"] if p == NP - 1 else []
            if form == "main":
                rr.append(dict(name=f"t{c}{p}n", insts=[f"u_t{c}{p}_n"], centre=[x, round(g["y"][f"{p}n"], 1)],
                               why=f"rp4a n half column {c} row pair {p} ({w} x {HN}); its S-face crossing is landed"))
                rr.append(dict(name=f"t{c}{p}s", insts=[f"u_t{c}{p}_s"] + extra,
                               centre=[x, round(g["y"][f"{p}s"] if not extra else (g["y"][f"{p}s"] + g["y"]["be"]) / 2, 1)],
                               why=f"rp4a s half column {c} row pair {p} ({w} x {HS})" +
                                   (" + own-lane pad + column BE (gather -> BE in-region)" if extra else "")))
            else:
                yc = (g["y"][f"{p}n"] + g["y"][f"{p}s"]) / 2
                rr.append(dict(name=f"t{c}{p}", insts=[f"u_t{c}{p}_n", f"u_t{c}{p}_s"] + extra, centre=[x, round(yc, 1)],
                               why=f"rp4a tile column {c} row pair {p}: both halves on one parent root (crossing direct)" +
                                   (" + own-lane pad + column BE" if extra else "")))
    return rr, g


def spec(form):
    w = 691.2 if form == "main" else 734.4
    rr, g = regions(form, w)
    hard = [f"u_t{c}{p}_{h}" for c in range(NC) for p in range(NP) for h in "ns"]
    return {
        "top": R.TOP,
        "top_lp": f"{R.TOP}_lp_{form}",
        "why": (f"HBM-DIEGAP/SMHPARENT 10-21 (H.STA.BLK.14): smh_attn x16 parent with the rp4a hardened halves, form {form.upper()} "
                f"({'per-half regions, n->s crossing LANDED' if form == 'main' else 'per-tile regions, both halves on one parent root'}). "
                f"Halves r3{'a (691.2 wide)' if form == 'main' else 'b (734.4 wide)'}; SM outline estimate {g['w']:.1f} x {g['h']:.1f} um."),
        "sources": ["rtl/hbm_accel/sm/attn/flat/ot_hbm_accel_smh_attn_rp4a.sv"],
        "child_sources": child_sources(),
        "defines": defines(),
        "defines_note": "the rp4 kit define set of the halves kits (smh_rp4ah{n,s}_r3*/spec.json minus OT_RP4A_HARD) = sm_elem_bench --rp4a",
        "params": {"KVMUT": 0, "BE_DELAY": 8 + 2 * R.G, "HOPD": 5, "GPAD": R.G},
        "synthesis_hard_instances": hard,
        "out_dir": f"rtl/hbm_accel/sm/attn/flat/lp_rp4a_{form}",
        "record_dir": f"results/arch/smh_attn_parent_1021/{form}",
        "clock_ports": ["clk"],
        "clock_pins": ["clk"],
        "reset_port": "rst_n",
        "reset_pins": ["rst_n", "rst_a"],
        "regions": rr,
        "D": 4,
        "E": 2,
        "landing_chunk_bits": 24,
        "landing_writer": "n32",
        "regional_reset_copies": True,
        "reset_region": "f",
        "mut_child": "u_bc",
        "bench": {"cycles": 4000, "reset_cycles": 16, "sim": "verilator", "quiet_reset": True, "warm": 1500,
                  "warm_note": "as HF-5c: tcl/bdc accumulators (no-reset data cuts) need a flush window before the compare",
                  "mut_waivers": {"4": "as HF-5c lp_mut4 (10-18): with quiet_reset every child's reset clears only valid / sticky "
                                       "flags that stay 0 under zero inputs, so a 1-stage reset slip is invisible to random lockstep; "
                                       "landing reset alignment is covered by MUT 2 (read K+1)"}},
        "compiler_note": {
            "rp4a_delta": (f"vs ot_hbm_accel_smh_attn (soft tiles): every gout lane +G={R.G} per rp4a tile (2+GN+GS+LR+2*OS, r3 kits); "
                           f"p1 own lanes padded +G in the parent (u_gp<c>) so every BE lane is +{2 * R.G}; BE_DELAY 8 -> {8 + 2 * R.G}; "
                           f"HOPD 4 -> 5 (rp4 pin register per hop). QK/PV calendar in command time unchanged; results +{2 * R.G} (flat) "
                           "plus the landed-parent result offset of this record."),
            "loop_resolution": "front split u_fl / u_fr as HF-5c (ot_smh_static_front result path reads only ql/qr)"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for form in ("main", "fb"):
        s = spec(form)
        p = OUT / f"lp_spec_{form}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        g = form_geometry(form)
        print(f"wrote {p.relative_to(ROOT)}: {len(s['regions'])} regions, SM outline ~{g['w']:.1f} x {g['h']:.1f} um")


if __name__ == "__main__":
    main()
