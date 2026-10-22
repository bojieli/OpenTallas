#!/usr/bin/env python3
"""S81-SLICE/PARENT 10-21: successor kits of the landed slice parent on the CURRENT parent RTL.

  c1x  ot_s81sl_slice_c1x_k8_cap5r_lp  (10 normal die slices + u_sl of the 4 MU72 end parents)
       kits k8c (MAIN, W 1252.8 = die column, 43.2 column channel) / k8d (FALLBACK, W 1296, 86.4 column channel)
  c3x  ot_s81sl_slice_c3x_k8_cap5r_lp  (HB=1: die s_4S (band q/pv) and s_3S (iq: ot_s81sl_slice_iq -> bo))
       kits k8e (MAIN, W 1468.8) / k8f (FALLBACK, W 1512): xr3 is 570.24 wide -> no C3 centre fits a 1252.8 column

Children: CLOSED views whose LEF port list equals the current RTL header AND whose sources did not change after the
closure (vq, rxsf, rxsb, vsw, vn, eg, capc5r closure s81sl_capc5r-163d31541 record 4a4d275ee).  Every other child is an
explicit STAND-IN (STANDIN_NOT_A_VIEW, OBS M1-M5, tools/qwen_dv/slice_standin.py) at its successor kit outline / faces:
  ot_s81sl_vp     734.4 x 864     no closed view (SL-VP SAFE redesign)          spec k8a standin (s81sl_vp)
  ot_s81sl_ve     345.6 x 345.6   ve_r5 not CLOSED (SL-VE)                       k8a standin (ve_r5)
  ot_s81sl_xgt_xo 734.4 x 777.6   kit s81sl_xgtxo gates live (SL-XG)             physical/ref_tile/s81sl_xgtxo
  ot_s81sl_xrt1   311.04 x 395.28 RG-FFN successor of xr1: CLOSED xr1f NOT aliased
  ot_s81sl_xrt3   570.24 x 395.28 successor of xr3: CLOSED xr3 NOT aliased
  ot_s81dv_xfin   345.6 x 345.6   STALE view (predates ENG 269ef81a1: no mode/e_*); SL-CHILD xfin_e2 (k8c_child_specs)
  ot_s81sl_vs     172.8 x 172.8   STALE view (b5a2e98f8 predates SW wr 8158a1e89, same ports); SL-CHILD vs_w2
Height 6868.8 for every variant: the centre (xgt_xo 734.4 x 777.6 + xfin_e2 345.6^2) needs CC 1209.6 (k8a 1080); die
row pitch 6912 -> street 43.2, or the upper slice row +43.2 (eng_00 street stays 86.4).  W: c1x 1252.8 (= die column)
MAIN / 1296 FALLBACK; c3x 1468.8 / 1512 (xr3 570.24 wide: no C3 centre fits a 1252.8 column -> s_3S / s_4S slots widen).
Centre band (region C): xg W column (ri_w / ro_w on the parent W face); E column cap -> xr (R180: dl/ci face xg, cfg
faces cap N, x_* / eg_* face up); row above xg: eg | xfin (xfin e_* W face -> eg).
DIAGNOSTIC while stand-ins remain; critical prefix s81dv_slice -> COORD-REVIEW-QUEUE, never REVIEW.json / submit.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L = 43.2
H_MAX = 6868.8          # die row pitch 6912 - 43.2 street (upper slice row +43.2: eng_00 street stays 86.4)
BASE = ROOT / "physical/ref_tile/s81dv_slice_lp_k8a/spec.json"     # k8a: landed-cluster spec fields (domains, route...)

CLOSED = {
    "ot_s81sl_vq": "physical/ref_tile/s81sl_vq/views/ot_s81sl_vq",
    "dsfd_su_t_rxsf": "physical/ref_tile/s81su_rxsf_ref/views/dsfd_su_t_rxsf",
    "dsfd_su_t_rxsb": "physical/ref_tile/s81su_rxsb_ref/views/dsfd_su_t_rxsb",
    "ot_s81sl_vsw": "physical/ref_tile/s81sl_vsw/views/ot_s81sl_vsw",
    "ot_s81sl_vn": "physical/ref_tile/s81sl_vn/views/ot_s81sl_vn",
    "ot_s81sl_eg": "physical/ref_tile/s81sl_eg/views/ot_s81sl_eg",
    "ot_s81sl_capc5r": "physical/ref_tile/s81sl_capc5r/views/ot_s81sl_capc5r",
}
SIZE = {"ot_s81sl_vq": (172.8, 129.6), "ot_s81sl_vs": (172.8, 172.8), "dsfd_su_t_rxsf": (140.4, 140.4),
        "dsfd_su_t_rxsb": (140.4, 140.4), "ot_s81sl_vsw": (224.64, 224.64), "ot_s81sl_vn": (356.4, 356.4),
        "ot_s81sl_vp": (734.4, 864.0), "ot_s81sl_ve": (345.6, 345.6), "ot_s81sl_xgt_xo": (734.4, 777.6),
        "ot_s81sl_xrt1": (311.04, 395.28), "ot_s81sl_xrt3": (570.24, 395.28), "ot_s81dv_xfin": (345.6, 345.6),
        "ot_s81sl_eg": (259.2, 259.2), "ot_s81sl_capc5r": (336.96, 414.72)}
# assumed stand-in insertion TT,FF,SS (ps): vp its 10-18 gate; ve / xg as k8a; xrt1 / xrt3 / xfin = the measured
# insertion of the CLOSED predecessor view (xr1f 414/340/536, xr3 625/516/802, xfin 274/228/350)
INS = {"ot_s81sl_vs": "247,203,319", "ot_s81sl_vp": "1219,994,1500", "ot_s81sl_ve": "400,330,520", "ot_s81sl_xgt_xo": "450,370,580",
       "ot_s81sl_xrt1": "414,340,536", "ot_s81sl_xrt3": "625,516,802", "ot_s81dv_xfin": "274,228,350"}
VARIANTS = {   # name: (flat, W, column channel, MAIN/FALLBACK)
    "k8c": ("c1x", 1252.8, L, "MAIN"),
    "k8d": ("c1x", 1296.0, 2 * L, "FALLBACK"),
    "k8e": ("c3x", 1468.8, L, "MAIN"),
    "k8f": ("c3x", 1512.0, 2 * L, "FALLBACK"),
}


def up(v):
    k = round(v / L)
    return round(k * L, 3) if abs(v - k * L) < 1e-6 else round((int(v / L) + 1) * L, 3)


def down(v):
    k = round(v / L)
    return round(k * L, 3) if abs(v - k * L) < 1e-6 else round(int(v / L) * L, 3)


def standin_specs(flat):
    def load(p):
        return json.loads((ROOT / p).read_text())
    keep = ("clock_port", "outline", "pins", "pin_ranges", "defines")
    out = {}
    out["ot_s81sl_vp"] = load("physical/ref_tile/s81dv_slice_lp_k8a/standin/ot_s81sl_vp.json")
    out["ot_s81sl_ve"] = load("physical/ref_tile/s81dv_slice_lp_k8a/standin/ot_s81sl_ve.json")
    s = {k: v for k, v in load("physical/ref_tile/s81sl_xgtxo/spec.json").items() if k in keep}
    s.update(top="ot_s81sl_xgt_xo", sources=["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgt_xo.sv"])
    out["ot_s81sl_xgt_xo"] = s
    xr = "xrt1" if flat == "c1x" else "xrt3"
    s = {k: v for k, v in load(f"physical/ref_tile/s81sl_{'xr1f' if flat == 'c1x' else 'xr3'}/spec.json").items() if k in keep}
    s.update(top=f"ot_s81sl_{xr}", sources=["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv"])
    out[f"ot_s81sl_{xr}"] = s
    # SL-CHILD successors (claude/s81sl-child-1021 @0618133cb, copied to k8c_child_specs/): xfin_e2 345.6^2 (e_* on W),
    # vs_w2 172.8^2 (CLOSED vs view b5a2e98f8 predates the SW wr RTL 8158a1e89: same ports, stale source -> stand-in)
    s = {k: v for k, v in load("tools/s81_slice/pl_slice/k8c_child_specs/s81dv_xfin_e2.json").items() if k in keep}
    s.update(top="ot_s81dv_xfin", sources=["rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv"])
    out["ot_s81dv_xfin"] = s
    s = {k: v for k, v in load("tools/s81_slice/pl_slice/k8c_child_specs/s81sl_vs_w2.json").items() if k in keep}
    s.update(top="ot_s81sl_vs", sources=["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv"])
    out["ot_s81sl_vs"] = s
    for m, s in out.items():
        s.pop("defines", None)
        s["outline"] = {"w": SIZE[m][0], "h": SIZE[m][1]}
        s["name"] = f"standin_{m}"
        s["_note"] = f"S81-SLICE/PARENT 10-21 stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) at the successor outline/faces of {m}"
    return out


def header_copy(sources, mod, outdir):
    """the module's ANSI header with its default integer parameters substituted (slice_standin.py evaluates widths
    numerically) -> <outdir>/<mod>_hdr.sv (stand-in pin source only; never synthesised)"""
    import re
    for src in sources:
        t = re.sub(r"//[^\n]*", "", (ROOT / src).read_text())
        m = re.search(r"\bmodule\s+%s\b\s*(#\s*\((.*?)\)\s*)?\((.*?)\);" % re.escape(mod), t, re.S)
        if not m:
            continue
        hdr = m.group(3)
        params = dict(re.findall(r"parameter\s+(?:integer\s+)?(\w+)\s*=\s*(\d+)", m.group(2) or ""))
        for k, v in params.items():
            hdr = re.sub(r"\b%s\b" % k, v, hdr)
        p = outdir / f"{mod}_hdr.sv"
        p.write_text(f"// stand-in pin source: header of {mod} from {src} with default parameters {params}\n"
                     f"module {mod} (\n{hdr.strip()}\n);\nendmodule\n")
        return str(p.relative_to(ROOT))
    raise SystemExit(f"{mod} not in {sources}")


def layout(flat, W, gc):
    """S -> N: L4, L3, C2 (leaf 2), CC (centre), L1, L0.  gc = channel between the two child columns."""
    xr = "ot_s81sl_xrt1" if flat == "c1x" else "ot_s81sl_xrt3"
    blocks = []                                # (inst, master, x, y, orient)
    x0, gv, gs = L, L, L / 2
    xb_leaf = down(W - L - SIZE["ot_s81sl_vn"][0])      # leaf column B right-aligned (extra width -> leaf channel)
    assert xb_leaf >= up(x0 + SIZE["ot_s81sl_vp"][0] + gc) - 1e-6, (W, xb_leaf)

    def leaf(k, y0):
        blocks.append((f"u_lf{k}.u_vp", "ot_s81sl_vp", x0, y0, "R0"))
        xb = xb_leaf
        blocks.append((f"u_lf{k}.u_vn", "ot_s81sl_vn", xb, y0, "R0"))
        y = up(y0 + SIZE["ot_s81sl_vn"][1] + gv)
        blocks.append((f"u_lf{k}.u_ve", "ot_s81sl_ve", xb, y, "R0"))
        y = up(y + SIZE["ot_s81sl_ve"][1] + gv)
        blocks.append((f"u_lf{k}.u_vsw", "ot_s81sl_vsw", xb, y, "R0"))
        top_b = y + SIZE["ot_s81sl_vsw"][1]
        ys = up(y0 + SIZE["ot_s81sl_vp"][1] + gv)
        x = x0
        for inst, m in (("u_vq", "ot_s81sl_vq"), ("u_vs", "ot_s81sl_vs"), ("u_rxsf", "dsfd_su_t_rxsf"), ("u_rxsb", "dsfd_su_t_rxsb")):
            blocks.append((f"u_lf{k}.{inst}", m, x, ys, "R0"))
            x = up(x + SIZE[m][0] + gs)
        assert x - gs <= xb + 1e-6
        top_a = ys + max(SIZE[m][1] for m in ("ot_s81sl_vq", "ot_s81sl_vs", "dsfd_su_t_rxsf", "dsfd_su_t_rxsb"))
        return up(max(top_a, top_b) + gv) - y0

    def centre(y0):
        xg_w, xg_h = SIZE["ot_s81sl_xgt_xo"]
        blocks.append(("u_xg", "ot_s81sl_xgt_xo", x0, y0, "R0"))
        xb = up(x0 + xg_w + gc)
        assert xb + SIZE[xr][0] <= W - L + 1e-6, f"{xr} overruns the E margin ({xb} + {SIZE[xr][0]} > {W - L})"
        blocks.append(("u_cap", "ot_s81sl_capc5r", xb, y0, "R0"))
        y_xr = up(y0 + SIZE["ot_s81sl_capc5r"][1] + gv)
        blocks.append(("u_xr", xr, xb, y_xr, "R180"))
        y_row = up(y0 + xg_h + gv)                    # row above xg: eg | xfin (xfin e_* on its W face -> eg)
        x_xf = down(xb - gc - SIZE["ot_s81dv_xfin"][0])
        blocks.append(("u_xf", "ot_s81dv_xfin", x_xf, y_row, "R0"))
        x_eg = down(x_xf - gv - SIZE["ot_s81sl_eg"][0])
        assert x_eg >= x0 - 1e-6
        blocks.append(("u_eg", "ot_s81sl_eg", x_eg, y_row, "R0"))
        top = max(y_xr + SIZE[xr][1], y_row + SIZE["ot_s81dv_xfin"][1])
        return up(top + gv) - y0

    y, bands = L, {}
    for name, fn in (("L4", lambda y: leaf(4, y)), ("L3", lambda y: leaf(3, y)), ("C2", lambda y: leaf(2, y)),
                     ("CC", centre), ("L1", lambda y: leaf(1, y)), ("L0", lambda y: leaf(0, y))):
        h = fn(y)
        bands[name] = (y - (L if name == "L4" else 0), y + h)
        y += h
    H = round(y, 3)
    assert H <= H_MAX + 1e-6, f"H {H} > die row height {H_MAX}"
    return blocks, bands, W, H


def build(name):
    flat, W, gc, role = VARIANTS[name.split("_")[-1]]
    top = f"ot_s81sl_slice_{flat}_k8_cap5r_lp"
    lp_dir = f"rtl/dsrom_sys/s81_dv/slice/landed/{flat}_k8_cap5r"
    rec_dir = f"results/rtl/drive_s81_slicep_1020/{flat}_k8_cap5r"
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    views = dict(CLOSED)
    sis = standin_specs(flat)
    for m, s in sis.items():
        s["sources"] = [header_copy(s["sources"], m, kd / "standin")]
        json.dump(s, open(kd / "standin" / f"{m}.json", "w"), indent=1)
        subprocess.run([sys.executable, str(ROOT / "tools/qwen_dv/slice_standin.py"), "--ins", INS[m], "--master", m,
                        str(kd / "standin" / f"{m}.json"), str(kd / "standin_views")], check=True, cwd=ROOT)
        views[m] = f"physical/ref_tile/{name}/standin_views/{m}"
    blocks, bands, W, H = layout(flat, W, gc)
    H = H_MAX                                       # die row height; spare height = N margin above L0
    c_lo, c_hi = bands["C2"][0], bands["CC"][1]
    mid = lambda b: round((bands[b][0] + bands[b][1]) / 2, 1)
    widths = {"ri_w": 1104, "ro_w": 1104, "xc": 4416, "ri_e": 1104, "ro_e": 1104, "vi": 276, "vo": 276, "bi": 1104,
              "bo": 513, "rt": 560, "ck_line": 16, "ck_v": 2, "ck_xc": 16, "ck_rt": 8, "sid": 4, "rst_n": 1, "ck_C": 1, "fault": 1}
    caps = ["ck_CAP_RT", "ck_CAP_CW", "ck_CAP_CE", "ck_CAP_RN", "ck_CAP_RS"]
    W_list = ["ri_w", "ro_w", "xc"]
    E_list = ["ri_e", "ro_e", "vi"] + caps + ["vo", "bi", "bo", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "rst_n", "ck_C", "fault"]
    span = c_hi - c_lo - 40.0
    pr = {}
    for lst in (W_list, E_list):
        fixed = sum(12.0 for p in lst if p in caps)
        tot = sum(widths[p] for p in lst if p not in caps)
        y = c_lo + 20.0
        for p in lst:
            h = 12.0 if p in caps else max(4.0, (span - fixed) * widths[p] / tot)
            pr[p] = [round(y, 3), round(y + h, 3)]
            y += h
    for r in ("L0", "L1", "L3", "L4"):
        m = mid(r)
        pr[f"ck_{r}"] = [m - 6.0, m + 6.0]
    spec = json.loads(BASE.read_text())
    stand = sorted(sis)
    children = [{"view": views[m], "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)], **({"orient": o} if o != "R0" else {})}
                for inst, m, x, y, o in blocks]
    hard = sum(SIZE[m][0] * SIZE[m][1] for _, m, _, _, _ in blocks)
    spec.update({
        "name": name, "top": top,
        "sources": [f"{lp_dir}/{top}.sv", f"rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_{flat}.sv",
                    "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_glue.sv",
                    "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
                    "rtl/common/landed_parent/ot_pl_land_reset_forest.sv", "rtl/common/landed_parent/ot_pl_land_kept_enable.sv"]
                   + [f"{views[m]}/{m}_bb.v" for m in stand]
                   + ["rtl/lib/ot_reset_sync.sv", "rtl/common/landed_parent/ot_pl_land_n32.sv"],
        "landed_record": f"{rec_dir}/{top}_record.json",
        "reset_landing": {"enable": False, "reason": "lp.py RTL lands it: rst_n -> u_lpr_root (ck_C) -> per-region runs + per-chunk reset forest + CAP region forests (cap5r); the port net has ONE sink"},
        "outline": {"w": W, "h": H, "exact": True},
        "children": children, "pin_ranges": pr,
        "pins": {"W": W_list, "E": ["ck_L4", "ck_L3"] + E_list + ["ck_L1", "ck_L0"], "N": [], "S": []},
        "structural_change": (f"S81-SLICE/PARENT 10-21 {name} ({role}, {flat}): successor of k8a/k8b on the CURRENT parent RTL "
                              f"{top} (CLOSED capc5r 4a4d275ee + fixed-depth CAP reset forests, u_xg ot_s81sl_xgt_xo, u_xr "
                              f"{'xrt1' if flat == 'c1x' else 'xrt3 + bi/bo'}); stand-ins {', '.join(stand)} (xfin CLOSED view stale: "
                              f"no ENG e_* ports); outline {W} x {H} ({W * H / 1e6:.2f} mm2, hard {hard / 1e6:.2f} mm2) = die row "
                              f"height 6825.6, column channel {gc}; centre re-arranged for the 734.4 x 777.6 xgt_xo."),
        "source_binding": {"closed_cap_record": "4a4d275ee", "closed_cap_closure": "s81sl_capc5r-163d31541",
                           "compiler_env": {"OT_S81_CAP5_C": "1"}, "capture_extra_edges": 12,
                           "cap_reset_status": "fixed: capc5r region-landed resets + fixed-depth forests from lpr_root (cap5r_lp)",
                           "xg_binding": "claude/s81-xgtxo-1021 6468d5e7d (xw_v/xw_d +1 edge, fault +1: MU.S81.CAL)"},
    })
    spec["job"] = {"owner": "Claude:S81-SLICE/PARENT", "branch": "claude/s81-slicep-k8c-1021", "tag": name.split("_")[-1],
                   "purpose": f"{role} slice-parent gate on current RTL + stand-ins: region clocks, landings, GRT, reach; DIAGNOSTIC",
                   "submit": False, "hold_merge": f"stand-in children ({', '.join(stand)}): diagnostic only, never route or bind",
                   "benches": [], "no_bench_reason": "diagnostic stand-in gate; landed lockstep/ENG benches: tools/s81_slice/pl_slice/pl_slice_bench.sh",
                   "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}",
                   "extra_paths": [rec_dir, lp_dir, "results/rtl/drive_s81_slicep_1020/c1x_k8_cap5"]}
    sp = kd / "spec.json"
    json.dump(spec, open(sp, "w"), indent=1)
    print(f"{name}: {top} outline {W} x {H} = {W * H / 1e6:.2f} mm2, hard {hard / 1e6:.2f} mm2 ({hard / (W * H):.0%}), bands "
          + ", ".join(f"{b} {v[0]:.1f}-{v[1]:.1f}" for b, v in bands.items()))
    for inst, m, x, y, o in blocks:
        if not inst.startswith("u_lf"):
            print(f"   {inst:6s} {m:18s} ({x}, {y}) {o}")
    if "--no-gen" not in sys.argv:
        subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(sp.relative_to(ROOT))], check=False, cwd=ROOT)


if __name__ == "__main__":
    for v in ([a for a in sys.argv[1:] if not a.startswith("--")] or list(VARIANTS)):
        build(f"s81dv_slice_lp_{v}")
