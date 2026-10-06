#!/usr/bin/env python3
"""W18 corner STA (tools/w18/corner_sta.py, unchanged policy) with an extra boundary SDC read after the propagated
clock is set, for blocks whose boundary delays are referenced to their own clock tree (-reference_pin; such an SDC
cannot be loaded with the design).  Also lists every violating path (startpoint, endpoint, slack) for class grouping."""
import argparse
import json
import shutil
from pathlib import Path

import corner_sta as C

_orig = C.script


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--extra-sdc", type=Path, required=True)
    ap.add_argument("--macro", action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    o = a.orfs_dir.resolve()
    shutil.copy(a.extra_sdc, o / "w18_extra.sdc")

    def script(corner, base, macros):
        s = _orig(corner, base, macros)
        check = "max" if corner == "ss" else "min"
        s = s.replace("set_propagated_clock [all_clocks]\n",
                      "set_propagated_clock [all_clocks]\nread_sdc /work/w18_extra.sdc\n", 1)
        listing = (f"foreach p [find_timing_paths -path_delay {check} -group_path_count 5000 -endpoint_path_count 1 "
                   f"-slack_max 0] {{ puts \"OT_PATH [get_full_name [get_property $p startpoint]] "
                   f"[get_full_name [get_property $p endpoint]] [get_property $p slack]\" }}\nexit\n")
        return s.rsplit("exit\n", 1)[0] + listing

    C.script = script
    rec = dict(schema="opentallas.w18.corner_sta.v1", orfs_dir=str(o), extra_sdc=a.extra_sdc.read_text(),
               setup_ss=C.run(o, "ss", a.macro), hold_ff=C.run(o, "ff", a.macro), libraries=C.LIBS,
               tool_sha256=C.sha(Path(C.__file__)),
               policy="AGENTS.md sign-off corners (2026-09-30): setup at SS, hold at FF, 60/25 ps")
    rec["closes_signoff"] = bool(rec["setup_ss"]["worst_slack_ps"] is not None and rec["setup_ss"]["worst_slack_ps"] >= 0
                                 and rec["hold_ff"]["worst_slack_ps"] is not None and rec["hold_ff"]["worst_slack_ps"] >= 0)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("setup_ss", "hold_ff", "closes_signoff")}, indent=1))


if __name__ == "__main__":
    main()
