`timescale 1ns/1ps
// KV-CTL10 2026-10-20: qkd_kv_ownership_obs_c32 = rtl/qwen_sys/static_kv_20261014/qkd_kv_ownership_obs.sv with the KV-SRAM-CTL
// RCOPIES reset-pin copies (codex/kv-ctl3-native36-1020 b5d750822 form), as a NEW module so the shared original (listed by
// closed kit specs) stays byte-identical on main.  RCOPIES 1 = the original logic.
// KVJ-F 2026-10-17 (stub audit K-4 / kv_static_join_plan "Ownership x1, beside the host root"): the actual producers of
// every open input of the native/HOST ownership calendar (qkd_static_kv_ownership_calendar) and of the static D2D end's
// KV-local status (qkd_d2d_static kv_active_local / kv_drained_local / kv_flush_local).  One instance per die; folded
// with the ownership calendar into the ownership tile (x1, beside the HOST root, which consumes native_reserved /
// ownership_valid).  Observations only: nothing here issues, holds, retries or moves a production slot.
//
//   go             one pulse per TOKEN: the layer programme's stage_start of stage 1 (stage_start also pulses at every
//                  later stage; those never re-start the ownership calendar, whose go must not repeat while active).
//                  Ages: stage_start / stage pins (1) -> go output register (2); the ownership calendar's own go pin
//                  capture follows, so every compiled ownership root is relative to layer-programme token start + 2
//                  edges + the die relays between the two (compiler-priced).
//   upstream_quiet ACTUAL drain evidence of the KV write path upstream of the PCs (the ownership calendar's contract:
//                  "every outstanding upstream command/data pipeline"; writer.active alone is insufficient): the link ->
//                  writer word valid (d2d kvn_word_valid) and the writer -> PC es lanes' command / data valids (es lane
//                  bits 287 s_v and 0 w_v) are observed at pin registers; quiet = no valid on any of them for QUIET_WIN
//                  consecutive edges, QUIET_WIN >= writer word -> es depth + the es relay depth to the farthest PC intake
//                  (compiler-priced from the die plan; past the PC intake the drain guards own the debt).  Reset: not
//                  quiet until one full window has passed.
//   host_quiet     the HOST root's actual quiet exports (qkd_host_root_admission host_launch_quiet and
//                  host_upstream_quiet[5:0], their own clock domains) through independent two-flop synchronisers, then
//                  one registered AND (the qkd_host_native_quiet reduction without the per-PC debt slices, which the
//                  die's HOST PC slices do not export).
//   kv_active_local   = ownership.active (native calendar running; the D2D end ORs it into execution_active, which the
//                       boot dispatcher refuses boot words under).
//   kv_drained_local  = every one of the 32 drain guards drained, none faulted, upstream quiet, ownership not faulted.
//   kv_flush_local    = the KV die's native state is fault-stopped (ownership fault or any drain-guard fault): its KV
//                       context must be flushed by reset before the HOST may reuse it (status bit of the token result).
// MUT (bench negative controls): 1 = go on every stage_start; 2 = es lanes not observed; 3 = drained ignores guard
// faults; 4 = no host synchroniser (raw host level used, one edge early).
// KV-SRAM-CTL 10-19: RCOPIES > 1 = KEPT identical copies of the reset pin flop rn (family g_rc.rnv, ot_rst_split).
module qkd_kv_ownership_obs_c32 #(parameter integer QUIET_WIN = 16, parameter integer MUT = 0, parameter integer RCOPIES = 1) (
    input  wire        ck, rst_n,
    input  wire        stage_start, input wire [5:0] stage,
    input  wire        word_valid, input wire [3:0] es_sv, es_wv,
    input  wire        host_launch_quiet, input wire [5:0] host_upstream_quiet,
    input  wire        own_active, own_fault,
    input  wire [31:0] group_drained, group_fault,
    output reg         go, upstream_quiet, host_quiet,
    output reg         kv_active_local, kv_drained_local, kv_flush_local
);
    generate if (QUIET_WIN < 1 || QUIET_WIN > 255) begin : g_bad
        initial $fatal(1, "qkd_kv_ownership_obs: QUIET_WIN %0d outside 1..255", QUIET_WIN);
    end endgenerate
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    generate if (RCOPIES > 1) begin : g_rc
        (* keep *) reg [RCOPIES-2:0] rc_q;
        always @(posedge ck) rc_q <= {(RCOPIES-1){rst_n}};
        (* keep, ot_rst_split *) wire [RCOPIES-1:0] rnv = {rc_q, rn};
    end endgenerate
    // ---- pin registers ----
    reg ss_q, wv_q, act_q, of_q; reg [5:0] st_q; reg [3:0] sv_q, ev_q; reg [31:0] dr_q, gf_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin ss_q <= 0; wv_q <= 0; sv_q <= 0; ev_q <= 0; act_q <= 0; of_q <= 0; end
        else begin ss_q <= stage_start; wv_q <= word_valid; sv_q <= es_sv; ev_q <= es_wv; act_q <= own_active; of_q <= own_fault; end
    always @(posedge ck) begin st_q <= stage; dr_q <= group_drained; gf_q <= group_fault; end
    // ---- host quiet: independent 2-flop synchronisers, then one registered AND ----
    (* async_reg = "true" *) reg [6:0] h_meta, h_sync;
    always @(posedge ck or negedge rn)
        if (!rn) begin h_meta <= 0; h_sync <= 0; host_quiet <= 0; end
        else begin
            h_meta <= {host_upstream_quiet, host_launch_quiet}; h_sync <= h_meta;
            host_quiet <= (MUT == 4) ? (host_launch_quiet && (&host_upstream_quiet)) : (&h_sync);
        end
    // ---- upstream (KV write path) quiet window ----
    wire any = wv_q || ((MUT == 2) ? 1'b0 : ((|sv_q) || (|ev_q)));
    reg [7:0] cnt;
    always @(posedge ck or negedge rn)
        if (!rn) begin cnt <= QUIET_WIN[7:0]; upstream_quiet <= 0; end
        else begin
            cnt <= any ? QUIET_WIN[7:0] : ((cnt != 0) ? cnt - 8'd1 : 8'd0);
            upstream_quiet <= !any && (cnt <= 8'd1);
        end
    // ---- token go, D2D KV-local status ----
    wire gf_any = (MUT == 3) ? 1'b0 : (|gf_q);
    always @(posedge ck or negedge rn)
        if (!rn) begin go <= 0; kv_active_local <= 0; kv_drained_local <= 0; kv_flush_local <= 0; end
        else begin
            go <= ss_q && ((MUT == 1) || st_q == 6'd1);
            kv_active_local <= act_q;
            kv_drained_local <= (&dr_q) && !gf_any && upstream_quiet && !of_q;
            kv_flush_local <= of_q || gf_any;
        end
endmodule

// QR-CTL 10-21 (c32d route 104fb88b7 FF -45.62: RESETN removal rst_n landing clone c62 -> u_bobs.f2[10]): successor of
// qkd_static_kv_boot_observe for the c32 ctl tile.  Reset only control / valid bits (safe rule 8): the 960 synchroniser
// data flops (a1 a2 f1 f2 c1 c2) carry NO reset; a 2-flop valid shift (v1 v2, reset, local to this block) masks the two
// stale stages after reset release, so applied_core / fault_core equal the original on every edge (original: a2/f2/c2 = 0
// for the first two edges after release, then the first post-release samples).  Reset load of the block 1123 -> 168 flops.
module qkd_static_kv_boot_observe_c32(
 input wire ck,rst_n,input wire[159:0]applied_hbm,fault_hbm,fault_leaf_core,
 output reg[159:0]applied_core,output reg fault_core
);
 (* async_reg="true" *)reg[159:0]a1,a2,f1,f2,c1,c2;
 // SQ-COLLECT 10-21 (c32e/c32f native census FAIL: v2 drove 161 loads): v2 = 5 KEPT identical copies (one per
 // 32-bit applied_core slice, <=32 loads each) + v2f for the fault term.  Same value every edge (all reset 0, all
 // load v1), so applied_core / fault_core are unchanged.
 reg v1;
 (* keep *) reg[4:0] v2;
 (* keep *) reg v2f;
 always @(posedge ck)begin a1<=applied_hbm;a2<=a1;f1<=fault_hbm;f2<=f1;c1<=fault_leaf_core;c2<=c1;end
 genvar gv;
 generate for(gv=0;gv<5;gv=gv+1)begin:g_v2
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin v2[gv]<=1'b0;applied_core[32*gv+:32]<=32'd0;end
   else begin v2[gv]<=v1;applied_core[32*gv+:32]<=v2[gv]?a2[32*gv+:32]:32'd0;end
 end endgenerate
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin v1<=0;v2f<=0;fault_core<=0;end
 else begin v1<=1'b1;v2f<=v1;
  fault_core<=fault_core||(v2f&&((|f2)||(|c2)));end
 end
endmodule
