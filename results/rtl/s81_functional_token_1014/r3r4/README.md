# S81 functional whole token, runs r3/r4 (2026-10-14)

The 1M-token DeepSeek-V4.1-Flash token (position 1,048,575, next token 21946) on S81 RTL, plus the DSpark (MTP)
draft. Everything was run on ot-epyc1tb under `/srv/opentallas-scratch/claude/s81-ftok/{r3,r4}`. The logs and JSON
records in this directory are copied from there. Sources: branch `claude/s81-ftok-r3-1014`, merged to main with
this record.

## One continuous run (every hand-off is data-chained and checked)

| step | vehicle / RTL | result |
|---|---|---|
| embed | `ot_dsrom_embed_row_reader` + ROM model, `tb_s81_embed_dump` | 320/320 words; `embed_hin.py` -> hin_L0 |
| L0..L39 | `tb_s81_die_layer` NG256: ctrl + stage seq + pkg ctrl, gather/capture, HC slab (hier), 4-die collective + link endpoints, REAL SU slab `dsfd_sp_su_h`, hop framer (HTX 2). Each layer's input is the previous layer's hop flits | 40/40 PASS, hop 640/640 exact, norm 330/330 and H_STORE 640/640, SU 969-1481 rows exact per layer (`r3/chain/chain.status`) |
| head glue | `chain_glue.py head` | L39 hop output == golden h_out; hc_pre + final norm == shard xf |
| head | `tb_s81_head_tp4` (4 x native head carried join + argmax chain) | 129,280/129,280 logits exact, token 21946 (bits 4173a558); MUT FAIL |
| MTP inputs | `chain_glue.py mtp0` | embed[21946] and embed[noise] x 4 == golden |
| DSpark | 3 stages x 5 rows on the same vehicle (program of L0), chained by hop flits | 15/15 PASS, SU 418/418 each; mtpo glue x5 PASS |
| draft head | `tb_s81_draft_head` (TP4 join + 32 Markov row engines a rank + argmax) | rows 0..2 PASS (108193, 8674, 71); rows 3, 4 and mut still running when this was recorded (`r3/dhead/run_m0.out`) |

Golden: w17 shards `ctx1048576_seed20260930`. The MTP golden (`tools/s81_ftok/mtp_golden.py`) runs on the real mtp
and embed shards, and it refuses zero-filled subset rows.

## Engines on RTL vs behavioural, by layer type (coverage)

| engine / op | RTL where | in the 40-layer chain |
|---|---|---|
| control plane, gather/capture, HC NORM/POST/H_STORE, collective | layer vehicle | every layer, RTL |
| SU slab: QN KV QB SW SE SO GQ GK + RA RB QR (F1) + RW (F11 part 1) | layer vehicle (`TB_SU_REAL`) | every layer, RTL. The chain used the pre-RW source, so ffn.weights was behavioural there. RW in the vehicle: `r3/su/t2rw` L0 L1 L2 L14 L20 L24 PASS + mut_rw FAIL; merged tree `r4/mgate/lay` L0 L20 PASS |
| SU ops with no job kind (F11: attn.cmp.*, attn.idx.newkey, attn.cand.final) | none | behavioural (port 11) on compressor/indexer layers |
| HC coefficient chain hc.fn/sumsq/rsqrt/pre_post/sinkhorn (F12) | none on S81 | behavioural (port 9), every layer |
| ROM field matvecs | `token_bench_l20.py`, L20 rank 0 at full shape, released weights | L20: 26 field ops / 34,880 rows exact; chain VM exact over 117 ops; selector exact; mutant detected. Other layers: golden roots |
| attention scan service `dsfd_svc_c` | `svc_layer.py` vectors from the real attention (L0 L1 L2 L3 L14 L20 L21 L24) | bench still verilating (top level > 5 h); not yet in the chain |
| Engram slab `dsfd_engram_c` | `engram_real.py` on the token's window + the 48 released rows (F13 fixed) | L1/L14 lookup exact (49,152 elements); the Engram compute after the lookup is behavioural in the chain |
| VM master | none bindable (F7+: `dsfd_sp_vm_m` has no SU/HC read/write ports) | bench VM model |
| die-composed run of die.v | blocked: S81 rtl-bind rb3 FAIL (4 unbound masters, 20 unknown ports, 22 unconnected inputs) | - |

Layer types in the 40-layer chain, all PASS: sliding L0 | engram+sliding L1 | ratio2+compressor+indexer L2,L8 |
ratio2 x15 | engram+ratio2+compressor+indexer L14 | ratio1+compressor+indexer+candidates L20 | ratio1 x15 |
ratio1+indexer L24,28,32,36. The model has no dense layer (all MoE).

## F13: Engram row format (fixed in this merge)

The released table has 8 UE8M0 exponents per 256-code row (`layers.{1,14}.engram.embed.scale [rows, 8]`). The S81
lookup carried one exponent per row, and its CRC overwrote released bytes 257..260. 45 of the token's 48 rows have
non-uniform exponents. Fix: 272-B HBM rows (codes, 8 exponents, CRC over 0..263 at 264..267). A row is still
9 atoms, and each beat now carries its own block exponent. Results:

- Real-token gate PASS 49,152/49,152 elements.
- `OT_ENGRAM_MUT_ONESCALE` FAIL 35,695 mismatches.
- Synthetic `engram_c_gate` PASS with all 5 negatives caught; throughput 351.0 is unchanged.

The boot packer `engram_boot_image.py` is fixed the same way.

## Measured SU job cycles (merged tree, full shape, hier = production)

RW 178 (price 259), RA 209 (185.6), RB 108 (117.6), QR 123 (117.6). Flat: 135 / 168 / 69 / 115.
