#!/usr/bin/env python3
"""die chain: rule-H1 padded die STA (qwen-relaunch-1011, 2026-10-11).

Takes a die chain STA script (sta_tcl.py output, grt_<c>.tcl) and a pads JSON (pad_from_ends.py) and writes
grt_<c>_pad.tcl: the same session with the rule-H1 die hold pads (tools/hbm_die_relay_sta.py OT_PAD_PROC: an ideal
incremental wire-arc delay into each listed load pin, x PAD_SCALE at TT / SS) applied after the clocks, and reports
renamed *_pad.  TT must be re-timed with the same pads (setup cost of the hold cells).

usage: pad_sta.py <grt_c.tcl> <pads.json> <tt|ff> <out_pad.tcl>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hbm_die_relay_sta import hold_pads  # noqa: E402

src, pads, c, out = sys.argv[1:5]
t = Path(src).read_text()
k = 'step sta {'
assert k in t, 'no sta step in ' + src
# single-corner die session: the one STA scene is 'default' (sta::find_scene ff = NULL); the pad SIZE keeps the
# corner's PAD_SCALE, only the scene the arc annotation lands on changes
hp = hold_pads(pads, c).replace(f'[ot_pad $l {c} ', '[ot_pad $l default ')
t = t.replace(k, hp + k, 1)
t = t.replace(f'grt_{c}_ends.rpt', f'grt_{c}_pad_ends.rpt').replace(f'grt_{c}_paths.rpt', f'grt_{c}_pad_paths.rpt') \
     .replace(f'grt_{c}_drv.rpt', f'grt_{c}_pad_drv.rpt')
Path(out).write_text(t)
