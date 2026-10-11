`timescale 1ns/1ps
`default_nettype none
// fe-push-hgi-1010 2026-10-10 (hardcore-1010 feasibility, ot_hgi_cp_die MTP=2 row): REGISTERED MX1 MTP COLLAR for the CP
// die.  ot_hgi_cp_die MTP=2 bound the MX1 collar hfd_cmdproc_s_mtp_native_mx1_mtp in its UNREGISTERED form: the die nets
// f_mtp 517 (from hgi_mtp_native t_cmdproc) / t_mtp 197 reached 15 gate levels of admission / join / emit-queue logic
// (rtl_boundary in->reg 15 of 16) and the mh_* host / provider die nets were feedthroughs or combinational.  This shell
// is the MX1 REGB=1 MTP side (physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv g_regb, the mtp-mx1 FT12
// form 7562e8086 incl. the host job channel in pin flops) WITHOUT the AR band and the ARGMAX dispatch relay, so that the
// CP die gets the same, already-gated boundary:
//   * valid/ready channels cross ot_sc_pfifo pin FIFOs (2 entries, in_ready / out_valid from flops): emit f_mtp[43] /
//     t_mtp[139]; command f_mtp[82] / t_mtp[82]; backend command t_backend[0] / f_backend[0]; completion f_backend[1] /
//     t_backend[270]; host records t_emit_host[0] / f_emit_host[0]; host done t_emit_host[74] / f_emit_host[1];
//   * the job channel f_host lands in pin flops (hv_q / hd_q), pin ready offered at most every other cycle;
//   * level inputs (native done / status, AM, backend identity / quiescent / fault) get one pin flop; native done is held
//     behind the emit FIFO, host done behind the host-record FIFO (ordering kept);
//   * every other output is a flop at the pin.
// Cost: +1 cycle on every crossing (+2 per round trip); the prompt / forced-token read loop (t_provider -> provider ->
// f_provider -> t_mtp) gains 2 cycles: the controller must wait PRL = 4 (hgi_mtp_native default: unchanged).
// Reset: the rst_n port drives only an ot_rst_relay (4 regions: inputs, backend side, host side, core + outputs);
// release 3 edges after the port (the MX1 form's 2-flop sync released after 2; transaction-level exact).
// MUT (bench mutants): 1 native done not held behind the emit FIFO; 2 host done not held behind the host-record FIFO.
module ot_hgi_cp_mtp_pinreg #(parameter integer ENABLE_MTP=1, parameter integer MUT=0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [516:0]  f_mtp,
    output wire [196:0]  t_mtp,
    input  wire [215:0]  f_host,
    output wire [4:0]    t_host,
    input  wire [178:0]  f_provider,
    output wire [37:0]   t_emit,
    output wire [42:0]   t_provider,
    input  wire [1:0]    f_emit_host,
    output wire [99:0]   t_emit_host,
    output wire          t_abort,
    output wire          t_drained,
    input  wire [17:0]   f_am,
    input  wire [72:0]   f_backend,
    output wire [270:0]  t_backend
);
    wire c = clk;
    wire [3:0] rr;   // relay regions: 0 inputs (level flops, job / emit / command FIFOs), 1 backend FIFOs, 2 host FIFOs, 3 core + outputs
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(c), .rst_n_in(rst_n), .rst_n(rr));
    wire rn_in = rr[0], rn_be = rr[1], rn_h = rr[2], rn_o = rr[3];
    wire rm_in = ~rn_in, rm_be = ~rn_be, rm_h = ~rn_h, rm_o = ~rn_o;
    // ---- core view of the pins
    wire [516:0] mi; wire [196:0] mo; wire [215:0] hi; wire [4:0] ho; wire [37:0] eo; wire [42:0] po;
    wire [1:0] ehi; wire [99:0] eho; wire ab, dr; wire [17:0] ami; wire [72:0] bi; wire [270:0] bo;
    // ---- level pin flops
    reg q81, q71, q72; reg [2:0] qst; reg qam; reg [16:0] qami; reg [67:0] qid;
    always @(posedge c or posedge rm_in) if (rm_in) begin q81 <= 0; q71 <= 0; q72 <= 0; qam <= 0; end
        else begin q81 <= f_mtp[81]; q71 <= f_backend[71]; q72 <= f_backend[72]; qam <= f_am[0]; end
    always @(posedge c) begin qst <= f_mtp[514 +: 3]; qami <= f_am[1 +: 17]; qid <= f_backend[2 +: 68]; end
    // ---- input channels (job: pin flops, one job per admission window; see the MX1 FT12 note)
    wire jf_ir, jf_ov; wire [214:0] jf_od; reg open_q, hv_q, h_rdy_q; reg [214:0] hd_q;
    wire h_rdy = jf_ir && rn_in && open_q && !h_rdy_q && !hv_q;
    always @(posedge c or posedge rm_in) if (rm_in) begin open_q <= 1'b0; hv_q <= 1'b0; h_rdy_q <= 1'b0; end
        else begin hv_q <= f_host[0] && h_rdy; h_rdy_q <= h_rdy; open_q <= ho[0] && !hv_q && !jf_ov; end
    always @(posedge c) hd_q <= f_host[1 +: 215];
    ot_sc_pfifo #(.W(215), .S(2), .G(32)) jf (.clk(c), .rst_n(rn_in), .in_valid(hv_q), .in_ready(jf_ir), .in_data(hd_q),
        .out_valid(jf_ov), .out_ready(ho[0]), .out_data(jf_od));
    wire ef_ir, ef_ov; wire [36:0] ef_od;
    ot_sc_pfifo #(.W(37), .S(2), .G(37)) ef (.clk(c), .rst_n(rn_in), .in_valid(f_mtp[43] && rn_in), .in_ready(ef_ir),
        .in_data(f_mtp[44 +: 37]), .out_valid(ef_ov), .out_ready(mo[139]), .out_data(ef_od));
    wire cf_ir, cf_ov; wire [200:0] cf_od;
    ot_sc_pfifo #(.W(201), .S(2), .G(32)) cf (.clk(c), .rst_n(rn_in), .in_valid(f_mtp[82] && rn_in), .in_ready(cf_ir),
        .in_data(f_mtp[83 +: 201]), .out_valid(cf_ov), .out_ready(mo[82]), .out_data(cf_od));
    wire kf_ir, kf_ov; wire [68:0] kf_od;
    ot_sc_pfifo #(.W(69), .S(2), .G(35)) kf (.clk(c), .rst_n(rn_be), .in_valid(f_backend[1] && rn_be), .in_ready(kf_ir),
        .in_data(f_backend[2 +: 69]), .out_valid(kf_ov), .out_ready(bo[270]), .out_data(kf_od));
    // ---- output channels
    wire bf_ir, bf_ov; wire [268:0] bf_od;
    ot_sc_pfifo #(.W(269), .S(2), .G(32)) bf (.clk(c), .rst_n(rn_be), .in_valid(bo[0]), .in_ready(bf_ir), .in_data(bo[1 +: 269]),
        .out_valid(bf_ov), .out_ready(f_backend[0]), .out_data(bf_od));
    wire hf_ir, hf_ov; wire [72:0] hf_od;
    ot_sc_pfifo #(.W(73), .S(2), .G(37)) hf (.clk(c), .rst_n(rn_h), .in_valid(eho[0]), .in_ready(hf_ir), .in_data(eho[1 +: 73]),
        .out_valid(hf_ov), .out_ready(f_emit_host[0]), .out_data(hf_od));
    wire hf_empty = (MUT == 2) ? 1'b1 : !hf_ov;
    wire df_ir, df_ov; wire [2:0] df_od;
    ot_sc_pfifo #(.W(3), .S(2), .G(3)) df (.clk(c), .rst_n(rn_h), .in_valid(eho[74] && hf_empty), .in_ready(df_ir),
        .in_data(eho[75 +: 3]), .out_valid(df_ov), .out_ready(f_emit_host[1]), .out_data(df_od));
    // ---- core inputs
    assign mi[42:0] = 43'b0;                                  // provider addresses leave through t_provider (below)
    assign mi[43] = ef_ov && mo[139];                         // the queue pushes exactly the beats the FIFO pops
    assign mi[44 +: 37] = ef_od;
    assign mi[81] = q81 && ((MUT == 1) ? 1'b1 : !ef_ov);      // native done stays behind the last emitted token
    assign mi[82] = cf_ov; assign mi[83 +: 201] = cf_od;
    assign mi[284 +: 230] = 230'b0; assign mi[514 +: 3] = qst;
    assign hi = {jf_od, jf_ov};
    assign ehi = {df_ir && hf_empty, hf_ir};
    assign ami = {qami, qam};
    wire [67:0] id = kf_ov ? kf_od[67:0] : qid;              // completion identity (see the MX1 note)
    assign bi = {q72, q71 && !bf_ov && !kf_ov, kf_od[68], id, kf_ov, bf_ir};
    hfd_cmdproc_s_mtp_native_mx1_mtp #(.ENABLE_MTP(ENABLE_MTP)) mtp (.ck(c), .rst(rm_o),
        .f_mtp(mi), .emit_pend(ef_ov), .t_mtp(mo), .f_host(hi), .t_host(ho), .f_provider(f_provider),
        .t_emit(eo), .t_provider(po), .f_emit_host(ehi), .t_emit_host(eho),
        .t_abort(ab), .t_drained(dr), .f_am(ami), .f_backend(bi), .t_backend(bo));
    // ---- registered outputs
    reg [196:0] tm_q; reg [4:1] th_q; reg [37:0] te_q; reg [42:0] tp_q; reg [24:0] teh_q; reg ab_q, dr_q;
    wire fifos_empty = !(jf_ov || ef_ov || cf_ov || kf_ov || bf_ov || hf_ov || df_ov);
    always @(posedge c or posedge rm_o) if (rm_o) begin tm_q <= 0; th_q <= 0; te_q <= 0; tp_q <= 0; teh_q <= 0; ab_q <= 0; dr_q <= 0; end
        else begin
            tm_q <= mo; th_q <= ho[4:1]; te_q <= ENABLE_MTP ? {ef_od, ef_ov && mo[139]} : 38'b0;
            tp_q <= ENABLE_MTP ? f_mtp[0 +: 43] : 43'b0;
            teh_q <= {eho[99], eho[78 +: 21], eho[75 +: 3]}; ab_q <= ab; dr_q <= dr && fifos_empty;
        end
    assign t_mtp = {tm_q[196:140], ef_ir && rn_in, tm_q[138:83], cf_ir && rn_in, tm_q[81:0]};
    assign t_host = {th_q, h_rdy};
    assign t_emit = te_q; assign t_provider = tp_q;
    assign t_emit_host = {teh_q[24], teh_q[23:3], teh_q[2:0], df_ov, hf_od, hf_ov};
    assign t_abort = ab_q; assign t_drained = dr_q;
    assign t_backend = {kf_ir && rn_be, bf_od, bf_ov};
endmodule
`default_nettype wire
