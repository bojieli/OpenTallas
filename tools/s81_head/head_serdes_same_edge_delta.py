#!/usr/bin/env python3
"""DIE-HEAD-75 (COORD 11-06 09:41 (2) / 10:01 (1) / 10:2x): one-block HEAD plan event l48ui on l48uh, hd_serdes only.

Declares the PHY receive data pma_rx as source-synchronous on its recovered clock pma_rck with SAME-EDGE eye capture
(tools/die_plan/pad_clock.py data_inputs capture=same_edge + eye_hold_extra_ps, merged I205 main 373b6eb241f):

  data_inputs: [{port pma_rx, max_ps 166.6, min_ps -90, capture same_edge, eye_hold_extra_ps 175}]

  max/min = the existing pma_rx input budget (Codex c5dcefaa8a, unchanged); eye_hold_extra_ps 175 = measured TT-FF
  stage-0 capture insertion gap 150-156 ps + margin (DIE-HEAD-74 09:35 F1 STA on the vB 4_cts DB).  Generated SDC:
  set_input_delay -max 166.6 / -min -265 -clock pma_rck on pma_rx[*] + set_multicycle_path 0 -setup -from pma_rx[*].
  Probe proof (DIE-HEAD-74 09:43, form (a)): same-edge + hold repair on pma_rx->l0 -> TT hold +25.28, FF hold
  +136.69, setup +389.54 / +314.08, all 544 bits.

SDC only: no outline, pin, bus, macro, strap, clock tree, reset or RTL key changes, 0 data cycles.  The hd_serdes
wrapper is regenerated and must stay byte-identical (asserted); wave_prepare.json digests are refreshed.

usage: head_serdes_same_edge_delta.py SRC_PREPARED_DIR OUT_DIR --republish TOOLS_ROOT [--event l48ui]
"""
import argparse, json, shutil, sys
from pathlib import Path

TYPE = "hd_serdes"
CLOCK_PAD = "pma_rck"
ROW = {"port": "pma_rx", "max_ps": 166.6, "min_ps": -90.0, "capture": "same_edge", "eye_hold_extra_ps": 175.0,
       "evidence": ("pma_rx is launched by the far-die PMA on the recovered clock pma_rck (ot_pdie_serdes.sv rxq "
                    "samples pma_rx on pma_rck; Codex c5dcefaa8a budget max 166.6 / min -90 unchanged). The rck "
                    "capture tree is ~1 pad period deep, so l0 samples the data of the SAME pma_rck edge "
                    "(DIE-HEAD-74 11-06 09:35 F1 OpenSTA on the hd_serdes vB 4_cts DB, TT + FF); eye_hold_extra_ps "
                    "175 = measured TT-FF stage-0 insertion gap 150-156 + margin, so FF hold sign-off covers the TT "
                    "eye edge. Probe 09:43: hold repair on pma_rx->l0 gives TT hold +25.28 / FF hold +136.69 / "
                    "setup +389.54 TT, +314.08 FF on all 544 bits. COORD 11-06 09:41 (2) + 10:01 (1) accepted.")}


def add_row(plan):
    T = plan["partition_types"][TYPE]
    pins = T["clock"]["pad_clock"]["pins"]
    rck = [p for p in pins if p.get("name") == CLOCK_PAD]
    assert len(rck) == 1 and rck[0]["dir"] == "in", rck
    assert "data_inputs" not in rck[0], ("already declared", rck[0]["data_inputs"])
    rck[0]["data_inputs"] = [dict(ROW)]
    return rck[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--republish", type=Path, required=True, help="tools root (>= main 373b6eb241f) with gen.py")
    ap.add_argument("--event", default="l48ui")
    a = ap.parse_args(argv)
    root = a.republish.resolve()
    sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
    import head_cland_stage_delta as D
    import pad_clock as PC, schema
    plan = json.loads((a.src / "source_plan.json").read_text())
    add_row(plan)
    P = schema.Plan(json.loads(json.dumps(plan)))           # schema + fail-closed pad_clock validation
    PC.pins(P, TYPE)
    sdc = PC.sdc(P, TYPE, "set non_clk_in [all_inputs -no_clocks]\n")
    assert "set_multicycle_path 0 -setup -from [get_ports {pma_rx[*]}]" in sdc, sdc
    old_rec = json.loads((a.src / "wave_prepare.json").read_text())
    if a.out.exists():
        D.writable(a.out)
        shutil.rmtree(a.out)
    shutil.copytree(a.src, a.out, symlinks=True)
    D.writable(a.out)
    (a.out / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    D.republish(a.out, root, [TYPE], a.out / "source_sidecar.json")
    rec = json.loads((a.out / "wave_prepare.json").read_text())
    old_w, new_w = old_rec["published_wrappers"].get(TYPE), rec["published_wrappers"][TYPE]
    assert old_w == new_w, ("hd_serdes wrapper changed: the event must be SDC only", old_w, new_w)
    assert rec["sidecar_sha256"] == old_rec["sidecar_sha256"]
    rec[a.event] = dict(event=a.event, tool="tools/s81_head/head_serdes_same_edge_delta.py", type=TYPE,
                        base_prepared=str(a.src), base_prepared_plan_sha256=old_rec["prepared_plan_sha256"],
                        data_inputs=[ROW], data_cycles_added=0, wrapper_unchanged=True)
    (a.out / "wave_prepare.json").write_text(json.dumps(rec, indent=1) + "\n")
    sums = a.out / "SHA256SUMS"
    if sums.exists():
        lines = []
        for ln in sums.read_text().splitlines():
            h, _, name = ln.partition("  ")
            p = a.out / name
            lines.append(f"{D.digest(p)}  {name}" if p.is_file() and not p.is_symlink() else ln)
        sums.write_text("\n".join(lines) + "\n")
    report = dict(event=a.event, type=TYPE, plan_sha256=rec["prepared_plan_sha256"],
                  sidecar_sha256=rec["sidecar_sha256"], wrapper=new_w,
                  sdc_lines=[l for l in sdc.splitlines() if "pma_rx" in l])
    (a.out / "same_edge_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
