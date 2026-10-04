# hbm-system-rtl: STATUS (handed over to Codex, 2026-10-03)

Branch: claude/hbm-system-rtl-20261003 (pushed). Records: results/rtl/hbm_system_rtl_20261003/ (REPLAY.md, *.json).

## Results so far (all reduced shape, default-off RTL under rtl/gpu_sys/)
- Qwen3 HBM system top (2 dies TP2 x 2 SIMT SMs, L2 slices, HBM partitions, CDC, NVLS collectives, cmdproc, ot_host_if rings):
  PASS. 18 decode steps (16 teacher-forced prompt + 2 generated) bit-exact vs tools/hdc_golden.py (groups=256, TP2);
  CQ tokens 1073 382 93 = oracle. Also PASS with Nash's W2 exact completion in every HBM partition (USE_W2=1).
  Records: qwen_e2e.json, qwen_e2e_w2.json.
- DS V4.1 HBM lowering (tools/gpu_sys/v41_hbm.py, chunk8 contract): bit-exact on the functional machine at positions 0-3,
  every layer + token (2815 3537 2047 1968). RTL SM supports it (block-scaled TC, div/sqrt, FMNMX, E2M1): SM unit gate 12/12 PASS.
- Unit gates PASS: simt_sm, cdc_fifo, coll, memsys (+W2 option), host_bridge, unit_small (cmdproc + lint).

## Running (detached, ot-epyc1tb; leave alone)
- /srv/opentallas-scratch/claude/hbm-system-rtl/sysv  : DS V4.1 RTL e2e, 3 teacher-forced positions (prompt prefix 3, ngen 1),
  sim PID 240052 (single-thread). Log sysv/case/sim.log (stdout buffered until the first STEP line, which $fflush-es);
  record -> v41_e2e.json. Manifest: MANIFEST.txt.
- /srv/opentallas-scratch/claude/hbm-system-rtl/sysv_t8: same, Verilator --threads 8, sim PID 348830 -> v41_e2e_t8.json.
  Expected steps: (0,2815) (3563,3537) (3745,2047). Note: ~113 MB/die HBM image (FP4 expert lines 1 of 8 lanes active).

## Not done / next steps (for Codex)
- DS: finish the RTL e2e above; copy records into the branch's results dir; DSpark: v41_dspark.py lowering of the
  drafter/verify commands of rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv (claude/dshbm-dspark-rtl-20261003, 525a751c8) was started
  by a subagent (state: tools/gpu_sys/v41_dspark.py in the local worktree if present, uncommitted) + a ctl->cmdproc bridge RTL.
- Qwen canonical launcher helper: subagent state/report in /srv/opentallas-scratch/claude/canonical-qwen-helper/ and
  codex_notes.txt (if it wrote one). Not verified by me.
- W4 (Euclid) RTL was not on any origin branch when checked; W6/W5/W10 not integrated into this system top.
- HBM controller/PHY remains the behavioural ot_hdc_hbm_model; weight load into HBM is a load-time image (no host DMA path).

## DSpark lowering (tools/gpu_sys/v41_dspark.py, pinned; successor tools/gpu_sys/v41_dspark_connected.py)
The per-column state slot stride 4608 B is 36 B short of its contents (X 2560 + PRE 16 + CTR 4 + SEL 128 + NSEL 4 +
MH 3 x 640 = 4644 B): the last main-hidden part overwrote the next slot's first residual words and broke the last
verify column.  On main this is fixed by the additive successor v41_dspark_connected.py (stride 4736, original file
pinned; its gate: results/rtl/ds_hbm_connected_20261003/reduced_functional_six_columns_r2.json, gamma 5, PASS).
Independent confirmation 2026-10-04 (v41_dspark_check_{forced,dspark}.log, run with the stride grown in place to
4672 in a branch copy, gamma 4, ngen 8): forced drafter tokens OK, logits bit-exact, passes equal, accepts [0,1,2,3],
3,472 launches; real DSpark drafter tokens OK, logits bit-exact, passes equal, accepts [0]*7, 6,095 launches.
The in-place edit was not landed (the successor pins the original).  --emit and the RTL run are not done.

## Multi-thread determinism (2026-10-04)
The DS V4.1 system run was exact single-threaded (v41_e2e.json) and wrong under Verilator --threads 8 at every step.
Cause (RTL race, not a Verilator bug): ot_gpu_simt_sm.sv wrote bd_xd (the block-scaled X-tile write data) with a
BLOCKING assignment in its clocked block, and u_bdtc's xmem samples it in another clocked process on the edge after
issue.  When an X write is pending on the edge a TCXB/TCXE issues (36 times per SM in every layer kernel, counted by
the bench trace), the result depends on process order; single-thread Verilator orders it one way, --threads leaves it
unordered.  Trace (+define+GPU_SYS_TRACE, per-SM hash of every global store and collective at each kernel end):
original --threads 8 first differs at kernel 1 (layer 0) on all four SMs (cycles 361,379 vs 358,365), embed equal.
Fix: bd_xd is a register (bd_xd <= the clocked block's own temporary bd_xn); the clocked block also no longer shares
the comb LSU block's loop temporaries jj/lj/bi (harmless in Verilator, but a race in any event simulator).
Fixed RTL under --threads 8: PASS, tokens 2815/3537/2047, 19,394,782 clk_sm cycles = the single-thread record to the
cycle (v41_e2e_threads8.json).  Fixed single-thread trace equals the original single-thread trace and the fixed
--threads 8 trace on all 114 kernels both had reached (cycles and hashes); the fixed single-thread full run
(det/fx_t1) was still running on a loaded host when this was recorded.
Minimal repro: rtl/test/gpu_sys/repro_verilator_threads_blkseq.sv.  Runs: ot-epyc1tb .../hbm-system-rtl/det/.
