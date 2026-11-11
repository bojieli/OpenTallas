#!/usr/bin/env python3
"""DIE-HBM-97 11-10 (COORD yes, dma-vpose3 B): one-edge-early fire compare for the MODE 1 command sequencer, under
`ifdef OT_CMD_FIRE_EARLY` only.  Without the define the file elaborates exactly as before (every other die/type).

Why: in ot_hgi_dma_back_static_vp4_banks_cp every routed form misses TT setup on u_cp.u_core fire_at -> head_pl/cmd
(-22..-35 ps, 95 endpoints): fire = head_v && cyc == fire_at is a 32-bit compare that then enables the CW-wide head
load and cmd capture.  With the define, fire is a flop (fire_q) computed one edge earlier from the NEXT state:
    ld    = nxt_v && (!head_v || fire)                          (the existing head-load condition)
    hv_n  = !fault_r && (ld || (head_v && !fire))               (head_v as assigned this edge)
    fire_q <= hv_n && (ld ? rel == nxt[31:0] : cyc1 == head_fire)
    cyc1 = cyc + 1 - M  (counter, reset 1 - M);  rel = cyc + 1 - nxt_lb - M (reloaded with nxt_lb on rd_q, else +1)
    M = 1 for MUT == 1 (fire one cycle late), else 0.
Invariant (proved by sat -tempinduct, see eq/): fire_q == head_v && cyc == fire_at, so every other line of the core sees
the same value as before: 0 cycles of latency, same schedule, same outputs.

Usage: cmd_fire_early_patch.py IN.sv OUT.sv     (works on ot_static_cmd_target.sv and on kit copies of the core,
e.g. the dma kits' cp_rstrep_core in rtl/candidate.sv: the patched lines are identical text)."""
import sys
src = open(sys.argv[1]).read()
def rep(old, new):
    global src
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"cmd_fire_early_patch: anchor found {n}x: {old[:60]!r}")
    src = src.replace(old, new)
rep("    wire fire = head_v && cyc == fire_at;\n",
"""`ifdef OT_CMD_FIRE_EARLY
    // OT_CMD_FIRE_EARLY (DIE-HBM-97 11-10): fire is a flop computed one edge early from the next state (0 latency).
    localparam [31:0] FE_M = (MUT == 1) ? 32'd1 : 32'd0;
    reg fire_q;
    reg [31:0] fe_cyc1, fe_rel;
    wire fire = fire_q;
    wire fe_ld = nxt_v && (!head_v || fire);
    wire fe_hv_n = !fault_r && (fe_ld || (head_v && !fire));
`ifdef OT_CMD_FIRE_EARLY_NEG
    wire fe_hit_n = fe_ld ? (fe_rel == nxt[31:0] + 32'd1) : (fe_cyc1 == head_fire + 32'd1);   // negative control: 1 late
`else
    wire fe_hit_n = fe_ld ? (fe_rel == nxt[31:0]) : (fe_cyc1 == head_fire);
`endif
`else
    wire fire = head_v && cyc == fire_at;
`endif
""")
rep("            tw_sel <= 2'd0;\n        end else begin\n",
"""            tw_sel <= 2'd0;
`ifdef OT_CMD_FIRE_EARLY
            fire_q <= 1'b0; fe_cyc1 <= 32'd1 - FE_M; fe_rel <= 32'd0;
`endif
        end else begin
""")
rep("            active <= seq_on || (|act_q);\n        end\n    end\n",
"""            active <= seq_on || (|act_q);
`ifdef OT_CMD_FIRE_EARLY
            // ---- one-edge-early fire (next-state compare; see the header of cmd_fire_early_patch.py)
            fe_cyc1 <= fe_cyc1 + 32'd1;
            fe_rel <= rd_q ? (cyc + 32'd2 - rd_lb - FE_M) : (fe_rel + 32'd1);
            fire_q <= fe_hv_n && fe_hit_n;
`endif
        end
    end
`ifdef OT_CMD_FIRE_EARLY
`ifdef FORMAL
    // inductive invariant: the early flop equals the original combinational fire in every reachable state
    always @* begin
        assert (fire_q == (head_v && cyc == fire_at));
        assert (fe_cyc1 == cyc + 32'd1 - FE_M);
        assert (!nxt_v || fe_rel == cyc + 32'd1 - nxt_lb - FE_M);
    end
`endif
`endif
""")
open(sys.argv[2], "w").write(src)
print("patched", sys.argv[1], "->", sys.argv[2])
