`timescale 1ns/1ps
// =====================================================================================================================
// Q-KVSYS PVJOIN 2026-10-16: KV-side compiled KVN context (the independent expectation kvn_compiled_identity[58:0] /
// kvn_compiled_generation[1:0] of the static D2D end qkd_d2d_static, ot_qwen_d2d_kvn_rx).
//
// TAG59 = {epoch16, stage6, token18, position13, segment6}.  The compute die forms the KVN word's identity as
// {host_epoch, command_stage, token, position, 0} (qfd_native59_command_context begin_tag), from the HOST cohort tag
// (stage and segment fields 0, enforced by ot_qwen_tp8_token_cohort begin_identity_ok) and its own layer stage.  This
// leaf forms the KV-side expectation from two KV-die sources that never read the received word:
//   * the HOST root's authoritative cohort tag / generation (cohort_tag, cohort_gen; held for the whole token), and
//   * the KV link calendar sequencer (qkd_d2d_cal_seq_pin): every compiled run start cal_start carries the run index
//     layer (registered with it) (0 = token run incl. L0, l = layer l run, 63 = admission run).  stage = layer + 1; the admission run (no
//     KVN traffic) leaves the stage unchanged.
// Fixed latency, no valid/ready/credit: cohort pin -> output 2 edges; cal_start pin -> stage -> output 3 edges.  The
// compiled KVN arrivals sit >= 640 edges after their run's cal_start (tools/qwen_kv_die/kvn_ctx_golden.py checks the
// window against the link compiler's program calendar), so the expectation is stable over every KVN word.
// Before the first token run the stage is 0: any KVN word then faults in ot_qwen_d2d_kvn_rx (stage must be 1..36).
// MUT (bench mutants only): 1 stage = layer (no +1); 2 cohort captured only at cal_start (stale for a cohort that
// changes inside the token run before L0's KVN).
// =====================================================================================================================
module qkd_kvn_ctx_cal #(parameter integer MUT = 0) (
    input  wire        ck, rst_n,
    input  wire        cal_start,
    input  wire [5:0]  layer,
    input  wire [58:0] cohort_tag,
    input  wire [1:0]  cohort_gen,
    output reg  [58:0] compiled_identity,
    output reg  [1:0]  compiled_generation
);
    // reset pin captured like every other input (one flop), drives only the 2 control flops below
    (* keep = "true" *) reg rn;
    always @(posedge ck) rn <= rst_n;
    // pin flops (data: no reset; validity is cs_q)
    (* keep = "true" *) reg cs_q;
    (* keep = "true" *) reg [5:0] lay_q;
    (* keep = "true" *) reg [58:0] tag_q;
    (* keep = "true" *) reg [1:0] gen_q;
    always @(posedge ck) begin lay_q <= layer; tag_q <= cohort_tag; gen_q <= cohort_gen; end
    reg [5:0] stage_q;
    wire run = cs_q && lay_q <= 6'd35;                     // a token / layer run (admission index 63 excluded)
    always @(posedge ck or negedge rn)
        if (!rn) begin cs_q <= 1'b0; stage_q <= 6'd0; end
        else begin
            cs_q <= cal_start;
            if (run) stage_q <= (MUT == 1) ? lay_q : lay_q + 6'd1;
        end
    reg [58:0] snap_q; reg [1:0] snap_g;                  // MUT 2 only (cohort sampled at the run start)
    always @(posedge ck) if (run) begin snap_q <= tag_q; snap_g <= gen_q; end
    wire [58:0] t = (MUT == 2) ? snap_q : tag_q;
    wire [1:0]  g = (MUT == 2) ? snap_g : gen_q;
    always @(posedge ck) begin
        compiled_identity <= {t[58:43], stage_q, t[36:6], 6'd0};
        compiled_generation <= g;
    end
endmodule
