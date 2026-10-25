`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsdv_idx_qfs (S81/IDXNET 2026-10-25, S81 DECISION 2): the iqf partition top = dsdv_idx_qf + the 2-beat serializer of
// the root's tree-frame words onto the plan lane qc__iqf__s_0N_LP (258 b).  A 513-b qc lane would put the col-6 s_0S_LP
// S face at 0.607 (> 0.60); the ql lane (s_0N lep -> iqf) stays 513 b.
//   qc = {data 256, beat, v}: a qc0 word w (valid w[0]) leaves as beat 0 {w[256:1], 0, 1} one edge later and beat 1
//   {w[512:257], 1, 1} the next edge (qs pin -> qc beat 0 = 4 edges).  The root's frame must come at <= 1 word / 2 cycles
//   (compiler: lower_bk paces the tree frame on qs); a word while beat 1 is pending is a sticky fault (st[4]) and is lost.
// Pins: qs / ql land in qf's pin flops, qr / qc leave flops.  MUT (bench): 1 beat 1 carries the low half again.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_idx_qfs #(
    parameter integer MUT = 0,       // -> dsdv_idx_qf MUT
    parameter integer SMUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [512:0]  qs,
    input  wire [512:0]  ql,
    output wire [512:0]  qr,
    output wire [257:0]  qc,
    output wire          fault
);
    localparam integer NJ = 11;                    // 11 x 24 >= 256 data bits
    wire [512:0] qc0; wire qfault;
    dsdv_idx_qf #(.MUT(MUT)) u_qf (.ck(ck), .rst(rst), .qs(qs), .ql(ql), .qr(qr), .qc0(qc0), .fault(qfault));
    reg rs0, rs1;
    always @(posedge ck or negedge rst) if (!rst) begin rs0 <= 1'b0; rs1 <= 1'b0; end else begin rs0 <= 1'b1; rs1 <= rs0; end
    reg hv, se; reg [255:0] hi; reg [257:0] qc_r; wire [NJ-1:0] hk;
    genvar j;
    generate for (j = 0; j < NJ; j = j + 1) begin : g_hk
        dsdv_qf_copy #(.W(1), .RESET(1), .ID(800 + j)) u (.ck(ck), .rn(rs1), .d(qc0[0]), .q(hk[j]));
    end endgenerate
    always @(posedge ck or negedge rs1)
        if (!rs1) begin hv <= 1'b0; se <= 1'b0; qc_r[1:0] <= 2'b00; end
        else begin
            hv <= qc0[0] && !hv;
            qc_r[0] <= qc0[0] || hv; qc_r[1] <= hv;
            if ((qc0[0] && hv) || qfault) se <= 1'b1;
        end
    always @(posedge ck) hi <= (SMUT == 1) ? qc0[256:1] : qc0[512:257];
    generate for (j = 0; j < NJ; j = j + 1) begin : g_d
        localparam integer LO = 24 * j, W = (256 - LO < 24) ? 256 - LO : 24;
        always @(posedge ck) qc_r[2 + LO +: W] <= hk[j] ? hi[LO +: W] : qc0[1 + LO +: W];
    end endgenerate
    assign qc = qc_r;
    assign fault = se; // one sticky registered fault; +1 edge on qf fault status only
endmodule
