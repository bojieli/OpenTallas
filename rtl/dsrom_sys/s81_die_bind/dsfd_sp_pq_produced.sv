`timescale 1ns/1ps
`default_nettype none
// Canonical PHW10 producer+calendar+native PQ composition candidate.
// Requires OT_PQ_CTL_STATIC and DSFD_PQ_STATIC_X2. Explicit command and
// calendar clock entries require actual fixed phase delivery at die level.
// No historical PHW9 physical view or component proof qualifies this parent.
module dsfd_sp_pq_produced (
    input  wire          ck_ctl, ck_qb, ck_fault,
`ifdef OT_PQ_QB_PIPE
    input wire ck_qb_align,
`endif
`ifdef OT_PQ_QB_PHYS_SPLIT
    input  wire [3:0]    ck_qb_aux,
`endif
    input  wire [1:0]    ck_aq,
`ifdef OT_PQ_AQ_PHYS_SPLIT
    input  wire [15:0]   ck_aq_aux,
`endif
    input  wire [3:0]    ck_ix,
`ifdef OT_PQ_IX_PHYS_SPLIT
`ifdef OT_PQ_IX_BANK_SPLIT
    input  wire [31:0]   ck_ix_read,
`else
    input  wire [15:0]   ck_ix_read,
`endif
`endif
`ifdef OT_PQ_BC_SLICED
    input  wire [15:0]   ck_bc,
`else
    input  wire [3:0]    ck_bc,
`endif
    input  wire          ck_lane,
    input  wire          rst,
    input wire ck_cmd,ck_calendar,
    input wire [84:0] c_cmd,
    output wire [8:0] c_done,
    output wire [1:0] c_st,
    output wire image_sealed,
`ifndef DSFD_PQ_SEQ_SLOT
    input wire [35:0] f_desc_pw,
    input wire calendar_prime,stage_start,
    input wire [11:0] calendar_base,
    input wire [12:0] calendar_length,
`endif
    output wire calendar_primed,calendar_fault,
`ifdef OT_PQ_CTL_STATIC
    output wire stream_end_v,output wire[1:0] stream_end_tag,
`endif
    output wire [38:0]   t_iss,
    output wire [19:0]   t_vm,
    input  wire [2048:0] f_vm,
    output wire [11:0]   ra0, ra1,
`ifdef DSFD_PQ_ROM4
    // S-ELEM-B 10-15 (S-BIND strict port-bind: die ra2 12 vs RTL 14): the 16,384-row stream ROM is FOUR die macros
    // ot_rom_4096x72_m8 (pqrom2a..d); ra2 = shared 12-bit address, rc2[b] = macro b enable, rq2[48b+:48] = macro b rd_out[47:0]
    output wire [11:0]   ra2,
    output wire          rc0, rc1,
    output wire [3:0]    rc2,
    input  wire [63:0]   rq0, rq1,
    input  wire [191:0]  rq2,
`else
    output wire [13:0]   ra2,
    output wire          rc0, rc1, rc2,
    input  wire [63:0]   rq0, rq1,
    input  wire [47:0]   rq2,
`endif
    output wire [457:0]  t_cnt,
    input  wire [203:0]  f_cnt,
`ifdef DSFD_PQ_STATIC_X2
    output wire [1100:0] xw, xe,
`else
    output wire [564:0]  xw, xe,
`endif
    input  wire [2:0]    xws, xes
`ifdef DSFD_PQ_DIAG_BF_X2
    ,output wire [536:0] x2w, x2e
    ,input wire [2:0] x2ws, x2es
`endif
);
    wire [92:0] f_iss;
    wire [74:0] calendar_action;
    wire calendar_active;
    // A zero-valued ACCEPT tag0 row is meaningful only together with the
    // fixed GO edge. Idle rows cannot cause an accept without GO.
    wire calendar_v=calendar_primed || calendar_active || (|calendar_action);
`ifdef DSFD_PQ_SEQ_SLOT
    // S-ELEM-B 10-15 (S-DIE strict bind: f_iss had no die producer): c_cmd / c_done / c_st = the layer sequencer's PQ engine
    // slot 11 (dsfd_stage_seq_static_c8 +define+DSFD_SSEQ_PQ11).  ot_s81_pq_seq_slot decodes the PQ class (GO / GO+stage
    // start / calendar PRIME), returns the prime's fixed done, and loads the descriptor image + calendar window from its own
    // real mask ROM after reset.  No host / VM port: the descriptor image is compile-time static per layer die.
    wire [84:0] ep_cmd;wire [8:0] ep_done;wire [1:0] ep_st;wire [35:0] f_desc_pw;
    wire calendar_prime,stage_start;wire [11:0] calendar_base;wire [12:0] calendar_length;wire image_loaded;
    ot_s81_pq_seq_slot u_slot (.ck(ck_cmd),.rst_n(rst),.s_cmd(c_cmd),.s_done(c_done),.s_st(c_st),
      .ep_cmd(ep_cmd),.ep_done(ep_done),.ep_st(ep_st),.desc_pw(f_desc_pw),
      .cal_prime(calendar_prime),.cal_start(stage_start),.cal_base(calendar_base),.cal_length(calendar_length),
      .image_loaded(image_loaded));
    ot_s81_pq_command_endpoint #(.PHW(10),.PINREG(1)) u_command (
      .ck(ck_cmd),.rst_n(rst),.c_cmd(ep_cmd),.f_desc_pw(f_desc_pw),
      .t_iss(t_iss),.f_iss(f_iss),.c_done(ep_done),.c_st(ep_st),
      .image_sealed(image_sealed));
`else
    ot_s81_pq_command_endpoint #(.PHW(10),.PINREG(1)) u_command (
      .ck(ck_cmd),.rst_n(rst),.c_cmd(c_cmd),.f_desc_pw(f_desc_pw),
      .t_iss(t_iss),.f_iss(f_iss),.c_done(c_done),.c_st(c_st),
      .image_sealed(image_sealed));
`endif
    ot_s81_pq_calendar_rom #(.ACTION_BITS(75),.PINREG(1)) u_calendar (
      .ck(ck_calendar),.rst_n(rst),.prime(calendar_prime),.stage_start(stage_start),
      .base(calendar_base),.length(calendar_length),.action(calendar_action),
      .active(calendar_active),.primed(calendar_primed),.fault(calendar_fault));
    dsfd_sp_pq_n u_datapath (.*);
endmodule
`default_nettype wire
