`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DS pass-through mux (hgi-adapters, 2026-10-09): the static strap mux that sits in FRONT of a unit die wrapper's
// input pin register.  sel = 0 (reset / DS mode): the legacy DS control bus reaches the wrapper's pin flops unchanged;
// sel = 1: the HGI adapter's command bus does.  The return direction needs no mux (both the legacy controller and the
// adapter observe the unit's return bus; the idle one ignores it).  sel is a static strap (a by_design die tie or a
// config-latched bit changed only under the drained reset), false-pathed, so the mux adds 0 cycles and no timing arc on
// the legacy path beyond one AND-OR level ahead of the existing pin flop: the DS control path stays cycle-identical
// (bench: rtl/hbm_accel/generic/adapters/tb/tb_hgi_ds_mux.sv, legacy -> mux -> flop == legacy -> flop every cycle).
// Instances per unit (die wrapper input bus, legacy source, HGI source):
//   hfd_sm   control_leaf c + sm_desc d (106 b a SM)   cmdproc launch tree     ot_hgi_sm_record sm_cmd
//   hfd_su   the vec op port (670 b)                    (no legacy SU ctl today) ot_hgi_su_record op_w / op_v
//   hfd_sfu  the vec op port (670 b)                                            ot_hgi_sfu_record
//   others   per tools/hgi_die_dispatch + results/rtl/hgi_adapters_20261009/port_manifest.json
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_ds_mux #(parameter integer W = 1) (
    input  wire         sel,
    input  wire [W-1:0] legacy,
    input  wire [W-1:0] hgi,
    output wire [W-1:0] q
);
    assign q = sel ? hgi : legacy;
endmodule
`default_nettype wire
