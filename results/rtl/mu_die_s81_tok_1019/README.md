# MU-DIE-S81/TOK (10-19): token simulation on the MU release die GEN mu1

Die: GEN mu1 strict-bind die.v (claude/mu-die-s81-1019 @1d43f2c12, sha256 81498f42..., 41 masters / 8,948 inst), plan
p4l_mu_lkcol, land plan p4l3. Tools + RTL: this branch = parent + claude/tok-s81-gaps-1018 ae517d216 (dv_cut_replay
83dca8cc4, cutter/kit/compiler lowerings, VP/VS/svc_rs fixes). Kits dv_rtl_kit --ref 9c2f5fe60 (die kit PASS 41 masters).

## Inputs built (local, python only)
- Compiler tree = die.v + plan + land plan; `land_plan_p4l3_mu_sim.json` adds the 4 MU lanes (mu_0S/mu_0N/mu_7S/rt_0N)
  with E = K = the die.v strap 1 (land plan K for MU lanes is OWED by MU-DIE-S81; with K 1 the cutter flight clamps to 0
  for any S1, so the sim equals the die.v).
- Programmes (compiler/): SU L0 GAP 10 / PART 32 / LOW 23 (65 ops); L2 32/33/18; L14 37/37/18; L20 30/36/18. MU = same +
  `--mu-cal calendar_ar_q4.json --mu-ctx` (L0 S000 46 users copy A; L2/L14/L20 copies A 23 + B 23; lemma PASS).
- Cuts recut from the MU die.v (cuts/): cut_0S 961 inst (lepw_mus), cut_3S 609, cut_7 2,251 (lepe_mu + lepe_nh_mus),
  cut_3S_ctl 3,352 (seq_host_mux). None identical to the G8R2 cuts (p4m die) -> no obj reuse.

## FINDING: compiled schedule faults on the S line (all four layers)
`logs/line_collision_witness.txt`, `logs/gen_cut_{0S,3S}_*.log`: on this die the G-unit HC coefficient row (vo_s, re-injected
by ot_s81sl_xr on the S line both ways) lands at u_s_2S/1S/0S ri_e on the SAME edge as the seq_host V CTL beat
vs.ffn.softplus_sqrt.RA.s0m01 (L0 10635/10647/10659; L2/L14/L20 likewise). ot_s81sl_rstop/xr: two CTL beats in one cycle =
sticky fault, so this is a real static-schedule fault (on G8R2 the gunit job landed 56 edges later, no overlap).
dv_cut_replay gen refuses cut_0S / cut_3S / cut_3S_ctl replays; cut_7 is not on those stops.
FIX OWED (compiler): dv_layer_compile must reserve the line slots of G-unit V re-injection (dv_cut_replay
derive_vctl_line_events model) when it places seq_host V CTL beats (or move the HC job), then regenerate the replays.

## Fleet runs (Verilator 5.050) -- see pending_results
- builds + 2,000-cycle idle: /srv/opentallas-scratch/claude/mu-die-s81-tok/out_<cut>_idle (ot-epyc8).
- SU replays cut_7 L0/L2/L14/L20: chain_su.sh -> runs/out_R_cut_7_<L>_su/check.json (scratch).
- MU issuer bench (real dsdv_seq_host = the issuer inside dsdv_seq_host_mux, run_mu.sh of MU-S81/TOK) on THIS die's MU
  programmes: out_mu_L0L2 (L0 46 users dense S000 incl. users 0/1/2 at 0/21313.7/42627 on the 4-edge grid, L2 copy A/B,
  mutants shift4 / ctx3 / raw-shift 21313 / user-drop) and out_mu_L20L14 (L20 copy A 23 users, L14 A/B, same mutants).
## Not done (owed)
- MU traffic on the cuts: dv_cut_replay has no multi-user mode (per-user {user,pos} tags on mu_c / h lanes, landings);
  needs a `gen --mu mu_slots.json --users ...` superposition of shifted per-user words + the MU lane events.
- Cycles vs priced and AR/MTP composition: wait for PASSing non-partial replays.
