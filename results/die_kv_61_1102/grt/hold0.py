#!/usr/bin/env python3
"""DIE-KV-61/grt: run die_sta_related.py with pair_slack_gate.HOLD_MIN_PS = 0 (OWNER 11-02: no +10 ps hold margin, FF hold >= 0).
usage: hold0.py TOOLS_DIR <die_sta_related args>"""
import runpy, sys
sys.path.insert(0, sys.argv[1]); tools = sys.argv.pop(1)
import pair_slack_gate as PSG
PSG.HOLD_MIN_PS = 0.0
sys.argv[0] = tools + "/die_sta_related.py"
runpy.run_path(sys.argv[0], run_name="__main__")
