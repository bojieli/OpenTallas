# HBM-VMEARLY-DMA (10-19): early VM-read issue on the DMA-back controller (hb_dbk_<q>, RR_RT 80)

Verdict: **no RTL change.** ISSUE_AHEAD would hide 0 DS cycles. The only DS record that reads VM through hb_dbk is
`DMA.KVWB_DS window_row_append`: one 8-chunk move per layer, far from the next one, and RAW-bound on the producer of the
KV row. The S2 schedule already hides its whole 93-edge lag (posted write). The DS cycles charged as "bl_dma" come from
DMA.LOAD and DMA.FENCE records, which never issue a dbk VM read.

## RTL bench (tools/hbm_v15_harden/bench_dma_vmearly.sh, Verilator 5.050 on ot-epyc9; evidence/dma_vmearly_1019/)
The bench uses the RR_RT 80 controller and 8 real landing banks on the GEN2c NE lanes, with the faces bank n+8 padded to
80. It runs 6 back-to-back moves (KVWB-shaped 8-chunk moves, plus partial, 80-chunk and 128-chunk moves) and a final RAW
move behind a producer VM write. Every beat is checked through the landing SRAMs.

- `pass`: PASS. 1872 beats exact. Exposed HBM-write edges between back-to-back moves: 87 / 89 (SL 2) / 87 / 87 / 87
  (mean 87 = drain lag 83 + 4). For the RAW move, the first write beat comes 86 edges after the producer retires and the
  last beat 93 edges after (85 + nchunk).
- `mut_ahead1`: the command is issued during the previous move's drain (`issue_at(i+1) = drain_at(i)`). FAIL with
  mv_fault, busy 1. **The controller does not accept the ISSUE_AHEAD-1 calendar.**
- `mut_early`: the next command comes one edge earlier than K = 3. FAIL with mv_fault.
- `mut_stale`: the reads reach the banks before the producer's write. FAIL with a stale payload.
- Compiler rule (`tools/hbm_die_v16/d4g_bank_latency.py dma_min_next_issue`):
  `issue_at(i+1) >= max(drain_at(i) + nchunk(i) + 4, producer retire)`.

## Per-record mix and model (tools/hgi_sim/d4g_bl_dma_split_1019.py on d4g_reprice3_1019, 45.03 B/edge)
Each DS layer has 6 DMA.LOAD records (HBM->VM tables), 1 KVWB_DS and 1 FENCE. Only the KVWB_DS reads VM via dbk.

| bl_dma charged on | info_bl_dma alone (DS cycles over base) | Qwen | info_banklat_all DS tok/s |
|---|---:|---:|---:|
| every DMA record (as committed) | +10,181 | +3,059 | 1,217.5 |
| VM-read DMA records only (KVWB/STORE) | **0** | +2,002 | **1,229.0 (+0.94 %)** |

Early-issue upper bound for this client:
- DS: 0. There is no back-to-back dbk pair, and the RAW read cannot issue before the producer retires.
- Qwen: below 2,002 cycles (0.16 %), under the 1 % adoption threshold.
- The 9,188 DS cycles (+0.94 %) are a model correction for the lead. It is not a hardware lever.
