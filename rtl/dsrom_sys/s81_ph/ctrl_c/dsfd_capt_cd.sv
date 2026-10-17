`timescale 1ns/1ps
// dsfd_capt_cd: the fld DONE word of the capture cluster as a hardened leaf (el1013 S81 capture, 2026-10-13).
// It is the t_cd text of ctrl_c/dsfd_sp_capture_c.sv (serial domain): {toggle, fault, phase 10} from the status
// word of the capture tile next to the control tile.  It was 16 flops of flat cluster logic on the serial clock;
// a cluster has no logic of its own, so they are this tile (scalar clock / reset pins, every output a register).
//   f_st  = t_st[13:0] of that tile: [0] busy, [2] done level, [3] fault, [13:4] phase (registers there)
//   t_cd  = {toggle, fault, phase[9:0]}: the toggle flips once per completed phase
// Mutant: S81PH_CAPCD_MUT_NOTOG (the toggle never flips: the field sequencer never sees a phase complete).
//
// Native capture restructure (S-VM-CAPT-CD 2026-10-16, zero cycles): the closed split1016 view failed the native pin
// audit on f_st[2] (capture 214.2 ps) and f_st[0] (191.7 ps) > 190: both fed the 4-input enable
//     fire = f_st[2] & !dr_q & armed & !f_st[0]
// which drove the hold-mux select of the 11 t_cd[9:0]/t_cd[11] flops.  Now:
//   * the registered part is precomputed one edge early: ok_q == (armed & !dr_q) of the old form, because
//         ok_next = armed_next & !f_st[2],  armed_next = f_st[0] | (armed & !fire),
//     and fire == 0 whenever f_st[2] == 0, so ok_next = !f_st[2] & (f_st[0] | armed)  (reset 0 == old 0 & !0);
//     dr_q has no other use and is gone;
//   * fire = f_st[2] & !f_st[0] & ok_q is the ENA of ONE ICG; the 11 t_cd[9:0]/t_cd[11] flops are plain registers on
//     its gated clock (as ot_s81_vm_x34 NAT=1), so f_st[13:4] reach their D pins without a mux.
// Every t_cd bit changes on exactly the same ckv edge as before (bit-exact, 0 cycles added).
//
// PINREG=1 (S-VM-CAPT-CD2 2026-10-16, opt-in; default 0 keeps every existing view/bench byte-for-byte in behaviour):
// the routed split1016n view (0c30c32f2, CLOSED TT +319.07/FF +30.18) still fails the native audit: f_st[2] capture
// 203.7 ps > 190 (R 90.0) because the ICG ENA samples on the un-inserted clock at the ICG, so no input->ENA path meets
// 190.  Every used f_st bit ([0],[2],[3],[13:4]; [1] is unused) now lands on a pin-register D pin directly (fs_q, no
// reset: the reset-synchronised state behind it ignores it until rv_s[1] rises), and the ok_q/armed/ICG structure
// above runs on fs_q.  Exactly equivalent to PINREG=0 fed with f_st delayed by one ckv edge:
//     COST: capture DONE toggle +1 ckv (every t_cd bit changes one serial edge later; f_st -> t_cd 1 -> 2 edges).
// A zero-cycle form cannot exist with registered outputs: the 10 phase flops must hold between completions, so
// f_st[2]/f_st[0] must select (mux or ENA) on the same edge.
module dsfd_capt_cd #(
    parameter integer PINREG = 0
) (
    input  wire        ckv,
    input  wire        rsv,
    input  wire [13:0] f_st,
    output wire [11:0] t_cd
);
    reg [9:0] ph_q; reg tg_q, ft_q;
    assign t_cd = {tg_q, ft_q, ph_q};
    reg [1:0] rv_s;
    always @(posedge ckv or negedge rsv) if (!rsv) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    // f_st as seen by the logic: the pins (PINREG=0) or the pin registers (PINREG=1)
    wire [13:0] fs;
    generate if (PINREG != 0) begin : g_pr
        reg [13:0] fs_q;
        always @(posedge ckv) fs_q <= {f_st[13:2], 1'b0, f_st[0]};
        assign fs = fs_q;
    end else begin : g_np
        assign fs = f_st;
    end endgenerate
    reg ok_q, armed;
    wire fire = fs[2] & ~fs[0] & ok_q;
    always @(posedge ckv or negedge rv_s[1])
        if (!rv_s[1]) begin ok_q <= 1'b0; armed <= 1'b0; ft_q <= 1'b0; end
        else begin
            ok_q <= ~fs[2] & (fs[0] | armed);
            armed <= fs[0] | (armed & ~fire);
            ft_q <= fs[3];
        end
`ifdef S81PH_CAPCD_MUT_NOTOG
    wire tog_d = tg_q;
`else
    wire tog_d = ~tg_q;
`endif
`ifdef SYNTHESIS
    wire gck;
    ICGx2_ASAP7_75t_R u_g (.CLK(ckv), .ENA(fire), .SE(1'b0), .GCLK(gck));
    always @(posedge gck or negedge rv_s[1])
        if (!rv_s[1]) begin ph_q <= 10'd0; tg_q <= 1'b0; end
        else begin ph_q <= fs[13:4]; tg_q <= tog_d; end
`else
    // simulation model: the ICG as its enable (same edges; no derived-clock race, cf. ot_s81_vm_x34 BAL=1 note)
    always @(posedge ckv or negedge rv_s[1])
        if (!rv_s[1]) begin ph_q <= 10'd0; tg_q <= 1'b0; end
        else if (fire) begin ph_q <= fs[13:4]; tg_q <= tog_d; end
`endif
endmodule
