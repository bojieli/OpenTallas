# TOK-QK 2026-10-27: B48 boot resume, QC per-layer on current main, compute<->KV latency table with the KV slice +1

Grade: lane receipt. No whole-token RTL pass is claimed.

## 1. B48 native KV boot (Codex codex-kv-boot-2005)
- Codex unit oth-ubuntu-2702208-1793070819 (intel2) exited 2 at 22:40 PDT on 10-26. The top Verilator frontend finished (20:19 to 22:33, 256 vm_classes). The top C++ make then stopped with `make[2]: *** No rule to make target 'Vkv3_hub_Wi_part.cpp'` (raw/codex_b48_top_make_fail.txt).
- Root cause (CHECKED): the epyc1 -> intel2 spill (spill.sh) copied only `*.a/*.h/*.mk/...`. So 56 unchanged hier libs and hub_Wi_part arrived with no `.cpp/.o`, and make tried to rebuild them. stage.py had meant those 56 dirs to be symlinks to tok-qk-b48/build3/obj, which now exists complete on intel2 (moved for the epyc1 retire at 23:41). All 56 `lib*.a` are byte-identical to build3 (cmp). hub_Wi_part got its `.cpp/.o` at 23:54.
- Fix: the 56 dirs are re-linked to build3/obj (the old partial copies are kept under build/spill_incomplete). No source or bench change. Only the top C++ make and the two boot sims are resumed (b48r4_run.sh): nominal, then mut_frame (+MUT_FRAME=100, must FAIL closed).
- Run: intel2 ot-run unit oth-ubuntu-3129816-1793089507 (--mem 320). Logs are in /srv/opentallas-scratch2/claude/tok-qk-b48r4/{top_make.log,nominal,mut_frame}/{exit,sim.log}.

## 2. QC per-layer (QCLM, 259 cases covering L0-L35 resid/silu/qk/qkv/gu/od + LM + emb) on current main
- QCLM r1 PASSED 259/259 on main b272ba0ec (claude/tok-qk-qclm-1026, CHECKED).
- The preprocessed source of current main 262d07038 differs from r1 by one line (raw/qclm_r2_pp_vs_r1.diff): `r_addr + 24'(q)` became `r_addr + q[23:0]` (YOSYS-CONCAT rewrite in qfd_dv_amax_mu, the same value).
- Fresh r2 rebuild and run: epyc2 unit oth-ubuntu-1744034-1793089766, /srv/opentallas-scratch2/claude/tok-qk-qclm-r2. Collect from stgdie/result.json.

## 3. Compute<->KV latency table / static schedule terms (base v7 QCE composer 296,341 cyc/token, 833 ps)
| term | composer | current-die evidence | delta/token |
|---|---|---|---|
| XDIE pair edge @pre_o (X + STATUS tail 213) | X 8, L0 X -214 | XD4 QC v7 x KV B48: X 8, L0 X -214, period 7056, RT 1957 | 0 |
| attention return (dr land + o_proj x) | 149 | bound-row attnret 149 = compiled | 0 |
| KV slice hr face +1 buses (KV-CORE-SLICE-1 ASK-1) | none | hr_plus1_price.json: 21 listed buses, none per-layer | 0 per layer, <= +21 per token (UNCHECKED, list incomplete) |
