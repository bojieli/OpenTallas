#!/usr/bin/env python3
"""HBM-SMXL (10-19/20): units_variants/smhbm_xl.json -- SM.MATVEC with the die x loader and x-load early issue.

Same schema and matching as toksim_smhbm_succ_units.py (successor PC, rotated layout, census rows, static GO cadence
80/64+8), but measured with tb_toksim_smhbm built -DXSLOT -DOPEN_IL (descriptor x slot base relocates every command's
xaddr = the die SM op_xb from the static programme; producer open interlock) and the compiler's SMB_XMODE:
  die  = die x-loader beat set (2 beats / x word, ctlx RL55 cadence), serial;
  xl   = die + ISSUE_AHEAD 1 static slot ring (RAW records stay serial);
  xlr  = xl + x reuse of a resident slot (same A descriptor + format, no writer between).
Qwen: every SM record's x is produced just before it (RAW), so the early issue does not apply; the Qwen rows are the
XSLOT/OPEN_IL re-runs of the TOKSIM t_* shapes (spans identical to the release runs).

  toksim_smhbm_xl_units.py RUNS_DIR CENSUS FIXROOT BRANCH OUT DSA,DSB QWEN_PREFIX MODE
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    runs, census, fix, branch, out, dsab, qpre, mode = sys.argv[1:9]
    R = Path(runs)
    with tempfile.TemporaryDirectory() as td:
        T = Path(td)
        for n in dsab.split(","):
            (T / f"{n}.json").symlink_to((R / f"{n}.json").resolve())
        for n in ("qkv48", "o128", "gu192", "down128"):
            (T / f"t_{n}_p80.json").symlink_to((R / f"{qpre}{n}.json").resolve())
        subprocess.run([sys.executable, str(HERE / "toksim_smhbm_succ_units.py"), str(T), census, fix, branch, out, "80", dsab],
                       check=True)
    doc = json.loads(Path(out).read_text())
    note = {"die": "die x loader (2 beats/word, ctlx RL55 cadence), serial x (slot 0)",
            "xl": "die x loader + ISSUE_AHEAD 1 static x slot ring (XSLOT: descriptor xb -> command xaddr, die op_xb)",
            "xlr": "xl + x reuse of a resident slot (same A + format, no writer between)"}[mode]
    doc.update(group="smhbm_xl", variant=mode, variant_note=note,
               rtl_defines="XSLOT OPEN_IL (ot_hbm_svc_sm_group_rel_id #(.XSLOT(1), .OPEN_IL(1)))",
               controller="successor SAFE (not bound in GEN2e3), rotated layout, x-load early issue")
    for d in doc["designs"].values():
        c = d["SM.MATVEC"]
        c["grade"] = "measured-newest-bench-passing-not-bound"
        c["xmode"] = mode
        for s in c["shapes"].values():
            if s.get("cycles") is not None:
                s["notes"] = (s.get("notes", "") + f"; HBM-SMXL {mode}: {note}").replace(
                    "toksim-smhbm-1019/out", "hbm-smxl-1019/out")
                s["job"] = s.get("job", "").replace("toksim-smhbm-1019", "hbm-smxl-1019")
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    main()
