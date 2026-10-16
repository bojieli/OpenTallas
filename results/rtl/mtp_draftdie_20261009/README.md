# MD-2 draft dies and MTP on the S81 dies (mtp-draftdie, 2026-10-09)

## 1. A/B draft ROM images (image-level exactness gate: PASS)

Tool: `tools/dsrom_mtp_draft_images.py` (source 086a41ed9). Host ot-epyc1tb, released V4.1-Flash checkpoint
dba1be0a (the three `mtp.*` shards and the index, sha256 identical to the local snapshot).

- Layout: the selected whole-superrow rowpack (`tools/dsrom_mtp_p2_rowpack.py`): 1,792 pairs a die, 14 pairs a region,
  13,762,560 of 14,680,064 words used (93.75 %). Word order is the element issue order, as the per-pair writer
  `tools/dsrom_mtp_p2_rowpack_image.py` writes it.
- MD-2 split: die A = `mtp.0` experts 0..127 + `mtp.2` experts 0..63; die B = `mtp.1` experts 0..127 + `mtp.2` experts
  64..127. Rank k = row quarter k of every expert matrix.
- 8 distinct images (side × rank) serve the 40 draft dies (5 row packages × 4 ranks × A/B). Each image is 998,244,480 B
  (a .npy array; hashes in `images/images.json`). They stay on
  `ot-epyc1tb:/srv/opentallas-scratch/claude/mtp-draftdie/images/`.

The gate (`images/check.json`) reads the eight images back without the emitter. It rebuilds all 1,152 released expert
tensors (FP4 codes and E8M0 scales) from A and B together over the 4 ranks and compares them with the released
safetensors byte for byte. It also checks:
- every tensor sits on the side the MD-2 rule names (computed from the tensor name; 0 violations);
- no block is missing or duplicated;
- words outside the plan are zero (sampled);
- 4 sampled pairs are byte-identical to the per-pair reference writer.

| Run | Result |
|---|---|
| A + B recombination | **PASS** (1,152 tensors, 50.8 s) |
| m1: `mtp.2` split boundary at 63 | FAIL as required (`mtp.2` expert 63: 368,640 blocks missing) |
| m2: one B word with its two banks swapped | FAIL as required (bytes differ) |
| m3: rank-1 B image served as rank 0 | FAIL as required (bytes differ) |

Scope: storage exactness only. The read schedule on this layout is RTL-qualified for the full-K pair-0 phase only
(`dsrom_mtp_p2_rowpack` bench); the field schedule is not qualified.

## 2. Generator: MTP on the dies

- `MTP_SEQ_DEFAULT = True`: every head die carries `dsfd_mtp_seq` (CLOSED c67a71fe5).
- `WFC_HARD_DEFAULT = True`: the WFC kit is complete (SOURCE HARD 910e67c7b CLOSED TT +152.31 / FF +4.02 / DRC 0).
  The `dsfd_wfc` slab is sized from the closed SOURCE (293.734 µm square) and STG (190.41 µm square)
  outlines: 328.32 µm tall, was 231.12.
- `--draft A|B`: the MD-2 draft die (layer1 recipe, no WFC; die A carries the `dsfd_p2` slab and its buses).
- Recipe base (`tools/s81/s81_dies_recipe.py`) = the s81-gen full layer1 recipe
  (`results/physical/s81_gen_20261009/s81_layer1_full.opts`). The older r3 + `--nxt-reach --host` base failed in
  `_hop_fix` on every die drawn from it: `rt_0_8a_y1` (773.7 µm hop) and the 20 mm `hw_SW` host chain.
  `--hop-r-cc 500` and `--path-pick` clear them.

## 3. Die records (`dies/`, generator at main c7822c972, host ot-epyc3)

| Die | Build | Placed mm² (util) | Legality / pin clashes / unbound | MTP masters | margin lint (edges): reach / far-side |
|---|---|---|---|---|---|
| layer1 full (s81-gen recipe, reference) | check | — | 0 / 0 / 0 | dsfd_wfc | 768 / 3,209 FAIL |
| draftA | plan | 417.10 (48.6 %) | 0 / 0 / 0 | dsfd_p2 | 768 / 3,221 FAIL |
| draftB | plan | 416.81 (48.6 %) | 0 / 0 / 0 | — | 768 / 3,209 FAIL |
| scan (q-only) | plan | 450.31 (52.5 %) | 0 / 0 / 0 | dsfd_wfc | 0 / 1,814 FAIL |
| head631 | plan | 322.34 (37.6 %) | 0 / 0 / 0 | dsfd_mtp_seq + 5 SerDes | 0 / 733 FAIL |
| headp2 (511) | plan | 297.26 (34.7 %) | 0 / 0 / 0 | dsfd_mtp_seq | 0 / 585 FAIL |

All six dies build legally with every functional pin bound. The margin-lint FAIL is the reference recipe's class,
reproduced on the identical layer1 base: 768 column-relay TT-tier hops (`g_xb_*` 670 µm), link `txs` relays
(far-side 280–400 µm) and `y_rt_*` return relays. The MTP homes add 12 far-side relays on draftA (the P2 buses)
and nothing on draftB. They are owned by the s81-gen relay work, not by MTP.
