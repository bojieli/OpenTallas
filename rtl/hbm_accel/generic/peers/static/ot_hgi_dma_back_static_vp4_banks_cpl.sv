`timescale 1ns/1ps
`default_nettype none
// HBM-HC7-DBK 2026-10-20 (H.STA.BLK.12): LANDED consumer-geometry successor of ot_hgi_dma_back_static_vp4_banks_cp.
// Why (Codex review 04:04, exact post-GRT buffer-transparent reach of hv16_dbk_cpl_s1/s2 @ca6707526, REFUSED):
//   rr_valid port (W face y 252) -> bank7.write_en 713.3 um, bank2/bank6 566.1/540.8 (the raw response valid fans to
//   the bank write enable AND the controller, so no port position serves both); controller W-face bank_output_en[7] /
//   bank_read_en[7] -> bank7 454.7 / 408.2 um (the NE bank is 417 um from the cluster centre); reset landing (E face
//   y 2.4) -> the u_rst_bk relay leaves 456.4 um.  One failed review = structural redesign, so every long single-cycle
//   wire now gets a registered hop beside its consumer, and the die/compiler take the recorded cycles:
//   * rr LANDING (clk_land[b], one regional parent CTS root per bank): every rr bit lands in one register at the face beside ITS bank
//     (rr_valid ports move from the W face centre to the bank's data group).  The valid bit lands TWICE (kept copies):
//     wv_q beside the bank (-> write_en) and cv_q half way to the controller (-> rr_valid_i).  Bank and controller see
//     the response on exactly the same edge as before, one edge after the port: the die delivers rr ONE EDGE EARLIER
//     (round trip at the controller pins stays RR_RT 80; die rr lanes padded to RR_RT-1 at the parent port).
//   * READ-PATH RELAYS: bank_read_en / bank_output_en / read slot / read address are relayed one edge per bank (kept,
//     anchored half way between the controller face and the bank pins).  The bank's whole read side runs one edge
//     later (its landing writes stay where they were, so drain-after-landing lag grows by one: still exact); wd leaves
//     every bank ONE EDGE LATER and wb_fill_start / wb_fill_bank / wb_fill_epoch are relayed one edge with it, so the
//     write-back sees the same wd-vs-fill alignment as before.  write_slot is NOT relayed (the write side stays in the
//     controller frame); bank 5 takes the W-face copy (383 um) instead of the N-face copy (401 um).
//   * reset: unchanged release (ot_rst_relay REGIONS 9 / 1, the same edges); the rst_n port moves to the E face beside
//     clk_rst and every relay leaf is anchored half way to its bank / leaf / controller (kit relay_anchor table).
//   Cycles (static, handed to the die schedule; lanes/HBM-HC7-DBK.md): rr at the parent port -1 edge (die pad), wd and
//   wb_fill_* +1 edge at the ports (write-back of every DMA-back move drains one edge later), reset release unchanged,
//   mv_src / mv_done / quiet / busy / rq unchanged.  No ready, no credit.
// RL_MUT (bench negative controls, simulation only; the kit never overrides it):
//   1 controller response valid straight from the port (no landing) -> must FAIL (mv_fault)
//   2 write_slot relayed like the read side (write frame shifted)    -> must FAIL (landing payload)
//   3 wb_fill_* not relayed (fill one edge ahead of wd)               -> must FAIL (lockstep)
module ot_hgi_dma_back_static_vp4_banks_rl #(
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0,
    parameter integer RR_RT=7,
    parameter integer RL_MUT=0
)(
    input wire clk,
    input wire clk_land_c,               // fill relays (parent root clk_rst, same die clock)
    input wire [7:0] clk_land,           // per-bank face landing roots (rr data + bank valid copy; clk_land[b] ports)
    input wire [2:0] clk_rly,            // per-group relay roots (S 0-2, W 3-5, N 6-7: read relays + controller valid copy)
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
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_controller u_control(
`else
    ot_hgi_dma_back_static_vp4_controller #(.STACK_BYTES(STACK_BYTES),.MUT(MUT),.RR_RT(RR_RT)) u_control(
`endif
        .clk(clk),.rst_n(rst_ctl_n),.stk(stk),.cycle_in(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
        .mv_wb_bank(mv_wb_bank),.mv_wb_epoch(mv_wb_epoch),.mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),
        .quiet(quiet),.busy(busy),.rq(rq),.wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),
        .wb_fill_bank(c_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(c_fill_epoch),
        .wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(c_fill_start),
        .wb_ready(wb_ready),.wa(wa),.rr_valid_i(rr_valid_i),.bank_read_en(bank_read_en),
        .bank_read_slot_s(rslot_s),.bank_read_slot_w(rslot_w),.bank_read_slot_n(rslot_n),
        .bank_write_slot_s(wslot_s),.bank_write_slot_w(wslot_w),.bank_write_slot_n(wslot_n),.bank_output_en(bank_output_en),
        .bank_read_addr_s(bank_read_addr[95:0]),.bank_read_addr_w(bank_read_addr[159:96]),.bank_read_addr_n(bank_read_addr[255:160]));
    // ---- write-back fill relay (+1 edge, with wd): N face, half way controller -> wb ports
    (* keep = "true" *) reg fl_start_q,fl_bank_q; (* keep = "true" *) reg [15:0] fl_epoch_q;
    always @(posedge clk_land_c) begin fl_start_q<=c_fill_start; fl_bank_q<=c_fill_bank; fl_epoch_q<=c_fill_epoch; end
    assign wb_fill_start=(RL_MUT==3)?c_fill_start:fl_start_q;
    assign wb_fill_bank =(RL_MUT==3)?c_fill_bank :fl_bank_q;
    assign wb_fill_epoch=(RL_MUT==3)?c_fill_epoch:fl_epoch_q;
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
            .read_addr(ra_q),.output_en(oe_q),.wd(wd[b*289+:289]));
    end
endmodule

// Same ports as ot_hgi_dma_back_static_vp4_banks_cp (drop-in master for hb_dbk_<q>; the die re-pads rr by one edge).
module ot_hgi_dma_back_static_vp4_banks_cpl #(
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
    ot_hgi_dma_back_cp_collar u_cp(
        .clk(clk_cp),.rst_n(rst_bk_n[8]),.tgt(tgt),
        .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .tgt_active(busy),.tgt_fault(mv_fault),
        .cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(cp_configured),.fault(cp_fault),.active(cp_active));
`ifdef OT_DBK_HARD
    ot_hgi_dma_back_static_vp4_banks_rl u_dbk(
`else
    ot_hgi_dma_back_static_vp4_banks_rl #(.STACK_BYTES(STACK_BYTES),.MUT(MUT),.RR_RT(RR_RT),.RL_MUT(RL_MUT)) u_dbk(
`endif
        .clk(clk),.clk_land_c(clk_rst),.clk_land(clk_land),.clk_rly(clk_rly),.rst_ctl_n(rst_ctl_n),.rst_bank_n(rst_bk_n[7:0]),.stk(stk),.clk_bank(clk_bank),.cycle(cycle),
        .mv_v(cmd_v),.mv((CP_MUT==1)?cmd[291:65]:cmd[290:64]),.issue_at(cmd[31:0]),.drain_at(cmd[63:32]),
        .mv_wb_bank(cmd[291]),.mv_wb_epoch(cmd[307:292]),
        .mv_src(mv_src),.mv_done(mv_done),.mv_fault(mv_fault),.quiet(quiet),.busy(busy),.rq(rq),.rr(rr),
        .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),
        .wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),.wb_reserve_sectors(wb_reserve_sectors),
        .wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wb_ready(wb_ready),.wd(wd),.wa(wa));
endmodule
`default_nettype wire
