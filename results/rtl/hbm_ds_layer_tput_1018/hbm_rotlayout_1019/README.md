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
- The full production run is `full96/` (bwsafe_face + FACE_MC3, G320/PNUM88/PADD8/FETCH96, compiled with this layout). Result: see `full96/README` once it is collected.

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

## Open (not done here)

- **Table copies.** Runtime-indexed tables need 4x capacity (2-block entries x 4 phase copies) for embedding / engram rows. This is not priced. No d4g table image compiler exists on this vehicle yet; the layout function and check are ready for it.
- **Qwen compiler.** `toksim_smhbm.compile_qwen` (TOKSIM-HBM-smhbm branch) places blocks at `desc_index * S.BSCALE`. With BSCALE now 1 that is slot-packed (+1 rotation). It should call `BL.check_addrs("weights", ...)`.
- **KV and other streams.** The KV write-back / DMA linear byte streams follow the kport law (the set changes every 128 words per PC), so they are rotated by construction. They are single-row writes per token, not block streams.
