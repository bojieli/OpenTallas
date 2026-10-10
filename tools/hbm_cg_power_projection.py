#!/usr/bin/env python3
"""redesign-hbm 2026-10-09: R25GP die power under COARSE PER-UNIT CLOCK GATING -- a PROJECTION from the measured
per-block power (results/physical/die_evidence_20261009/hbm_r25gp_power.json: a20 = peak in phase, a00 = clocked idle
floor) and the measured unit duties (its options.b_duty_mix), until die-evidence-2 re-measures the gated routes.

Per master: gated parts cost  duty x a20 + (1 - duty) x (r x a00 + leak)   (r = residual clock above the ICG clones and the
wake flops, bracketed 0.05 / 0.15 until the gated routes are measured); ungated parts cost duty x a20 + (1 - duty) x a00.
Scenarios: none (no ICG), smatt (SM tiles / back ends + attention quads: the built gating), all (every hub unit too).
Relay stations at their a00 floor + the duty-mix die wires (evidence wire_w).  Exits 1 if the built scenario exceeds the
cooling limit at the bracket's high residual.
    python3 tools/hbm_cg_power_projection.py [--evidence J] --out OUT.json
"""
import argparse, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
UNIT = {"sm": "SM", "attn_tile": "ATT", "svc": "SVC"}
HUB = {"hfd_su": "SU+FUSED", "hfd_sfu": "SFU", "hfd_hc": "HC", "hfd_idx_score_native_grid": "IDX", "hfd_coll": "COLL"}
# gated fraction of a master's power (measured part shares): SM = 16 tiles + 8 back ends of the 7.93 W SM (fronts ungated);
# attention half = its 8 hgrp leaves (the quad HC banks, relay banks and half top stay on the raw clock)
def gated_share(m, v):
    parts = v.get("parts") or []
    tot = sum(p["count"] * (p.get("w_each_a20") or 0) for p in parts) or 1.0
    if v["kind"] == "sm":
        g = sum(p["count"] * p["w_each_a20"] for p in parts if p["part"].startswith(("sm_tile", "sm_be")))
    elif v["kind"] == "attn_tile":
        g = sum(p["count"] * p["w_each_a20"] for p in parts if p["part"] == "attn_hgrp")
    else:
        return 0.0
    return g / tot
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", default=str(ROOT / "results/physical/die_evidence_20261009/hbm_r25gp_power.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.loads(Path(a.evidence).read_text())
    limit = d["cooling_limit_w"]
    out = dict(schema="opentallas.redesign_hbm.cg_power_projection.v1", evidence=a.evidence, cooling_limit_w=limit,
               grade="PROJECTION (measured per-block a20 / a00 + measured duties; gated residual r bracketed) -- to be "
                     "replaced by die-evidence-2's re-measure of the gated routes", workloads={})
    for wl, mix in d["options"]["b_duty_mix"].items():
        duty = mix["duty"]
        res = {}
        for scen in ("none", "smatt", "all"):
            for r in (0.05, 0.15):
                tot = 0.0
                for m, v in d["masters"].items():
                    w = v.get("w") or {}
                    a20 = w.get("a20", v.get("assumed_w", 0.0)) or 0.0
                    a00 = w.get("a00")
                    if a00 is None:
                        a00 = a20 * d["total"]["assumed_point_ratios_from_measured"]["a00_over_a20"]
                    leak = v.get("leak_w", 0.0) or 0.0
                    u = UNIT.get(v["kind"]) or HUB.get(m) or "ON"
                    dt = duty.get(u, 1.0)
                    if scen == "none":
                        gs = 0.0
                    elif scen == "smatt":
                        gs = gated_share(m, v)
                    else:
                        gs = gated_share(m, v) if v["kind"] in ("sm", "attn_tile") else (1.0 if u != "ON" else 0.0)
                    idle = (1 - gs) * a00 + gs * (r * a00 + leak)
                    tot += dt * a20 + (1 - dt) * idle
                tot += d["relay_stations"]["w"]["a00"] + mix.get("wire_w", 0.0)
                res[f"{scen}_r{int(r*100):02d}"] = round(tot, 1)
        out["workloads"][wl] = dict(duty=duty, evidence_no_icg_w=mix.get("no_icg_w"), evidence_with_icg_w=mix.get("with_icg_w"),
                                    projection_w=res)
    env = out["workloads"]["envelope_max"]["projection_w"]
    out["verdict"] = dict(built_scenario="smatt", envelope_max_w_high_residual=env["smatt_r15"], limit_w=limit,
                          passes=env["smatt_r15"] <= limit,
                          note="the peak in-phase a20 point (613.5 W) assumes every unit busy at once, which the measured "
                               "workloads never do; gating changes the duty-mix point, not a20")
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v["projection_w"] for k, v in out["workloads"].items()}, indent=1))
    print("VERDICT", out["verdict"])
    return 0 if out["verdict"]["passes"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
