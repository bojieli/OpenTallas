DIE-KV-16 2026-10-28 (KV die owner; successor of DIE-KV-15 943e483d2e; branch claude/die-kv-16-1028).
Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-16-1028.  CHECKED-own = my run/count; nothing NUMBER-CHECKed independently.

(1) V-word landing fix, ESTIMATE FIRST: estimate.md (this dir).
  RULE (RTL): the PV ctl checks the 8 vport headers at one age and issues "the command word for the arrival at pa+1"; the
  bank registers pv2/bc on one edge and takes V on c_r.take.  Per bank b fed by vport p:  VDH = dV - dcmd - dH(p) = 0
  (dX = landed - as-built; H = vport out_t -> ctl in_t).  Launch-invariant: no boot DQ/W/RT value absorbs it.  This is the
  KV-P6-PV correction d218a2b989 that the DIE-KV-14d column table (cmd/flag only) dropped.  The DIE-KV-15 per-source
  criterion (one dV - dcmd per vport source) is necessary, not sufficient (a constant offset per vport and lo/hi of one row
  register as two sources both pass it).  ASTK pe2: one (dpe2 - dcmd) per astk source (external, free launch).
  bind4 measured [CHECKED-own]: 2022 / 2078 members off; V VDH -16..-114 (V early on every vport), pe2 spread <= 11.
  Options: (a) V pads at the PV partition entry to VDH = 0 + pe2 one offset: 765,784 FF shared estimate, realised
  797,696 FF in the bound kv3_pv* RTL (ot_dp_dly W x D, bind5 - bind4) [CHECKED-own count] = 0.23 mm2 = 0.077 % of the
  299.5 mm2 die (area UNCHECKED, 0.29 um2/FF), power ~1.6 W <= ~0.9 % of the >= 179.5 W measured hg+hgi+pv (UNCHECKED);
  max pad 114 stages; 0 schedule cycles (restores as-built relative timing).  (b) bank-side count-aligned V buffer released
  by the command: depth >= 114 (outside the 12.16 standard 8/16), >= 6.16 M storage bits even at exact depth, new shared
  bank RTL + LEC -> >= 8x (a).  COORD 18:59 conditions met ((a) <= 3 %, (b) larger) -> (a) built.
  Generator + check: physical/die_plan/qwen_kvsys/r8/kv_pv_v_pads.py (pads | check), test_kv_pv_v_pads.py 2 passed.
(2) Bench coverage gap (why the earlier KV token numbers did not see it):
  - 4051.0 tok/s is the nativev7 COMPOSER (QCE 296341 cycles/token) over component benches, not a bound-die simulation.
  - The PV component bench (native PV 128/128) drives the pair at its pins with the as-built V/cmd schedule; the vport
    bench (RT/DQ 128000 checks) is lockstep vport_b vs reference.  Neither contains the die lanes vport -> bank, ctl -> bank,
    vport -> ctl header, so per-bank V-D-H is outside both.
  - The KV-P7 whole-die vehicle (RECIPE, kv_bound_carve) that would see it never completed a token run on a bind (TOK-QW:
    B33 boot FAIL; B48 build2 live) and was never run on the DIE-KV-14/15 binds.
  - The static V-D-H self-check (Codex kv_pv_pads_selfcheck, d218a2b989) belonged to the withdrawn KV-P6-PV table; the
    DIE-KV-14d replacement was checked only by regen_constants kv_pv_trunk (cmd/flag law), which has no V term.
  Closing it: kv_pv_v_pads.py check is the static per-bank gate on every KV bind (run in post_bind16.sh); mutant bind5m
  (one bank V +1 stage, recipe_kv16_b5m) -> FAIL on exactly that member (V:1 x1) [CHECKED-own]; the token vehicle must
  also run bind5m and FAIL the RESULT compare (NOT run, next lane).
(3) Rebuild: recipe_kv16_b5 = recipe_kv15_b3 + pv_v_pads_b4.json -> bind5 (ot-run intel1) 0 errors; V-D-H PASS 512 banks /
  2078 members; DIE-KV-15 v_offset_check PASS (0/36); KV REGEN_CONSTANTS PASS {OK 40, WARN 2: VPORT_DQ, CFG_FIA 166}
  identical to bind4; QC peer unchanged (COLL_LS MISMATCH = ONEQC owner).  Image (results/kv_native_image_13 run_constants2 + emit_assets, QC peer fresh_v3): 96 DCFG + 19 AGE words, 0 new W pads, DCFG/AGE hex byte-identical to DIE-KV-15 img4; TXDP 030304aa unchanged (img5_assets/).
  B48 token sim NOT run (whole-die KV-P7 vehicle on bind5 + img5, then bind5m mutant): next lane.
(4) (b2) red_issue copies: NOT started (after the V fix, per COORD).
