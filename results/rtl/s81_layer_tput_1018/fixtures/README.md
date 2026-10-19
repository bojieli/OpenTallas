# S81 layer fixtures (LAYERBENCH-S81, TOK.DS.BENCH.2, 2026-10-18)

These fixtures replace the S81 layer fixtures from 10-13/14, which were lost with the retired host ot-epyc1tb.
Each fixture is regenerated from committed sources:
- the generator `tools/s81_dv/dv_layer_fixtures.py`;
- the released DeepSeek-V4.1-Flash checkpoint (snapshot `dba1be0a40aa`);
- the golden `tools/hdc_golden_v41.py` (`HDC_V41_ARITH=chunk8`);
- the w17 1M headline token: context 1,048,576, position 1,048,575, seed 20260930, input token 16754, next token 21946.

The KV / index state and the token history are the campaign's `synthetic_state` / `token_history`. Each layer has its
own RNG stream, so a layer is generated on its own.

## What a fixture holds (per layer, directory `DIR`)

| Part | Content |
|---|---|
| `ops/<op>.bin` + `ops.json` | The golden value at every op boundary of the priced token DAG. The op ids are those of `results/arch/token_path_20261009/ds_rom.json`, the ones `dv_layer_price.py` prices and the layer compiler schedules. Every DAG op of the layer is covered; transport ops (hops, all-gathers) carry the value they move. Parts are suffixed, e.g. `attn.norm.sumsq`, `ffn.experts.<id>.gu`. |
| `io/` | `h_in` (4 × 5120 HC copies), `pre_in`, `h_out`, `pre_out`. These are the layer bench's entry and exit. |
| `state/` | The images the HBM service reads, packed as in the campaign's `images()`: the 127 window rows (E4M3 + UE8M0, signed zero kept); for compressor layers the compressed rows (E2M1 + E4M3/16) and this rank's quarter of the index keys (E2M1 + UE8M0/32); the open-group slots. Engram rows appear as the `eng.*` ops. |
| `weights/` | This rank's raw checkpoint slices of every matrix the layer reads (campaign `die_slices` TP4 split; only the token's six experts are populated). They are the input of the frame ROM image writer. |
| `meta.json` | The checks, the shard / checkpoint / source pins, the TP4 rank split of each op (`tp_split`) and the generator command. |
| `manifest.sha256` | `sha256sum -c` format. |

**Exactness.** The tool writes nothing unless the recorded op-by-op run matches the pinned w17 golden shard
(`ctx1048576_L<L>.npz` / `_head.npz`) bit for bit. The compared fields are attn_norm, attn, router, ffn_norm, ffn, h_out,
pre_out, block, the experts, and, where the layer has them, engram, index_scores, its own window row and the new
ckv / ik rows. For the head the compared fields are the final norm and the logits. The op values are therefore the
golden's own, not a re-derivation.

The indexer is checked one step further: the four ranks' local top-512 lists over their contiguous quarters merge to
exactly the golden selection.

## Layers (rank 0)

| Layer | Kind | Ops | Files | Experts / token | Bulk | Wall |
|---|---|---|---|---|---|---|
| L0 | sliding window | 100 | 171 | 61 69 112 170 299 357 | 74 MB | 7–24 s |
| L2 | ratio 2 + compressor + indexer | 120 | 204 | 33 36 59 182 279 352 | 241 MB | 93 s |
| L14 | Engram + ratio 2 + compressor + indexer | 129 | 217 | 26 29 114 155 334 352 | 279 MB | 94 s |
| L20 | ratio 1 + compressor + indexer + candidates | 121 | 203 | 41 65 158 164 259 266 | 398 MB | 156 s |
| HEAD | final hc_pre + norm + lm_head + argmax | 9 | 14 | next token 21946 | 317 MB | 55 s |
| MTP draft | — | — | — | **GAP** (below) | — | — |

The committed manifests are `<layer>.sha256.json`. Each one lists every file's sha256 and every op's shape, dtype and
sha256, plus the checks and the command.

- **Bulk copies:** `ot-epyc4` and `ot-epyc5` under `/srv/opentallas-scratch/claude/layerbench-s81/fixtures/<layer>`, verified against the manifests.
- **Working copy:** the checkpoint host, at `/home/ubuntu/scratch/layerbench-s81/fixtures`.
- **Reproducibility:** the generator is deterministic. A re-run of L0 gave a byte-identical `manifest.sha256`.

Checking a copy:

    python3 tools/s81_dv/dv_layer_fixtures.py --verify DIR --manifest results/rtl/s81_layer_tput_1018/fixtures/L0.sha256.json

Regenerating a layer, on the checkpoint host (the localhost, which holds the 476 GB snapshot; peak RSS 3–12 GB):

    HDC_V41_ARITH=chunk8 python3 tools/s81_dv/dv_layer_fixtures.py --layer L0 --out DIR \
        --manifest-out results/rtl/s81_layer_tput_1018/fixtures/L0.sha256.json

The run reads the w17 1M shard from `OT_DSROM_1M_GOLD`, default `/home/ubuntu/w17work/ref/ctx1048576_seed20260930`.
- **Copies of the shard:** a 14 MB copy is kept on ot-epyc4/5 at `/srv/opentallas-scratch/claude/layerbench-s81/ctx1048576_seed20260930`.
- **Regenerating the shard:** run `rtl_v41_fullshape_layer_campaign.py --steps golden --contexts 1048576 --seed 20260930`.

Test (pure python, no checkpoint): `python3 tools/s81_dv/test_dv_layer_fixtures.py`.

## Gaps (recorded, not filled)

1. **MTP draft layer: no fixture.**
   - The checkpoint has the DSpark stages (2,401 `mtp.*` tensors), and `hdc_golden_v41.Model.draft` / `dspark_stage` define the arithmetic.
   - What is missing is the stage's *state*: the per-stage window caches `state["dsk"]` of the 128 positions before the anchor. Each row is `dspark_row(main_x(pos))`, built from the main-model hidden rows of earlier positions.
   - `synthetic_state` builds no `dsk`. The w17 shard has no draft stage. `w19_v41_mtp_golden.py` is the verify pass (main layers over 6 positions), not the draft.
   - A golden-consistent synthetic DSpark window state, for example 127 rows drawn like the main window rows with the stage's kv_norm gain, is a new state rule. It needs a coordinator decision before the MTP draft fixture can be pinned.
2. **Frame ROM images per bind9 frame instance are not emitted.** The row → frame placement belongs to the layer compiler (LB-S81-CC: each matrix's output rows sit in the frames of the owning slice). This fixture provides:
   - the rank's raw weight slices (`weights/`);
   - each matvec's golden input and output (`ops/`).

   From these, `v41_die_images_w17w10.add_phase` / `frame_bench.py` write the ROM / cfg7 images once a placement exists.
3. **Campaign packer bug.** `rtl_v41_fullshape_layer_campaign.pack_fp8_ue8m0` maps −0 and +0 to one E4M3 code (it uses `np.unique`), so its round-trip assert fails on the L2 window rows. This tool packs from the sign bit instead (`pack_fp8_exact`, code 0x80 for −0). `images()` in the campaign is still affected.
4. **Indexer and candidate set.**
   - `attn.idx.topk_local` / `topk_merge` are the TP4 rank decomposition, checked equal to the golden selection.
   - The golden itself has a single top-k.
   - `attn.cand.topk_local` holds the block maxima and `attn.cand.merge` the kept blocks.
