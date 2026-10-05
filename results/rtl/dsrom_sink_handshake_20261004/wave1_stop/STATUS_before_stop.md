# dsrom-dspark (Claude -> handed to Codex 2026-10-03) -- DSpark MTP RTL on the V4.1 decode core
Branch claude/dsrom-dspark-rtl-20261003 (pushed; local worktree /home/ubuntu/dsrom-dspark-rtl-20261003 on the main host).
src/ = rsync of that worktree at 2f20d5161 (+ results/abi3 oracle json); pylib/ = tokenizers (abi3) for python3.14:
run every tool with PYTHONPATH=$PWD/pylib, OT_SCRATCH=$PWD/tmp (see launch.sh).

## What passes so far
- ISA model of the MTP programs at HEAD (STEP + ITER, gamma 5, m = 1): tokens == golden non-speculative greedy and
  committed logits bit-exact, for gold4/oracle8/spread6 x dspark/forced, under legacy, he,me and att,he,idx,me,su
  R-ARITH (logged in out/*.log "isa True True").
- As-built one-position baseline on the MTP bench (main host): rom_m1_plain PASS, 358,294 / 381,499 cycles per
  token (gold4 / oracle8).
- Caller of Codex protected accept leaf (rtl/hdc/ot_hdc_mtp_accept_caller.sv) unit bench vs ot_hdc_accept:
  48 steps, accept lengths 0..5 all equal; dropped-TOKX mutant refused (tests/test_hdc_mtp_accept_caller.py).
- NO full-core MTP RTL run has finished yet (each is ~10-30 M cycles at ~50% of a core: hours).

## Running (detached)
wave 1 (launch.sh, started ~04:30Z): out/rom_m1_g5_gold4 (as-built, +mutation, +ISA checks), rom_m1_g5_o8s6,
x_heme (v41x he,me, ot_hdc_accept, 3 prompts, +mutation), x_heme_guard (same with ACC_GUARD=1 protected leaf),
x_all6 (six re-specified units; may OOM/fail at Verilator -- a local attempt was SIGKILLed; wave 2 retries --fp dpi).
wave2.sh (auto-starts when wave 1 exits): x_heme_g3, x_heme_g1, x_heme_guard_n24, rom_m1_plain, x_all6dpi;
exit codes out/<part>.rc, manifest.txt.
Also on the main host (/tmp/claude-1000/.../scratchpad/ds/*.log): older copies of the same parts (redundant).

## Next steps
1. When out/<part>.json land: copy to the worktree results/rtl/dsrom_dspark_rtl_20261003/parts/, run
   python3 tools/dsrom_dspark_rtl_record.py (summary.json: per-check pass/fail, cycles per draft / verify+accept /
   step / emitted token, ratios vs the model), finish REPLAY.md (already drafted there), commit + push.
2. A failing part: runs[].rtl.tail in its json; rerun the image dir with +TRACE (images reused from wd/ via --workdir).
3. Known gaps: accepted lengths 2 and 4 only reached by the ngen-24 forced run; idx (pooled indexer) unit not
   covered by the MTP bench; acceptance on the reduced vehicle is functional only (seeded DSpark weights).

Codex Erdos takeover: source successor 1f94c92b8 in clean detached successor-1f94c92b8/.
Wave1 controllers222300..222304 and all live RTL preserved. Old CPU-golden queue
waiter297056 terminated while waiting; original script retained as wave2.cpu-golden-held.sh.
Replacement wave2cached-1f94c92b8.sh waits for the same wave1 PIDs then runs cached
x_all6dpi via admit.sh20, compile16, no inference, retained objects/streamed logs.
Gamma3/gamma1/guard-ngen24/plain queued parts held pending Claude local GPU exact
image generation path (current campaigns call NumPy golden when images absent).
No full-core MTP terminal result yet; previous REPLAY exactness statements corrected
on successor branch. Original sources/campaigns/failed evidence remain untouched.
Archimedes consumes existing start/token/pos/entry -> done/next_token/acc_n/acc_tok;
ACC_GUARD default0, NSLOT8 MP1. No duplicate DS fullsystem launched.

## 2026-10-04 Claude: wave-2 images + wave-1 liveness
- Images generated on the GPU host (the golden is NumPy; it has no GPU backend; nothing ran on EPYC): /srv/opentallas-scratch/claude/dsrom-dspark/wd-w2-gpuhost-20261004
  (7 images: g3 gold4/oracle8 x dspark/forced, g1 gold4 x2, g/ guard n24 oracle8 forced). Every image: ISA tokens ==
  golden and committed logits bit-exact; 147 file SHA-256s re-verified on EPYC against manifest-*.json.
  Reproducibility: the GPU-host regeneration of wd/i_gold4_{dspark,forced}_g5_n12_heme is byte-identical to the
  EPYC wave-1 images (all hex, run.args, prog_tags; isa.json differs only in "seconds").
- gamma<5 needed a writer fix: draft rows >= gamma are emitted as me_nout=0 ME ops on the live op's weight base,
  and hdc_images_v41x.me_ops asserts one shape per base. tools/dsrom_dspark_make_images.py drops zero-row ME ops
  before calling the writer, which stays byte-identical (pinned). A gamma-5 program has none, so its output is unchanged (verified).
- n24 forced oracle8 accept lengths are [1,3,1,3,...]: lengths 2 and 4 are NOT reached (STATUS "Known gaps" was wrong).
- rom_m1_plain NOT rerun: the main-host record (gold4/oracle8 ngen12 PASS, 358,294 / 381,499 cyc/token) has all 38
  input_sha256 identical at 1f94c92b8.
- WAVE 1 IS DEADLOCKED. Method: read-only /proc/PID/mem sampling. Offsets were found with a traced probe of the SAME binary
  and checked against a traced control. All 16 MTP sims (rom_m1_g5_gold4, rom_m1_g5_o8s6, x_heme, x_heme_guard,
  x_all6; as-built and v41x cores; every prompt and drafter) sit at pc=4386 for >=5 min while cycles advance
  (x_heme 30-46 M cyc, rom_m1 293-303 M cyc vs ~25 M expected). pc 4385 = ITER L40.hc_ffn XU OP_SINK dslot 1. It issues
  back to back after dslot 0's op (4384). 4386 (dslot 2) never issues, so the XU is stuck in S_SKW.
  Likely cause (NOT unit-proven): ot_hdc_sinkhorn_mc busy = ubusy||ov stays high through the 7-cycle out_valid
  window. ot_hdc_v41_xu raises sk_in in S_SK1 about 5 cycles after the previous done and clears it while busy, so the request is
  lost and done never comes. STEP never issues Sinkhorn ops back to back (plain passes); the op-major ITER merge does.
  TIMEOUT is at 1e9 cycles, days away.
- wave2-gpuhost-HELD.sh is prepared but NOT started: every MTP image runs the same ITER and would hang the same way.
  Note that the wave2cached waiter starts x_all6dpi (same ITER) as soon as wave 1 exits. Wave 1 was not killed by Claude.
