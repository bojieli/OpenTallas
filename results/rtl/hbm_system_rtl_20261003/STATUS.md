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
