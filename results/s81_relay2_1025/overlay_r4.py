#!/usr/bin/env python3
"""CLOCK-RESET/relay2 10-25: apply the Codex legacy r4 recipe (codex/s81-legacy-1025, kits/{rstg,payload}_r4_m5:
HOLD_SLACK_MARGIN 5, SLEW_MARGIN 50, OT_TAP_PORT ck, SKIP_INCREMENTAL_REPAIR + post-GRT hold-only hook, CTS without
timing repair, post-CTS FF hold STOP gate, raw+ODB face_guard) onto a freshly generated gen_core_kit_legacy.py kit.
Only recipe files are taken from r4; RTL, pins, SDC, face_guard/face_flops/signoff tools stay the generated (main) ones.
    overlay_r4.py R4_KIT NEW_KIT [HOLD_MARGIN_PS]"""
import re, shutil, sys
from pathlib import Path
r4, kd = Path(sys.argv[1]), Path(sys.argv[2])
hm = sys.argv[3] if len(sys.argv) > 3 else "5"
for f in ("cts_post.tcl", "cts_hold_gate.tcl", "run_kit.sh"):
    shutil.copy2(r4 / f, kd / f)
nick = re.search(r"^export DESIGN_NICKNAME = (\S+)$", (kd / "config.mk").read_text(), re.M).group(1)
c = (r4 / "config.mk").read_text()
c = re.sub(r"^export DESIGN_NICKNAME = \S+$", "export DESIGN_NICKNAME = " + nick, c, flags=re.M)
c = re.sub(r"^export HOLD_SLACK_MARGIN = \S+$", "export HOLD_SLACK_MARGIN = " + hm, c, flags=re.M)
gen = (kd / "config.mk").read_text()
# the r4 config must differ from the generated one only in the recipe keys
keys = lambda t: {l for l in t.splitlines() if l and not l.startswith("#") and not re.match(
    r"export (DESIGN_NICKNAME|HOLD_SLACK_MARGIN|SLEW_MARGIN|OT_TAP_PORT|OT_TAP_CLOCK|SKIP_INCREMENTAL_REPAIR) ", l)}
assert keys(c) == keys(gen), sorted(keys(c) ^ keys(gen))
(kd / "config.mk").write_text(c)
p = (kd / "post_grt_drv.tcl").read_text()
assert p.count("-hold_margin 5 ") == 1
(kd / "post_grt_drv.tcl").write_text(p.replace("-hold_margin 5 ", f"-hold_margin {hm} "))
r = (kd / "run_kit.sh").read_text()
r = r.replace("HOLD_SLACK_MARGIN=5", "HOLD_SLACK_MARGIN=" + hm).replace("NAME=krepin-", "NAME=relay2-")
(kd / "run_kit.sh").write_text(r)
print(kd, nick, "hold_margin", hm)
