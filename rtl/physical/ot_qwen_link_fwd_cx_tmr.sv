`timescale 1ns/1ps
// Centre-aligned forwarded-clock link station (redesign-2, 2026-10-08). Successor of ot_qwen_die_link_fwd_full_tmr
// (that source is not modified).
//
// Why: the full-cycle station captured on the forwarded clock's RISING edge, the same edge the upstream launched on, so
// every hop was an edge-aligned (zero-cycle) hold race against the forwarded clock's insertion. The two-inverter clock
// forward sat inside the clock tree, CTS rewrote it, and the generated clocks lost their pins (mm-CTS: TT setup -452 /
// FF hold -310, unrepairable with 2,778 buffers).
//
// Structure (the S81 ot_fwd_link_stage pattern, reused): each station captures on the FALLING edge of its received
// forwarded clock and forwards the INVERTED clock (fclk_o = ~fclk_i, a kept cell). The upstream launches on its own
// falling edge = our rising edge, so data is centre-aligned: half a cycle for setup AND half a cycle for hold against
// the forwarded clock, whatever the (matched) wire delay. Every hop is identical; polarity alternates per hop.
// The station is the hardened block: its forwarded clocks are PORTS (generated clock on the fclk_o port, which no CTS
// rewrite can unbind); the inter-station wire is die-level (srcsync model, half-cycle P).
//
// Latency: a hop is half a cycle (the full-cycle station's hop was one cycle). No cycle is added; the link gets shorter.
//
// TMR release semantics are unchanged: raw POR reaches the six release rails per direction; each rail is an
// independent two-flop chain (now on the capture edge); the 16 control bits clear from the 2-of-3 majority.
module ot_qwen_link_fwd_cx_station #(
    parameter integer LW = 528,
    parameter integer CW = 16
)(
    input  wire rst_n,
    input  wire fclk_ab_i, fclk_ba_i,
    output wire fclk_ab_o, fclk_ba_o,
    input  wire [LW-1:0] ab_i, ba_i,
    output wire [LW-1:0] ab_o, ba_o
);
    (* keep_hierarchy = 1 *) ot_qwen_link_fwd_cx_dir_tmr #(.LW(LW),.CW(CW)) ab(
        .rst_n(rst_n),.fclk_i(fclk_ab_i),.fclk_o(fclk_ab_o),.d_i(ab_i),.d_o(ab_o));
    (* keep_hierarchy = 1 *) ot_qwen_link_fwd_cx_dir_tmr #(.LW(LW),.CW(CW)) ba(
        .rst_n(rst_n),.fclk_i(fclk_ba_i),.fclk_o(fclk_ba_o),.d_i(ba_i),.d_o(ba_o));
endmodule

(* keep_hierarchy = 1 *)
module ot_qwen_link_fwd_cx_dir_tmr #(parameter integer LW=528, CW=16, FWD_INV=5)(
    input wire rst_n, fclk_i, input wire [LW-1:0] d_i,
    output wire fclk_o, output wire [LW-1:0] d_o
);
    // Cold POR only (as the full-cycle station). Only release-chain storage is triplicated.
    (* async_reg = "true", keep = 1, dont_touch = 1 *) reg [2:0] release0, release1;
    genvar rail;
    generate for(rail=0;rail<3;rail=rail+1) begin: release_rail
        (* keep = 1, dont_touch = 1 *) always @(negedge fclk_i or negedge rst_n)
            if (!rst_n) begin release0[rail]<=0; release1[rail]<=0; end
            else begin release0[rail]<=1; release1[rail]<=release0[rail]; end
    end endgenerate
    (* keep = 1 *) wire release_run;
    assign release_run=(release1[0]&release1[1]) |
                       (release1[0]&release1[2]) | (release1[1]&release1[2]);
    (* keep = 1, dont_touch = 1 *) reg [LW-CW-1:0] data_q;
    (* keep = 1, dont_touch = 1 *) reg [CW-1:0] control_q;
    always @(negedge fclk_i) data_q <= d_i[LW-1:CW];
    always @(negedge fclk_i or negedge release_run)
        if (!release_run) control_q<=0;
        else control_q<=d_i[CW-1:0];
    assign d_o={data_q,control_q};
    // A real cell (kept hierarchy): flattened, yosys would fold the inversion into the next station's flops.
    // DRIVE-1113 2026-10-08: delay-matched forward. The output window is half a cycle against the forwarded clock AT
    // THE PORT; data leaves leaf + clk->QN + INV + port buffer (~227 ps TT), the clock leaf + INV + port buffer (~34 ps),
    // so the launch path ate the whole half-cycle setup window (a TT -16 / b -68) while output hold had +253 ps (FF).
    // FWD_INV kept inverters in series (odd: the forward stays inverted) move the forwarded edge later by ~(FWD_INV-1)
    // inverter delays: setup gains that, output hold loses it. Same logic function; no cycle added.
    wire [FWD_INV:0] fwd_c;
    assign fwd_c[0]=fclk_i;
    genvar fi;
    generate for(fi=0;fi<FWD_INV;fi=fi+1) begin: fwd_chain
        (* keep = 1, dont_touch = 1 *) ot_qwen_link_fwd_cx_inv u_fwd_inv(.a(fwd_c[fi]),.y(fwd_c[fi+1]));
    end endgenerate
    assign fclk_o=fwd_c[FWD_INV];
endmodule

(* keep_hierarchy = 1 *)
module ot_qwen_link_fwd_cx_inv(input wire a, output wire y);
    assign y=~a;
endmodule
