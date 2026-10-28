`timescale 1ns/1ps
`default_nettype none
// HBM-BIND-CMP 2026-10-26 (COORD ruling 4, PATH-HBM-R2): the static-schedule REQUEST CHECK of one SM.
// The SM service group's S1 consumer copy (ot_smh_static_feed in ot_hbm_svc_sm_feed_programmed_rel_id) produces
// expected_request(t) = sm_command(t-1)[82:40] = {v, address32, tag10}, the request the compiler scheduled; the SM
// (ot_hbm_accel_smh_attn) produces request(t) = its landed command(t-1)[82:40] (normal mode) or its KV descriptor request
// (attention mode, itself checked against command[82:40] inside the SM).  Both are views of ONE scheduled word, so after
// the fixed round trip RQD they must agree bit-exactly whenever either side is valid.
//   * sm_req lands on one pin flop (partition pin rule); expected is delayed RQD edges in a reset shift line.  With
//     sm_command(t) leaving the group, expected_request(t) = sm_command(t-1) and the SM's request(t) =
//     sm_command(t - Ls - 1 - QSPLIT) (QSPLIT landing + the front's request register), back at this pin flop Lr edges
//     later, so RQD = Ls + Lr + 1 + QSPLIT  (Ls = lane(svg -> sm, sm_command), Lr = lane(sm -> svg, request); the die SM
//     is QSPLIT 1).  tools/hbm_b2/b2_delays.py derives RQD from the plan's lane table (formula in its derivations).
//   * compare enable: armed RQD + 1 edges after reset (the transport stations, which have no reset, have flushed);
//     then a cycle is checked when the scheduled valid bit or the SM's valid bit is set (schedule off = both 0 = no check).
//     mismatch = (v_sm != v_exp) || (v_exp && {addr, tag} differ).
//   * the compare result is registered, then accumulated in ONE sticky bit (fault flag only: no stall, no backpressure,
//     nothing waits on it).  Cleared by reset or by a host write (clr = the group's programme configuration write).
// MUT (bench negative controls only): 1 = expected delayed one edge too few, 2 = sticky not held (pulse), 3 = address/tag
// ignored (valid only).
module ot_hbm_sm_req_check #(parameter integer RQD = 2, parameter integer MUT = 0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        clr,
    input  wire [42:0] exp_req,
    input  wire [42:0] sm_req,
    output reg         mismatch
);
    localparam integer D  = (MUT == 1) ? RQD - 1 : RQD;
    localparam integer AW = 9;
    localparam [AW-1:0] ARM = RQD + 1;
    reg [42:0] req_q;
    reg [42:0] line [0:(D > 0 ? D : 1) - 1];
    reg [AW-1:0] arm_cnt;
    reg armed, cmp_r;
    wire [42:0] exp_d = line[D - 1];
    integer k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            req_q <= 43'd0;
            for (k = 0; k < D; k = k + 1) line[k] <= 43'd0;
        end else begin
            req_q <= sm_req;
            line[0] <= exp_req;
            for (k = 1; k < D; k = k + 1) line[k] <= line[k - 1];
        end
    wire v_diff  = req_q[42] != exp_d[42];
    wire at_diff = (MUT == 3) ? 1'b0 : (req_q[41:0] != exp_d[41:0]);
    wire bad     = armed && (v_diff || (exp_d[42] && at_diff));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            arm_cnt <= {AW{1'b0}}; armed <= 1'b0; cmp_r <= 1'b0; mismatch <= 1'b0;
        end else begin
            if (!armed) arm_cnt <= arm_cnt + 1'b1;
            if (arm_cnt == ARM) armed <= 1'b1;
            cmp_r <= bad;
            if (clr)                  mismatch <= 1'b0;
            else if (MUT == 2)        mismatch <= cmp_r;
            else if (cmp_r)           mismatch <= 1'b1;
        end
    initial if (RQD < 1 || RQD > 400) $error("ot_hbm_sm_req_check: RQD %0d outside 1..400", RQD);
endmodule

// The SM service group with the request check (opt-in successor of ot_hbm_svc_sm_group_rel_id, which stays byte-identical).
// Port list = ot_hbm_svc_sm_group_rel_id minus the S1 consumer copy's data views (expected_request, lt0, lt1, lb0, lb1, fm:
// the copy exists for its fault check; the SM decodes sm_packet / sm_command itself, so those outputs were never read on the
// die and are now internal: expected_request feeds the check, lt/lb/fm are dead and pruned by synthesis) plus the SM's
// request input.  fault = the group's fault OR the sticky request mismatch (host-visible per SM through cp_svg tgt_fault ->
// hleaf t_fault, and through sfault svg_fault).
module ot_hbm_svc_sm_group_rel_id_rc #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer NID=6,parameter integer IDW=9,parameter integer PAW=11,parameter integer PREL=1,parameter integer DD=256,parameter integer IMUT=0,
 parameter integer DAW=(DD>128)?8:7,parameter integer ID_COHORT=0,
 parameter integer XSLOT=0,parameter integer CTXW=(XSLOT!=0)?53:46,
 parameter integer OPEN_IL=0,
 parameter integer ATT_MARK=0,
 parameter integer RQD=2,parameter integer RQMUT=0)(
 input wire[1:0]id_stack,input wire[2:0]id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output wire running,run_done,program_active,fault,
 output wire[1098:0]sm_packet,output wire[82:0]sm_command,
 input wire[42:0]sm_request,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 wire g_fault,req_mismatch;
 wire[42:0]expected_request;
 ot_hbm_svc_sm_group_rel_id #(.LBANKS(LBANKS),.LB(LB),.NID(NID),.IDW(IDW),.PAW(PAW),.PREL(PREL),.DD(DD),.IMUT(IMUT),.DAW(DAW),
  .ID_COHORT(ID_COHORT),.XSLOT(XSLOT),.CTXW(CTXW),.OPEN_IL(OPEN_IL),.ATT_MARK(ATT_MARK)) u_g(
  .id_stack(id_stack),.id_sm(id_sm),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .stream_bank_clk(stream_bank_clk),.hbm_fifo_clk(hbm_fifo_clk),.hbm_pc_clk(hbm_pc_clk),
  .program_cfg_we(program_cfg_we),.program_cfg_addr(program_cfg_addr),.program_cfg_data(program_cfg_data),
  .desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data),
  .run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_layer),
  .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort),
  .running(running),.run_done(run_done),.program_active(program_active),.fault(g_fault),
  .sm_packet(sm_packet),.sm_command(sm_command),
  .expected_request(expected_request),.lt0(),.lt1(),.lb0(),.lb1(),.fm(),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
  .k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 ot_hbm_sm_req_check #(.RQD(RQD),.MUT(RQMUT)) u_rqc(.clk(stream_clk),.rst_n(stream_rst_n),.clr(program_cfg_we),
  .exp_req(expected_request),.sm_req(sm_request),.mismatch(req_mismatch));
 assign fault=g_fault||req_mismatch;
endmodule
`default_nettype wire
