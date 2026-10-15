`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_rgx_wtx + ot_hgi_coll_rgx_snkm (HBM peer-to-peer step 1, 2026-10-14): the ROW_GATHER write path of the SW
// quadrant engine split at the die net, so that the VM W2 group client (ot_hgi_coll_rgx_snk, unchanged) sits AT its lane
// arbiter beside the SW slice.  ot_hgi_vm_lanearb merges the owner's lanes with its registered grant in the same edge
// (a client station on the group bus): the client's c_req / c_gnt / c_q / c_cr / c_rsp can not cross the die through
// relays, and its 32 x 280 = 8,960 b lane bundle was the widest net of the v14 die (el1014-hbm-p2p-coll.log 11:57).
//   die net engine -> slice   t_v DEL, t_addr DEL x 40, t_data DEL x FW, t_vm   (2,213 b at DEL 4, FW 512), registered;
//   die net slice -> engine   f_cr DEL (one credit a flit taken by the sink), f_fault, registered.
// Credit flow control per delivery lane, CRD credits = the slice-side FIFO depth, so ANY number of relay stages is
// legal (the rate is CRD / round trip a lane).  The engine's ep pops its rg_w head when the lane holds a credit (local
// register, no cross-die combinational path).  idle = every credit home = every flit taken by the sink: the record's
// drained condition (ot_hgi_coll_qep rg_w_idle), so a run still retires only after its last flit reached the sink.
module ot_hgi_coll_rgx_wtx #(
    parameter integer DEL = 4,
    parameter integer FW  = 512,
    parameter integer CRD = 16
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [DEL-1:0]     rg_w_v,
    input  wire [DEL*40-1:0]  rg_w_addr,
    input  wire               rg_w_vm,
    input  wire [DEL*FW-1:0]  rg_w_data,
    output wire [DEL-1:0]     rg_w_rdy,
    output reg                idle,
    output reg  [DEL-1:0]     t_v,
    output reg  [DEL*40-1:0]  t_addr,
    output reg  [DEL*FW-1:0]  t_data,
    output reg                t_vm,
    input  wire [DEL-1:0]     f_cr,
    input  wire               f_fault,
    output reg                fault
);
    localparam integer CW = $clog2(CRD + 1);
    reg [CW-1:0] cr [0:DEL-1];
    reg [DEL-1:0] fcr_q; reg ff_q;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_rdy
        assign rg_w_rdy[l] = rg_w_v[l] && (cr[l] != '0);
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer l = 0; l < DEL; l = l + 1) cr[l] <= CW'(CRD);
            t_v <= '0; t_vm <= 1'b0; fcr_q <= '0; ff_q <= 1'b0; fault <= 1'b0; idle <= 1'b1;
        end else begin : st
            reg all_home;
            fcr_q <= f_cr; ff_q <= f_fault;
            all_home = 1'b1;
            for (integer l = 0; l < DEL; l = l + 1) begin
                cr[l] <= cr[l] - CW'(rg_w_rdy[l]) + CW'(fcr_q[l]);
                if (cr[l] - CW'(rg_w_rdy[l]) + CW'(fcr_q[l]) != CW'(CRD)) all_home = 1'b0;
                if (cr[l] == CW'(CRD) && fcr_q[l] && !rg_w_rdy[l]) fault <= 1'b1;       // credit overflow
            end
            idle <= all_home;
            t_v <= rg_w_rdy;
            for (integer l = 0; l < DEL; l = l + 1) if (rg_w_rdy[l]) begin
                t_addr[l*40 +: 40] <= rg_w_addr[l*40 +: 40]; t_data[l*FW +: FW] <= rg_w_data[l*FW +: FW];
            end
            if (|rg_w_rdy) t_vm <= rg_w_vm;
            if (ff_q) fault <= 1'b1;
        end
endmodule

// The slice-side master: pin capture, CRD-deep FIFO a lane, the unchanged sink ot_hgi_coll_rgx_snk (VM W2 group client +
// the two HBM write clients), one credit back a flit the sink takes.
module ot_hgi_coll_rgx_snkm #(
    parameter integer DEL = 4,
    parameter integer FW  = 512,
    parameter integer CRD = 16,
    parameter integer LQ  = 32,
    parameter integer MUT = 0,              // bench: 1 a lane's credit is returned twice (overdraws the FIFO)
    parameter integer SMUT = 0              // bench: the sink's own mutants (ot_hgi_coll_rgx_snk MUT)
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [DEL-1:0]     t_v,
    input  wire [DEL*40-1:0]  t_addr,
    input  wire [DEL*FW-1:0]  t_data,
    input  wire               t_vm,
    output reg  [DEL-1:0]     f_cr,
    output reg                f_fault,
    // VM W2 group client (ot_hgi_vm_lanearb c_*), at the arbiter
    output wire               c_req,
    input  wire               c_gnt,
    output wire [32*280-1:0]  c_q,
    input  wire [31:0]        c_cr,
    input  wire [31:0]        c_rsp,
    // HBM write lanes
    output wire [2*326-1:0]   xw,
    input  wire [1:0]         xwa
);
    localparam integer AW = $clog2(CRD);
    reg [DEL-1:0] v_q; reg [DEL*40-1:0] a_q; reg [DEL*FW-1:0] d_q; reg vm_q, vm_run;
    reg [40+FW-1:0] fq [0:DEL-1][0:CRD-1];
    reg [AW-1:0] hd [0:DEL-1], tl [0:DEL-1]; reg [AW:0] n [0:DEL-1];
    reg ovf;
    wire [DEL-1:0] w_v, w_rdy; wire [DEL*40-1:0] w_a; wire [DEL*FW-1:0] w_d; wire sfault;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_h
        assign w_v[l] = (n[l] != '0);
        assign w_a[l*40 +: 40] = fq[l][hd[l]][40+FW-1 -: 40];
        assign w_d[l*FW +: FW] = fq[l][hd[l]][FW-1:0];
    end
    ot_hgi_coll_rgx_snk #(.DEL(DEL), .FW(FW), .LQ(LQ), .MUT(SMUT)) u_s (.clk(clk), .rst_n(rst_n), .rg_w_v(w_v), .rg_w_addr(w_a),
        .rg_w_vm(vm_run), .rg_w_data(w_d), .rg_w_rdy(w_rdy), .c_req(c_req), .c_gnt(c_gnt), .c_q(c_q), .c_cr(c_cr), .c_rsp(c_rsp),
        .xw(xw), .xwa(xwa), .fault(sfault));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            v_q <= '0; vm_q <= 1'b0; vm_run <= 1'b0; f_cr <= '0; f_fault <= 1'b0; ovf <= 1'b0;
            for (integer l = 0; l < DEL; l = l + 1) begin hd[l] <= '0; tl[l] <= '0; n[l] <= '0; end
        end else begin
            v_q <= t_v; a_q <= t_addr; d_q <= t_data; vm_q <= t_vm;
            // a run's flits all carry its O space; a run retires only drained (every credit home), so the FIFOs hold
            // one run at a time
            if (|v_q) vm_run <= vm_q;
            for (integer l = 0; l < DEL; l = l + 1) begin : ln
                reg push, pop;
                push = v_q[l]; pop = w_v[l] && w_rdy[l];
                if (push) begin
                    if (n[l] == (AW+1)'(CRD) && !pop) ovf <= 1'b1;
                    fq[l][tl[l]] <= {a_q[l*40 +: 40], d_q[l*FW +: FW]};
                    tl[l] <= (tl[l] == AW'(CRD - 1)) ? '0 : tl[l] + 1'b1;
                end
                if (pop) hd[l] <= (hd[l] == AW'(CRD - 1)) ? '0 : hd[l] + 1'b1;
                n[l] <= n[l] + (AW+1)'(push) - (AW+1)'(pop);
                f_cr[l] <= pop || (MUT == 1 && l == 0 && push);
            end
            f_fault <= sfault | ovf;
        end
endmodule
`default_nettype wire
