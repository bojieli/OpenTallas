`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_crl_tx / ot_hgi_coll_crl_rx (HBM peer-to-peer step 1, 2026-10-14): a valid/ready stream carried across the
// die by CREDIT flow, so that any number of relay registers is legal (a valid/ready pair through relays duplicates or drops
// transfers: the sender sees a stale ready).  tx: local valid/ready, ready = a credit is held (local register); every die
// output leaves a flop.  rx: pin capture, CRD-deep FIFO, local valid/ready to the consumer, one credit back (registered)
// a transfer.  idle (tx) = every credit home = every transfer accepted by the far consumer: the producer's completion
// waits for it.  Rate = CRD / round trip.  MUT (rx, bench): 1 a credit returns at the push as well (overdraw).
module ot_hgi_coll_crl_tx #(
    parameter integer W   = 568,
    parameter integer CRD = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_v,
    input  wire [W-1:0]  in_d,
    output wire          in_rdy,
    output reg           idle,
    output reg           t_v,
    output reg  [W-1:0]  t_d,
    input  wire          f_cr,
    output reg           fault
);
    localparam integer CW = $clog2(CRD + 1);
    reg [CW-1:0] cr; reg fcr_q;
    assign in_rdy = (cr != '0);
    wire take = in_v && in_rdy;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr <= CW'(CRD); fcr_q <= 1'b0; t_v <= 1'b0; t_d <= '0; idle <= 1'b1; fault <= 1'b0; end
        else begin
            fcr_q <= f_cr;
            cr <= cr - CW'(take) + CW'(fcr_q);
            idle <= (cr - CW'(take) + CW'(fcr_q)) == CW'(CRD);
            if (cr == CW'(CRD) && fcr_q && !take) fault <= 1'b1;
            t_v <= take; if (take) t_d <= in_d;
        end
endmodule

module ot_hgi_coll_crl_rx #(
    parameter integer W   = 568,
    parameter integer CRD = 8,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          t_v,
    input  wire [W-1:0]  t_d,
    output reg           f_cr,
    output reg           out_v,
    output reg  [W-1:0]  out_d,
    input  wire          out_rdy,
    output reg           fault
);
    localparam integer AW = (CRD > 1) ? $clog2(CRD) : 1;
    reg v_q; reg [W-1:0] d_q;
    reg [W-1:0] fq [0:CRD-1]; reg [AW-1:0] hd, tl; reg [AW:0] n;
    wire pop = out_v && out_rdy;
    always @(posedge clk) d_q <= t_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; hd <= '0; tl <= '0; n <= '0; f_cr <= 1'b0; fault <= 1'b0; out_v <= 1'b0; end
        else begin
            v_q <= t_v;
            if (v_q) begin
                if (n == (AW+1)'(CRD) && !pop) fault <= 1'b1;
                fq[tl] <= d_q; tl <= (tl == AW'(CRD - 1)) ? '0 : tl + 1'b1;
            end
            if (pop) hd <= (hd == AW'(CRD - 1)) ? '0 : hd + 1'b1;
            n <= n + (AW+1)'(v_q) - (AW+1)'(pop);
            out_v <= (n + (AW+1)'(v_q) - (AW+1)'(pop)) != '0;
            if ((n == 0 && v_q) || (n == 1 && pop && v_q)) out_d <= d_q;
            else if (pop && n > 1) out_d <= fq[(hd == AW'(CRD - 1)) ? '0 : hd + 1'b1];
            f_cr <= pop || (MUT == 1 && v_q);
        end
endmodule
`default_nettype wire

`default_nettype none
// ot_hgi_coll_vmport (HBM peer-to-peer step 1, 2026-10-14): the SW quadrant engine's VM-side master, placed AT the SW
// slice's VM face (a client station of the lane arbiter: no relay between it and the slice).  Ends of the engine's two
// credit-flow write streams: ROW_GATHER writes (ot_hgi_coll_rgx_snkm: FIFO + the unchanged ot_hgi_coll_rgx_snk = VM W2
// group client + the two HBM write clients to the loader) and TOPK_MERGE line writes (ot_hgi_coll_crl_rx: FIFO + the
// slice's valid/ready tkw port).  Faults (sticky) return on f_fault.
module ot_hgi_coll_vmport #(
    parameter integer DEL = 4,
    parameter integer FW  = 512,
    parameter integer CRD = 16,
    parameter integer TCRD = 8,
    parameter integer LQ  = 32
) (
    input  wire               clk,
    input  wire               rst_n,
    // from the engine (die nets)
    input  wire [DEL-1:0]     rgx_t_v,
    input  wire [DEL*40-1:0]  rgx_t_addr,
    input  wire [DEL*FW-1:0]  rgx_t_data,
    input  wire               rgx_t_vm,
    output wire [DEL-1:0]     rgx_f_cr,
    input  wire               tkw_t_v,
    input  wire [FW+55:0]     tkw_t_d,        // {addr 40, mask 16, data FW}
    output wire               tkw_f_cr,
    output reg                f_fault,
    // VM W2 group client (ot_hgi_vm_lanearb c_*) and the TOPK line write port of the slice (valid / ready, local)
    output wire               c_req,
    input  wire               c_gnt,
    output wire [32*280-1:0]  c_q,
    input  wire [31:0]        c_cr,
    input  wire [31:0]        c_rsp,
    output wire               tkw_v,
    output wire [FW+55:0]     tkw_d,
    input  wire               tkw_rdy,
    // HBM write lanes (loader)
    output wire [2*326-1:0]   xw,
    input  wire [1:0]         xwa
);
    wire sf, tf;
    ot_hgi_coll_rgx_snkm #(.DEL(DEL), .FW(FW), .CRD(CRD), .LQ(LQ)) u_rgx (.clk(clk), .rst_n(rst_n), .t_v(rgx_t_v),
        .t_addr(rgx_t_addr), .t_data(rgx_t_data), .t_vm(rgx_t_vm), .f_cr(rgx_f_cr), .f_fault(sf),
        .c_req(c_req), .c_gnt(c_gnt), .c_q(c_q), .c_cr(c_cr), .c_rsp(c_rsp), .xw(xw), .xwa(xwa));
    ot_hgi_coll_crl_rx #(.W(FW + 56), .CRD(TCRD)) u_tkw (.clk(clk), .rst_n(rst_n), .t_v(tkw_t_v), .t_d(tkw_t_d),
        .f_cr(tkw_f_cr), .out_v(tkw_v), .out_d(tkw_d), .out_rdy(tkw_rdy), .fault(tf));
    always @(posedge clk or negedge rst_n) if (!rst_n) f_fault <= 1'b0; else f_fault <= sf | tf;
endmodule
`default_nettype wire

`default_nettype none
// Physical receive leaf: data and consume pulse land in pin flops. The head epoch lets the
// local issuer suppress a repeated grant while its registered consume pulse crosses the boundary.
module ot_hgi_coll_rx_native #(parameter integer W=552, CRD=16)(
    input wire clk,rst_n,t_v,
    input wire [W-1:0] t_d,
    output reg out_v,
    output wire [W-1:0] out_d,
    input wire out_rdy,
    output reg epoch,
    output reg fault
);
    localparam integer AW=(CRD>1)?$clog2(CRD):1;
    reg v_pin,pop_pin;reg[W-1:0]d_pin;
    reg[AW:0]n;
    wire pop=out_v&&pop_pin;
    wire load_new=(n==0&&v_pin)||(n==1&&pop&&v_pin);
    wire load_next=pop&&n>1;
    always @(posedge clk)d_pin<=t_d;
    // Each region owns its read/write pointer copies. A single binary head pointer
    // otherwise drives thousands of mux inputs even though the payload has no reset.
    for(genvar r=0;r<(W+63)/64;r=r+1)begin:g_region
        localparam integer RW=(W-64*r<64)?W-64*r:64;
        ot_hgi_coll_rx_region #(.W(RW),.CRD(CRD)) u_region(
            .clk(clk),.rst_n(rst_n),.push(v_pin),.pop(pop),.d(d_pin[64*r+:RW]),
            .load_new(load_new),.load_next(load_next),.head(out_d[64*r+:RW]));
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin v_pin<=0;pop_pin<=0;n<=0;out_v<=0;epoch<=0;fault<=0;end
        else begin
            v_pin<=t_v;pop_pin<=out_rdy;
            if(v_pin&&n==(AW+1)'(CRD)&&!pop)fault<=1;
            if(pop)epoch<=!epoch;
            n<=n+(AW+1)'(v_pin)-(AW+1)'(pop);
            out_v<=(n+(AW+1)'(v_pin)-(AW+1)'(pop))!='0;
        end
endmodule

// Local payload region, sharing the leaf clock. Payload state has no reset gate;
// retained pointer copies bound each select network to at most 64 payload bits.
(* keep_hierarchy = "yes" *)
module ot_hgi_coll_rx_region #(parameter integer W=64,CRD=16)(
    input wire clk,rst_n,push,pop,load_new,load_next,
    input wire [W-1:0]d,
    output reg [W-1:0]head
);
    localparam integer AW=(CRD>1)?$clog2(CRD):1;
    (* keep=1 *) reg[AW-1:0]hd,tl;
    reg[W-1:0]q[0:CRD-1];
    always @(posedge clk)begin
        if(push)q[tl]<=d;
        if(load_new)head<=d;
        else if(load_next)head<=q[(hd==AW'(CRD-1))?'0:hd+1'b1];
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin hd<=0;tl<=0;end
        else begin
            if(push)tl<=(tl==AW'(CRD-1))?'0:tl+1'b1;
            if(pop)hd<=(hd==AW'(CRD-1))?'0:hd+1'b1;
        end
endmodule
`default_nettype wire
