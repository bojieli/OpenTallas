# TOK-ALL lane (successor to TOK-DS-9, TOK-QK-2, TOK-HBM; release gate = per-layer RTL sims on current dies + static schedule + inter-die traffic, real cycles)

## 2026-10-27 05:34 PDT TOK-ALL-1: per-design token table (current plan)
Labels: CHECKED = I read it from a sim log / receipt or reproduced the arithmetic; UNCHECKED = priced model, derived, or not independently re-run.

| Design (plan) | Priced cycles/token -> tok/s | Measured on current-die RTL (real cycles) | Per-layer RTL sims on current die | Blocker |
|---|---|---|---|---|
| DS ROM = S81 array 47 users + HEAD | S81 all-19-rows MTP 3,655.3 / AR 1,259.6 tok/s (TOK-DS-6b compose, UNCHECKED: rows summed, no joint DAG solve). Per-layer compiler priced spans L0 13,450.5 / L2 26,100.2 / L14 26,067.4 / L20 28,115.9 cyc (UNCHECKED vs measurement) | HEAD MTP wave 2,558,056 cyc PASS, 61 emitted (TOK-DS-8, CHECKED); XR7 vpx bench 5/5 baselines PASS + 10/10 mutants caught (TOK-DS-9b, component only, CHECKED by Codex receipts) | 0 of 6 layer types (CHECKED) | main die_b178.v strict bind FAIL (below); attn.rows_allgather GAP |
| Qwen ROM = QC + KV, 4 users | v7 QCE composer 296,341 cyc = 4,051.0 tok/s (UNCHECKED; user basis of the composer figure not re-derived) | QC compute L0-L35 + LM + emb 259/259 PASS on main 262d07038; spans resid 1,173 / silu 945 / qk 1,192 / od 1,555 cyc (CHECKED, TOK-QK-2). KV B48 boot: FAIL (below) | QC 36/36 (CHECKED); KV attention 0/36; whole QC+KV layer 0/36 | KV B48 boot never reaches setup_ready |
| HBM unified SU/MTP/MU, planU3f | ds_ar upper 1,905.97 tok/s, OWNER-accepted 10-27 02:39 (UNCHECKED model, HBM-MU-QUAD-3) = ~629,600 cyc at 833.33 ps (my derivation, UNCHECKED) | SU native multirate top on main: PR0 PASS serial 7,116 / stream 9,489 edges, max completion tick 27,652 (x 2500/9 ps = 7.681 us = 9,217 core cyc); PR1 PASS 7,120 / 9,495, tick 27,668 (9,223 cyc); compiled delta 0; throughput_qualified=false (CHECKED from positive.log + endpoints.json). P3 MTP producer-aligned lowering 3,916 records I1-I7 PASS, native_execution=false (CHECKED, lower_check.json) | 0 of 41 DS segments (CHECKED, TOK-HBM 02:00) | no unified die top / planU LAT pkg / MU views yet |

E2E token pass: NOT PASSED on any die. No whole-token measured number exists for any design.

### Collected (task 1)
- TOK-QK tok-qk-b48 (epyc1, died 05:25; logs on intel2:/srv/opentallas-scratch2/claude/tok-qk-b48/{asis,fixed}/sim.log): NOT finished and NOT worth a rerun. Both were stalled: frames_sent 0, images_ready 0 at cyc 29.6 M (asis) / 21.6 M (fixed) (CHECKED). Verilator is deterministic, so the same binary + inputs reproduces the stall (= Codex's 8-undriven-region-clock bench defect). The successor vehicle codex-kv-boot-2005 (r4) supersedes it. EPYC1-RETIRE also lists it as not rerun. **No rerun launched.**
- TOK-QK tok-qk-b48r4 (intel2, done): nominal exit 0 but **KVSLICE_BOOT FAIL**. frames 7404/7404, images 14/14, digests ok, errors 7354, setup_ready never (cyc -1), run ends cyc 59,977 (CHECKED). First error at cyc 2063: "boot_pr word before die reset release". The host die_rst_n to hub_C (dut.x_hub_Wi_o_host_die_rst_n_hub_C) stays 0 for the whole run. From cyc 20,747 every HBM slice boot faults (WS/WN/ES/EN done 8, ok 4). mut_frame FAIL as expected (boot_fault 1, 839/7404). NOTE: "exit 0" is the process status, not the verdict. run6 (10-26) had errors 0 with setup_ready also 0, so r4 is a further regression on the die-reset release. smoke_old on the same binary shows the identical FAIL line (CHECKED).
- TOK-QK KVL (intel2 tok-qk-kvl): top C++ make is 478 of 9,984 objects at 05:24 after 48 min, -j12 (CHECKED). ETA many hours (UNCHECKED). chain.sh will then launch 12 sims on the same codex-kv-boot-2005 hier libs. Those sims would hit the same boot FAIL: they use +START_AFTER_SETUP, so no token phase runs and there is no FAR_LAYER_SUMMARY. Not killed (ASK COORD).
- TOK-DS-9 (intel1): vehicle tree_b178 built from main die_b178.v; identity vs fc31 = 416 landings / 21,406 stations, 0 diff (CHECKED). Strict die_port_bind FAIL (CHECKED, results/token_pass/tokds9_1027/vehicle/bind_b178_summary.json):
  - port_not_in_rtl 5: dsdv_bk_sel_vmtx tpn_i/tpn_o/tps_o; dsdv_idx_rg3(+_nq) fault;
  - stub: s81b_ckrst (no_behaviour);
  - unresolved child: ot_s81ph_native_guarded_mux -> ot_s81ph_native_sel_slice;
  - undriven 656 bits: idxn_tp bk_sel s_*_LP 2x276, u_f_*_xok 96, f_irg 8;
  - output_open 33 ports; input_tied 81 (mostly sid/uid/k ID straps).
  - The layer compiles L0/L2/L14/L20 on b178 all FAIL with FileNotFoundError on rtl/.../frame/col_h10_l4_lp_asb_x.sv: the compiler looks up one file per module, but the module lives in s81_asb_models.sv (CHECKED).
  - LIVE: prep_cuts on intel1, unit oth-ubuntu-3026512-1793101781 (dv_rtl_kit after the bind FAIL, diagnostic only). Collect cuts_b178/prep.log RC line.
  - WIP pushed to the hub: claude/tok-ds-9-1027@7e345cd0d5 (mk_vehicle_current.sh, prep fix, ROM INSTANCE path params, receipts). Not READY.
- TOK-HBM PR0/PR1 positives collected (above). LIVE mut_DATA mutants: intel1 units 1184282 (pr0, from 04:58) / 1184281 (pr1, from 05:13), ~80 min each (UNCHECKED). Collect tok-hbm-su-main-1027/pr{0,1}/mut_DATA.log: it must be nonzero / MUTANT caught.

### Next per-layer sims (task 3): none started. No design has a current-die RTL vehicle that a per-layer sim can honestly run on.
- DS: needs the 5 port/1 stub/1 child/656-bit bind fixes in main die_b178.v or RTL (S81 plan owner), plus the compiler module->file lookup fix (TOK lane).
- Qwen KV: needs the B48 die_rst_n release fix (KV boot owner) and a rebuild on current main (incl. KVSCTL-3 +1).
- HBM: needs the unified die top (HBM-MU-QUAD-4/5).

## CODEX notes 2026-10-27 08:20 PDT
CODEX took over token collection/composition and HEAD native source integration on codex/head-g5-0818@315c5ba17a (source-only helper, tests2 PASS incl missing-tile mutant). DS/Qwen/HBM work is owned by tokens/ds, tokens/qk and tokens/hbm_token respectively; all remain active.
- KV boot root cause resolved at source-build level: 28 inline PCs used old vehicle4 qkd_ctrl_pc_nc.sv without boot_win while 4 PC0 hierarchical libraries used boot2005 fixed RTL; explains exactly4/32 boot slices. Source overlay fixes ALL top+library args, fresh incremental build queued; no new RTL change or KV token PASS.
- HEAD R17+source delta candidate generated native_bind: strict net/leaf PASS326inst,0open/tied/undriven/stub; tie_audit528 accepted, nested2217 PASS. Overall first receipt FAIL(module_missing10) is retained: copied stage had no Git metadata so module checker could not resolve providers. Exact-git module-only correction + functional elaboration is running separately on epyc2 unit oth-ubuntu-1917224-1793114381, intel2 client2260023; path /srv/opentallas-scratch2/claude/wt/codex-head-g5-git-0818/results/token_pass/head_g5_0818/{module_check_git.json,functional}. No repeated old numerical benches.
- Native source gap: physical manifest deliberately has BB ROM/element views; real CV+memory models are selected explicitly. Generated tile wrapper previously used default INSTANCE="h" for every tile, aliasing all264tile weight images. Native helper parameterizes only simulation image lookup per partition (0cycle change), emits required image inventory. Current physical-view equivalence/actual boot schedule/numerical token execution still pending; no whole-token PASS.
