#!/usr/bin/env python3
"""DH58-PROTO: die_sta_related --core-view directory with a TYPED hard_core_latency contract for a signed HEAD core whose
view has no <MODULE>.core.json (lep_pair, kp4_dchn).  Same output form as results/die_head_1027/scripts/mk_core_view.py
(elemA/elemB): <MODULE>_{tt,ff}.lib, <MODULE>.lef, pins.json (from the signed LEF via tools/s81_head/head_pins_from_lef.py),
provenance.json, <MODULE>.core.json.  Every number is COPIED from the signed signoff.json (corners.<c>.insertion_pinflops =
pin-register clock insertion, the same basis as the elemA/elemB contracts); nothing is derived here.

  mk_typed_view.py MODULE CLOCK_PIN TT_LIB FF_LIB LEF SIGNOFF_JSON RESIGN_PROVENANCE_JSON PLAN_PINS_JSON PLAN_PINS_REL OUT"""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import die_sta_related as DSR  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(a):
    mod, clk, tt, ff, lef, so_p, pv_p, plan_pins, rel, out = a
    so, pv = json.loads(Path(so_p).read_text()), json.loads(Path(pv_p).read_text())
    if so.get("verdict") != "SIGNED" or not str(pv.get("verdict", "")).startswith("SIGNED"):
        raise SystemExit(f"{mod}: verdict {so.get('verdict')}/{pv.get('verdict')} -> not a signed view")
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tt, out / f"{mod}_tt.lib"); shutil.copyfile(ff, out / f"{mod}_ff.lib"); shutil.copyfile(lef, out / f"{mod}.lef")
    subprocess.run([sys.executable, str(ROOT / "tools" / "s81_head" / "head_pins_from_lef.py"), str(out / f"{mod}.lef"),
                    str(out / "pins.json"), "--source-label", f"signed LEF {lef}"], check=True)
    pins = json.loads((out / "pins.json").read_text())
    canon = DSR.canon_sha256(DSR.canon_pins(pins, pins["outline_um"]))
    pd = json.loads(Path(plan_pins).read_text())
    plan_canon = DSR.canon_sha256(DSR.canon_pins(pd, pd.get("outline_um")))
    meas = {c: so["corners"][c]["insertion_pinflops"] for c in ("tt", "ff")}
    prov = dict(schema="opentallas.provenance.v1", verdict="SIGNED", core=mod, run=so["inputs"].get("orfs"),
                src_commit=pv.get("src_commit"), flow_tag=pv.get("flow_tag"), signoff=str(so_p), resign_provenance=str(pv_p),
                lec_verdict=pv.get("lec_verdict"), signoff_generated=so.get("generated"),
                kit=dict(pins_file=rel, pins_sha256=sha(out / "pins.json"), pins_canon_sha256=canon,
                         outline_um=pins["outline_um"], signed_lef_sha256=sha(lef)),
                plan_pins=dict(file=rel, sha256=sha(plan_pins), canon_sha256=plan_canon, content_equal_signed_lef=plan_canon == canon),
                sha256={f"{mod}_tt.lib": sha(tt), f"{mod}_ff.lib": sha(ff), f"{mod}.lef": sha(lef)})
    (out / "provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    core = dict(module=mod, clock_pin=clk,
                clock_latency_measured=dict(contract=dict(kind="hard_core_latency", clock_port=clk,
                                                          basis="publish measured routed core insertion (signed signoff.json "
                                                                "corners.<c>.insertion_pinflops); common latency is a design target"),
                                            measured=meas),
                signed=dict(setup_tt_wns_ps=so["checks"]["setup_tt"]["wns_ps"], hold_ff_wns_ps=so["checks"]["hold_ff"]["wns_ps"]),
                libs=dict(TT=f"{mod}_tt.lib <- {Path(tt).name}", FF=f"{mod}_ff.lib <- {Path(ff).name}"),
                note="DH58-PROTO mk_typed_view.py: values copied from the signed signoff.json; no number derived here")
    (out / f"{mod}.core.json").write_text(json.dumps(core, indent=1) + "\n")
    print(mod, "canon", canon[:12], "plan", plan_canon[:12], "EQUAL" if plan_canon == canon else "DIFFERS",
          "TT", meas["tt"]["mean"], "FF", meas["ff"]["mean"])


if __name__ == "__main__":
    main(sys.argv[1:])
