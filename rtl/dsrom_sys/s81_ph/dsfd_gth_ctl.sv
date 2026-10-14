`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_gth_ctl -- control leaf of the gather cluster (s81-gather 2026-10-13): everything of dsfd_sp_gather_c that is
// not a root, with the SAME registers on every path, so the control lane, t_xgo, c_done and c_st are cycle-identical
// to the flat master:
//   * reset synchronisers (stream / serial) and 8 kept reset copies rc, one per root column (async assert, the
//     leaves release synchronously, 2 cycles a leaf down the column);
//   * VM control words: f_vm pin register (serial) -> ratio CDC -> stream register (dsfd_sp_gather);
//   * the fld command / start / done endpoint and the 4-entry phase stage (dsfd_sp_gather_c, unchanged text);
//   * status: trunk {fault, live} pin registers, the 8 column status chains cs = {busy, fault} (pin registers),
//     g_fault sticky / g_busy / g_live and the status register {live, busy, fault | c_ovf}.
// tc = t_capture[6946:6784] = {live, busy, fault, cq 159, cqv}.  Status differs from the flat master only in the
// arrival time of busy / fault (they come down a registered column chain: <= 4 leaves + 1 pin register here).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_gth_ctl #(parameter integer MUT = 0) (
    input  wire         ck,
    input  wire         rst,
    input  wire         ckv,
    input  wire         rsv,
    input  wire [159:0] f_vm,
    input  wire [23:0]  tst,                 // trunk i (rW0..5, rE0..5): [2i +: 2] = {fault, live}
    input  wire [15:0]  cs,                  // column g: [2g +: 2] = {busy, fault}
    input  wire [84:0]  c_cmd,
    output wire [8:0]   c_done,
    output wire [1:0]   c_st,
    input  wire [11:0]  f_cd,
    output reg  [10:0]  t_xgo,
    output wire [162:0] tc,
    output reg  [7:0]   rc
);
    // ---- resets: 2-flop synchronisers per domain
    reg [1:0] rst_s, rv_q;                  // rst_s[1]: the margin SDC's rst_mcp2 cell name
    always @(posedge ck or negedge rst) if (!rst) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    always @(posedge ckv or negedge rsv) if (!rsv) rv_q <= 2'b00; else rv_q <= {rv_q[0], 1'b1};
    wire rs_n = rst_s[1], rv_n = rv_q[1];
    always @(posedge ck or negedge rs_n) if (!rs_n) rc <= 8'h00; else rc <= 8'hFF;
    // ---- status
    reg [23:0] tq; reg [15:0] cq_s;
    always @(posedge ck) begin tq <= tst; cq_s <= cs; end
    reg g_fault, g_busy, g_live; reg cflt;
    integer i;
    always @(posedge ck or negedge rs_n)
        if (!rs_n) begin g_fault <= 1'b0; g_busy <= 1'b0; g_live <= 1'b0; cflt <= 1'b0; end
        else begin
            cflt <= cq_s[0] | cq_s[2] | cq_s[4] | cq_s[6] | cq_s[8] | cq_s[10] | cq_s[12] | cq_s[14];
            g_fault <= g_fault | cflt;
            for (i = 0; i < 12; i = i + 1) if (tq[2*i + 1]) g_fault <= 1'b1;
            g_busy <= cq_s[1] | cq_s[3] | cq_s[5] | cq_s[7] | cq_s[9] | cq_s[11] | cq_s[13] | cq_s[15];
            g_live <= &{tq[22], tq[20], tq[18], tq[16], tq[14], tq[12], tq[10], tq[8], tq[6], tq[4], tq[2], tq[0]};
        end
    // ---- control words from the VM: pin register (serial) -> ratio crossing -> stream
    reg [159:0] fv;
    always @(posedge ckv or negedge rv_n) if (!rv_n) fv <= 160'd0; else fv <= f_vm[159:0];
    wire c_rdy, c_v; wire [158:0] c_d;
    reg c_ovf;
    ot_ratio_cdc_fifo #(.W(159), .DEPTH(4)) u_ctl (.wclk(ckv), .wrst_n(rv_n), .w_v(fv[0]), .w_rdy(c_rdy), .w_d(fv[159:1]),
        .rclk(ck), .rrst_n(rs_n), .r_v(c_v), .r_rdy(1'b1), .r_d(c_d), .w_live(), .r_live());
    always @(posedge ckv or negedge rv_n) if (!rv_n) c_ovf <= 1'b0; else if (fv[0] && !c_rdy) c_ovf <= 1'b1;
    reg c_ovf_s1, c_ovf_s2;    // sticky flag into the stream domain (level, 2-flop)
    always @(posedge ck or negedge rs_n) if (!rs_n) {c_ovf_s2, c_ovf_s1} <= 2'b00; else {c_ovf_s2, c_ovf_s1} <= {c_ovf_s1, c_ovf};
    reg [162:0] tr;            // dsfd_sp_gather's output register, bits [6946:6784]
    always @(posedge ck) begin
        tr[159:0] <= {c_d, c_v};
        tr[162:160] <= {g_live, g_busy, g_fault | c_ovf_s2};
    end
    // ---- dsfd_sp_gather_c: phase stage + fld endpoint (text of ctrl_c/dsfd_sp_gather_c.sv)
    reg [1:0] rs_s;
    always @(posedge ck or negedge rst) if (!rst) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    wire rs2_n = rs_s[1];
    wire        w_v = tr[0];
    wire [158:0] w_d = tr[159:1];
    wire        w_ph = w_v && (w_d[1:0] == 2'd0);
    reg [158:0] sq [0:3]; reg [1:0] swp, srp; reg [2:0] sn;
    wire jv, jnew; wire [83:0] jd, jnd; wire epf;
    wire rel = jnew;                                   // a descriptor entered: release the stage head
    wire [9:0] dph = jnd[16:7];                        // descriptor arg[9:0]
    wire [158:0] head = sq[srp];
    wire pop = rel && sn != 0;
    reg sf; reg [158:0] cq; reg cqv; reg fly;
    (* async_reg = "true" *) reg [2:0] tg_s;
    always @(posedge ck or negedge rs2_n) if (!rs2_n) tg_s <= 3'b000; else tg_s <= {tg_s[1:0], f_cd[11]};
    wire ev   = tg_s[2] ^ tg_s[1];
    // Capture the stable bundled payload at its face pin. The toggle traverses
    // tg_s before ev, so this adds no completion cycle for the bundled protocol.
    (* keep = "true" *) reg [10:0] fcd_pin;
    always @(posedge ck or negedge rs2_n)
        if (!rs2_n) fcd_pin <= 11'd0;
        else fcd_pin <= f_cd[10:0];
    wire dn   = ev && fly && jv && !fcd_pin[10] && fcd_pin[9:0] == jd[16:7];
    wire dbad = ev && !dn;
    always @(posedge ck or negedge rs2_n)
        if (!rs2_n) begin swp <= 0; srp <= 0; sn <= 0; sf <= 1'b0; cqv <= 1'b0; t_xgo <= 11'd0; fly <= 1'b0; end
        else begin
            cqv <= 1'b0; t_xgo <= 11'd0;
            if (w_ph) begin sq[swp] <= w_d; swp <= swp + 1'b1; if (sn == 3'd4 && !pop) sf <= 1'b1; end
            if (w_v && !w_ph) begin cqv <= 1'b1; cq <= w_d; end                   // reset words pass through
            if (rel) begin
                fly <= 1'b1;
                if (sn == 0 || head[58:49] != dph || (w_v && !w_ph)) sf <= 1'b1;   // nothing staged / wrong phase
`ifdef S81PH_MUT_XGO
                else begin cqv <= 1'b1; cq <= head; t_xgo <= {1'b1, dph ^ 10'd1}; end   // MUTANT: wrong phase to the x source
`else
                else begin cqv <= 1'b1; cq <= head; t_xgo <= {1'b1, dph}; end
`endif
            end
            if (pop) srp <= srp + 1'b1;
            case ({w_ph, pop}) 2'b10: sn <= sn + 1'b1; 2'b01: sn <= sn - 1'b1; default: sn <= sn; endcase
            if (dn) fly <= 1'b0;
            if (dbad) sf <= 1'b1;
        end
    assign tc = {tr[162:160], cq, cqv};
    ot_s81_slab_ep #(.QD(8), .JQ(1), .MUT(MUT)) u_ep (.c_clk(ck), .c_rst_n(rst), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck), .e_rst_n(rst), .j_v(jv), .j_d(jd), .j_new(jnew), .j_new_d(jnd),
        .j_present(sn != 0), .j_done(dn), .slab_fault(sf), .ep_fault(epf));
endmodule
