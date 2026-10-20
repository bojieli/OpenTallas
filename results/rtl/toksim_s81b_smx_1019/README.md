# TOKSIM-S81B/SMX: attention softmax chain on the S81 p4l-MU release RTL (10-19)

**PASS, measured-release-RTL, bit-exact.** The release softmax share `ot_s81_su_sms` (the `u_sms` in every regional
service slice `dsdv_svc_rs`) runs a full decode softmax at production shape. All 16 heads run lockstep. T is 128 (L0/L1)
or 640 (L2-L39 = 128 window + 512 selected). The cycles printed at the share pins are below.

| DAG op | old per instance | measured (T 128 / T 640) | definition (cycle 0 = first score row at the pins) |
|---|---:|---:|---|
| attn.max | 186.9 / 221.6 | **28 / 60** | first score row -> root max out |
| attn.exp | 236.3 / 289.7 | **92 / 124** | root max -> last e row at the pins |
| attn.den | 72 / 88 | **32 / 32** | last e row -> row sum at the root |
| attn.sink | 196 | **29 / 44** | row sum -> o_den at the pins (lt 3 / 6) |
| attn.normalize | 244.9 | **85** | first P.V row -> last o row at the pins (+ 132 priced SO->XS tail, see below) |
| attn.gather | 808-819 | pending | not measurable on the existing bench |

max + exp + den + sink = se_chain (181 / 260), so the parts add up with no gap and no overlap. AR critical:
41,399.8 -> 13,642 measured (+5,280 priced tail = 18,922).

- Golden: `tools/dsrom_su_softmax.reference` (hdc_golden_v41) on the real L0 / L2 operands of the 1M token
  (`su_cases_v2_ildr.pkl`). `tools/s81_su_sm/toksim_smx_prep.py` asserts it equal to the chain checks (`cases.json`). There
  are also 4 random stress cases. Every e row (FP32 x16) and every o row (BF16) is bit-exact on all 16 heads (`runs/`).
- RTL: all 25 executing files are blob-identical with 19bf4121e and ceaed19c4 (`RELEASE_BLOBS.txt`). Verilator is 5.050.
  Builds: flat16 (with internal probes), smt16 (the hardened-tile views `dsfd_su_t_*`, pin cycles identical) and flat2.
- In-context check: the release 16-slice `dsdv_svc_rs` bench was traced (`svctr/`, the TOKSIM-S81/SU exe). For every slice,
  last SE row -> first e row is 106 cycles (full1m T 640 and short300 T 428). That equals the standalone se_pin, so no
  wire stage sits between the slice score assembler and the share.
- Why the old numbers were much larger: they came from the S58 hub SU, with BCAST 22 / RET 15 wire stages and hub-slab
  stations on every op. On p4l-MU the share is local to each slice.

Owed / not folded:

- mu4c has no SM target storage. The svc_rs SM face `w_*` is open (LEAD2-S81 INBOX [BIND 17:40]). GEN mu5 (SMWIRE, not the
  release) adds the SO target, with the priced edges "last SO write -> last XS arrival 115 E / 132 W". The record carries
  132 on normalize as `tail_priced` (graded priced), so that transport is not dropped.
- attn.gather is pending. The svc_rs bench issues SEL_IDS / ROWS frames host-paced (row requests at cycles 55..3162, GO at
  5016) and models the HBM latency. A vehicle that issues SEL_IDS at the compiled cycle with fixed HBM latency is needed.
- Bench weakness: `tb_toksim_smx` compares with `!=`, and a golden X compares false. job1 ran an empty case glob and printed
  a vacuous `PASS nv=0` (`job1_build.otrun.log`). Only run2 is used, where nv is 8 / 40 and checks = NH x (nv + 32). No
  mutant witness was produced.

Reproduce: `tools/s81_su_sm/toksim_smx_job.sh` (build) and `toksim_smx_run.sh` (cases) under ot-run on a host with
/srv/opentallas-scratch/claude/toksim-s81b-smx. Element record: `SMX.json`.
