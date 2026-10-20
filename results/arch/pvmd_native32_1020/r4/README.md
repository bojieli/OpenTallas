# R4: bp role counters -> full native32 census PASS (HBM-SMATT5 2026-10-20)

R3 (ec4d27d02) census left 8 combinational roots, 41..43 loads: the 3->8 decodes of u_core.bp
(mapped FFs _36766.._36768, D = u_core.nb). Remaining bp readers: entry busy/fl/fin enable +
m_fault/pv_v, e_tag[r] for pv_tag, e_tag[r] for node_tag/finish_slot, sw_a {r,e_k[r]},
stack read nb (sr_a/rk), TURNREG q_* read at nb.

R4 (FAN32=1 only; FAN32=0 is bp/nb exactly as before): each reader class takes its own kept
same-edge barrel counter (c_ent, c_tag, c_sw, c_nt, c_sr, c_q), reset by groups 10/11/12/12/14/14
(21/21/21+6/19+6 terminals -> <=27). No edge, schedule or reset-semantics change; a sim
assertion checks every copy == bp every edge.

Census (same native.ys/run.sh as r3, actual 5 TT cell Liberties + SRAM Liberty, 042aa171b tool):
PASS, roots 63873, max dynamic loads 32, 0 violations, 0 role errors; textbook refuse-mode 32 PASS.
mapped.v sha256 581dfaa10563cf61822939556492eac587c62e1a9a288d13030477e55b4d40da.

Benches (Verilator 5.050, fleet ot-epyc7, src = r3 tree + this commit's core/tb/bench):
- native_on (FAN32 1, tight, REASSERT1, XRAND): PASS 192 / 597 edges
- native_stop (REASSERT2 stopped clock, now also checks all 6 role counters): PASS 192 / 598
- legacy_off (FAN32 0): PASS 192 / 597
- MUT4 fold FAIL 64; MUT5 late turn copy FAIL; MUT10/MUT12 stopclk FAIL (tb STOPCLK check)
- MUT13 (new: c_sr/c_q lose async reset): FAIL; with -DSYNTHESIS (no internal asserts) caught by
  the tb STOPCLK_RESET_NOT_PROPAGATED check at 68 ns (mut13_synth_stop_*).
Next: PVM layout gate (kits smh_pvm_ref_s5a/s5b geometry) on this source.
