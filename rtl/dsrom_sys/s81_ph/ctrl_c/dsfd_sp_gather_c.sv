`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_gather_c (s81-ctl-1011, 2026-10-11): the gather slab master WITH the field (fld, engine 0) command / start /
// done endpoint (physical/s81_ctrl/ADAPTER_CONTRACT_1011.json v2, non-PQ dies).  Generator: --ctrl-adapters.
//   = dsfd_sp_gather UNCHANGED (rows, roots, the VM control-word crossing) + ot_s81_slab_ep (JQ 1) + the phase stage:
//   * the VM posts phase words (f_vm kind 0) ahead of time; they no longer go straight to the capture but wait in a
//     4-entry phase stage (e_inputs_present = stage non-empty); reset words (kind 1) pass straight through;
//   * START: a fld descriptor (arg[9:0] = phase id) releases the stage head into the capture control lane and pulses
//     t_xgo = {v, phase} to the x source (VM / x start blocks: the field broadcast of that phase).  A head whose
//     phase differs from the descriptor's is a fault (fail closed, nothing released);
//   * DONE: the capture's phase-drained event (f_cd = {toggle, fault, phase} from dsfd_sp_capture_c, serial domain,
//     toggle synchronised here) for the descriptor's phase.  A drained event for another phase, or with the capture
//     fault set, is a fault and returns no done.
// One phase in flight (the capture holds CAPACITY 1): the next descriptor is accepted only after the done.
// Added cycles (priced): +1 on a phase word (stage flop) beyond the descriptor wait; done +3 (toggle sync + compare).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_sp_gather_c #(parameter integer ROOTD = 128, parameter integer MUT = 0) (
    input wire [0:0] ck, input wire [0:0] rst, input wire [0:0] ckv, input wire [0:0] rsv,
    input wire [511:0] f_vm,
    output wire [6946:0] t_capture,
    input wire [691:0] rW0, input wire [760:0] rW1, input wire [760:0] rW2, input wire [760:0] rW3,
    input wire [760:0] rW4, input wire [691:0] rW5,
    input wire [691:0] rE0, input wire [760:0] rE1, input wire [760:0] rE2, input wire [760:0] rE3,
    input wire [760:0] rE4, input wire [691:0] rE5,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,
    input wire [11:0] f_cd,
    output reg [10:0] t_xgo
);
    wire [6946:0] tr;
    dsfd_sp_gather #(.ROOTD(ROOTD)) u_g (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_vm(f_vm), .t_capture(tr),
        .rW0(rW0), .rW1(rW1), .rW2(rW2), .rW3(rW3), .rW4(rW4), .rW5(rW5),
        .rE0(rE0), .rE1(rE1), .rE2(rE2), .rE3(rE3), .rE4(rE4), .rE5(rE5));
    reg [1:0] rs_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    wire rs_n = rs_s[1];
    // ---- control lane of the gather output: {c_d 159, c_v} at [6784 +: 160]
    wire        w_v = tr[6784];
    wire [158:0] w_d = tr[6785 +: 159];
    wire        w_ph = w_v && (w_d[1:0] == 2'd0);
    // ---- phase stage (4 entries)
    reg [158:0] sq [0:3]; reg [1:0] swp, srp; reg [2:0] sn;
    wire jv, jnew; wire [83:0] jd, jnd; wire epf;
    wire rel = jnew;                                   // a descriptor entered: release the stage head
    wire [9:0] dph = jnd[16:7];                        // descriptor arg[9:0]
    wire [158:0] head = sq[srp];
    wire pop = rel && sn != 0;
    reg sf; reg [158:0] cq; reg cqv; reg fly;
    // ---- capture phase-drained event (serial domain toggle, synchronised)
    (* async_reg = "true" *) reg [2:0] tg_s;
    always @(posedge ck[0] or negedge rs_n) if (!rs_n) tg_s <= 3'b000; else tg_s <= {tg_s[1:0], f_cd[11]};
    wire ev   = tg_s[2] ^ tg_s[1];
    wire dn   = ev && fly && jv && !f_cd[10] && f_cd[9:0] == jd[16:7];
    wire dbad = ev && !dn;
    always @(posedge ck[0] or negedge rs_n)
        if (!rs_n) begin swp <= 0; srp <= 0; sn <= 0; sf <= 1'b0; cqv <= 1'b0; t_xgo <= 11'd0; fly <= 1'b0; end
        else begin
            cqv <= 1'b0; t_xgo <= 11'd0;
            if (w_ph) begin sq[swp] <= w_d; swp <= swp + 1'b1; if (sn == 3'd4 && !pop) sf <= 1'b1; end
            if (w_v && !w_ph) begin cqv <= 1'b1; cq <= w_d; end                   // reset words pass through
            if (rel) begin
                fly <= 1'b1;
                if (sn == 0 || head[58:49] != dph || (w_v && !w_ph)) sf <= 1'b1;   // nothing staged / wrong phase
                else begin cqv <= 1'b1; cq <= head; t_xgo <= {1'b1, dph}; end
            end
            if (pop) srp <= srp + 1'b1;
            case ({w_ph, pop}) 2'b10: sn <= sn + 1'b1; 2'b01: sn <= sn - 1'b1; default: sn <= sn; endcase
            if (dn) fly <= 1'b0;
            if (dbad) sf <= 1'b1;
        end
    assign t_capture = {tr[6946:6944], cq, cqv, tr[6783:0]};
    ot_s81_slab_ep #(.QD(8), .JQ(1), .MUT(MUT)) u_ep (.c_clk(ck[0]), .c_rst_n(rst[0]), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck[0]), .e_rst_n(rst[0]), .j_v(jv), .j_d(jd), .j_new(jnew), .j_new_d(jnd),
        .j_present(sn != 0), .j_done(dn), .slab_fault(sf), .ep_fault(epf));
endmodule
