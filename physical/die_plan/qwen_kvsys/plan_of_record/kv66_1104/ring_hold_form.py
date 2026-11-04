#!/usr/bin/env python3
"""DIE-KV-66 11-04: KV die clock.ring_hold form (A) + ft budget. write_edge fall, sender_ps -385 (DIE-KV-65 measured far
exports), ft_ring_max_ps = 0.2 T = the plain IO ring budget. An ft ring input with the 0.92 T hop budget cannot be
captured at the T/2 fall (ioft_a1: -451..-499 ps TT, 4_cts placement RC). Source-synchronous: fclk flies with the data,
so the hop cancels; the residual is priced in die STA (die_sta_related ca_ring).

    ring_hold_form.py PLAN   (span edit of the one ring_hold line)
"""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
t = p.read_text()
raw = json.loads(t)
per = float(raw["die"]["period_ps"])
old = raw["clock"]["ring_hold"]
new = dict(old, sender_ps=-385.0, write_edge="fall", ft_ring_max_ps=round(0.2 * per, 2))
raw["clock"]["ring_hold"] = new
p.write_text(json.dumps(raw, indent=1) + "\n")
print(old, "->", new)
