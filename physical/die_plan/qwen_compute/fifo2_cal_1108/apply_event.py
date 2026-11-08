"""QC calendar FIFO2 plan event (DIE-QC-93, 2026-11-08). R5 READY plan event for adopting FIFO2.

What changes (only partition type tt_ctlm; no other type, no cycles, no ports):
  * plan: tt_ctlm drops its four hard cores u_bound.u_core.u_gi.u_cal.g_fifo[0..3].u_fifo
    (ot_sram_1r1w_64x512_m1_r2c2, 171.288x77.784 each). They become standard-cell storage.
  * asbuilt: the tt_ctlm source rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv
    is replaced by its *_fifo2.sv alternate. That alternate changes only the four g_fifo master tokens to
    ot_qc_cal_fifo2_512; every port connection is byte-identical. The helper rtl/physical/ot_qc_cal_fifo2_512.sv
    is added to "files".
Proof of the helper: tools/qwen_dv/cal_fifo2_0222 (run1 PASS: 792x512-bit reads, 0 differences against the
old macro .v; the wrong-row and extra-edge mutants are detected). It assumes the constructor precondition:
literal 0/1 addresses and zero repair inputs.
Data cycles 0, pin cycles 0, boot cycles 0.
The tt_ctlm base type and the asbuilt prefer entry are hash/literal guarded. A changed base is refused.
"""
import argparse, copy, hashlib, json, re
from pathlib import Path

TYPE = "tt_ctlm"
FIFO_RE = re.compile(r"u_bound\.u_core\.u_gi\.u_cal\.g_fifo\[[0-3]\]\.u_fifo")
FIFO_MODULE = "ot_sram_1r1w_64x512_m1_r2c2"
OLD_SRC = "rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv"
NEW_SRC = "rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_fifo2.sv"
HELPER = "rtl/physical/ot_qc_cal_fifo2_512.sv"


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def patch_type(t):
    t = copy.deepcopy(t)
    removed = [h for h in t["hard_cores"] if FIFO_RE.fullmatch(h["inst"])]
    assert len(removed) == 4 and all(h["module"] == FIFO_MODULE for h in removed), [h["inst"] for h in removed]
    t["hard_cores"] = [h for h in t["hard_cores"] if not FIFO_RE.fullmatch(h["inst"])]
    assert "g_fifo" not in json.dumps(t), "residual g_fifo reference in tt_ctlm"
    t["note"] = (t.get("note") or "") + " | DIE-QC-93 11-08 FIFO2: 4 calendar FIFO SRAMs -> ot_qc_cal_fifo2_512 cells"
    return t, [h["inst"] for h in removed]


def patch_asbuilt(a):
    a = copy.deepcopy(a)
    pref = a["prefer"]
    assert pref.count(OLD_SRC) == 1 and NEW_SRC not in pref, "asbuilt prefer base changed"
    a["prefer"] = [NEW_SRC if x == OLD_SRC else x for x in pref]
    if HELPER not in a["files"]:
        a["files"] = list(a["files"]) + [HELPER]
    a["note"] = (a.get("note") or "") + " | DIE-QC-93 11-08 FIFO2 source swap (tt_ctlm only)"
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out-plan", required=True, type=Path)
    ap.add_argument("--asbuilt", action="append", type=Path, default=[])
    ap.add_argument("--out-asbuilt", action="append", type=Path, default=[])
    ap.add_argument("--write-guards", action="store_true")
    a = ap.parse_args()
    assert len(a.asbuilt) == len(a.out_asbuilt)
    plan = json.loads(a.plan.read_text())
    gpath = Path(__file__).resolve().parent / "base_guards.json"
    if a.write_guards:
        gpath.write_text(json.dumps({TYPE: digest(plan["partition_types"][TYPE])}, indent=1) + "\n")
    guards = json.loads(gpath.read_text())
    if digest(plan["partition_types"][TYPE]) != guards[TYPE]:
        raise SystemExit(TYPE + ": base type changed; review composition")
    plan["partition_types"][TYPE], removed = patch_type(plan["partition_types"][TYPE])
    a.out_plan.write_text(json.dumps(plan, indent=1) + "\n")
    for src, dst in zip(a.asbuilt, a.out_asbuilt):
        dst.write_text(json.dumps(patch_asbuilt(json.loads(src.read_text())), indent=1) + "\n")
    print(json.dumps({"types": [TYPE], "removed_hard_cores": removed, "data_cycles": 0, "pin_cycles": 0,
                      "boot_cycles": 0, "asbuilt_patched": len(a.asbuilt)}))


if __name__ == "__main__":
    main()
