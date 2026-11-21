# FABLE-FIX-S81-COLROM-R2 handoff (11-21 09:1x PST; successor of FABLE-FIX-S81-COLROM, read that file for the generator)
Dirs: epyc10 M=/srv/opentallas-scratch2/claude/fable-fix-s81-colrom, hub H = same path on intel2.
## Done
- Static gate of tree1 (candC3g + colrom delta a10c16b8 + RD_EXTRA=1 sidecars): ELAB 0, BIND 0, LATCHECK 873/873, G0 35 = 35 inherited, 0 new (M/gate1).
- signed_view_sha_s81.json in tree1: added ot_s81_cfg7_seq _tt.lib 7be441f9ca06... (copy+mv). The J7 tree needs the same entry.
- Functional bench M/bench1 (tb_colrom_loop.sv, run.sh SRC OUT; out in M/bench1/out, hub log H/bench1_otrun.log): closed loop seq + 7 cfg ROMs + q stage +
  dsfd_qbank_S + element hw/he wired as the bound RTL of col_h10_r1, A = no ROM-input stage, B = with it, same stimulus.
  Serial ops (2 seeds x 30 ops) and preload K >= 10 (pend path used, 10-28 held loads): PASS, same partial records, each +1 cycle, 0 faults.
  Stale-ef window (go at the lc pin -> next cfg_go while the other tag bank is live): A faults for K <= 8 (exists today), B for K <= 9.
  So the stage raises the minimum go -> next cfg_go spacing from 9 to 10 lc cycles. Nothing else changes (B ld_start at most +1).
  Mutants: stage on cfg only (go/xs early) FAIL; seq ef tied free FAIL at K=30 (inert at K=150, no held load there).
  Limit: weight ROMs are empty (pval 0); records compare row/seg/tag/pos.
- Token compile (M/tokc/run_tokc_colrom.sh, out M/tokc/out_colrom, same recipe as s81-j6/tokc out_c3g_child3): TOKC_RC 0, L0/L2/L14/L20 schedules numerically
  identical to the C3g baseline (price/span 15548 / 28229.7 / 28190.9 / 30555.4, 0 numeric leaves differ). The priced slice is u_s_0S; col ROM-field
  ops stay PARTIAL/GAP, so this shows no priced loss, not that the col pipes are modelled.
## Open
1. COORD/token owner: confirm the hub calendar keeps go -> next cfg_go >= 10 lc cycles per pair (or never preloads). Then the delta may enter J7.
   Structural follow-up (closes the window for both): in ot_s81_cfg7_seq hold ld_ok for 11 edges after the seq's own go (pend instead of load). Needs a
   re-harden of the cfg7 RDX view (FAM-S81-COL-R2 signed it 11-21).
2. Rep kit col_h10_r1__t1__cld01bb4ae: gen FAILED, clock_landings "stale clock landing endpoints/width on attn__svc_11__svc_9__0": sidecar_new.json of every
   C3g-based candidate (C3g, C3i, J7b) is stale against the svc H8 plan. Needs the J7 sidecar from S81-J6-ASSEMBLY-R4, or a rebuild on the live J6 tree
   (kw45 src_s81_pin_3c913dbdfb23_d8j6_1117_work, bind ..._bind_11210316; needs RDX view/RTL/define/registry + dead-input re-proof like j7_post.sh).
   Use kit_wave.py private-spec (the old hand spec H/wave1/spec.json is not allowed any more). No job of this lane is running.
3. In the rep read first: ROM pval -> bn output stage (needs ~160 ps late clock; if not, add a pipeline stage, no skew).
