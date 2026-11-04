#!/usr/bin/env python3
"""S81 plain-lane input budget event (DIE-S81-51/PLAN 11-03; COORD 10:49 plain-seam input-face class part 2).

    delta_plain_seam_split_1103.py PLAN [OUT]

Adds plan clock.plain_seam_split {rx_in_max_ps 480, rx_in_raw_max_ps 580} (gen_phys.plain_seam_split derives every
plain ft lane's receiver input max and registered sender output max from it).  Basis: SAFE-STATION-1 t30 pilot
(10:46): plain seam ft2_i[150] -> u_ft_ft2_o_0, input external delay 599.7 ps (= 0.84 T - W 100), 2 HB4 hold pads
135.6 ps, slack -49.1 (+86.5 without the pads).  The window W cancels against the early capture tap, so the face path
gains exactly the raw cut: raw 699.7 -> 580 gives +119.7 ps -> +70.6 ps with the 2 pads (>= one hold pad, 70 ps);
written <= 480 (= 580 - 100) on every type, rx_in_max 480 binds where W < 100.  Writes main's plan format."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import added_tap_recentre as AT

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else src
S0 = open(src).read()
P = json.loads(S0)
P["clock"]["plain_seam_split"] = {
    "rx_in_max_ps": 480.0, "rx_in_raw_max_ps": 580.0,
    "note": "DIE-S81-51/PLAN 11-03 (COORD 10:49 plain-seam input-face class part 2): plain ft-lane receiver input max "
            "min(0.84 T, 580 raw, 480 + window) -> written <= 480 ps, face path keeps >= one hold pad (70 ps) setup "
            "after hold repair (t30 pilot basis); cut taken from registered ft_o senders whose every die port is a "
            "plain lane (output max T - receiver max); other senders keep 0.16 T (O + I <= T on every seam)"}
open(out, "w").write(AT.dumps_like(P, S0))
