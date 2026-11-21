# FABLE-FIX-S81-COLROM handoff (started 11-21 05:2x PST; updated 06:1x)
Owns lever 1 of FABLE-CLOSURE-0600: S81 col ROM-input stage (216 col types). Took it from FAM-S81-COL-R3 (05:24 handoff post).
Work dir: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom (M). Hub dir: intel2 same path (H).

## Generator (done)
- M/gen_colrom_rows.py PLAN BOUND_RTL_DIR OUT_DELTA [--out-plan P] [--sidecars DIR --sidecars-out DIR] [--hop-max 400] [--no-pval].
  Self-contained (no donor). Per col type, from its own hard cores and the bound leaf names in BOUND_RTL_DIR/<type>.sv
  (u_<inst with . -> _>, else the same without the u_rN_ region prefix):
  rom_in (13 input ports per ROM element half, seat 5.59 um off the pin face), cfg7_q (cfg ROM rd_out -> ot_s81_cfg7_seq q<M>,
  bfp skipped, seat pulled toward the sequencer when the hop is over 400 um), rom_pval where the base lacks it, repoint of every
  ot_s81_cfg7_seq core to the RDX view, RD_EXTRA=1 in the romq_split hard-params sidecars. Row-level adds only.
- On candC3g: M/gen_c3g/colrom_delta.json (sha a10c16b8), plan.json (sha afdf78f0), report.json, sidecars/. 216 types,
  22,464 rom_in + 6,048 q rows, 864 repoints, 0 pval rows missing.
- Equal row for row to S81-J6-ASSEMBLY-R3 rows/j7_rdx_fix (32,992 rows, 0 differences), except 12 seats
  (col_h10_r1 u_s8.q3: 455 um hop -> 400).
- Checkers: M/sitecheck.py BASE NEW (seat to pin distances), M/cmp_rows.py A B.
- R3 gen_rdx_rows.py and R2 mkplan2.py emit u_rN_ names: wrong on h9_r1, h9_r2, h10_r1, h10_r2, h9_r0_p3, h9_r0_p6. Do not use.
- The tree also needs (assembly lane j7_post.sh does them): define OT_S81_CFG7_RDX in asbuilt_run.json, signed view + RTL,
  hard_core_built_params entry, reprove41 dead-input proof.

## Timing basis (read from J5 kits on intel1, TT)
- seq go_tag -> ROM pin: seq clk->q 389 ps + 252 ps wire against a 609 ps window: -32. With the stage: +170 / +540 estimated.
- cfg ROM rd_out -> seq q: ROM clk->q 529 + 259 wire: -47. With the stage at the ROM face: about +240, then 400 um in a full cycle.
- ROM pval -> bn (output half, FAM-S81-COL-H10 owns the proof): ROM q lands 137 ps after the edge; the stage only works if its
  clock is about 160 ps late. Watch this path first in the rep read.

## Proof in flight (rep col_h10_r1__t1__cld01bb4ae)
- Tree M/tree1 = cp -al of s81-j6/candJ7RDX + gen_c3g plan + sidecars (mktree1.sh). Tools rt 2ddb19c08ba6 (M/rt, H/rt).
- Gate: M/gate1.sh tree1 gate1 = elab + strict bind + LATCHECK + G0 vs candC3g, out M/gate1/ (bind_out there).
  Unit oth-ubuntu-1452049-1795268387 on epyc10, hub log H/gate1_otrun.log. First try failed only on the missing elab.
- Hub chain H/chain1.sh (setsid, log H/chain1.log): gate pass -> kit_wave run-item H/wave1/spec.json (env = wave die_gen_env +
  item_env + flow_tag, COORD ruling d442c09bb6e; src_manifest off) -> place/geom -> config.mk diff vs the J5 wave kit
  (epyc7 kw43-wave-1109n .../224567138ab/items/<type>/attempt_19) in H/wave1/config.diff -> post.
## Next
1. Read gate result (BIND/LATCHECK/G0 new errors). signed_view_sha_s81.json has no rdx_1121 entry: gen may refuse the view.
2. Read config.diff; then route: on intel2 `ot-run --mem 64 --threads 16 --disk 40 --hosts epyc10,epyc7,epyc8 --dir $G -- bash
   $G/run_kit.sh $G/<type> route 64 16` (G = kit gen dir). Read TT after the post-GRT repair and the endpoint classes
   (ROM pins must be gone), then sign-off. For export, rebuild from a src_manifest tree or let J7 carry the rows.
3. Second rep: one col_h9_r0_p2 (u_r0_ prefix form).
4. Open: the rom_in stage delays cfg_v/go one edge; bank_free/sh_free -> seq ef return is unchanged (loop +1). TOKEN-1121 must
   compile with the declared cycles; no bench of the loader loop with the stage exists yet.
