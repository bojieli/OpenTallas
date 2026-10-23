# Selected s8 source recovery and distinct CRH qualification

Source commits: e8b79a17b exact original RP1 packet; 82e883827 split recovery;
d13d01357 unique CRH kit and RP1 seam receipts; 54454faad ARF1 test.
The existing s7 diagnostic and progressing jobs remain immutable.

The closed xleaf NCH4/READ_PIN_PIPE1/FILL_PIPE1 body matches released099253177
byte for byte (source_identity.json). s8 uses OT_S5_HARD+OT_S8_SIM to select these
actual params in simulation. Legacy s7 OT_S5_HARD suppresses the overrides and
simulates0/0. Its current lockstep therefore does not calibrate the hard1/1 path.
XHEAD3 fixed READ1/FILL_LEAD5/DX14 and direct safe2 lane head0..7 remain selected;
u_su8_rst3 is the controller and remains unchanged.

RP1 recovery follows c0f8097f3: ARM subcommand1, eight group1 return words,
sequence k, address bit11 half-write/bit10 bank, wordbase+k/2, duplicated512-bit
payload. The split adapter masks consumed ARM and return valid from the existing
bounded ctl without modifying its closed body. It merges writes before the new
suvm/VM8q CROM path. qfd_dv_s8_crh_rp1 has a real bank-specific write enable,
kept half/bank bits captured at the existing table-control age, and the actual
expanded legal-address predicate. It is a new unclosed source: using the old
qfd_dv_s8x_crh view is forbidden.

Actual fleet RP-to-CRH-to-SRAM test82e883827, gold2 unit2758850 rc0:
8 distinct payloads -> 4 addresses x 2 banks, all low/high words byte-exact;
ARM/return ctl masking checked, ninth return forwarded after disarm.
Bank-swap mutant fails beat0; missing half-mask fails final bank0 word0.
This test does not calibrate full parent timing.

ARF1 recovers the original framer before the existing fdn output register:
no extra sequential stage. Actual source54454faad agidock128 unit2908791 rc0,
three distinct payload/tag/last checks and nonzero slice unarmed passthrough.
Early-last mutant fails beat1. Logs under arf1/.

Generated LP audits pass D4/E2 and D8/E4:187 landings, one pad of3/5edges.
Table-write path is now STM->RP at ctl->SU, with actual crossings, not an
imaginary zero-age command overlay. No selected whole-programme age claim or
compiler default changes have been made. Actual timing receipt remains owed.

## CRH SAFE checklist before physical adoption

1. Pins: source PASS, all data/control inputs captured, q/fault registered;
   actual placed IO geometry pending pre-gate.
2. Reach: original outline259.2x276.48 and exact original macro locations;
   actual matched-bit geometric reach pending pre-gate. No waiver.
3. Fanout: two kept half/bank control FF added; mapped native32 census pending.
4. Depth: existing data pipeline retained; two bank WCE predicates and legal
   half-address predicate added. Actual mapped depth/timing pending.
5. Storage: PASS unchanged two1024x256 SRAMs; no new datapath array.
6. Floorplan: ref_tile gen PASS, two original SRAMs/channels/outline. Current
   local pre-route gate PASS0warn. Final PNGs and measured fill owed.
7. Clock: single existing S-face clock, two reset landing stages; within-region
   TT/FF spread, insertion, final clock mass and all PNGs owed.
8. Schedule: zero new CRH/FDN register stages. Full selected LP ages unmeasured;
   existing12-slice36-edge RP prologue is only monolithic source reference.

No critical REVIEW, submit, parent layout, or main merge was performed.
