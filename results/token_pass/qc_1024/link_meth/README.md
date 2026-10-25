# QC token side: link passes (tp8 / xdie / ovl4u) on the methodology re-plan bind, 2026-10-25

Bind: epyc1:/srv/opentallas-scratch2/claude/qc/bind_meth_cb16 (plan claude/qc-meth-1024 @a281ceb5ce, R8 + CB16 pads,
0 bind errors, verify PASS). Constants: `tools/die_plan/regen_constants.py` on that bind with the KV peer kv41
(`physical/die_plan/qwen_kvsys/bind/bound_pv`), 25/25 OK (`../xt1_meth/constants_meth_peer_pv.json`). kv44
(claude/kv-bind-1024r bound_kv44) as the peer gives the same xdie constants.

Source assembly: `git archive` a281ceb5ce (rtl, tools, configs, macros). Fixtures come from the same commits as the 10-24
pass (`stage_link_meth.sh`; `link_fixtures.sha256` is byte-identical to `qc_tok_1024/link/link_fixtures.sha256`).
Verilator 5.050, run on intel1 through ot-run (`run_link.sh tp8|xdie|ovl4u`).

| test  | constants used | positives | mutants / negatives | verdict |
|-------|----------------|-----------|---------------------|---------|
| tp8   | COLL_BENCH_ARGS `--relays 0 11 11 11 --lanes 2 2 21 2 2 20 --lx 23 4 22`, LS 407; MU window recompiled at LS 407 | 3/3 PASS (cal, cal_seqsu, mu: 61,440 words mm 0 + user-0 ref) | 9/9 FAIL as required (cal_minus1 = LS 406 faults all 8 dies) | PASS |
| xdie  | XDIE_DIE_STAGES `2,2,2,3,2,2/34,34,32,32,32,31,31`, TXDP C 0a010308 / K 03030443 (unchanged) | 9/9 PASS | 13/13 FAIL as required | PASS |
| ovl4u | `--release-masters`, OVL frame compiled for the same seam | 2/2 PASS (codec1, codec2) | 8/8 FAIL as required | PASS |

## What changed vs the bound_r8 pass (qc_tok_1024/link, 10-24)

- **tp8.** The collective lanes got longer in the re-plan, which pays for the 405-um stations: COLL_LS 389 -> 407 (capacity
  bind 391), F2/F3/F4 relays 7/8/8 -> 11/11/11, lanes 10 -> 21/20, LX 12/4/12 -> 23/4/22. The static MU calendar was
  recompiled at LS 407 (`tp8/mu_cal_ls407.json`). At LS 389 the same call reproduces the committed `mu_cal_ls389.json`
  apart from its "source" note. The compile reports no collision.
  Cycles: AR256 E 297 -> 315, argmax E 449 -> 467, token all-reduce 36x2xE 21,384 -> 22,680 (+1,296 cycles = +1.08 us
  per token at 833 ps), token_span 58,633 -> 59,947. The tp8 bench and the collective RTL are identical in the two
  assemblies, so every cycle change comes from the new lane/relay constants. The calendar's compiled spans also moved:
  AR256x2 back-to-back 1,559 -> 1,082 (the second AR now starts 256 cycles after the first, where it previously started
  751 cycles after), and the MU window 38,149 -> 36,780 (user 0 alone 35,238 -> 30,586). I record these as measured; I
  did not analyse why the compiler places the second AR earlier at LS 407.
- **xdie / ovl4u.** The seam constants did not change (XDIE_SEAM_C 2,2,2,3,2,2; TXDP C/K unchanged), and the bound pair
  image rebuilt by `tools/qwen_split/d2d_cal_image_production.sh` is byte-identical to the 10-24 image. Cycles are
  identical: xdie round trip 1,887, period 7,056 per layer; ovl4u 13,708 tok/s aggregate. Their verdicts confirm the new
  assembly against unchanged seam constants.

## Failed attempts (logs kept, run data deleted)

1. tp8 first run: OOM-killed by ot-run at my `--mem 48` (6 cases at a time peaked at 48.0 GiB;
   `logs/otrun_tp8_fail1_oom48.log`). This was my memory estimate, not a bench or design problem. The rerun used `--mem 100`.
2. ovl4u first run: every config hit BUILD_FAIL with `MODMISSING d2d_sram_1r1w_64x137_m1_r2c2_p192`
   (`logs/ovl4u_fail1_stale_bench.log`). This is a bench-staging issue. Main 93985ba5ee ("F5: use real p192 replay SRAM
   master") renamed the macro that `ot_qwen_d2d_safe7.sv` instantiates, and main dc11eabc33 changed the release tb's
   record-witness check together with the RTL (kind-14 records only). The 10-21 copy of the release bench that the fixture
   commit (claude/tok-func2-qw-1021) carries is stale on both points. The fix is to use the assembly's own
   `rtl/test/qwen_split/{run_d2d_ovl_mu_rel.sh,tb_d2d_ovl_mu_rel.sv}` (`ovl4u/BENCH_FROM_ASSEMBLY.txt`). No check was
   relaxed: the macro's ports and cycles are unchanged per 93985ba5ee, and all 8 mutants still fail on D2DOVL checks, not
   on build errors.
3. tp8 collector: `stage_link.collect.py` reads `tp8/fx/lanes/coll_lane_latency.json`. The 10-24 run dir carried a
   hand-written record of the bench lanes. This run writes the same record from the regen constants (`tp8/lanes/`).

Wall times on intel1: xdie ~9 min, ovl4u ~7 min, tp8 ~16 min (memory limit 100 GB).

## Reset (owner decision 13, wavefront)

The re-plan declares `reset.release = wavefront`, but the bound top does not realise it yet. `qwen_compute_bound_top.sv`
still fans the die `rst_n` to the `arst_n` of all 377 partitions, and the bind recipe keeps the as-built
qfd_rstsync/qfd_rstseq sources. The link benches are partition and link RTL with their own reset, so their timing
assumptions are unaffected. The published per-partition release offsets (`reset_tree.py offsets`, root sl_W0_ctl,
max release 128 cycles) are recorded in `../xt1_meth/reset_offsets_meth.json`. They apply when the bind or kits carry the
wavefront, together with the start broadcast (decision 13c).
