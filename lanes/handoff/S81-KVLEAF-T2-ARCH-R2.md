# S81-KVLEAF-T2-ARCH-R2 handoff (Fable; successor of S81-KVLEAF-T2-ARCH)
Brief + rules: localhost scratchpad resume_1123b.txt + rules.txt (session c228d9e1). Lane dir (inherited): intel2 /srv/opentallas-scratch2/claude/s81-kvleaf-t2-arch (wt = lane clone, branch s81-kvleaf-t2-hardkv, RTL draft UNCOMMITTED: kv_bank HARD_RQ>=2, cmp_pool HARD, kv_leaf, slice_w3 KV_HARD_RQ(2), new hier/dsfd_su_t_kvcn.sv).
## Measured (synth1, yosys synth + abc -fast ASAP7 RVT TT, rc 0, 04:58; module ot_s81sl_kv_leaf CNIK=1 CP=1 = bank + pool + leaf glue, WITHOUT the u_lf band = part A)
- 10,669,080 mapped cells, 1.089 mm2 cell area (0.102 um2/cell), 1,352,201 flops (0.398 mm2). No buffers/sizing.
- Storage: 176 SRAM macros in this module (144 x 32x64 + 32 x 64x512 = 1.34 Mbit). Flops are pipeline only: ot_hdc_f12_cut 413k, ot_hdc_delay 390k (204k of them bank-level relays), actquant 149k, kve local 131k. No flop-array store.
- Composition (each / total): kve x56 87,066 / 4.88M; kve RoPE x8 125,268 / 1.00M; kvq x16 72,289 / 1.16M; cn_write x16 53,295 / 0.85M; ik_write x4 91,564 / 0.37M; qnh x4 66,637 / 0.27M; ik_reduce 184,199; kvt x4 42,269 / 0.17M; qnr (kvr) 130,199; pool lane x8 149,833 / 1.20M.
- Soft residue with every engine black-boxed: 466,954 mapped cells (bank 451,808 = 25,956 glue + ~408k relay delays + 17.7k cn_norm_write; leaf 13,227; pool 1,919).
- eq2: flatten stat HARD_RQ 0/1/2 identical cell-type counts (only section order differs). Count equality, NOT LEC.
- FAM-S81-MISC-R4 fast count (t2count) crashed: yosys rc 139 (map::at). Their flat t2 place unit kwp-98f6e645758fadd68b0e (kit ...FAM-S81-MISC-R4/ot_s81sl_kv_leaf__t2_1123034934) was live at 05:5x: flat 10.7M + part A, cannot close; theirs to cancel.
## Verdict (posted 06:2x)
Option (d) hierarchy (closest listed option = (c) without new arithmetic). Not (a): storage is already SRAM. Not (b): a 28-piece cut makes 28 unique closures out of 10 repeated bodies.
Why 1: 97% of the cells are 10 module bodies repeated 118 times, flattened into one run. Why 2: slice top passes KV_HARD_RQ 0 and row t2 has no hard_cores; the 10-30 natural cut (DIE-S81-36) covered only the u_lf band shared with t1/t3/t4/t5. Why 3: no plan-row check counts mapped cells per soft type; the estimate was generic x 4.58 and area 0.979 um2/cell (macros included), so the row was sized by area and the hierarchy question was never asked.
Correction to predecessor: closed masters usable as-is = kvq, kvr, qnh only. kve/kvp/kvt need the CN ports -> new masters kvec/kvpc/kvtc; plus cnw, ikw, ikr, cpl = 7 new masters. Fit is NOT proven: B masters ~2.85 mm2 at 0.5 util + part A 1.77 + SRAM 0.54 + soft 0.2 = ~5.36 vs 5.31 slot before channels -> expect t2 outline growth or u65 forms.
## Plan / owners / ETA: see post. Next for me
1. Bench HARD_RQ=2 (tools/s81_dv/rtlgap_sukv_1021/hard_rq.py needs images L2/L14/L20 .mem: not found yet under scratch; ask FAM-S81-MISC-R4 / look in the 10-21 rtlgap run dirs).
2. Commit RTL in wt with slice top LEFT at KV_HARD_RQ 0 for J9 (zero netlist change), push via ot-push-main with tests.
3. Master private kits (7 new + re-check of 3 closed under the current flow), intel1.
4. t2 floorplan draft (hard_cores around the SRAM columns, A|B cut) to FAM-S81-MISC-R4.
## State 06:4x
- Posts: TAKING d0c915e8, VERDICT a2a395cb, PLAN 6e13a6dd (owners + ETAs; J9 = REASONED asked of FABLE-RC-S81; earliest GATED 11-24 evening, estimate).
- RTL committed on lane branch s81-kvleaf-t2-hardkv @ 9deebeb5cf (4 files; defaults unchanged). The slice-top line KV_HARD_RQ(2) is NOT in the commit: saved as tmp/slice_w3_hardrq2.patch in the lane dir, apply only in the private t2 tree. NOT pushed to main (bench pending).
- Open: bench images (asked in PLAN post); 7 ref_tile specs under tools/ref_tile/specs_s81su/ (model on s81su_kve_ref.json etc.; old masters used the 10-12 M5-cap ref_tile flow, current leaf cores use cores/views/rt22m_hx_1030 with obs_max M7 + pins_file: check contract); floorplan input to FAM-S81-MISC-R4 by 14:00; no reply read yet from FABLE-RC-S81 / FAM-S81-MISC-R4 / FIX-LEDGER.

## Codex scope 11-23 10:0x
- t3 relaunch is PENDING REASONED with FABLE-RC acceptance pending. OPUS R10 J9-LEAF-REACH recorded -329 ps across 610 um and 20 stages from the VN rb_v_c flop to u_x.q[21]. This is a VN soft RF read/write cone; t2 HARD_RQ2 native and SAT results do not qualify t3. Check same-edge local one-hot/row preference under actual mapped structure before introducing the preauthorized CBC cycle and repricing the VN valid/data interface. No unchanged relaunch.
- E9 private t2 proof: native L2/L14/L20 and 176251/176251 n0/n2; 420167 to 321548 mapped parent cells with true 118+144 blackboxes. Current joint input placement `master_drafts_codex/engine_order_codex/joint_actual_inward_4907x1918_28-30_s0_bottom.json` e59a94b00645 fits 118 hard seats, 192 same-age data relays and 151 original SRAM rows at 4907.52 x 1918.08. Exact 65792 input data/valid hops <=400.772 um and zero footprint overlaps. Private continuation tightens downstream QNH/KVR and paired KVQ positions while KVE->CNW/KVQ spans still exceed the three-stage current reach on some paths. Seven draft views remain unsigned.
