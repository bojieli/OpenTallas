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

## 2. Generator

See the commit message and the `MD-2` / `MTP defaults` comments in `tools/dsrom_s81_fulldie.py`.
