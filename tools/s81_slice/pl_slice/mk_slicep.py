#!/usr/bin/env python3
"""DRIVE-S81-SLICEP 10-20: DIAGNOSTIC landed slice parent kits s81dv_slice_lp_k8{a,b} (ot_s81sl_slice, die master
dsdv_slice x 12 + inside every end-slice cluster).  Critical prefix s81dv_slice: gate PNGs -> COORD-REVIEW-QUEUE, never
REVIEW.json / submit.  Early die-level integration with the CURRENT child views (owner EFFICIENCY 10-18):

  top      ot_s81sl_slice_c1x_k8_lp (lp.py tools/s81_slice/pl_slice/c1x_k8.json: PL-SLICE c1x regions C / L0 / L1 / L3 / L4,
           8 landings D 4 / E 2, reference schedule, census-safe landings: chunk 8 + per-chunk reset forest + kept enable)
  children CLOSED views on main: vq, vs, rxsf, rxsb, vsw, vn (x 5 each), xr1 (xr1f), xfin (x5), eg, capc2.
           STAND-INS (STANDIN_NOT_A_VIEW, tools/qwen_dv/slice_standin.py, real kit outline + pins):
             ot_s81sl_vp x 5 (no closed view; spec s81sl_vp 734.4 x 864, 10-18 gate WARN never submitted -> regate live)
             ot_s81sl_ve x 5 (s81sl_ve_r5 345.6^2, regate + auto-submit live, DRIVE-S81-VE)
             ot_s81sl_xg     (= s81sl_xg5 outline 648 x 561.6 / pins; slice still instantiates ot_s81sl_xg -- same ports;
                              the RTL swap to ot_s81sl_xg5 is owed with its +2 / +1 edges to MU.S81.CAL)
  layout   N -> S: L0, L1, C (centre band + leaf 2), L3, L4.  All parent ports are region C (lp record: port offsets 0) ->
           every port sits on the W / E faces of the C rows (no C-clock wire across a leaf band); ck_L<k> enter at their
           own band; rst_n / ck_C / fault on the E face of C.
  a        compact: leaf band 1166.4 (43.2 channels), centre band 1080, W 1252.8.
  b        fallback: 86.4-um channels between child columns / rows (room for leaf glue, landings and relays), W 1339.2.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SC = Path("/home/ubuntu/scratch/drives81-slicep/specs")
L = 43.2

CLOSED = {
    "ot_s81sl_vq": "physical/ref_tile/s81sl_vq/views/ot_s81sl_vq",
    "ot_s81sl_vs": "physical/ref_tile/s81sl_vs/views/ot_s81sl_vs",
    "dsfd_su_t_rxsf": "physical/ref_tile/s81su_rxsf_ref/views/dsfd_su_t_rxsf",
    "dsfd_su_t_rxsb": "physical/ref_tile/s81su_rxsb_ref/views/dsfd_su_t_rxsb",
    "ot_s81sl_vsw": "physical/ref_tile/s81sl_vsw/views/ot_s81sl_vsw",
    "ot_s81sl_vn": "physical/ref_tile/s81sl_vn/views/ot_s81sl_vn",
    "ot_s81sl_xr1": "physical/ref_tile/s81sl_xr1f/views/ot_s81sl_xr1",
    "ot_s81dv_xfin": "physical/ref_tile/s81dv_xfin/views/ot_s81dv_xfin",
    "ot_s81sl_eg": "physical/ref_tile/s81sl_eg/views/ot_s81sl_eg",
    "ot_s81sl_capc2": "physical/ref_tile/s81sl_capc2/views/ot_s81sl_capc2",
}
# assumed stand-in insertion TT,FF,SS (ps): vp = its 10-18 gate (TT 1219 / FF 994); ve r5 / xg5 ~ closed siblings
INS = {"ot_s81sl_vp": "1219,994,1500", "ot_s81sl_ve": "400,330,520", "ot_s81sl_xg": "450,370,580"}
SIZE = {"ot_s81sl_vq": (172.8, 129.6), "ot_s81sl_vs": (172.8, 172.8), "dsfd_su_t_rxsf": (140.4, 140.4),
        "dsfd_su_t_rxsb": (140.4, 140.4), "ot_s81sl_vsw": (224.64, 224.64), "ot_s81sl_vn": (356.4, 356.4),
        "ot_s81sl_vp": (734.4, 864.0), "ot_s81sl_ve": (345.6, 345.6), "ot_s81sl_xg": (648.0, 561.6),
        "ot_s81sl_xr1": (311.04, 395.28), "ot_s81dv_xfin": (181.44, 181.44), "ot_s81sl_eg": (259.2, 259.2),
        "ot_s81sl_capc2": (336.96, 414.72)}


def up(v):          # next 43.2 lattice point >= v
    k = int(v / L - 1e-6) + 1
    return round(k * L, 3) if abs(v - round(v / L) * L) > 1e-6 else round(v, 3)


def standin_specs():
    out = {}
    vp = json.load(open(SC / "vp.json"))
    out["ot_s81sl_vp"] = {k: vp[k] for k in ("top", "sources", "clock_port", "outline", "pins", "pin_ranges") if k in vp}
    ve = json.load(open(SC / "ve_r5.json"))
    s = {k: ve[k] for k in ("top", "clock_port", "pins", "pin_ranges") if k in ve}
    s["sources"] = ["rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv"]      # the header the slice binds (r5 extra sources are branch-only)
    s["outline"] = {"w": 345.6, "h": 345.6}
    out["ot_s81sl_ve"] = s
    xg = json.load(open(SC / "xg5.json"))
    s = {k: xg[k] for k in ("clock_port", "outline", "pins", "pin_ranges") if k in xg}
    s["top"] = "ot_s81sl_xg"
    s["sources"] = ["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xg.sv"]
    out["ot_s81sl_xg"] = s
    for m, s in out.items():
        s["name"] = f"standin_{m}"
        s["_note"] = f"DRIVE-S81-SLICEP 10-20 stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) at the real kit outline/pins of {m}"
    return out


def layout(variant):
    g = L if variant == "a" else 2 * L         # channel between columns / rows
    blocks = []                                # (inst, master, x, y)
    x0 = L

    def leaf(k, y0):
        vpw, vph = SIZE["ot_s81sl_vp"]
        blocks.append((f"u_lf{k}.u_vp", "ot_s81sl_vp", x0, y0))
        xb = up(x0 + vpw + g)
        blocks.append((f"u_lf{k}.u_vn", "ot_s81sl_vn", xb, y0))
        y = up(y0 + SIZE["ot_s81sl_vn"][1] + g)
        blocks.append((f"u_lf{k}.u_ve", "ot_s81sl_ve", xb, y))
        y = up(y + SIZE["ot_s81sl_ve"][1] + g)
        blocks.append((f"u_lf{k}.u_vsw", "ot_s81sl_vsw", xb, y))
        top_b = y + SIZE["ot_s81sl_vsw"][1]
        ys = up(y0 + vph + g)
        x = x0
        for inst, m in (("u_vq", "ot_s81sl_vq"), ("u_vs", "ot_s81sl_vs"), ("u_rxsf", "dsfd_su_t_rxsf"), ("u_rxsb", "dsfd_su_t_rxsb")):
            blocks.append((f"u_lf{k}.{inst}", m, x, ys))
            x = up(x + SIZE[m][0] + g / 2)          # small hard children: half channel (>= 21.6, 4 x halo)
        assert x - g / 2 <= xb + 1e-6, f"leaf small row overruns column B ({x} > {xb})"
        top_a = ys + max(SIZE[m][1] for m in ("ot_s81sl_vq", "ot_s81sl_vs", "dsfd_su_t_rxsf", "dsfd_su_t_rxsb"))
        return up(max(top_a, top_b) + g) - y0, xb + SIZE["ot_s81sl_vn"][0]

    def centre(y0):
        blocks.append(("u_xg", "ot_s81sl_xg", x0, y0))
        xc = up(x0 + SIZE["ot_s81sl_xg"][0] + g)
        blocks.append(("u_cap", "ot_s81sl_capc2", xc, y0))
        blocks.append(("u_xf", "ot_s81dv_xfin", xc, up(y0 + SIZE["ot_s81sl_capc2"][1] + g)))
        y2 = up(y0 + SIZE["ot_s81sl_xg"][0 + 1] + g)
        blocks.append(("u_xr", "ot_s81sl_xr1", x0, y2))
        blocks.append(("u_eg", "ot_s81sl_eg", up(x0 + SIZE["ot_s81sl_xr1"][0] + g), y2))
        top = max(y2 + SIZE["ot_s81sl_xr1"][1], up(y0 + SIZE["ot_s81sl_capc2"][1] + g) + SIZE["ot_s81dv_xfin"][1])
        return up(top + g) - y0, xc + SIZE["ot_s81sl_capc2"][0]

    # S -> N: L4, L3, [leaf 2, centre] = C, L1, L0
    y, bands, wmax = L, {}, 0.0
    for name, fn in (("L4", lambda y: leaf(4, y)), ("L3", lambda y: leaf(3, y)), ("C2", lambda y: leaf(2, y)),
                     ("CC", centre), ("L1", lambda y: leaf(1, y)), ("L0", lambda y: leaf(0, y))):
        h, w = fn(y)
        bands[name] = (y - (L if name == "L4" else 0), y + h)
        wmax = max(wmax, w)
        y += h
    W = up(wmax + L)
    H = round(y, 3)
    return blocks, bands, W, H


def build(name, variant):
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    views = dict(CLOSED)
    for m, s in standin_specs().items():
        json.dump(s, open(kd / "standin" / f"{m}.json", "w"), indent=1)
        subprocess.run([sys.executable, str(ROOT / "tools/qwen_dv/slice_standin.py"), "--ins", INS[m], "--master", m,
                        str(kd / "standin" / f"{m}.json"), str(kd / "standin_views")], check=True, cwd=ROOT)
        views[m] = f"physical/ref_tile/{name}/standin_views/{m}"
    blocks, bands, W, H = layout(variant)
    c_lo, c_hi = bands["C2"][0], bands["CC"][1]
    mid = lambda b: round((bands[b][0] + bands[b][1]) / 2, 1)
    # ports: all region C -> W / E faces of the C rows only
    cy = c_lo + 20.0
    W_list = ["ri_w", "ro_w", "xc"]
    E_list = ["ri_e", "ro_e", "vi", "vo", "bi", "bo", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "rst_n", "ck_C", "fault"]
    widths = {"ri_w": 1104, "ro_w": 1104, "xc": 4416, "ri_e": 1104, "ro_e": 1104, "vi": 276, "vo": 276, "bi": 1104,
              "bo": 513, "rt": 560, "ck_line": 16, "ck_v": 2, "ck_xc": 16, "ck_rt": 8, "sid": 4, "rst_n": 1, "ck_C": 1, "fault": 1}
    span = c_hi - c_lo - 40.0
    pr = {}
    for lst in (W_list, E_list):
        tot = sum(widths[p] for p in lst)
        y = cy
        for p in lst:
            n = widths[p]
            h = max(4.0, span * n / tot)
            pr[p] = [round(y, 3), round(y + h, 3)]
            y += h
    # region clock ports at their own bands (E face)
    for r in ("L0", "L1", "L3", "L4"):
        m = mid(r)
        pr[f"ck_{r}"] = [m - 6.0, m + 6.0]
    pins = {"W": W_list, "E": ["ck_L4", "ck_L3"] + E_list + ["ck_L1", "ck_L0"], "N": [], "S": []}
    lp = json.load(open(ROOT / "tools/s81_slice/pl_slice/c1x_k8.json"))
    lp_dir = lp["out_dir"]
    top = lp["top_lp"]
    children = [{"view": views[m], "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)]} for inst, m, x, y in blocks]
    fill_hard = sum(SIZE[m][0] * SIZE[m][1] for _, m, _, _ in blocks)
    spec = {
        "name": name, "top": top, "kind": "cluster",
        "sources": [f"{lp_dir}/{top}.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c1x.sv",
                    "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_glue.sv",
                    "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
                    "rtl/common/landed_parent/ot_pl_land_reset_forest.sv", "rtl/common/landed_parent/ot_pl_land_kept_enable.sv"]
                   + [f"{views[m]}/{m}_bb.v" for m in ("ot_s81sl_vp", "ot_s81sl_ve", "ot_s81sl_xg")],
        "params": {k: v for k, v in lp["params"].items()},
        "defines": list(lp.get("defines", [])) + ["OT_S81SL_HARD"],
        "hard_define": "OT_S81SL_HARD",
        "cluster_level": 2,     # capc2 (and the real vp) are clusters with PG top M7 -> slice PG M8 stripes, signals M2-M7
        "clock": "multiple_cts_roots", "clock_port": "ck_C",
        "clock_ports": ["ck_C", "ck_L0", "ck_L1", "ck_L3", "ck_L4"],
        "clock_data_paths": "related_same_frequency",
        "clock_relationship": {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
        "clock_entry_domains": {
            "core": {"ratio": [1, 1], "ports": ["ck_C"], "inputs": ["rst_n", "sid", "ri_w", "ri_e", "vi", "bi", "rt"],
                     "outputs": ["ro_e", "ro_w", "vo", "bo", "xc", "ck_line", "ck_v", "ck_xc", "ck_rt", "fault"]},
            **{f"l{r[1]}": {"ratio": [1, 1], "ports": [f"ck_{r}"], "inputs": [], "outputs": []} for r in ("L0", "L1", "L3", "L4")}},
        "landed_record": f"{lp['record_dir']}/{top}_record.json",
        "reset_ports": ["rst_n"],
        "reset_landing": {"enable": False, "reason": "lp.py RTL lands it: rst_n -> u_lpr_root (ck_C) -> per-region runs + per-chunk reset forest; the port net has ONE sink"},
        "outline": {"w": W, "h": H, "exact": True},
        "children": children,
        "pins": pins, "pin_ranges": pr,
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 128, "period_ps": 833.333333, "macro_halo_um": 5.4,
                  "hold_margin_ns": 0.03, "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}},
        "orfs_vars": {"OT_OFLOP_GAP": "4.5"},
        "io_flop_at_pins": {"cols": 21},
        "structural_change": (f"DRIVE-S81-SLICEP 10-20 {name}: first gate of the landed slice parent ot_s81sl_slice (PL-SLICE c1x "
                              "regions, census-safe chunk-8 landings), 41 closed child views + 11 stand-ins (vp x5, ve x5, xg); "
                              f"outline {W} x {H} ({W*H/1e6:.2f} mm2, hard children {fill_hard/1e6:.2f} mm2) vs die slot 950 x 4600 "
                              "(4.37 mm2). " + ("a: compact 43.2 channels." if variant == "a" else "b: 86.4 channels (fallback).")),
        "job": {"owner": "Claude:DRIVE-S81-SLICEP", "branch": "claude/drive-s81-slicep-1020", "tag": name.split("_")[-1],
                "purpose": "early slice-parent integration with current child views + stand-ins: region clocks, landings, GRT, reach; DIAGNOSTIC",
                "submit": False, "hold_merge": "stand-in children (vp/ve/xg): diagnostic only, never route or bind",
                "benches": [], "no_bench_reason": "diagnostic stand-in gate; landed lockstep/ENG benches: tools/s81_slice/pl_slice/pl_slice_bench.sh",
                "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}",
                "extra_paths": [lp["record_dir"], lp_dir]},
    }
    sp = kd / "spec.json"
    json.dump(spec, open(sp, "w"), indent=1)
    print(f"{name}: outline {W} x {H} = {W*H/1e6:.2f} mm2, hard {fill_hard/1e6:.2f} mm2 ({fill_hard/(W*H):.0%}), bands "
          + ", ".join(f"{b} {v[0]:.1f}-{v[1]:.1f}" for b, v in bands.items()))
    subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(sp.relative_to(ROOT))], check=False, cwd=ROOT)


if __name__ == "__main__":
    for v in (sys.argv[1:] or ["a", "b"]):
        build(f"s81dv_slice_lp_k8{v}", v)
