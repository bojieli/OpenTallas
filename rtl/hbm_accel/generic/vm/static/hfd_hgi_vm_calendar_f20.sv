`timescale 1ns/1ps
`default_nettype none
// H-NETLIST 0600 (H-DIE option A, collar fold): the universal VM calendar with its F20 programme target inside.
// The standalone ot_static_program_target collar (~630 pins, ~0.01 mm2) is pin-bound as its own tile, so it is folded
// here as pin-registered soft logic: the face takes the F20 broadcast bus + the identity strap tgt[7:0] (TGT_PIN=1),
// and the target's registered programme/start outputs feed the calendar's own W capture rung internally (reg->reg).
// The target is the W-face front end: clocked by clk_cap (the related phase-0 root of the W capture rung) so its F20
// pin flops sit on the short root; calendar body/outputs stay on clk.
// Cycle behaviour is exactly the two-tile composition (collar outputs are flops; no stage added or removed).
module hfd_hgi_vm_calendar_f20 #(parameter integer RMUT=0) (
    input wire clk,clk_cap,clk_mem,rst_n,
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire tgt_configured,tgt_fault,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [9:0] client_seq,
    output wire [4:0] response_enable,
    output wire [9:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [23:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [5:0] hub_ring_client,
    output wire [7:0] rslot_v,
    output wire [7:0] wslot_v,
    output wire [23:0] rslot,
    output wire [23:0] wslot,
    output wire [1:0] ring_tx_enable,
    output wire [5:0] ring_tx_source,
    output wire replay_enable,
    output wire replay_source,
    output wire [23:0] lg_local_read,
    output wire [23:0] lg_local_write
);
    wire p_we,p_sv; wire [9:0] p_wa,p_sb; wire [255:0] p_wd; wire [10:0] p_sl; wire [15:0] p_lp;
    ot_static_program_target #(.TARGET(8'hff),.PCW(10),.TGT_PIN(1)) u_target(
        .clk(clk_cap),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(active),.program_cfg_we(p_we),.program_cfg_addr(p_wa),.program_cfg_data(p_wd),
        .program_start_v(p_sv),.program_start_base(p_sb),.program_start_limit(p_sl),.program_start_loops(p_lp),
        .configured(tgt_configured),.fault(tgt_fault));
    hfd_hgi_vm_calendar #(.RMUT(RMUT)) u_calendar(
        .clk(clk),.clk_cap(clk_cap),.clk_mem(clk_mem),.rst_n(rst_n),.cfg_we(p_we),.cfg_addr(p_wa),.cfg_data(p_wd),
        .start_v(p_sv),.start_base(p_sb),.start_limit(p_sl),.start_loops(p_lp),
        .calendar_v(calendar_v),.active(active),.done(done),.fault(fault),.ordinal(ordinal),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),.bank_enable(bank_enable),
        .bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),.rslot_v(rslot_v),
        .wslot_v(wslot_v),.rslot(rslot),.wslot(wslot),.ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),
        .replay_enable(replay_enable),.replay_source(replay_source),.lg_local_read(lg_local_read),.lg_local_write(lg_local_write));
endmodule
`default_nettype wire
