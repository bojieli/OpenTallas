`timescale 1ns/1ps
`default_nettype none
// LH-UNREAD 10-19 (held class universal_calendar_capacity_tail_review): role-width successor of the universal
// hfd_hgi_vm_calendar_f20 for calendars whose die clients use only a low payload prefix (epcal_<q>: W 19, epcal_SW: W 38,
// vmfc_<q>: W 89).  Identical F20 target fold, reset synchroniser, programme SRAM, capture rung and cycle timing; the
// only differences are
//   (1) the programme core is ot_vms_calendar_static_xcap #(.W(W)) instead of W 187, so its existing word check
//       (captured[223:W]==0) REJECTS any row whose bits above the role payload are nonzero: the row emits zero and the
//       EXISTING sticky `fault` (-> hleaf t_fault) is raised.  The universal master accepts and exports such a tail.
//   (2) the payload leaves as ONE packed port payload[W-1:0] = universal calendar[W-1:0] (bit-identical, same edge);
//       the universal capacity tail calendar[186:W] has no port and no flops.
// Default source (hfd_hgi_vm_calendar_f20, closed view hv16_vm_cal_f20_ww) is unchanged; this master needs its own
// physical closure (no hard view admitted).  RMUT=1: reset synchroniser bypassed (as the universal bench mutant).
module hfd_hgi_vm_calendar_f20_role #(parameter integer W=19, parameter integer RMUT=0) (
    input wire clk,clk_cap,clk_mem,clk_tgt,rst_n,
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
    output wire [W-1:0] payload
);
    initial if(W<1 || W>=187)$fatal(1,"role calendar width must be a strict prefix of the universal 187-bit word");
    wire p_we,p_sv; wire [9:0] p_wa,p_sb; wire [255:0] p_wd; wire [10:0] p_sl; wire [15:0] p_lp;
    ot_static_program_target #(.TARGET(8'hff),.PCW(10),.TGT_PIN(1),.CAP_CLK(1)) u_target(
        .clk(clk_tgt),.clk_cap(clk_cap),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(active),.program_cfg_we(p_we),.program_cfg_addr(p_wa),.program_cfg_data(p_wd),
        .program_start_v(p_sv),.program_start_base(p_sb),.program_start_limit(p_sl),.program_start_loops(p_lp),
        .configured(tgt_configured),.fault(tgt_fault));
    // = hfd_hgi_vm_calendar body with the role width
    (* async_reg = "true" *) reg rst_meta,rst_sync;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin rst_meta<=1'b0;rst_sync<=1'b0;end
        else begin rst_meta<=1'b1;rst_sync<=rst_meta;end
    wire local_rst_n=(RMUT==1)?rst_n:rst_sync;
    ot_vms_calendar_static_xcap #(.W(W)) u_programme (
        .clk(clk),.clk_cap(clk_cap),.clk_mem(clk_mem),.rst_n(local_rst_n),.cfg_we(p_we),.cfg_addr(p_wa),.cfg_data(p_wd),
        .start_v(p_sv),.start_base(p_sb),.start_limit(p_sl),.start_loops(p_lp),
        .calendar(payload),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
endmodule
`default_nettype wire
