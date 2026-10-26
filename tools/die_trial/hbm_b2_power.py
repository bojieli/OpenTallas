#!/usr/bin/env python3
"""ESTIMATED peak power map of the HBM accelerator B2r2 die plan (TRIAL-HBM, die trial step 2).

    python3 tools/die_trial/hbm_b2_power.py PLAN.json --out power_map.json

Method: every partition gets an area x class density (W/mm2, a20 = 0.2 activity on every non-clock net, clock every
cycle, TT 0.70 V) from the MEASURED r25gp HBM-die block power (results/physical/die_evidence_20261009/
hbm_r25gp_power.json, masters[*].w_per_mm2_outline_a20 / proposed_dens).  The IO PHY contents (HBM3E PHY, 112G
SerDes macros, host UCIe) get their own power from repo-sourced energy/bit x bandwidth and replace the class density
inside their content rectangle.  Every number carries its source; ASSUMED marks a number with no measurement.
Output regions are die-frame rectangles: the IR tool rasterises (partition rect x class density) and then replaces the
density inside each IO content rect.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import schema as S  # noqa: E402

R25 = "results/physical/die_evidence_20261009/hbm_r25gp_power.json"
CLASS = {   # class: (W/mm2, source, grade)
    "sm": (2.1787, R25 + " masters.hfd_sm.w_per_mm2_outline_a20 (32 SMs, measured w/ 1 proxy part)", "measured, transferred to the HNX-SM P3 slot"),
    "su": (1.1271, R25 + " masters.hfd_su (measured lanes + estimated envelope)", "measured/estimated"),
    "sfu": (1.4375, R25 + " masters.hfd_sfu (measured lanes + estimated envelope)", "measured/estimated"),
    "hc": (0.7002, R25 + " masters.hfd_hc (measured lanes + estimated envelope)", "measured/estimated"),
    "idx": (1.05, R25 + " masters.hfd_idx_score_native_grid (25.205 W / 24.0045 mm2)", "ASSUMED (r25gp assumed class)"),
    "hub": (0.938, R25 + " proposed_dens.hub.measured_w_per_mm2 (7 masters, 74.8 mm2)", "measured"),
    "svc": (0.52, R25 + " proposed_dens.svc.measured_w_per_mm2", "measured"),
    "spine": (0.424, R25 + " proposed_dens.spine.measured_w_per_mm2 (9 masters: ft / spine / coll-class)", "measured"),
}
TYPE_CLASS = [("q_sm", "sm"), ("q_su", "su"), ("q_b11", "sfu"), ("q_b10", "idx"), ("q_b0", "hc"), ("q_hub", "hub"),
              ("root", "hub"), ("NW_io", "spine"), ("NE_io", "spine"), ("PHY_N", "spine")]
CONTENT_CLASS = {"hfd_ep_static": "hub", "ot_hbm_svc_sm_xcal_rel_t": "svc", "ot_static_run_target": "svc"}

# IO PHY power (repo-sourced energy per bit x bandwidth)
HBM_BW_BPS = 1.2e12 * 8          # configs/hardware/technology.json hbm.hbm3e.published_stack_ceiling (Micron, >1.2 TB/s)
HBM_PJ = 0.8e-12                 # results/rtl/hbm_accel_qwen_die_power_20261006/README.md "HBM PHY: 0.8 pJ/bit (O'Connor)"
HBM_IDLE_W = 2.8                 # configs/hardware/technology.json power.memory_interface_idle_w_per_stack (band 1.2-6.4)
SERDES_LANES, SERDES_GBPS = 6, 112.0   # tools/die_plan/die_io.py: ot_pdie_serdes = 6 x 112G PAM4 (614 Gb/s)
SERDES_PJ = 6.5e-12              # results/uarch/hbrom/inputs/hbrom-power.json primitives.link_j_per_bit.board_serdes_112g
UCIE_LANES, UCIE_GBPS = 64, 16.0       # die.io basis: UCIe-A x64 module; 16 GT/s ASSUMED (UCIe Adv 16)
UCIE_PJ = 0.5e-12                # results/uarch/hbrom/inputs/hbrom-power.json primitives.link_j_per_bit.ucie_advanced
PHY_W, PHY_H = 8500.032, 1177.2  # physical/asap7_memory_macros/ot_hbm3e_phy_rc_e8p5/ot_hbm3e_phy_rc_e8p5.lef SIZE


def io_power():
    hbm = HBM_BW_BPS * HBM_PJ + HBM_IDLE_W
    ser = SERDES_LANES * SERDES_GBPS * 1e9 * SERDES_PJ
    ucie = 2 * UCIE_LANES * UCIE_GBPS * 1e9 * UCIE_PJ
    return dict(
        ot_hbm3e_phy_rc_e8p5=dict(w=hbm, basis=f"{HBM_BW_BPS / 8e12:.1f} TB/s x {HBM_PJ * 1e12:.1f} pJ/bit + {HBM_IDLE_W} W idle",
                                  grade="ASSUMED (published bandwidth x sourced PHY pJ/bit; PHY on the core 0.7 V grid)",
                                  source="technology.json hbm.hbm3e.published_stack_ceiling; results/rtl/hbm_accel_qwen_die_power_20261006/README.md; technology.json power.memory_interface_idle_w_per_stack"),
        ot_pdie_serdes=dict(w=ser, basis=f"{SERDES_LANES} x {SERDES_GBPS:g} Gb/s x {SERDES_PJ * 1e12:.1f} pJ/bit (per-lane TX+RX efficiency)",
                            grade="ASSUMED rate (die_io.py), sourced pJ/bit",
                            source="tools/die_plan/die_io.py; results/uarch/hbrom/inputs/hbrom-power.json link_j_per_bit.board_serdes_112g"),
        ot_pdie_ucie_col=dict(w=ucie, basis=f"2 dir x {UCIE_LANES} lanes x {UCIE_GBPS:g} Gb/s x {UCIE_PJ * 1e12:.1f} pJ/bit",
                              grade="ASSUMED rate, sourced pJ/bit",
                              source="die.io basis (UCIe-A x64); results/uarch/hbrom/inputs/hbrom-power.json link_j_per_bit.ucie_advanced"))


def type_class(tn):
    for pre, c in TYPE_CLASS:
        if tn.startswith(pre):
            return c
    return "spine"


def die_rect(P, part, o, wh):
    (ax, ay), (bx, by) = P.to_die(part, o), P.to_die(part, (o[0] + wh[0], o[1] + wh[1]))
    return [round(min(ax, bx), 4), round(min(ay, by), 4), round(max(ax, bx), 4), round(max(ay, by), 4)]


def build(raw):
    P = S.Plan(raw)
    io = io_power()
    parts, specials, cores = [], [], []
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        t = P.types[tn]
        c = type_class(tn)
        dens = CLASS[c][0]
        r = list(P.rect(n))
        A = (r[2] - r[0]) * (r[3] - r[1]) / 1e6
        sp = []
        for ct in t.get("contents", []):
            m = ct["module"]
            if m == "ot_hbm3e_phy_rc_e8p5":        # PHY macro at the die edge (top of PHY_N, pins to the core)
                w, h = t["outline_um"]
                o = ((w - PHY_W) / 2, h - PHY_H)
                rr = die_rect(P, n, o, (PHY_W, PHY_H))
                sp.append(dict(inst=ct["inst"], module=m, rect_um=rr, w=io[m]["w"], kind="hbm_phy",
                               note="PHY macro placed at the die edge (top band of PHY_N, ASSUMED placement)"))
            elif m in io and "outline_um" in ct:
                rr = die_rect(P, n, ct["origin_um"], ct["outline_um"])
                sp.append(dict(inst=ct["inst"], module=m, rect_um=rr, w=io[m]["w"],
                               kind="serdes" if "serdes" in m else "ucie"))
            elif m in CONTENT_CLASS and "outline_um" in ct:
                rr = die_rect(P, n, ct["origin_um"], ct["outline_um"])
                cc = CONTENT_CLASS[m]
                a = (rr[2] - rr[0]) * (rr[3] - rr[1]) / 1e6
                sp.append(dict(inst=ct["inst"], module=m, rect_um=rr, w=a * CLASS[cc][0], kind=cc))
        sp_area = sum((s["rect_um"][2] - s["rect_um"][0]) * (s["rect_um"][3] - s["rect_um"][1]) for s in sp) / 1e6
        w = (A - sp_area) * dens + sum(s["w"] for s in sp)
        for s in sp:
            s["part"] = n
            s["w_per_mm2"] = round(s["w"] / ((s["rect_um"][2] - s["rect_um"][0]) * (s["rect_um"][3] - s["rect_um"][1]) / 1e6), 3)
            s["w"] = round(s["w"], 4)
        specials += sp
        parts.append(dict(name=n, type=tn, orient=p.get("orient", "R0"), rect_um=[round(v, 4) for v in r],
                          area_mm2=round(A, 4), cls=c, w_per_mm2=dens, w=round(w, 3),
                          cells=t.get("cells"), io_w=round(sum(s["w"] for s in sp if s["kind"] in ("hbm_phy", "serdes", "ucie")), 3)))
        for hc in t.get("hard_cores", []):
            rr = die_rect(P, n, hc["origin_um"], hc["outline_um"])
            a = (rr[2] - rr[0]) * (rr[3] - rr[1]) / 1e6
            cores.append(dict(part=n, inst=hc["inst"], module=hc["module"], rect_um=rr, w=round(a * dens, 4)))
    tot = sum(p["w"] for p in parts)
    by_cls = {}
    for p in parts:
        by_cls[p["cls"]] = round(by_cls.get(p["cls"], 0) + p["w"] - p["io_w"], 3)
    for s in specials:
        if s["kind"] in ("hbm_phy", "serdes", "ucie"):
            by_cls[s["kind"]] = round(by_cls.get(s["kind"], 0) + s["w"], 3)
    # cell-based cross-check: plan cell estimates x the measured logic-tile median W per instance at a20
    cells = sum((P.types[p["type"]].get("cells") or 0) for p in parts)
    hot = sorted(parts, key=lambda p: -p["w"] / p["area_mm2"])[:8]
    return dict(
        schema="opentallas.die_trial.power_map.v1", die=P.name, plan="physical/die_plan/hbm_arch/B2r2/die_plan.json",
        point="peak in-phase a20 (0.2 activity every non-clock net, clock every cycle), TT 0.70 V",
        grade="ESTIMATED: class densities measured on r25gp HBM-die blocks, transferred to B2r2 partitions by class; IO PHY ASSUMED rates x sourced pJ/bit",
        classes={k: dict(w_per_mm2=v[0], source=v[1], grade=v[2]) for k, v in CLASS.items()},
        io_power=io, die_area_mm2=round(P.W * P.H / 1e6, 3), total_w=round(tot, 2),
        avg_w_per_mm2=round(tot / (P.W * P.H / 1e6), 4), by_class_w=by_cls,
        cross_check=dict(plan_cells=cells, uw_per_cell_a20=0.33,
                         w=round(cells * 0.33e-6, 1),
                         note="plan cell estimates x 0.33 uW/inst (median of the measured r25gp logic tiles sm_tile/attn_hgrp/quant/mcast at a20). "
                              "Far below the area estimate: the B2r2 SM slot holds 8.28M cells in 22.7 mm2 (0.37 Mcell/mm2 vs 7.8 on the r25gp SM tile), "
                              "so the area x density map is the conservative (upper) load for IR."),
        hottest_partitions=[dict(name=p["name"], w=p["w"], w_per_mm2=round(p["w"] / p["area_mm2"], 3)) for p in hot],
        hottest_regions=sorted([dict(part=s["part"], inst=s["inst"], kind=s["kind"], w=s["w"], w_per_mm2=s["w_per_mm2"])
                                for s in specials], key=lambda s: -s["w_per_mm2"])[:8],
        partitions=parts, regions=specials, hard_cores=cores)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = build(S.load(a.plan))
    Path(a.out).write_text(json.dumps(d, indent=1) + "\n")
    print(json.dumps({k: d[k] for k in ("total_w", "avg_w_per_mm2", "by_class_w", "hottest_partitions", "hottest_regions", "cross_check")}, indent=1))


if __name__ == "__main__":
    main()
