#!/usr/bin/env python3
"""QC PG IR at WORST-CASE power (METHODOLOGY 12.7a/12.7b): explicit, recorded power inputs per region, native PDNSim
window/coupon kits (core: infra_pg.window_kit; UCIe: infra_pg_domains.make with PHY-local reinforcement) and the IR
verdict written into a PG json die_infra.pg_ir_state() reads (top-level ir_verdict + per-region psm{...: {verdict}}).

  gen-core OUT       core_centre coupon at the worst-case core density, 100-um C4
  gen-ucie OUT       UCIe window: published 16-col field (all vacants supply), separate VDDPHY, dense M8/M9 + M7 straps
  verdict --core DIR --ucie DIR --out pg.json
No plan edit, no signed view touched.
"""
import argparse, json, re, sys
from pathlib import Path
import infra_pg as I
import infra_pg_domains as X

VDD, BUDGET_FRAC = 0.7, 0.05
# ---------------------------------------------------------------- worst-case power (the ONLY power inputs used here)
_CAP_W, _DESIGN_W, _AREA = 474.56, 618.55, 815.0          # results/arch/power_scenarios.json qwen3_8b_rom_8k.ar_batch1
WORST_CASE = {
    "core": dict(
        w_mm2=round(_DESIGN_W / _AREA, 6),
        sustained_w_mm2=round(_CAP_W / _AREA, 6),
        peak_activity="ar_batch1 die_w_at_design_rate 618.55 W = the full-rate static schedule at 100% issue, UNCAPPED "
                      "(results/arch/power_scenarios.json A_measured_implementation.qwen3_8b_rom_8k)",
        margin="x1.303 over the 474.56 W liquid-cooling cap the die can sustain (0.5823 W/mm2, the density used by "
               "every earlier QC coupon); dflash 1116 W design rate is 2.35x the cap and cannot be issued by the static "
               "schedule (excluded, recorded)",
        per_type="one density for every core type: no per-type measured power exists yet; the uncapped design-rate "
                 "density is applied to every partition (hottest-type density <= die design-rate average is an "
                 "ASSUMPTION to replace with per-type power when the kits report it)"),
    "ucie": dict(
        w=round(I.UCIE_X64_W, 6),
        peak_activity="UCIe x64: 128 lanes (64 TX + 64 RX) x 32 GT/s x 0.6 pJ/b, all lanes toggling at full rate "
                      "(PHY_ASSUMPTIONS UCIE.ENERGY upper end, UCIE.RATE 32 GT/s)",
        margin="x1.0: 0.6 pJ/b is already the published UPPER energy at the maximum rate; no idle/low-power credit",
        distribution="uniform over the full 777.6 x 777.6 um PHY footprint (no AFE-only credit)"),
    "serdes": dict(w_per_macro=4.37, note="PHY_ASSUMPTIONS SER.MACRO6_POWER published 4.37 W per active 6-lane macro; "
                                          "3 SerDes windows NOT run in this pass"),
}
CORE_C4_PITCH = 100.0
PHY_M7_PITCH = 0.768     # VDDPHY/VSS 0.288-um M7 strap pairs: 75 % M7 inside the PHY footprint only
R = Path(__file__).resolve().parents[2]
PLAN = R / "physical/die_plan/qwen_compute/die_plan_b12.json"
PG = R / "results/infra_pg_1026/candidate130/pg.json"


def _plan():
    return I.S.Plan(I.S.load(PLAN), PLAN)


def _pg(src):
    pg = json.loads(Path(src).read_text())
    pg["core_w_mm2"] = WORST_CASE["core"]["w_mm2"]
    pg["bump_pitch_um"] = CORE_C4_PITCH
    return pg


def gen_core(a):
    P = _plan(); pg = _pg(a.pg)
    win = next(x for x in I.default_windows(P, pg, core_um=864) if x["name"] == "core_centre")
    m = I.window_kit(P, PLAN.parent, pg, Path(a.out), win["name"], win["rect_um"], core_w_mm2=pg["core_w_mm2"])
    m["worst_case"] = WORST_CASE["core"]; (Path(a.out) / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
    print(json.dumps({k: m[k] for k in m if k in ("power_w", "window_um", "bumps")}, default=str)[:400])


def gen_ucie(a):
    P = _plan(); pg = _pg(a.pg)
    win = json.loads(Path(a.window).read_text())
    bumps = json.loads(Path(a.bumps).read_text())["bumps"]
    m = X.make(P, PLAN.parent, pg, win, Path(a.out), .72, bumps, phy_m7_pitch=a.m7_pitch, phy_m6_pitch=a.m6_pitch, phy_m5_pitch=a.m5_pitch,
               power={"core_w_mm2": WORST_CASE["core"]["w_mm2"]})
    print(json.dumps({k: m[k] for k in ("power_w", "phy_grid", "phy_m7_pitch_um", "phy_m6_pitch_um", "load_blocks")}))


def _psm(log):
    t = Path(log).read_text(); out = {}
    for net, body in re.findall(r"Net\s*:\s*(\S+)(.*?)######", t, re.S):
        g = lambda k: float(re.search(k + r"\s*:\s*([-0-9.e+]+)", body).group(1))
        out[net] = dict(power_w=g("Total power"), worst_mv=round(g("Worstcase IR drop") * 1e3, 3),
                        avg_mv=round(g("Average IR drop") * 1e3, 3))
    conn = {n: f"All shapes on net {n} are connected" in t for n in out}
    return out, conn, "OT_DONE" in t


def verdict(a):
    budget = BUDGET_FRAC * VDD * 1e3; psm = {}
    for name, d, nets in (("core_centre", a.core, ["VDD"]), ("io_ucie_kv_u_ucie_kv", a.ucie, ["VDD", "VDDPHY"])):
        lg = Path(d) / "psm/psm.log"
        r, conn, done = _psm(lg if lg.exists() else Path(d) / "psm.log")   # run dir or its results/ copy
        for n in nets:
            key = name if n == "VDD" and name == "core_centre" else (f"{name}:{n}")
            ok = done and n in r and conn.get(n)
            psm[key] = dict(run=str(d), net=n, **r.get(n, {}), budget_mv=budget, continuity="PASS" if conn.get(n) else "FAIL",
                            verdict="PASS" if ok and r[n]["worst_mv"] <= budget else "FAIL")
    pg = _pg(a.pg)
    pg.update(worst_case_power=WORST_CASE, core_c4_pitch_um=CORE_C4_PITCH, phy_m7_strap_pair_pitch_um=PHY_M7_PITCH, psm=psm,
              ir_verdict="PASS" if all(v["verdict"] == "PASS" for v in psm.values()) else "FAIL",
              ir_scope="native PDNSim coupons (core_centre 864 um, UCIe window) at WORST_CASE power; VDD/VDDPHY nets; "
                       "3 SerDes + coll_ucie windows not run (coll_ucie = same PHY/template)",
              tool="tools/die_plan/infra_pg_worstcase.py")
    Path(a.out).write_text(json.dumps(pg, indent=1) + "\n")
    print(json.dumps(dict(ir_verdict=pg["ir_verdict"], psm=psm), indent=1))
    return 0 if pg["ir_verdict"] == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__); sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("gen-core", "gen-ucie", "verdict"):
        s = sp.add_parser(n); s.add_argument("--pg", default=str(PG))
        if n != "verdict": s.add_argument("out")
    sp.choices["gen-ucie"].add_argument("--window", required=True); sp.choices["gen-ucie"].add_argument("--bumps", required=True)
    sp.choices["gen-ucie"].add_argument("--m7-pitch", type=float, default=PHY_M7_PITCH)
    sp.choices["gen-ucie"].add_argument("--m6-pitch", type=float, default=None)
    sp.choices["gen-ucie"].add_argument("--m5-pitch", type=float, default=None)
    v = sp.choices["verdict"]; v.add_argument("--core", required=True); v.add_argument("--ucie", required=True); v.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"gen-core": gen_core, "gen-ucie": gen_ucie, "verdict": verdict}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
