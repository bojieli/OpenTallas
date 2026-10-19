# HBM-NEXT-P3-UNITS: non-SM units at P = 3 (2026-10-19)

The owner's decision (10-19, 0le) sets the next-release HBM die to P = 3 SM accumulator lanes with a shared 3-lane x store. This lane checked every non-SM unit for a dependence on P. The SM tile itself belongs to lane P3-SM.

Branch: `claude/hbm-next-p3units-1019`. Benches ran on Verilator 5.050 on the fleet (ot-epyc4), from git-archive bundles `6a5a54688` and `f7906c728` (schedule-model fix).

**P vs N.** P is the number of SM accumulator lanes, i.e. the query lanes that share one weight or KV stream. N is the number of rows in a record (positions or users). N stays general (1..6), and no unit below sizes anything from N = P.

## Audit

| Unit (RTL) | Depends on P? | Action |
|---|---|---|
| ATT4 (`rtl/hbm_next/att`: issue, slice, smerge, spvm) | **Yes.** Query lanes NL = P: one KV-line union stream feeds NL lanes. At P = 3, MTP's 6 positions are 2 full passes, and 4 users take 2 passes (3 + 1, CMTP). | **NL defaults to 3; NL stays generic.** issue / slice / smerge already took NL as a parameter (1..4). spvm hard-coded 4 and now takes NL (3..4): lanes 0-1 on the N face, lanes 2..NL-1 on the S face. The mask word keeps the fixed CMTP R10 layout at every NL, so the plan record does not depend on P. That layout is 4 bits per row: lane l of row 16a+i is bit 4i+l, and mw_data is 64 b. MUT 4 (lane^1) is guarded for odd NL. The benches take `--nl`, default 3. |
| FUSED (`rtl/hbm_next/fused`) | **No.** KX is the number of x row slots. Row p+KX reuses slot p, so KX is set by how long row p's r takes to come back. It is not set by P (it is a power of two). | None. KX = 4 at rgap 0 stays the design point (KX = 2 needs rgap >= 64). The 128x256 x-store macro holds KX x NM = 80 words at either P. The "P = 4 sizing assumption" is dropped: there was none in KX. |
| VM (`rtl/hbm_next/vm`) | **No.** Capacity grows with N (resident columns, 2^19). The SM writer `smw` (d4g `..._lanes4`) has write lanes per quadrant, not SM accumulator lanes. | None. A P-lane publish gives P lane-major results at +8 edges a lane through the same writer. The beat count is priced by CMTP; no RTL changes. |
| IDX / IDXN / IDXQ (`idx`, `idxn`, the idxq branch) | **No.** N_Q counts KV quadrants. NP counts key lines in the key buffer. The query rows are N. | None. |
| SU / SUDMA / SFU (`su`) | **No.** Rows are N. The "P" in `ot_hnx_sfu_rowstep` is the row period, not the lane count. | None. |
| COLL (gq train, cxdl5) | **No.** Payload is xN. L = 5 counts delivery lanes, not P. | None. |
| HC (`hc`) | **No.** Rows are N, with II 250 per added row. W counts MAC lanes. | None. |
| ARGMAX / DMA KVWB / QDQ | **No.** Rows are N. LP = 8 is the number of vector lanes. | None. |
| tools: `isa_rows.py` P_LANES = 4, `plane_compiler.py` | Yes (compiler) | Owned by P3-CMTP. They set P_LANES = 3; ATT plan mode then refuses n > 3. |
| tools: `die/plan_p4.py`, `pin_plan_p4.py`, `clock_plan_p4.py` | Yes (floorplan; P-bit lane mask pins) | Owned by P3-DIE. |

## ATT4 at P = 3: benches (Verilator 5.050, ot-epyc4, `att4/`)

These use the production A1 variant: the shared merge, LV 3. Each run checks bit-exactness per lane against the single-query goldens. It also checks that every lane's cross-SM merge equals `att_pv`.

| Run | Union lines | Ops | QK span max | PV span max | Union rows max (job) | Same lanes run one at a time (QK / PV) |
|---|---|---|---|---|---|---|
| sh_s00 (full overlap) | 642 | 160/160 PASS | 421 | 371 | 34 | 1,089 / 1,017 |
| sh_s03 | 809 | 160/160 PASS | 538 | 523 | 55 | 1,089 / 1,017 |
| sh_s10 | 1,083 | 40/40 PASS | 667 | 643 | 72 | |
| sh_sdj (disjoint = users) | 1,666 | 160/160 PASS | 859 | 835 | 96 | 1,089 / 1,017 |
| sh_k500 / k490 / k486 (flush paths) | 794 / 776 / 616 | 160/160 PASS each | 538 / 536 / 421 | 507 / 491 / 371 | 55 / 53 / 34 | |
| nl4_s03 (generic-NL regression at 4) | 865 | 40/40 PASS | 597 | 531 | 58 | identical to the step-4 P = 4 run |

- **Throughput form unchanged:** an op costs a fixed ~113-127 cycles plus 7.8 cycles per union row. At P = 3 a job has fewer union rows: 55 vs 58 at sigma 0.3, and 96 vs 128 when disjoint.
- **Publication path** (`ot_hnx_att4_spvm` NL 3, PUBLISH 1): pub_m0 576 nodes and pub_s2 864 nodes, both bit-exact.
- **Schedule model** (`att4_smerge_sched.py --nl 3`): 20,000 trials, 149,715 nodes, 0 faults. Worst node latency is 6 turns (48 cycles), against 8 turns at NL 4. The illegal-record negative control faults.
  - The control was hard-coded to lane 3. It now uses lane nl-1.
- **Mutants, all FAIL** (witnesses in `att4/witness/`): smerge sh_smut1/2/3/4k; issue sh_imut1/2/3/4; publication pub_m1..m5. The smut4 case at top-k 512 is still not exercised, as at P = 4.

## Area for DIE (`synth/area.txt`; yosys 0.68, ASAP7 RVT TT, same flow at both NL)

| spvm | NL 3 | NL 4 |
|---|---|---|
| cell area | 23,587 um2 | 28,954 um2 |
| flops | 47,020 + 7,261 async | 61,049 + ~7.3k |

- NL 3 / NL 4 = **0.815**.
- Applied to the gated P = 4 figures (+4.21 mm2 cells / +5.87 mm2 outline per die, at 512 columns): P = 3 gives **+3.43 mm2 cells / +4.78 mm2 outline**, i.e. **-0.78 / -1.09 mm2** vs P = 4.
- Tile outline at util 0.55: about 226.8 x 226.8 um, down from 250.56.
- ATT4's issue x stores and its tcpv columns belong to the SM BF16 column, so they are counted in P3-SM's tile.

## Open

- **P3 spvm tile kit `hnx_rp3a3_spvm`: not made.** It is a critical attention tile (report only). Its kit should copy `physical/hbm_next/att4/hnx_rp4a4_spvm.json` with NL 3, std_area ~27k, outline 226.8, witnesses `units/p3/att4/witness/`. Gate it after the step-4 P = 4 gate (pid 2534186) reports, so that gate's timing lesson carries over.
- **ATT4 production front** (live agent, worktree `hnx-att4pf-1019`):
  - `ot_hnx_att4_plan` and `tb_hnx_att4_plan` default to NL 4.
  - The slice's `mw_data` port is now 64 b. It is the same R10 layout the plan loader already writes.
  - That agent should set NL = 3, and fault on a mask bit for a lane >= NL in the plan loader. The issue ignores such bits.
