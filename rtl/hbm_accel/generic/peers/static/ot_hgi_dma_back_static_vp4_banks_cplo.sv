`timescale 1ns/1ps
`default_nettype none
// HBM-DBK9 2026-10-21 (H.STA.BLK.12): OUTPUT-LANDED successor of ot_hgi_dma_back_static_vp4_banks_cpl (_cplo / core _rlo).
// Why (daemon route hv16_dbk_cpl_l1-l1-f5284ed97, EARLY_FAIL_SETUP post-CTS TT WNS -538.3 ps / 2,494 endpoints /
// TNS -689,018 at 833.333, IO paths judged at the IO reference): EVERY failing endpoint is a child-macro output driven
// straight to a parent output port (macro->out, max fanout 1, no logic): controller wb_reserve_base -538.3 (child arc
// 368.6 + 330 ps unbuffered port wire, slew 1,047 ps), bank wd -525..-362 (arc 340-440 + wire 237-408 ps over 150-330 um
// to the S/N faces), collar cp_configured -425.8, rq / mv_* / quiet / busy.  The l1 landing put registers on every
// INPUT and every internal long wire but left the outputs as child pin flops seen through 150-500 um of parent wire;
// a child flop -> parent port path cannot meet the IO budget (0.2 T outside) across the cluster.  Structural fix:
// EVERY parent output leaves from a kept parent register at its face (one edge, regional root beside the face group):
//   * wd of banks 0,3 / 1,2 (S face) on clk_out[0] / clk_out[1]; banks 4,5 / 6,7 (N face) on clk_out[2] / clk_out[3];
//   * wb_reserve_* and wb_fill_* (N face x 400-430) on clk_out[3] (wb_fill keeps its half-way relay: 2 edges);
//   * rq (W face y 252-294) on clk_land[3] (the lane-3 landing strip, W y 172-260, adjacent);
//   * mv_src / mv_done / mv_fault / quiet / busy and cp_configured / cp_fault / cp_active (E face) on clk_rst;
//     the collar keeps the unregistered busy / mv_fault (internal frame unchanged).
// Cycles (static, handed to the die schedule): every output +1 edge vs _cpl (wd and wb_fill_* +2 vs _cp, all others +1);
// rq +1 => the die pads every rr lane to RR_RT-2 = 78 at the port (DIE_PRE 2; controller round trip stays RR_RT 80);
// wa (write-back ack count) returns one edge later (pending/quiet one edge later, no fault: ack later is safe).
// No ready, no credit.  Face registers are datapath (unreset): bank / controller outputs are reset at the source and the
// face copy is clean one edge after reset.
// Inner structure (rr landing, read / fill relays, reset leaves) = _cpl, see ot_hgi_dma_back_static_vp4_banks_cpl.sv.
module ot_hgi_dma_back_static_vp4_banks_rlo #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,
    parameter integer RR_RT=7,
    parameter integer RL_MUT=0
)(
    input wire clk,
    input wire clk_land_c,               // fill relays (parent root clk_rst, same die clock)
    input wire [7:0] clk_land,           // per-bank face landing roots (rr data + bank valid copy; clk_land[b] ports)
    input wire [2:0] clk_rly,            // per-group relay roots (S 0-2, W 3-5, N 6-7: read relays + controller valid copy)
    input wire [3:0] clk_out,            // face output roots: wd S banks 0,3 / S 1,2 / N 4,5 / N 6,7 + wb_* (HBM-DBK9)
    input wire rst_ctl_n,
    input wire [7:0] rst_bank_n,
    input wire [1:0] stk,
    input wire [7:0] clk_bank,
    input wire [31:0] cycle,
    input wire mv_v,
    input wire [226:0] mv,
    input wire [31:0] issue_at,drain_at,
    input wire mv_wb_bank,
    input wire [15:0] mv_wb_epoch,
    output wire mv_src,mv_done,mv_fault,
    output wire quiet,busy,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output wire [15:0] wb_reserve_epoch,wb_fill_epoch,
    output wire [11:0] wb_reserve_sectors,
    output wire [31:0] wb_reserve_base,
    output wire wb_fill_start,
    input wire wb_ready,
    output wire [8*289-1:0] wd,
    input wire [11:0] wa
);
    wire [7:0] rr_valid_i,bank_read_en,bank_output_en;
    wire [6:0] rslot_s,rslot_w,rslot_n,wslot_s,wslot_w,wslot_n;
    wire [255:0] bank_read_addr;
    wire c_fill_bank,c_fill_start; wire [15:0] c_fill_epoch;
    wire [8*17-1:0] c_rq; wire [8*289-1:0] c_wd;
    wire c_res_v,c_res_bank; wire [15:0] c_res_epoch; wire [11:0] c_res_sectors; wire [31:0] c_res_base;
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_controller u_control(
`else
    ot_hgi_dma_back_static_vp4_controller #(.STACK_BYTES(STACK_BYTES),.MUT(MUT),.RR_RT(RR_RT)) u_control(
`endif
        .clk(clk),.rst_n(rst_ctl_n),.stk(stk),.cycle_in(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
        .mv_wb_bank(mv_wb_bank),.mv_wb_epoch(mv_wb_epoch),.mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),
        .quiet(quiet),.busy(busy),.rq(c_rq),.wb_reserve_v(c_res_v),.wb_reserve_bank(c_res_bank),
        .wb_fill_bank(c_fill_bank),.wb_reserve_epoch(c_res_epoch),.wb_fill_epoch(c_fill_epoch),
        .wb_reserve_sectors(c_res_sectors),.wb_reserve_base(c_res_base),.wb_fill_start(c_fill_start),
        .wb_ready(wb_ready),.wa(wa),.rr_valid_i(rr_valid_i),.bank_read_en(bank_read_en),
        .bank_read_slot_s(rslot_s),.bank_read_slot_w(rslot_w),.bank_read_slot_n(rslot_n),
        .bank_write_slot_s(wslot_s),.bank_write_slot_w(wslot_w),.bank_write_slot_n(wslot_n),.bank_output_en(bank_output_en),
        .bank_read_addr_s(bank_read_addr[95:0]),.bank_read_addr_w(bank_read_addr[159:96]),.bank_read_addr_n(bank_read_addr[255:160]));
    // ---- write-back fill relay (+1 edge, with wd): N face, half way controller -> wb ports
    (* keep = "true" *) reg fl_start_q,fl_bank_q; (* keep = "true" *) reg [15:0] fl_epoch_q;
    always @(posedge clk_land_c) begin fl_start_q<=c_fill_start; fl_bank_q<=c_fill_bank; fl_epoch_q<=c_fill_epoch; end
    // ---- N face output registers (clk_out[3], beside the wb ports x 400-430): write-back reserve + fill (2nd fill edge)
    (* keep = "true" *) reg of_start_q,of_bank_q; (* keep = "true" *) reg [15:0] of_epoch_q;
    (* keep = "true" *) reg or_v_q,or_bank_q; (* keep = "true" *) reg [15:0] or_epoch_q; (* keep = "true" *) reg [11:0] or_sectors_q;
    (* keep = "true" *) reg [31:0] or_base_q;
    always @(posedge clk_out[3]) begin
        of_start_q<=(RL_MUT==3)?c_fill_start:fl_start_q; of_bank_q<=(RL_MUT==3)?c_fill_bank:fl_bank_q;
        of_epoch_q<=(RL_MUT==3)?c_fill_epoch:fl_epoch_q;
        or_v_q<=c_res_v; or_bank_q<=c_res_bank; or_epoch_q<=c_res_epoch; or_sectors_q<=c_res_sectors; or_base_q<=c_res_base;
    end
    assign wb_fill_start=of_start_q; assign wb_fill_bank=of_bank_q; assign wb_fill_epoch=of_epoch_q;
    assign wb_reserve_v=or_v_q; assign wb_reserve_bank=or_bank_q; assign wb_reserve_epoch=or_epoch_q;
    assign wb_reserve_sectors=or_sectors_q; assign wb_reserve_base=or_base_q;
    // ---- W face rq output registers (clk_land[3]: the lane-3 landing strip W y 172-260 is adjacent to rq W y 252-294)
    (* keep = "true" *) reg [8*17-1:0] orq_q;
    always @(posedge clk_land[3]) orq_q<=c_rq;
    assign rq=orq_q;
    // ---- per bank: response landing + read-path relays.  Slot copies by face group: S = banks 0-2, W = 3-5, N = 6-7.
    for(genvar b=0;b<8;b=b+1)begin:L
        localparam integer G=(b<3)?0:(b<6)?1:2;
        wire [6:0] rslot=(G==0)?rslot_s:(G==1)?rslot_w:rslot_n;
        wire [6:0] wslot=(G==0)?wslot_s:(G==1)?wslot_w:wslot_n;
        (* keep = "true" *) reg [255:0] rd_q;     // rr data landing, at the bank's rr face
        (* keep = "true" *) reg wv_q;             // rr valid landing copy -> bank write_en
        (* keep = "true" *) reg cv_q;             // rr valid landing copy -> controller rr_valid_i (half way)
        (* keep = "true" *) reg re_q,oe_q;        // read enable / output enable relays
        (* keep = "true" *) reg [6:0] rs_q;       // read slot relay (per-bank copy of the group register)
        (* keep = "true" *) reg [31:0] ra_q;      // read address relay
        wire [6:0] wslot_b;                       // the bank's write slot: the controller register, no relay
        // face landing region (clk_land[b]) / relay region between the controller and the bank group (clk_rly[G]):
        // gate 063306/063307 measured one root per bank over both regions at 77-85 ps boundary spread (> 80).
        always @(posedge clk_land[b]) begin rd_q<=rr[b*257+:256]; wv_q<=rr[b*257+256]; end
        always @(posedge clk_rly[G]) begin
            cv_q<=rr[b*257+256];
            re_q<=bank_read_en[b]; oe_q<=bank_output_en[b]; rs_q<=rslot; ra_q<=bank_read_addr[b*32+:32];
        end
        if(RL_MUT==2)begin:G_WS (* keep = "true" *) reg [6:0] ws_q; always @(posedge clk_rly[G]) ws_q<=wslot; assign wslot_b=ws_q; end
        else begin:G_NOWS assign wslot_b=wslot; end
        assign rr_valid_i[b]=(RL_MUT==1)?rr[b*257+256]:cv_q;
        ot_hgi_dma_back_landing_bank u_bank(
            .clk(clk_bank[b]),.rst_n(rst_bank_n[b]),
            .read_en(re_q),.read_slot(rs_q),
            .write_en(wv_q),.write_slot(wslot_b),.rr_data(rd_q),
            .read_addr(ra_q),.output_en(oe_q),.wd(c_wd[b*289+:289]));
        // S/N face output register of bank b's wd (+1 edge): S banks 0,3 -> clk_out[0], 1,2 -> clk_out[1];
        // N banks 4,5 -> clk_out[2], 6,7 -> clk_out[3]
        localparam integer O=(b==0||b==3)?0:(b==1||b==2)?1:(b==4||b==5)?2:3;
        (* keep = "true" *) reg [288:0] owd_q;
        always @(posedge clk_out[O]) owd_q<=c_wd[b*289+:289];
        assign wd[b*289+:289]=owd_q;
    end
endmodule

// Ports of ot_hgi_dma_back_static_vp4_banks_cpl + clk_out[3:0] (4 more die-forwarded face clock entries, same die clock);
// the die re-pads rr by two edges (DIE_PRE 2) and takes every output one edge later than from _cpl.
module ot_hgi_dma_back_static_vp4_banks_cplo #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,
    parameter integer CP_MUT=0,
    parameter integer RST_MUT=0,
    parameter integer RL_MUT=0,
    parameter integer RR_RT=7
)(
    input wire clk,rst_n,
    input wire clk_cp,
    input wire clk_rst,             // parent CTS root: reset relays + wb_fill relays (same die clock)
    // HBM-HC7-DBK 10-20 (gate 054637: ONE clk_rst tree over 2,425 landing/relay flops across the cluster = TT insertion
    // 650.7 ps, boundary pin-flop spread 284.6 ps > 80): one regional CTS root per bank region, beside clk_bank[b]
    // (CLOCKING STANDARD: local region trees, never one tree across the parent).  Same die clock, forwarded by the die.
    input wire [7:0] clk_land,
    input wire [2:0] clk_rly,       // relay-region roots per bank group (S / W / N), same die clock
    input wire [3:0] clk_out,       // HBM-DBK9: face output roots (S W-half / S E-half / N W-half / N E-half), same die clock
    input wire [1:0] stk,
    input wire [7:0] tgt,
    input wire [7:0] clk_bank,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire cp_configured,cp_fault,cp_active,
    output wire mv_src,mv_done,mv_fault,
    output wire quiet,busy,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output wire [15:0] wb_reserve_epoch,wb_fill_epoch,
    output wire [11:0] wb_reserve_sectors,
    output wire [31:0] wb_reserve_base,
    output wire wb_fill_start,
    input wire wb_ready,
    output wire [8*289-1:0] wd,
    input wire [11:0] wa
);
    wire [8:0] rst_bk_n; wire [0:0] rst_ctl_q;
    ot_rst_relay #(.REGIONS(9),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_bk(.clk(clk_rst),.rst_n_in(rst_n),.rst_n(rst_bk_n));
    ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(2)) u_rst_ctl(.clk(clk_rst),.rst_n_in(rst_n),.rst_n(rst_ctl_q));
    wire rst_ctl_n = (RST_MUT==1) ? rst_n : rst_ctl_q[0];
    wire cmd_v; wire [307:0] cmd; wire [31:0] cycle;
    wire c_src,c_done,c_fault,c_quiet,c_busy,c_cfgd,c_cpflt,c_cpact;
    ot_hgi_dma_back_cp_collar u_cp(
        .clk(clk_cp),.rst_n(rst_bk_n[8]),.tgt(tgt),
        .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .tgt_active(c_busy),.tgt_fault(c_fault),
        .cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(c_cfgd),.fault(c_cpflt),.active(c_cpact));
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_banks_rlo u_dbk(
`else
    ot_hgi_dma_back_static_vp4_banks_rlo #(.STACK_BYTES(STACK_BYTES),.MUT(MUT),.RR_RT(RR_RT),.RL_MUT(RL_MUT)) u_dbk(
`endif
        .clk(clk),.clk_land_c(clk_rst),.clk_land(clk_land),.clk_rly(clk_rly),.clk_out(clk_out),.rst_ctl_n(rst_ctl_n),.rst_bank_n(rst_bk_n[7:0]),.stk(stk),.clk_bank(clk_bank),.cycle(cycle),
        .mv_v(cmd_v),.mv((CP_MUT==1)?cmd[291:65]:cmd[290:64]),.issue_at(cmd[31:0]),.drain_at(cmd[63:32]),
        .mv_wb_bank(cmd[291]),.mv_wb_epoch(cmd[307:292]),
        .mv_src(c_src),.mv_done(c_done),.mv_fault(c_fault),.quiet(c_quiet),.busy(c_busy),.rq(rq),.rr(rr),
        .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),
        .wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),.wb_reserve_sectors(wb_reserve_sectors),
        .wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wb_ready(wb_ready),.wd(wd),.wa(wa));
    // ---- E face status output registers (clk_rst; +1 edge): the collar keeps the unregistered busy / mv_fault
    (* keep = "true" *) reg os_src_q,os_done_q,os_fault_q,os_quiet_q,os_busy_q,os_cfgd_q,os_cpflt_q,os_cpact_q;
    always @(posedge clk_rst) begin
        os_src_q<=c_src; os_done_q<=c_done; os_fault_q<=c_fault; os_quiet_q<=c_quiet; os_busy_q<=c_busy;
        os_cfgd_q<=c_cfgd; os_cpflt_q<=c_cpflt; os_cpact_q<=c_cpact;
    end
    assign mv_src=os_src_q; assign mv_done=os_done_q; assign mv_fault=os_fault_q; assign quiet=os_quiet_q; assign busy=os_busy_q;
    assign cp_configured=os_cfgd_q; assign cp_fault=os_cpflt_q; assign cp_active=os_cpact_q;
endmodule
`default_nettype wire
