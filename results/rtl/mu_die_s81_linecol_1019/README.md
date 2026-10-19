# MU-DIE-S81/LINECOL (10-19): tier-line slot reservation in the layer compiler

Finding fixed: MU-DIE-S81/TOK (claude/mu-die-s81-tok-1019 @1e20a0406, `results/rtl/mu_die_s81_tok_1019/logs/line_collision_witness.txt`):
on the MU GEN mu1 die the G-unit HC coefficient row (vo_s -> u_s_3S V -> ot_s81sl_xr re-inject both ways) and the seq_host
V CTL beat `vs.ffn.softplus_sqrt.RA.s0m01` (column-4 re-inject) land on u_s_2S/1S/0S ri_e in the same edge in L0/L2/L14/L20
(= two sources on u_s_3S ro_w, ot_s81sl_rstop sticky fault).  The line genuinely needs ONE slot per beat: no RTL change.

## Change (compiler only; static fixed-cycle schedule, no arbitration)
- `tools/s81_dv/dv_layer_compile.py` `line_slots` / `line_collisions`: after the calendar CTL events are placed, every
  tier-line beat is derived with dv_cut_replay's own line model (landed_words = derive_line_events + derive_vctl_line_events
  on the die build) -> slots (slice, ri_e/ri_w, landed edge) and xr slots (slice, landed edge) of the CTL beats a slice takes
  (ot_s81sl_xr f1: two CTLs on two faces in one cycle).  A slot held twice moves the seq_host V row's op later by the
  smallest delay that clears every reserved slot (`line_delay {op: edges}`, re-lowered; lower_vs takes it), else a compile
  fault.  schedule.json gains `line_slots` {line_delay, collisions 0, slot counts}.
- `tools/s81_dv/layer_prog/lower_vs.py`: plan(line_delay) -- the op's first command starts +d edges past the priced start.
- Bug fixed on the way: the svc-tag re-lower recursion dropped `mu_ctx` -> TOK's prog_L0_mu calendar had NO `+ctx` row
  (byte-identical to prog_L0_su); now 2 `+ctx` rows as in L2.  TOK's MU L0 issuer bench (out_mu_L0L2) ran that stale L0
  programme: re-run run_mu.sh on compiler/prog_L0_mu of this branch.

## Result (tree = TOK tree_mu: mu1 die.v sha 81498f42, plan p4l_mu_lkcol, land plan p4l3 + MU lanes; fixtures layerbench-s81)
| layer | collisions before -> after | line_delay softplus_sqrt | RA issue | calendar END / last event | priced cost (RA on crit path) |
|---|---|---|---|---|---|
| L0  | 3 -> 0 | +3 | 10593 -> 10596 | unchanged 12763 / 12822 | +3 edges = 0.019 % of 15,492 |
| L2  | 3 -> 0 | +3 | 22255 -> 22258 | unchanged 26052 / 26111 | +3 = 0.011 % of 28,120 |
| L14 | 3 -> 0 | +3 | 22180 -> 22183 | unchanged 27052 / 27111 | +3 = 0.011 % of 28,045 |
| L20 | 3 -> 0 | +2 | 24967 -> 24969 | unchanged 44162 / 44221 | +2 = 0.007 % of 30,449 |
Only the RA row moves (calendar row diff). Its successor ffn.router_allgather is GAP (not lowered), so the compiled span is
unchanged; the priced cost is the delay on the critical path (cost.json).  `verify/<L>_{su,mu}.json` = independent check
(verify_lines.py, TOK witness method): SU 0 collisions; MU superposition of every user of each die copy (mu_slots shifts:
L0 46 users gap 21,312; L2/L14/L20 copies A/B 23 users gap 42,624; L20 span 44,221 > gap, so users overlap) 0 collisions.

## Replays (dv_cut_replay gen, SCHEDULE, stale False, die sha match)
cut_0S and cut_3S L0/L2/L14/L20 generate (were refused); replays/ = replay.json.  cut_3S_ctl needs the idle run
(--idle-run + ks sweep) -> chain_lc.sh.  Fleet (Verilator 5.050, OBJ reuse of TOK's mu1 cut builds; TOK's cut_3S build was
SIGTERMed (exit 143) and is relaunched by chain_lc.sh --mem 100): see pending_results (MU-DIE-S81/LINECOL).
