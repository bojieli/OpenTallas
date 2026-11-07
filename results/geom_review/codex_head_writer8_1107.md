# HEAD RX writer8 geometry review — 2026-11-07

VIEWED original vB final placement, clocks and congestion:
intel1:/srv/opentallas-scratch2/claude/dh77w/hd_spn_wshim_rx_vB/s81_head/l48uj/items/hd_spn_wshim_rx/gen/hd_spn_wshim_rx/run/reports/asap7/dp_hd_spn_wshim_rx/base/final_{placement,clocks,congestion}.webp.
Local viewed copies: /tmp/codex-head-safe-1107/rx_vB_*.webp.

GEOMETRY: no macros or macro walls. Payload occupies the upper approximately300um
of the699.84x1036.8 inherited slot, with separated register stripes. Slot height
comes from the existing tile-facing pin window. There is no license to shrink
or move its pins without a separate die-plan change. Worst native slew430.66ps
comes from a shared writer decode: BUFx10 place4855/net4854 drives109AND3inputs.
325 of357TT slew violations are inside the count-aligned landing;32 are FT.
SMELLS:4/5/7/10 (clock reach, distributed control, pin reach and long FT wires).

REDESIGN: opt-in writer enables per8bits with kept state; eight read-select
copies per64bits; payload-group placement prevents START rekeying those copies
into one control cluster. FREG adds one input PIN cycle, FT depth3→6 adds3more,
so physical hop budget reduces233→116.64um at unchanged W/E bit order. Separate
pin FREG bank and enlarged ring bank fit without a macro/channel obstruction.
Signals capM6 with shared conservative-kit pin-access exceptions.

VIEWED candidate plan: results/codex_head_writer8_1107/rx_vC_plan.png.
Verdict PASS-COND for ONE PLACE pilot: straight aligned W→E lanes, no crossings,
six short staged hops, no macros. Actual placed density, capture reach, control
locality and subsequent clock insertion still must be reviewed before CTS/route
or a batch. PIN CYCLES+4, K+2; private DO_NOT_COUNT until compiler/token and POR
integration. The unrelated HEAD G0C stale raw-export cohort and native pma_rck
release qualification remain open; this review does not waive them.
