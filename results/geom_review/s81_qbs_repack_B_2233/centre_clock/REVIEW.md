# Disabled coherent hist centre M5 clock-entry candidate

ROOT authorized this physical clock-entry event. This extends the disabled internal macro repack B proposal; it is a new physical ck pin contract, with the same ck name/one-bit width/833ps frequency, unchanged RTL/register count/data-reset pin contracts. Original M3 entry is held; there is no default/canonical adoption or as-built view claim.

The literal core centre(324,324) lies in the new OFQ halo (macro top322.92um +4.32um). The candidate instead places ck at(324.012,331.212)um on the actual local M5 grid(offset.012,pitch.048), with rectangle[323.988,330.972,324.036,331.452]:48nm×480nm. Both coordinates also permit the on-track M4 landing. Nominal source-PDN M5 stripe-pair metal clearance is1.968um; actual regenerated PG and via landing remain required. A4.32×4.32um clock-entry driver bay[321.84,328.32,326.16,332.64] sits outside all32 macrohalos and face bands. Its16 actual historical row spans offer18.6624um²,0 old fixed/TAP occupancy and0 final FF targets. The bay reserves space for a normal clock entry buffer/CTS; no physical clock buffer was invented or preplaced. Actual buffer count/area and latency must be priced in the future clock stage.

All31847 FF positions were assigned again with this bay reserved (8231 moved,1801 functional faces preserved), using original-row orientation for moves. Independent full occupancy audit is0 and full native G.r2r has0>405um over29249 captures. Max real FF endpoint hop remains404946DBU and exact directional macro-port hop404943DBU at1000DBU/um. Comb/buffers remain free; all FFs must become FIRM without resizing/cloning in any prototype.

Clock source→sink L1 guidance improves: longest macro clock-pin distance817.731→491.508um and longest FF-centre distance941.340→644.127um. These are geometric lengths, not insertion timing. TT250/FF202.5ps targets,40ps window, actual clock+reset source ABI and corner controls remain in force. Rebuild rows/taps/PG and normal clock stages, inspect LOOK and preflight before route; no die elaboration. Exact SYNTH reuse is allowed only if the RTL/config/netlist event is truly unchanged. Hist parent EQ is still held: current051 prepared only; both foreign rb2/rb4 legacy proofs still run, original70diff retained.

Coherent inactive references are concrete:

- New source table physical/die_plan/s81/inputs/core_pins/dsdv_bksel_q_centre_disabled.json and its identical packet copy contain1803 pins,1802 byte-equivalent pin entries.
- dsdv_bksel_q_contract.lef changes only the ck PIN block from the existing LEF. All non-ck text is exact. This is a contract candidate; its old OBS/timing are not a newly extracted internal implementation, and must not be used as physical qualification.
- parent_type_overlay_disabled.json changes all4 dsdv_bksel_q references in the existing bk_sel__t2 parent type, selecting the same candidate LEF/table. The parent type has1 placed parent instance in this source plan. The future actual child LIB path is intentionally absent/HOLD; old insertion and signoff are not borrowed. Regenerate the child view and replace all refs coherently before any parent physical activation.
- io_clock_override.tcl can place the exact same ck BTerm rectangle after generated io.tcl in a fresh own candidate core kit. This packet does not invoke it.

LOOK: viewed the full centre candidate image before any CAD. The green driver bay and M5 entry sit immediately above the moved OFQ row, with data/reset face pins preserved. The FF reservations exclude the bay and all new macro halos. Original no-repackFAIL,405boundaryFAIL and previousB model results remain untouched.

The new bay-reserved FF coordinates also receive the same finite23 actual-native hypergraph global-cut census:0 necessary violations, worst x250um3752 min-crossing nets/12044.25 nominal derated PG-duty-reserved M2–M5 tracks(31.152%). This remains a lowerbound, not local congestion or actual PG/via qualification.
