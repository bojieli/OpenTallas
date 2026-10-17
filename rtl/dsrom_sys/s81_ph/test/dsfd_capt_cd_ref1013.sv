`timescale 1ns/1ps
// FROZEN REFERENCE (S-VM-CAPT-CD 2026-10-16): ctrl_c/dsfd_capt_cd.sv as of 2314b2b4d (the CLOSED split1016 view's
// source), renamed; the lockstep oracle of tools/s81_ph/capcd_eq_bench.sh.  Mutant macro renamed so it never applies here.
// dsfd_capt_cd: the fld DONE word of the capture cluster as a hardened leaf (el1013 S81 capture, 2026-10-13).
// It is the t_cd text of ctrl_c/dsfd_sp_capture_c.sv (serial domain): {toggle, fault, phase 10} from the status
// word of the capture tile next to the control tile.  It was 16 flops of flat cluster logic on the serial clock;
// a cluster has no logic of its own, so they are this tile (scalar clock / reset pins, every output a register).
//   f_st  = t_st[13:0] of that tile: [0] busy, [2] done level, [3] fault, [13:4] phase (registers there)
//   t_cd  = {toggle, fault, phase[9:0]}: the toggle flips once per completed phase
// Mutant: S81PH_CAPCD_REF_NEVER_DEFINED (the toggle never flips: the field sequencer never sees a phase complete).
module dsfd_capt_cd_ref1013 (
    input  wire        ckv,
    input  wire        rsv,
    input  wire [13:0] f_st,
    output reg  [11:0] t_cd
);
    reg [1:0] rv_s;
    always @(posedge ckv or negedge rsv) if (!rsv) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    reg dr_q, armed;
    always @(posedge ckv or negedge rv_s[1])
        if (!rv_s[1]) begin dr_q <= 1'b0; armed <= 1'b0; t_cd <= 12'd0; end
        else begin
            dr_q <= f_st[2];
            t_cd[10] <= f_st[3];
            if (f_st[0]) armed <= 1'b1;
            if (f_st[2] && !dr_q && armed && !f_st[0]) begin
                t_cd[9:0] <= f_st[13:4];
`ifndef S81PH_CAPCD_REF_NEVER_DEFINED
                t_cd[11] <= ~t_cd[11];
`endif
                armed <= 1'b0;
            end
        end
endmodule
