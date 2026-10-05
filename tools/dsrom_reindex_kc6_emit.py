#!/usr/bin/env python3
"""Emit one default-off additive kc5 correction; originals remain byte-identical."""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / "results/uarch/dsrom_reindex_kc6_20261005/kc5_original.sv"
OUT = ROOT / "rtl/experimental/dsrom_reindex_kc6_20261005"


def once(s, old, new):
    if s.count(old) != 1:
        raise ValueError(f"source anchor is not unique: {old[:70]}")
    return s.replace(old, new)


def emit():
    s = DONOR.read_text()
    if hashlib.sha256(DONOR.read_bytes()).hexdigest() != "88864591d588add3b2f23578e778557ece9f53f9bfe7abd698aa15b60938d89d":
        raise ValueError("kc5 donor pin changed")
    for m in ("ot_hdc_v41x_idx_kgctl", "ot_hdc_v41x_idx_kgdata",
              "ot_hdc_v41x_idx_kgather", "ot_hdc_v41x_kg_kreg"):
        s = re.sub(r"\b" + m + r"\b", m + "_kc6", s)
    for m in ("ot_hdc_v41x_idx_kgctl_kc6", "ot_hdc_v41x_idx_kgather_kc6"):
        s = once(s, f"module {m} #(\n", f"module {m} #(\n    parameter integer OPT_KC6 = 0,\n")
    s = once(s, "ot_hdc_v41x_idx_kgctl_kc6 #(.NPC(NPC)",
             "ot_hdc_v41x_idx_kgctl_kc6 #(.OPT_KC6(OPT_KC6), .NPC(NPC)")
    old = """                for (k = 0; k < 4; k = k + 1) begin
                    cpart[e][k]     <= ~|pend_c[e][8*k +: 8];
                    cpart[e][4 + k] <= ~|pend_s[e][8*k +: 8];
                end"""
    s = once(s, old, """                if (!OPT_KC6)
                    for (k = 0; k < 4; k = k + 1) begin
                        cpart[e][k]     <= ~|pend_c[e][8*k +: 8];
                        cpart[e][4 + k] <= ~|pend_s[e][8*k +: 8];
                    end""")
    s = once(s, """    always @(posedge clk) begin
        // decode pipe""", """    always @(posedge clk) begin
        // Derived partials have no reset value; adm_q/cmp still reset-clear.
        // NBA reads the same pre-edge pending state as the donor.
        if (OPT_KC6)
            for (e2 = 0; e2 < WB; e2 = e2 + 1)
                for (c2 = 0; c2 < 4; c2 = c2 + 1) begin
                    cpart[e2][c2] <= ~|pend_c[e2][8*c2 +: 8];
                    cpart[e2][4+c2] <= ~|pend_s[e2][8*c2 +: 8];
                end
        // decode pipe""")
    s = once(s, "    reg [2*NPC-1:0] rm;", """    reg [2*NPC-1:0] rm;
    wire [FW:0] fq_nm1 [0:2*NPC-1];
    wire [FW:0] fq_np1 [0:2*NPC-1];
    wire [FW:0] fq_np2 [0:2*NPC-1];
    generate for (genvar fp = 0; fp < 2*NPC; fp = fp+1) begin : g_count_alternatives
        // Fixed-width modular arithmetic, before the ready-dependent pop.
        assign fq_nm1[fp] = fq_n[fp] - 1'b1;
        assign fq_np1[fp] = fq_n[fp] + 1'b1;
        assign fq_np2[fp] = fq_n[fp] + 2'd2;
    end endgenerate
    reg push_a, push_b, pop_now;""")
    s = once(s, """                    fq_n[p] <= cnt;""", """                    if (OPT_KC6) begin
                        push_a = ch_q[(2*g+0)*CHW + (p < NPC ? CG : 0) + c];
                        push_b = ch_q[(2*g+1)*CHW + (p < NPC ? CG : 0) + c];
                        pop_now = p < NPC ? (iss[p % NPC] && !use_s[p % NPC])
                                          : (iss[p % NPC] && use_s[p % NPC]);
                        // Late pop selects precomputed counts; rm above still
                        // sees pushed count BEFORE pop, exactly as the donor.
                        case ({push_a, push_b})
                            2'b00: fq_n[p] <= pop_now ? fq_nm1[p] : fq_n[p];
                            2'b11: fq_n[p] <= pop_now ? fq_np1[p] : fq_np2[p];
                            default: fq_n[p] <= pop_now ? fq_n[p] : fq_np1[p];
                        endcase
                    end else fq_n[p] <= cnt;""")
    s = once(s, "    wire           can1 = can0 && (d_left > 1) && rq1;", """    wire           can1 = can0 && (d_left > 1) && rq1;
    wire drain_eligible = run && (d_left != 0) && rq0;
    wire drain_two = (d_left > 1) && rq1;
    wire [WB-1:0] next_hoh;
    wire [WB-1:0] rotated_one = rotl(hoh, 1);
    wire [WB-1:0] rotated_two = rotl(hoh, 2);
    generate for (genvar hs=0; hs<GS; hs=hs+1) begin : g_head_local
        ot_dsrom_kc6_ready_last #(.W(SG)) u_select (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(hoh[hs*SG +: SG]), .one_head(rotated_one[hs*SG +: SG]),
            .two_head(rotated_two[hs*SG +: SG]), .next_head(next_hoh[hs*SG +: SG]));
    end endgenerate""")
    s = once(s, """                    hoh <= can1 ? rotl(hoh, 2) : rotl(hoh, 1);""", """                    if (!OPT_KC6) hoh <= can1 ? rotl(hoh, 2) : rotl(hoh, 1);""")
    s = once(s, """                nu = inuse + (disp ? QW'(2) : QW'(0))""", """                if (OPT_KC6) hoh <= next_hoh;
                nu = inuse + (disp ? QW'(2) : QW'(0))""")
    s += """
// Preserve local combinational selection boundaries, not duplicated state.
// Keep the actual ready as the last mux input; no sampled-ready substitution.
(* keep_hierarchy = "yes" *)
module ot_dsrom_kc6_ready_last #(parameter integer W=16) (
    input wire eligible, two, ready,
    input wire [W-1:0] old_head, one_head, two_head,
    output wire [W-1:0] next_head
);
    (* keep = 1 *) wire [W-1:0] eligible_head = eligible ? (two ? two_head : one_head) : old_head;
    assign next_head = ready ? eligible_head : old_head;
endmodule
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ot_hdc_v41x_idx_kgather_kc6.sv").write_text(s)
    # Source-selected copies of the ORIGINAL fixture/context, no oracle changes.
    for src, dest, module in (
        ("rtl/test/tb_hdc_v41x_idx_kgather.sv", "tb_hdc_v41x_idx_kgather_kc6.sv", "ot_hdc_v41x_idx_kgather"),
        ("rtl/hdc/v41x/phys/ot_hdc_v41x_reindex_ctx.sv", "ot_hdc_v41x_idx_kgctl_kc6_ctx.sv", "ot_hdc_v41x_idx_kgctl"),
    ):
        t = (ROOT / ("results/uarch/dsrom_reindex_kc6_20261005/kc5_context_original.sv"
                     if "reindex_ctx" in src else src)).read_text()
        if "reindex_ctx" in src:
            helpers = t[t.index("module ot_reindex_ctx_launch"):t.index("module ot_hdc_v41x_sel_mdrop_ctx")]
            t = helpers + t[t.index("module ot_hdc_v41x_idx_kgctl_ctx"):]
            t = t.replace("ot_hdc_v41x_idx_kgctl_ctx", "ot_hdc_v41x_idx_kgctl_kc6_ctx")
            t = t.replace("ot_reindex_ctx_launch", "ot_reindex_ctx_launch_kc6")
            t = t.replace("ot_reindex_ctx_capture", "ot_reindex_ctx_capture_kc6")
            top = "ot_hdc_v41x_idx_kgctl_kc6_ctx"
        else:
            top = "tb_hdc_v41x_idx_kgather"
        t = once(t, "module " + top + " #(\n", "module " + top + " #(\n    parameter integer OPT_KC6 = 0,\n")
        t = t.replace(module + " #(", module + "_kc6 #(.OPT_KC6(OPT_KC6), ")
        (OUT / dest).write_text(t)
    return OUT


if __name__ == "__main__":
    print(emit())
