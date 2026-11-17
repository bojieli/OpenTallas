# FABLE-FIX-HEAD-RESET handoff (Fable), started 2026-11-17 ~07:40 PST
Owner of the HEAD (s81_head, 833 ps) reset/START seam problem. HEAD-PLAN-R4 owns the NF15f geometry event; scope ACK posted.
Nothing deleted, no kills, no heavy job launched.

## 1. Mechanism (real r4 census, lanes/evidence/head_reset_model_1117/feasibility_r4.json, old NF15c clock)
714 seams = 357 receiver parts x (arst_n, start_i); every part has one parent. 530 FF hold fails, 26 seams (13 parts) TT setup < -42.
- ONE mechanism: clock-region insertion phase. capture - launch skew -906 .. +1725 ps (p10 -213 / p50 303 / p90 814) on an 833 ps clock.
- Crossing distance is NOT a cause: minimum data delay is flat (p10 99 / p50 209 / p90 211 / max 344 ps).
- "No local tap" (410) is a consequence: no existing tap sits at the right phase; it is not a missing-tap problem.
- BUF4 is the remedy model, not a hold model: it pads up to 1 ns with a TT/FF ratio of 1.53 and needs 33 view classes / 17,236 cells.
- The 13 reverse-phase parts are the same mechanism with the opposite sign.
Split of the 530 by the smallest change that closes them (classify_r4.py):
| class | seams |
| whole-cycle label only (capture edge 1-2 cycles earlier), margin >= 100 ps | 157 |
| whole-cycle label closes it but margin < 100 ps (wants the half cycle) | 271 |
| needs the falling capture edge (no whole-cycle label passes) | 102 |
Window TT setup + FF hold per seam: 557 .. 967 ps (p50 696), so a half-cycle grid always has an edge.

## 2. Form: strap-selected entry phase (tools/die_plan/pin_entry_phase.py)
- Type knob reset.pin_entry_phase = true: entry cell ot_dp_rrelay_ph for reset and START = rising capture + falling capture +
  static select ph + one rising local handoff. ph = 1-bit ID strap strap_rst_ph (existing id_straps path: port, kit false path,
  die-top tie, strap audit). 3 FF per entry bit. No delay cell, no clock fork, no new type or view class.
- Instance row partitions[].reset_entry_phase = h (half cycles the declared capture edge is EARLIER than the nominal next rising
  edge). strap = h mod 2. Wavefront release moves by -ceil(h/2) vs the two-stage nominal entry (wf_plan row
  entry_phase_half_cycles). Die STA label: setup multiplier 1 - floor(h/2) on the selected capture, false path to the other.
- The type view is phase-agnostic: a new clock (NF15f) changes only strap values and labels, never a type layout.
- Reset is quasi-static, START is a level, both stay fully timed (no false path on the seam itself).

## 3. Model on r4 (entry_phase_model_r4.json in lanes/evidence/head_reset_entry_phase_1117/)
357 parts, 0 fails; min margin 118.8 ps (sp3), 9 parts under 150 ps; margin = min(TT setup + 42, FF hold, TT hold).
h: -2:1, -1:14, 0:51, 1:229, 2:36, 3:23, 4:2, 5:1. strap 1 on 267 parts, 0 on 90; 9 of 25 types use both values.
Cycle delta vs today's plan per part: 0 on 265 parts, +1 on 65, +2 on 1, -1 on 25, -2 on 1. Accumulated over the wavefront
-3 .. +4, 310 parts change; CA root settle 88 -> 92 on this old clock. Numbers are for the OLD clock only.

## 4. Code
Worktree epyc9 /srv/opentallas-scratch2/claude/fable-fix-head-reset/wt (sparse: tools rtl physical/common_flow).
Files: tools/die_plan/pin_entry_phase.py (new), test_pin_entry_phase.py (new), reset_tree.py, gen_rtl.py, schema.py,
die_plan.schema.json (dump-schema), parent_id_straps.py (strap_rst_ph width 1). Default off: other plans byte-identical.
Branch claude/head-reset-entry-phase-1117 @671942fabfd0206a4f38e113c6b34f2a7c67e569 (pushed). Tests: test_pin_entry_phase.py 7/7
(identity when off, refusals, labels, plan errors, STA rows, iverilog counted frame over skew -906..+1725 x data 99/209/344 with
a wrong-strap control). Gate: ot-run on epyc2, client log intel2 ~/fable-fix-head-reset-logs/gate_671942f.log (see posts for verdict).
die_sta.py run --entry-phase ROWS.json (rows from `pin_entry_phase.py rows PLAN OUT`): multicycle + mask per instance; a capture
register that does not resolve prints OT_ENTRY_PHASE_MISS and exits 3. The pin pattern is NOT yet run on a real netlist.

## 5. Functional compose rs1 (epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-reset/rs1, 1.5 GB)
prep_rs1 = copy of HEAD-R3 stage/prep_f1 (plan 3210bf1f, the gated NF15f cycle tuple) + compose_rs1.py: 25 types opted in
(all but root type hd_spn_end), 357 parts with strap + label from the r4 model. Plan sha 69cef9f459c63a67.
Done with the real tool (wf_rs1.py, light): plan_errors 0; wf_plan release delta per part = the model exactly
(-3:1 -2:2 -1:5 0:48 +1:122 +2:135 +3:36 +4:9); wavefront max release 96 -> 97; hd_tile emits ot_dp_rrelay_ph on u_rst_in and u_run_in.
NOT run: receipt, kit RTL, bind, cohort, LATCHECK, G0. epyc10 scratch fell to 12 GB at 07:55 and ot-run refuses the host
(floor 50); the plan needs epyc10-local inputs (kw45 src, native_release_proof 3.5 GB). ALERT posted.
Launch when epyc10 admits again (one attempt per directory, marker RS1_ATTEMPTED):
  ot-run --mem 64 --threads 16 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/fable-fix-head-reset/rs1 -- bash run_rs1.sh

## 6. Open, in order
1. rs1 gates (above). Expect G0/bind findings on the new strap pin: hd_tile's other straps carry sites_um + layer; strap_rst_ph
   needs a site per type in the event (HEAD-PLAN-R4 owns pin geometry) before any kit.
2. Final labels: redo the census on the NF15f clock (census_r4.py on the new die_sta.json), then model_r4.py -> rows. No type changes.
3. Calendar: per-part START/reset admission and CA root settle come from wf_plan (88 + max accumulated delta; +4 on the old clock).
   Goes with lever 7 item 3 (HEAD-PLAN-R4 calendar regeneration); count-align gate after.
4. Pilot: hd_tile (264 instances, both strap values). Kit with the knob -> post-CTS/routed internal FF hold on cap_f -> q and
   cap_r -> q, then a two-instance die STA pair with --entry-phase on the worst old pair tE1o0 -> tE0b1 (FF -936) and the
   reverse pair tW5o7 -> tW4b8 (TT setup -334). Not started: no NF15f kit exists (HEAD-PLAN-R4 blocker (2), no kit launch).
5. Duty: the falling capture rides the clock duty. Read duty at the entry taps of the NF15f GEN; 9 parts sit under 150 ps.
6. Superseded if this lands: BUF4/HB4 phase classes (33 view classes) and the N30 clock fork + handoff for the 13
   (pin_entry_handoff, branch claude/head-reset-entry-fall-1117 @98308db8). pin_entry_fall stays valid (it is h = 1 fixed per type).

## 7. Gate
GREEN 146/146 (GATE main=e251fda2da5), record intel2 ~/merge-queue/gates/671942fabfd0206a4f38e113c6b34f2a7c67e569.json. READY posted 2026-11-17.
