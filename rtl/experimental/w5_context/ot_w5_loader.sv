// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_pair_pq_ld: the configuration loader of ot_v41_pair_w17w10 (cfg ROM address -> registered word -> element
// configuration port, CW = 3*NSEG+1 words; `act` = a class of the phase is valid, which gates `go`) as a module, with
// the PQ addition of DS-ROM recovery lever "field" (2026-10-04): the load fills the element's configuration
// SHADOW, so it may run while the element still walks the current op; a broadcast that finds the shadow still full
// (not yet copied into the live fields) or the output-tag bank it would write still draining is held (pending) and
// loaded when both clear; a second broadcast before the load, or a go before the load finished, is a FAULT.
// PQ = 0: the pinned loader (load at the broadcast).
// ---------------------------------------------------------------------------
module ot_w5_loader_raw #(
    parameter integer NSEG = 8,
    parameter integer PHW = 6,
    parameter integer PQ = 0,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           cfg_go,
    input  wire [PHW-1:0] cfg_ph,
    input  wire [2:0]     cfg_np,
    input  wire           go,
    input  wire           e_sh_free,
    input  wire           e_bank_free,
    output wire [AW-1:0]  cm_a,
    input  wire [47:0]    cm_q,
    (* keep, dont_touch *) output reg            c_v,
    (* keep, dont_touch *) output reg  [4:0]     c_a,
    (* keep, dont_touch *) output reg  [47:0]    c_d,
    output wire           go_e,
    output wire           ld_busy,
    (* keep, dont_touch *) output reg            fault,
 output wire [85:0] snapshot
);
    (* keep, dont_touch *) reg         ld_run;
    (* keep, dont_touch *) reg [4:0]   ld_k;
    (* keep, dont_touch *) reg [AW-1:0] ld_a;
    (* keep, dont_touch *) reg [2:0]   ld_np;
    (* keep, dont_touch *) reg         pend;
    (* keep, dont_touch *) reg [PHW-1:0] pend_ph;
    (* keep, dont_touch *) reg [2:0]   pend_np;
    wire        ld_ok = (PQ == 0) || (e_sh_free && e_bank_free);
    wire        ld_start = (cfg_go && ld_ok) || (PQ != 0 && pend && !cfg_go && ld_ok);
    assign cm_a = ld_a;
    assign ld_busy = ld_run || c_v || pend;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ld_run <= 1'b0; ld_k <= 5'd0; c_v <= 1'b0; pend <= 1'b0; fault <= 1'b0;
        end else begin
            c_v <= ld_run;
            if (PQ != 0) begin
                if (cfg_go && !ld_ok) begin pend <= 1'b1; pend_ph <= cfg_ph; pend_np <= cfg_np; end
                else if (ld_start) pend <= 1'b0;
                if (cfg_go && (pend || ld_run)) fault <= 1'b1;               // a second broadcast before the load
                if (go && (pend || ld_run || c_v || cfg_go)) fault <= 1'b1;  // go before the load finished
            end
            if (ld_start) begin
                ld_run <= 1'b1; ld_k <= 5'd0;
                ld_a <= AW'(cfg_go ? cfg_ph : pend_ph) * AW'(CW);
                ld_np <= cfg_go ? cfg_np : pend_np;
            end else if (ld_run) begin
                ld_k <= ld_k + 5'd1;
                ld_a <= ld_a + 1'b1;
                if (ld_k == 5'(CW - 1)) ld_run <= 1'b0;
            end
        end
    end
    // An element with no class in the phase gets no `go` (W17 gate, 2026-09-30): the OR of the phase's class-valid
    // bits as they are loaded
    (* keep, dont_touch *) reg act;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) act <= 1'b0;
        else if (cfg_go || ld_start) act <= 1'b0;
        else if (c_v && c_a >= 5'(NSEG) && c_a < 5'(2 * NSEG) && c_d[0]) act <= 1'b1;
    end
    assign go_e = go && act;
    always @(posedge clk) begin
        c_a <= ld_k;
        if (ld_run) c_d <= (ld_k == 5'(2 * NSEG)) ? (cm_q | {42'd0, ld_np, 3'd0}) : cm_q;
    end
assign snapshot={ld_run,ld_k,(ld_run||c_v)?ld_a:11'b0,ld_run?ld_np:3'b0,
 pend,pend?pend_ph:6'b0,pend?pend_np:3'b0,act,c_v,c_v?c_a:5'b0,c_v?c_d:48'b0,fault};
endmodule

module ot_w5_loader_checked #(parameter integer ENABLE=0)(
 input wire clk,por_n,cfg_go,input wire [5:0] cfg_ph,input wire [2:0] cfg_np,
 input wire go,input wire [47:0] cm_q,output wire [10:0] cm_a,
 output wire c_v,output wire [4:0] c_a,output wire [47:0] c_d,
 output wire go_e,ld_busy,fault
);
wire cp,gp,bp,fp,cr,gr,br,fr,lc,bad;
wire [4:0] ap,ar;wire [47:0] dp,dr;wire [10:0] mp,mr;
wire [85:0] sp,sr;
(* keep,dont_touch *) reg sticky,sticky_inverse;
wire stop=bad|sticky|~sticky_inverse;
always @(posedge clk or negedge por_n)
 if(!por_n)begin sticky<=0;sticky_inverse<=1;end
 else if(ENABLE!=0 && stop)begin sticky<=1;sticky_inverse<=0;end
 else if(ENABLE==0)begin sticky<=0;sticky_inverse<=1;end
generate if(ENABLE!=0)begin:g_protected
 assign bad=|(sp^sr);
 ot_hdc_cg u_freeze(.clk(clk),.en(!stop|!por_n),.gclk(lc));
 ot_w5_loader_raw #(.PHW(6),.PQ(0)) u_r(.clk(lc),.rst_n(por_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),
 .cfg_np(cfg_np),.go(go),.e_sh_free(1'b1),.e_bank_free(1'b1),.cm_a(mr),.cm_q(cm_q),
 .c_v(cr),.c_a(ar),.c_d(dr),.go_e(gr),.ld_busy(br),.fault(fr),.snapshot(sr));
end else begin:g_default
 assign bad=0;assign sr=sp;assign lc=clk;
end endgenerate
 ot_w5_loader_raw #(.PHW(6),.PQ(0)) u_p(.clk(lc),.rst_n(por_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),
 .cfg_np(cfg_np),.go(go),.e_sh_free(1'b1),.e_bank_free(1'b1),.cm_a(mp),.cm_q(cm_q),
 .c_v(cp),.c_a(ap),.c_d(dp),.go_e(gp),.ld_busy(bp),.fault(fp),.snapshot(sp));
assign cm_a=mp;assign c_a=ap;assign c_d=dp;
assign c_v=cp&!stop;assign go_e=gp&!stop;assign ld_busy=bp|stop;assign fault=fp|stop;
endmodule
