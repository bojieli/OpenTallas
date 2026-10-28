#!/usr/bin/env python3
"""DIE-HEAD-3 (3): die_sta_related --core-view directory for a SIGNED HEAD core capsule
(results/head_core_clockfreeze_release/<elem>_signed: PROVENANCE.json, signoff.json, LEF, _tc.lib (TT), _BC.lib (FF)).

    mk_core_view.py CAPSULE_DIR PLAN_PINS_JSON OUT_VIEWDIR [--plan-pins-rel REL]

Writes OUT_VIEWDIR/<MODULE>_tt.lib (= capsule _tc.lib), <MODULE>_ff.lib (= _BC.lib), <MODULE>.lef, pins.json (the pin
file regenerated FROM THE SIGNED LEF by tools/s81_head/head_pins_from_lef.py, the same tool that made the plan pin
file), provenance.json {verdict, kit{pins_file, pins_sha256, pins_canon_sha256, outline_um}} and <MODULE>.core.json
{module, clock_pin, clock_latency_measured, signed numbers, sha256}.  Every number is copied from the capsule's own
files; fails closed when a capsule file's sha256 differs from PROVENANCE.json or the verdict is not SIGNED.
pins_canon_sha256 uses die_sta_related.canon_pins/canon_sha256 (GATE-PINS-2 content form), so the gate's pin match
compares the plan pin file with the signed LEF's own pins, not with a declared hash."""
import hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import die_sta_related as DSR  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv):
    cap, plan_pins, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    rel = argv[argv.index("--plan-pins-rel") + 1] if "--plan-pins-rel" in argv else str(plan_pins)
    prov = json.loads((cap / "PROVENANCE.json").read_text())
    so = json.loads((cap / "signoff.json").read_text())
    mod = prov["core"]
    if prov.get("verdict") != "SIGNED" or so.get("verdict") not in ("SIGNED", "PASS", "SIGNED-PASS"):
        raise SystemExit(f"{mod}: capsule verdict {prov.get('verdict')}/{so.get('verdict')} -> not a signed view")
    src = {"lef": cap / f"{mod}.lef", "tt": cap / f"{mod}_tc.lib", "ff": cap / f"{mod}_BC.lib"}
    for k, f in src.items():
        want = prov["sha256"].get(f.name)
        if want != sha(f):
            raise SystemExit(f"{mod}: {f.name} sha256 {sha(f)[:12]} != PROVENANCE {str(want)[:12]}")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src["lef"], out / f"{mod}.lef")
    shutil.copyfile(src["tt"], out / f"{mod}_tt.lib")
    shutil.copyfile(src["ff"], out / f"{mod}_ff.lib")
    subprocess.run([sys.executable, str(ROOT / "tools" / "s81_head" / "head_pins_from_lef.py"), str(out / f"{mod}.lef"),
                    str(out / "pins.json"), "--source-label", f"signed capsule {cap.name} LEF (PROVENANCE run {prov['run']})"],
                   check=True)
    pins = json.loads((out / "pins.json").read_text())
    canon = DSR.canon_sha256(DSR.canon_pins(pins, pins["outline_um"]))
    plan_doc = json.loads(plan_pins.read_text())
    plan_canon = DSR.canon_sha256(DSR.canon_pins(plan_doc, plan_doc.get("outline_um")))
    clk = re.search(r"clock\s*:\s*true", (out / f"{mod}_tt.lib").read_text())
    lt = (out / f"{mod}_tt.lib").read_text()
    m = re.search(r'pin\s*\(\s*"?([A-Za-z0-9_\[\]]+)"?\s*\)\s*\{[^{}]*?clock\s*:\s*true', lt)
    view_prov = dict(schema="opentallas.provenance.v1", verdict=prov["verdict"], core=mod, run=prov["run"],
                     src_commit=prov.get("src_commit"), flow_tag=prov.get("flow_tag"), capsule=str(cap),
                     signoff_generated=so.get("generated"),
                     kit=dict(pins_file=rel, pins_sha256=sha(out / "pins.json"), pins_canon_sha256=canon,
                              outline_um=pins["outline_um"], signed_lef_sha256=prov["sha256"][f"{mod}.lef"]),
                     plan_pins=dict(file=rel, sha256=sha(plan_pins), canon_sha256=plan_canon,
                                    content_equal_signed_lef=plan_canon == canon),
                     freshness="UNCHECKED here: capsule signoff.generated vs run mtime is the capsule packager's check "
                               "(HEAD-R22 / codex head-1351 receipts)")
    (out / "provenance.json").write_text(json.dumps(view_prov, indent=1) + "\n")
    core = dict(module=mod, clock_pin=m.group(1) if m else None,
                clock_latency_measured=so.get("core_latency"),
                signed=dict(setup_tt_wns_ps=so["checks"]["setup_tt"]["wns_ps"], hold_ff_wns_ps=so["checks"]["hold_ff"]["wns_ps"]),
                libs=dict(TT=f"{mod}_tt.lib <- {src['tt'].name}", FF=f"{mod}_ff.lib <- {src['ff'].name}"),
                sha256={f.name: prov["sha256"][f.name] for f in src.values()},
                note="DIE-HEAD-3 mk_core_view.py: all values copied from the signed capsule; no number derived here")
    (out / f"{mod}.core.json").write_text(json.dumps(core, indent=1) + "\n")
    print(mod, "canon", canon[:12], "plan canon", plan_canon[:12], "EQUAL" if plan_canon == canon else "DIFFERS",
          "clock_pin", core["clock_pin"], "latency", json.dumps(so.get("core_latency"))[:120])


if __name__ == "__main__":
    main(sys.argv[1:])
