# HBM-ROTLAYOUT (10-19): rotated bank layout is the only HBM layout of every d4g stream

Owner rule 10-19 (COORD 18:46): the HBM compiler / weight layout must use the rotated bank layout for every stream.
Branch `claude/hbm-rotlayout-1019` (on `claude/l2h-bw-safe-1019` incl. MC3b a575dc283).

## Compiler change

- `tools/hbm_layer_vehicle/hbm_bank_layout.py` (new) holds the address law, THE layout and the refusal check.
  - Address law: block address `{row[17:3], set[2:0]}`, where `set` = descriptor `base[9:7]` = bank[4:2] on each of the SM's 4 PCs.
  - Layout (`assign_sets`, beam search over the fetch order): every stream starts on sets 0,1,2 and steps +1. The fewest -1/-2 phase steps are added so that its tail flows into the head of any stream that may follow it.
  - Routed experts: copy triples are chosen by routed POSITION (p mod 3), never by id. DS L14 puts w1+w3 on 4/5/6, the shared w2 on 7 and w2 on 0/1/2.
  - Runtime-indexed tables: entry e owns one DRAM row, with 8//nb phase copies. Lookup p reads copy p mod (8//nb).
  - Check (`check_stream`, `check_wrapped`, `check_sequence_pairs`): any violation raises `ROTLAYOUT REFUSED`.
    - **R1**: two blocks on the same set but different rows must be at least T_HIDE 35 column words apart.
    - **R2**: no block may sit 4 or 5 sets ahead of a block less than REF_WIN 160 words earlier. Those are the sets REFpb picks in `ot_hbm_r14_aq_pc_safe.sv:414`.
    - **R3**: a stream must use more than one set.
- `smb_unit.py` (d4g SM weight/expert/LM-head image compiler):
  - `SMB_LAYOUT` must be `bw` and `SMB_BSCALE` must be 1; the as-built layout is refused.
  - `layout_bw` = `hbm_bank_layout.layout_bw`. Each kind is laid out against the actual heads of every kind (fixpoint).
  - Checks: every kind's fetch order, plus every kind->kind boundary. The result goes in `budget.rotlayout`.
- `att_images.kv_image` (DS attention KV image): KV blocks are laid out by `static_run` and checked; the descriptor carries `base[9:7]` = set.
- `hbm_bw_unit.py`: one census pattern per stream class, every address from the layout functions above.

## R2 calibration (rot_fit over the MC3 census logs)

Excess cycles are measured on the block in question, by distance from the nearest earlier block whose set it is 4/5 ahead of:

| distance (words) | stall rate | mean excess (cycles) |
|---|---|---|
| < 160 | 26-44 % | +20 to +71 |
| 160-199 | 18 % | +11 |
| 200-239 | 0.7 % | — |
| >= 240 | 0 % | — |

LEAD + tRFCpb = 244 cycles. REF_WIN = 160 is the hard refusal limit. It is the tightest window that still admits the DS routed structure (w1+w3 a..a+2 / shared w2 a+3 / w2 a+4..a+6).

## Regenerated layer images (`images/`, ot-epyc5)

- `smb_compile.txt`, `smb_images/compile.json` cover L00/L02/L14/head.
  - `rotlayout.all_rotated = true`, 23 checks.
  - Per kind: phase steps 2/3/2/1, triples, and the full set sequence.
- `SMB_LAYOUT=asbuilt` gives `ROTLAYOUT REFUSED` (`smb_compile_asbuilt.txt`).
- `kv_image/L02`, `kv_image/L14`: PASS (readback exact), with rotated sets 0,1,2,1 per SM.
- The full production run is `full96/` (run_smb_unit.sh ff63e9fd7 bwsafe_face, XDEF=,FACE_MC3, G320/PNUM88/PADD8/FETCH96, ot-epyc5, Verilator 5.050). The images were compiled with this layout and run through the real issuer + MC3b leaves.
  - Result: **SMB_UNIT PASS**, ops 66/66 bit-exact, gos 154/154 with go_slots_exact, END 45260 cycles (same as the MC3b baseline), dram_reads 35372.
  - END is unchanged because the calendar is paced at the price; the rotated addresses only have to decode exactly.

## Exposed-bank census on the successor controller (MC3b a575dc283, tb_hbm_bw_pc4 +EXPOSE, MR SAFE OT_PC_SAFE_MC3, Verilator 5.050, ot-epyc5) — `census_mc3b/`

B/edge/SM is the steady value. Peak is 104.17.

| stream class | pattern (compiler layout) | B/edge/SM | exposed HBM cyc/ACT | verdict |
|---|---|---:|---:|---|
| DS layer stream (weights + routed + shared) | ds_rot s1/s2/s3 | 100.09 / 100.22 / 100.01 | 0.37 / 0.32 / 0.38 | ROTATED |
| DS non-expert weights, in that stream | ds_rot per-block accounting | 101.08 / 101.50 / 100.97 | | |
| DS routed experts, in that stream | ds_rot per-block accounting | 98.65 / 97.66 / 98.29 | | |
| DS non-expert weights, alone | weights | 99.42 | 0.59 | ROTATED |
| DS attention KV | kv | 102.78 | 0.11 | ROTATED |
| LM head / embed_head run | embed_head | 103.89 | 0.06 | ROTATED |
| Qwen3-8B INT8 SM weights | qwen | 103.95 | 0.01 | ROTATED |
| runtime-indexed tables, 4 phase copies | tables s1/s2/s3 | 101.53 / 101.50 / 101.54 | 0.14 | ROTATED |

Refused layouts, measured on the same RTL:

| layout | B/edge/SM | exposed cyc/ACT | refused by |
|---|---:|---:|---|
| asbuilt (row per block, set 0) | 26.15 | 46.9 | R1 |
| ds_nodup | 54.87 | 10.9 | R2 |
| tables_home (entries on home sets, random order) | 60.09 | 9.65 | R2 |
| routed experts back to back with no shared w2 between (stress, not a production order) | 84.45 | 2.08 | R2 |
| HBM-MC2 hand ds layout | 91.62 | 1.56 | R2 (and R1 at the layer boundary) |

Diagnostic: random rows with a +1 rotation (rand_rot) reach 102.95, so the row order does not matter; the set sequence does.

## Table copies priced + table image compiler (HBM-ROTLAYOUT-TBL, branch `claude/hbm-rotlayout-tbl-1019`)

`tools/hbm_layer_vehicle/hbm_table_images.py` (layout_stream, plan, Allocator, compile_table, readback, price). Price in `tables/price.{json,txt}`, selftest `tables/selftest.txt`, census `census_tbl/` (MC3b, tb_hbm_bw_pc4 +EXPOSE, Verilator 5.050, ot-epyc5).

Per-die HBM 144 GB (4 x 36 GB). Tables placed in HBM:

| design | table | rows / die | row | raw | v3 copies | chosen |
|---|---|---:|---:|---:|---:|---:|
| HBM-DS (96 dies) | embedding (replicated) | 129,280 | 10,240 B | 1.32 GB | 4 copies 9.00 GB | **2 copies 4.50 GB** |
| HBM-DS | Engram L1 / L14 (id mod 96) | 4.0 M each | 264 B | 1.06 GB each | 8 copies 278.5 GB each: **does not fit** | **1-copy sector rows 1.06 GB each** |
| HBM-Qwen (4 dies) | embedding (replicated) | 151,936 | 4,128 B | 0.63 GB | 8 copies 10.58 GB | **4 copies 5.29 GB** |

LM head (both designs) is streamed in full every token (embed_head class, 103.9), not row-gathered: no copies. RoPE / norm tables are POS-indexed static rows: no copies. Routed experts x3 position copies (DS) are priced as well: 9.0 GB/die.

Totals per die with the chosen laws: **HBM-DS 16.1 GB (11.2 %), HBM-Qwen 10.2 GB (7.1 %)**. Both fit. With the v3 copies for the embeddings (and sector rows for Engram) they would be 20.6 / 15.5 GB, which also fits. Only v3 block copies for Engram would not fit.

Law: an entry is nb = ceil(lines/64) balanced blocks, and copy j sits on sets j*nb.. of the entry's row index. A short lookup run (AR 1, DS MTP 2) cannot sit between two streams: every 1-3 block run between a HEAD-compatible tail and HEAD breaks R2 or R4. So lookups are **tokens of the first layer's weight stream** (`layout_stream` beam search). Each lookup takes the copy that continues the rotation, and the stream is checked R1..R4 behind the actual LM-head tail and wrapped into HEAD. `min_copies` picks the fewest copies that pass every run length the design issues (DS {1, 2}, Qwen {1, 8, 16}).

Measured (B/edge/SM steady):

| pattern | layout | B/edge/SM | verdict |
|---|---|---:|---|
| tables_mix_ds2 s1/s2 | DS: LM-head run, then 1 or 2 lookups (2 copies) + L14 weights | 101.69 / 101.69 | ROTATED |
| tables_mix_q4 s1/s2 | Qwen: LM-head run, then 1/8/16 lookups (4 copies) + layer weights | 103.86 / 103.85 | ROTATED |
| tables_q8 s1 | Qwen 31-line entries, 8 copies, 128 back-to-back lookups | 97.38 | ROTATED |
| kv4 | v3 att_images KV run 0,1,2,1 (68-word blocks), read twice per layer | 99.3 | ROTATED (R4-clean) |
| tables_pp / ppq | 1 copy, every lookup on sets 0,1 (41 / 36-word blocks) | 16.0 / 14.3 | REFUSED by R4a |
| pp68 | sets 0,1,0,1 with 68-word blocks | 76.7 | REFUSED by R4b |
| tables_ppmix | the 1-copy lookups mixed into weight streams | 52.4-53.5 | REFUSED by R4a |

**New check R4** (`hbm_bank_layout`). The pingpong layouts pass R1/R2 but measure 16-77, so R1/R2 alone are not sufficient.
- R4a: a new row on the set used 2 blocks earlier needs a block of at least 64 words in between.
- R4b: any 8 consecutive blocks must use at least 3 sets.

With R4 the smb kinds L00/L02 get new set sequences: the old ones re-opened a set 2 blocks later with a short block between. L14, head and the KV images are unchanged. The images were regenerated (`images/`), and the full96 functional rerun is in `full96_tbl/` (pending at commit time).

## Open (not done here)

- **Table copies**: priced and compiled (section above).
- **Qwen compiler**: done on branch `claude/toksim-hbm-smhbm-rotchk-1019` (bf2cea8c0, on claude/toksim-hbm-smhbm-1019). compile_qwen now lays the blocks out with `BL.static_run` and calls `BL.check_addrs`; the result goes in `budget.rotlayout`.
- **Integration (LEAD2-HBM compiler mainline)**: the DS / Qwen program compilers must place embedding lookups as tokens of the first layer's stream (`hbm_table_images.layout_stream`). Engram rows stay indexed-DMA sector rows.
- **KV and other streams.** The KV write-back / DMA linear byte streams follow the kport law (the set changes every 128 words per PC), so they are rotated by construction. They are single-row writes per token, not block streams.
