# Die-level RTL bench of the generic HBM die (stream hgi-e2e, 2026-10-09)

The question: does one token layer run through the generic HBM die (r25 / R25G with HGI-1) in RTL? The bench is
`rtl/hbm_accel/generic/e2e/tb_hgi_e2e.sv`. It runs the simulator's real program for that layer through the die's
command path. Each unit is real RTL where RTL exists on main. Where it does not, a labelled replay stub stands in.

- **Harness:** `tb_hgi_e2e.sv`, `hgi_e2e_slots.sv` and `hgi_e2e_dpi.cpp`. The driver is `tools/hgi_e2e/run.py` (prep, script, report).
- **Golden export:** `tools/hgi_e2e/export.py`.
- **Source under test:** branch `claude/hgi-e2e-20261009` at 18685d362, which contains main 860000448.
- **Overlays:** where a run carries a suffix such as `_685ae3`, it overlays files from `claude/hgi-adapters-20261009` fc5794beb. Those files are not on main yet: the SU adapter DIVB opcode fix, and the FUSED HC_PRE_NORM / HC_POST micro-sequences.
- **Where the runs ran:** ot-epyc4, Verilator 5.050, under `/srv/opentallas-scratch/claude/hgi-e2e/out_18685d362`.
- **Per-run records:** in `runs/<run>/`: `run.log`, `e2e_records.txt` and `report.json`.

## What the bench does

**Command path.** The host writes over AXI-lite to `ot_hgi_loader_cp`. That covers the full 64-word model descriptor through the CFG window, then CFG_COMMIT, the doorbell, and the completion FIFO read-back. The loader link feeds `ot_hgi_cp_die`. Inside it, `ot_hgi_cp` holds the config path and the v1.0 sequencer. The die block also carries:
- the record-ring fetch on loader lane 1;
- VM packet reads;
- per-unit credits;
- the coll, quant and idx record buses.

**Unit slots.**

| Unit | Real RTL in the slot | Models around it |
|---|---|---|
| DMA | `ot_hgi_dma_record` + `ot_hgi_dma_mover` | kport lane to the HBM model; VM packet client |
| SU / SFU | `ot_hgi_su_record` / `ot_hgi_sfu_record` + the reference stream unit `ot_hdc_v41x_vec` (N64 / M64 / LV7) | the VM model's synchronous ports |
| FUSED | `ot_hgi_fused_record` + its mover + its own vec | QDQ is forwarded to the quant slot |
| QUANT | `ot_hgi_quant_unit` | VM packet client |
| IDX | `ot_hgi_idx_unit` | VM packet client |
| COLL | `ot_hgi_coll_ep`: record binding, GX11 decoder, PSG TU endpoint, gather bypass | the SU-quarter inject and deliver data path, and the switch tier with the other ranks. This is the single-rank method of `tb_hbm_accel_tu_endpoint`: peers' partials carry their exported A, so this die's owned slice is reduced by the RTL tree from real operands; other owners' results are golden placement. |

**Stubs.** SM, ATT and HC have no record-driven peer on main, so they always run as stubs. A stub holds the record for the simulator's unit cost, then applies the simulator's golden writes of that record. A stub computes nothing.

**Memories.** VM and HBM are both models:
- VM: 262,144 words. Packet responses come back in order after VLAT = 6 cycles, with up to 4 outstanding.
- HBM: sparse. Ring fetch latency is FLAT and kport latency is KLAT; both are 40 cycles unless a run says otherwise.

**Golden.** The golden is an `hgi_sim` run on the released weights. Rank 0 is captured record by record: the effective operands, the VM and HBM write sets, and every rank's COLL contribution.
- **Qwen3-8B L0 at P8191, TP4:** 34 dispatched records. The layer output equals `qwen_r25`.
- **DS-V4.1 L0 at 1M, rank 0 of 96:** 91 records. `ds_native` passes against the released golden.

The vehicles' metadata and the SHA-256 of their binaries are in `vehicles/`.

**Checks.**
- Every CP dispatch must equal the golden record: unit, 128-bit header, and the effective base and n of every operand.
- When a real unit retires a record, all of that record's golden VM and HBM writes must already be present, bit for bit, with no stray write.
- After every unit has drained, the whole VM must match the golden final VM, every golden HBM write range must match, and the completion token must match.

## Matrix: unit × real or stub × exact

| Unit | Qwen L0 (P8191, TP4) | DS L0 (1M, rank 0 / 96) | Notes |
|---|---|---|---|
| CP: config, sequencer, fetch, dispatch | real: **34/34 dispatches exact**, token exact | real: **91/91 dispatches exact**, token exact | Needs the F1 workaround (CFG CRC word) |
| DMA (record + mover) | real: **9/9 exact** | real: **8/8 exact**, including KVWB_DS | Slow: F6 |
| SU (adapter + reference vec) | real: **10/10 exact** | real: **33/33 exact**, with the fc5794beb DIVB fix | Main's adapter refuses DIVIMM (F8). The die's `hfd_su` is not bound to records (D1). |
| SFU (GLU) | real: **1/1 exact** | n/a: DS has no SFU.GLU in L0 | — |
| FUSED (front) | real: **4/4 ROW_NORM exact** | real: QDQ_FP8 forwarded, **1/1 exact**. HC_PRE_NORM is **refused** (F7). | Scratch is excluded from the checks |
| QUANT (QDQ) | n/a | real: **1/1 exact** (kv_row_qdq) | — |
| IDX | n/a | real: **1/1 exact** (route.top6, TOPK k6 asc) | INDEX frames are not on L0 |
| COLL, die build (PSG PFMAX 64, BF16 1) | real: **FAULT** (mode_error, pf 256) | real: **FAULT** at the first ALL_GATHER (pf 80) | F4, F2 |
| COLL, what-if PFMAX 512 (Qwen also BF16 0) | real: **2/2 exact** | real: **13/13 exact** (12 bypass gathers + GROUP_REDUCE_MCAST s 8, BF16) | Built from a copy of `ot_hgi_coll_ep`. F3 is the cost. |
| SM | stub (4) | stub (27) | The RTL exists (adapter, x-load, pub, smh), but a 32-SM die build is not tractable in Verilator. Exactness is covered on `tb_hgi_sm_e2e`. |
| ATT | stub (4) | stub (2) | No attention controller peer (D4) |
| HC | n/a | stub (2) | No HC unit wrapper |
| ARGMAX | n/a: not in L0 | n/a | Head vehicle not built (STREAM producers are stubs) |

**All real units together:**
- **DS L0:** DMA, QUANT, IDX, SU, COLL (PFMAX 512), plus the SU fix. **PASS:** 56 real records exact, 91/91 dispatches, 86,320 cycles.
- **Qwen L0:** DMA, SU, SFU, FUSED, COLL (PFMAX 512, FP32). The run is still going at the time of writing; see the COLLECT section of `hgi-e2e.log`.

## Cycles against the simulator (doorbell to completion, 1.2 GHz cycles)

| Run | Qwen L0 | DS L0 |
|---|---|---|
| Simulator S2 (`hgi_sim.timing`; DS uses NativeCost) | 32,957 | 12,087 |
| All stubs, FLAT 40 | 32,960 | 16,155 |
| All stubs, FLAT 8 | — | 13,644 |
| All stubs, FLAT 104 (measured HBM first access) | 33,682 | 38,134 |
| Real DMA | 145,843 | 42,257 |
| Real FUSED | 101,026 | — |
| Real SU (+ SFU) | 35,525 | 16,155 |
| Real COLL, what-if | 32,714 | 58,694 |
| All real (what-if COLL) | pending | 86,320 |

Per-unit busy time (dispatch to retire) in RTL, against the simulator's unit cost:

| Unit | Vehicle | RTL busy | Simulator cost | Ratio |
|---|---|---:|---:|---:|
| DMA | Qwen | 131,864 | 754 | 175× |
| DMA | DS | 29,761 | 747 | 40× |
| FUSED ROW_NORM (gain loads by the mover) | Qwen | 68,674 | 600 | 114× |
| COLL | DS | 50,570 | 5,317 | 9.5× |
| COLL | Qwen | 2,458 | 2,700 | 0.91× |
| IDX | DS | 1,267 | 283 | 4.5× |
| SU (reference vec, N64) | Qwen | 6,062 | 1,336 | 4.5× |
| SU (reference vec, N64) | DS | 2,909 | 3,230 | 0.9× |

The all-stub column checks the CP: with the stubs at the simulator's costs, the RTL CP reproduces S2 on Qwen. On DS it is fetch-bound (F5).

## Findings

**F1 — CFG window (owner: `ot_hgi_cp`).** Model-descriptor words 62 and 63 cannot be staged, because pair 31 is the CFG_COMMIT address (`c_wr` excludes the commit). Every real descriptor therefore fails with E_CRC. The CP then keeps image_base at 0 and executes 4,096 CTL.NOP sectors of empty HBM before it reaches the image: 92k cycles measured with +CFGFIX=0.
- Proposed fix: one line, `c_wr = we_q && win`, so the commit write also stages 62 and 63.
- The harness deposits those two words (+CFGFIX=1, the default) as that fix would.

**F2 — COLL result format.** `ot_hgi_coll_ep` builds the PSG endpoint with BF16 = 1, and ALL_REDUCE_SUM ignores O.fmt. Qwen's all-reduces have an FP32 O, but the die would deliver `to_bf16(sum)`. A per-record result format is needed. The FP32 what-if is exact.

**F3 — COLL ALL_GATHER cost.** The bypass sends the whole A row from every rank (pf = A.n × bits / 512), not the rank's even-split slice.
- The 5,120-element DS gathers deliver 96 × 320 flits.
- DS COLL busy time is 50,570 cycles against 5,317 priced.
- The SU deliver-side slice selection exists neither in RTL nor in normative text; the harness model applies spec 6.7.

**F4 — COLL capacity.** The die's PSG endpoint is built with PFMAX 64 flits, which is 1,024 FP32 per contributor. Qwen's 4,096-element all-reduces fault (mode_error), as do the DS 1,280, 2,304 and 5,120-element gathers. With PFMAX 512, everything is exact.

**F5 — CP fetch.** `ot_hgi_cp_die` keeps one 32-B ring sector in flight on the loader lane (`fq_busy`), although `ot_hgi_seq` issues up to NOS = 8.
- On DS L0 stubs, the run grows from 13,644 cycles at FLAT 8 to 38,134 at FLAT 104 (S2 is 12,087).
- Qwen hides this behind its SM records.
- Fix: keep NOS sectors in flight with in-order responses, or use longer bursts.

**F6 — DMA mover rate.** The mover handles one element every 4 edges, plus one kport round trip per sector miss: its documented boot-path rate. It dominates both real-DMA runs, and Qwen's FUSED through the gain loads. The PS stream fork is the fast-path successor that is still owed.

**F7 — FUSED HC_PRE_NORM gain format.** `ot_hgi_fused_record` (fc5794beb) requires B to be HBM BF16. The DS lowering (`ds_native`) emits the norm gain as HBM FP32 with 5,120 elements, so the record is refused (rec_fault at record 0). The compiler and the adapter must agree on one gain format.

**F8 — SU DIVIMM.** Main's `ot_hgi_su_record` refuses DIVIMM (DS q_norm.rs and kv_norm.rs). The fix (fc5794beb) is not on main; with it, 33/33 DS SU records are exact.

**Program note.** The Qwen layer program's CTL.END has wait mask 0. The completion can therefore precede the layer's last record (row_scale_down+residual retires about 60 cycles later). The bench drains every unit before its final checks.

**Die gap.** `ot_hgi_cp_die` exposes only valid / ready / done / fault for units without a record bus (ux_*), and its unit-4 bus carries A and O only. The bench taps the sequencer's dispatch registers (`cpd.u_cp.d_*`) for the record payload. A die-level record bus is owed for SM, SU, SFU, ATT, DMA, HC and ARGMAX, plus the FUSED B and C operands.

## Reproduce

```
python3 -m hgi_e2e.export qwen|ds ... --out EXP              (tools/, on a host with the checkpoint)
python3 tools/hgi_e2e/run.py prep EXP
python3 tools/hgi_e2e/run.py script --vehicle V --real dma,su,sfu,fused,quant,idx,coll [--g COLL_PFMAX=512 ...] --out run.sh
SRC=<checkout> VEC=<dir of vehicles> OUT=<out> VERILATOR=verilator-5.050 bash run.sh
python3 tools/hgi_e2e/run.py report OUT/<run> --out report.json
```
