#!/usr/bin/env python3
"""S81-RST-RELAY-LAND (OPUS-FIX-S81-LEAF-R10 11-23, RC-GAP "leaf reset recovery", J9/J10 row J9-LEAF-RST-LAND).

Fable RC review (FABLE-RC-REVIEW.tsv, S81 leaf, MISSED, 24/28 runs, -49..-722 ps): the recovery check
u_lpad_leafdn_i0.q[594] -> u_vp.u_rr.relay_q / rst_n (RESETN of DFFASRHQN) fails, for example t43 attempt_5 CTS post-hook
-215.8 ps.  ot_rst_relay clears EVERY relay flop (REGIONS * TREE_STAGES) asynchronously from the rst_n_in port, so the
synchronous pad-bank reset flop must reach every relay flop of every core (>1 mm away) in ONE cycle.

LAND (opt-in with the bare-name define OT_RST_RELAY_LANDED; without it the source is unchanged) gives ot_rst_relay the
rtl/lib/ot_rst_relay_l.sv behaviour, the reset_landing standard: the port net reaches ONLY the SYNC_STAGES synchroniser
flops, and the relay flops are cleared by the last synchroniser stage.  The reset waveform at every rst_n[k] is identical:
assert stays asynchronous (port low -> sync_q clear -> relay clear, no clock needed), and release still takes
SYNC_STAGES + TREE_STAGES edges.  The distance from pad to core becomes SYNC_STAGES + 1 one-cycle hops (pad -> sync_q[0] ->
sync_q[1] -> relays) instead of one, at 0 cycles.  Because the define is per kit (verilog_defines), every ot_rst_relay in
the type (vp, vn, crr) lands, and other kits are untouched.
Both edits stay on their own source lines (no line is added or removed).

  python3 -I s81_rst_relay_land_overlay.py ROOT|FILE     exact counted replacements; refuses on a miss or a second run.
"""
import os
import sys
from pathlib import Path

REL = "rtl/lib/ot_rst_relay.sv"
TAG = "S81-RST-RELAY-LAND"
EDITS = [  # (old text, new text), each must occur exactly once
    ("    (* keep = \"true\", dont_touch = \"true\" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];\n",
     "    (* keep = \"true\", dont_touch = \"true\" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];"
     "  wire relay_clr_n; assign relay_clr_n = `ifdef OT_RST_RELAY_LANDED sync_q[SYNC_STAGES-1] `else rst_n_in `endif ;  // "
     + TAG + "\n"),
    ("            always @(posedge clk or negedge rst_n_in) begin\n                if (!rst_n_in)\n"
     "                    relay_q[t] <= {REGIONS{1'b0}};\n",
     "            always @(posedge clk or negedge relay_clr_n) begin\n                if (!relay_clr_n)\n"
     "                    relay_q[t] <= {REGIONS{1'b0}};\n"),
]


def patch(s):
    if TAG in s:
        raise SystemExit("RRL_OVERLAY_TWICE ot_rst_relay.sv already carries " + TAG)
    n0 = s.count("\n")
    for old, new in EDITS:
        c = s.count(old)
        if c != 1:
            raise SystemExit(f"RRL_OVERLAY_MISS expected 1 x {old.strip()[:70]!r}, found {c}")
        s = s.replace(old, new)
    if s.count("\n") != n0:
        raise SystemExit("RRL_OVERLAY_LINES the edit moved a source line")
    return s


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    p = Path(argv[0])
    if p.is_dir():
        p = p / REL
    new = patch(p.read_text())
    tmp = p.with_name(p.name + ".rrl.tmp")
    tmp.write_text(new)
    os.replace(tmp, p)
    print(f"{TAG}: {p} patched (define OT_RST_RELAY_LANDED: relay flops cleared by the last sync stage, port -> sync only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
