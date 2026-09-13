# DeepSeek-V4.1-Flash on mask ROM: a candidate feasibility study

**Status:** candidate model, analytical only. Profiled 2026-09-13 from the
official checkpoint's safetensors headers at one pinned revision; executed by
no lane in this repository; bound to no release figure. Every number below is a
deterministic model output and carries the artifact that produces it.

**Question asked:** DeepSeek released V4.1-Flash on 2026-09-10. Can this
program's model-specific ROM inference machine implement it, and what does the
analytical model say a ROM wafer and a ROM reticle array would do against an
HBM GPU cluster on it?

**Short answer.** Yes, at the analytical layer, and it is a better fit for
this architecture than DeepSeek-V4-Flash was: its per-token KV traffic is about
seven times smaller at 200K context, so the ROM machine stays bound by its
on-wafer collective rather than by its HBM beachfront up to batch 32 at 200K,
and its advantage over the GPU comparator no longer collapses at 1M context.
The price is capacity: the checkpoint is 510.3 GB <!-- figure: 510.3 src="data/inventory/deepseek-v4.1-flash.json#checkpoint_bytes" scale="1e-9" name="V4.1 checkpoint GB" -->
against 166.9 GB <!-- figure: 166.9 src="data/inventory/deepseek-v4-flash-0731.json#checkpoint_bytes" scale="1e-9" name="V4-Flash checkpoint GB" -->
for V4-Flash, of which 202.8 GB <!-- figure: 202.8 src="data/inventory/deepseek-v4.1-flash.json#lookup_table_bytes.engram_table_packed" scale="1e-9" name="Engram table GB" -->
is Engram lookup tables, so the central N4-class envelope needs three wafers
where V4-Flash needed one, and a reticle array needs 84 to 91 chips, which puts
the array's per-user rate barely above the GPU's. What is *not* done is every
executable step: no compiler front end, kernel IR, RTL vector or oracle exists
for this model, and the KV byte widths are read off the released code rather
than measured by running it.

Regenerate everything cited here with:

```sh
PYTHONPATH=src python3 tools/profile_hf.py --model deepseek-v4.1-flash --model deepseek-v4.1-flash-engram_host
make iso-node model-traffic      # ~10 s
python3 tools/run_roofline_studies.py --force   # ~10 min; writes results/roofline/candidates/
```

---

## 1. What was released, and what was read from it

The sources are pinned in [`SOURCES.md`](SOURCES.md) as `SRC-DSV41-FLASH-*`.
The full checkpoint was **not** downloaded: it is 510.3 GB and this host had
372 GB free. The profiler needs only `config.json`, the safetensors index and
the JSON header of each of the 48 shards, fetched by HTTP range, which is the
same method every other model in `configs/models/` was profiled with. The
headers give every tensor's exact shape, dtype and byte extent, and their sum
equals the index's declared total to the byte.

| Published (model card, report) | Read from the pinned checkpoint | Artifact |
|---|---:|---|
| 552B backbone parameters | 551.9B: decode-dense 7.64B + routed 543.58B + embedding/vision 1.15B | `data/inventory/deepseek-v4.1-flash.json` → `parameter_counts` |
| 196B Engram parameters | 196.6B <!-- figure: 196.6 src="data/inventory/deepseek-v4.1-flash.json#parameter_counts.engram_table" scale="1e-9" name="Engram parameters" --> | same, `parameter_counts.engram_table` |
| 16B activated per decode token | 16.13B: 7.64B dense + 543.58B × 6/384 (author's arithmetic on the two cells) | same, `parameter_counts` |
| 8B activated per prefill token | 7.89B over the 20 encoder layers (author's arithmetic on the per-layer inventory; nothing in `results/` produces this figure) | -- |
| 890 bytes of global KV per token | 890 <!-- figure: 890 src="configs/models/candidates/deepseek-v4.1-flash.json#metadata.global_kv_bytes_per_token" name="global KV bytes per token" --> | `configs/models/candidates/deepseek-v4.1-flash.json` |
| 40 layers, 384 experts, top-6, 5,120 hidden, 1M context | identical | `config.json`, SHA-256 in `SOURCES.md` |

The released bytes, by role, from 96,085 <!-- figure: 96,085 src="data/inventory/deepseek-v4.1-flash.json#tensor_count" name="tensor count" -->
tensors:

| Role | Bytes | What it is |
|---|---:|---|
| routed experts, streamed 6 of 384 per layer | 288.8 GB <!-- figure: 288.8 src="data/inventory/deepseek-v4.1-flash.json#decode_routed_bytes" scale="1e-9" name="routed expert GB" --> | 40 × 384 I8-packed MXFP4 experts with E8M0 scales |
| Engram tables, looked up by row | 202.8 GB | two FP8 tables of 384,006,168 and 384,016,682 rows × 256 |
| dense decode weights, streamed every token | 8.5 GB <!-- figure: 8.5 src="data/inventory/deepseek-v4.1-flash.json#decode_dense_bytes" scale="1e-9" name="dense decode GB" --> | attention, shared experts, gates, mHC, Engram projections, untied BF16 head |
| DSpark draft blocks, read only under speculation | 7.2 GB <!-- figure: 7.2 src="data/inventory/deepseek-v4.1-flash.json#draft_routed_bytes" scale="1e-9" name="draft routed GB" --> routed + 0.7 GB dense | three blocks of 128 experts |
| resident-only besides Engram | 2.3 GB | input embedding, DeepSeek-ViT, projector |

## 2. The architecture, in this program's terms

DeepSeek-V4.1-Flash is a 40-layer **Causal Encoder-Decoder**: 20 encoder
layers whose final hidden state is projected into the decoder's single shared
global KV, then 20 decoder layers. Every layer keeps its own 128-token FP8
sliding window. On a **decode** token all 40 layers run, so decode is charged
in full; the encoder-decoder split halves *prefill*, which is outside this
program's decode-only scope and is not modelled.

**CSA2 modes, read off `kv_source_layer_ids`, `index_source_layer_ids` and
`candidate_source_layer_id` exactly as `inference/model.py` reads them.** Only a
Full-mode layer owns a compressed cache; only a Full or Reindex layer scans an
index; a Reuse layer takes its predecessor's top-512 selection and scans
nothing. The decoder's four Reindex layers score only the candidate pool the
decoder's Full layer builds, 2,048 blocks of 8 positions, so their scan stops
growing with context.

| Layers | Ratio | Mode | Owns cache | Scans index | Scan bound |
|---|---:|---|---|---|---|
| 0, 1 | -- | sliding window only | -- | -- | -- |
| 2, 8, 14 | 2 | Full | yes | yes | context / 2 |
| 3-7, 9-13, 15-19 | 2 | Reuse | no | no | -- |
| 20 | 1 | Full (candidate source) | yes | yes | context |
| 24, 28, 32, 36 | 1 | Reindex | no | yes | 16,384 |
| 21-23, 25-27, 29-31, 33-35, 37-39 | 1 | Reuse | no | no | -- |

Representing this needed four fields on the attention-group schema
(`kv_owner`, `scans_index`, `index_scan_entries_cap`, `window_entry_bytes` in
`src/opentallas/schema.py`), honoured by the traffic model, the roofline's
access-granularity and per-layer-latency terms, and the A100 expansion policy.
Every profile that predates the fields serialises and evaluates byte for byte
as before; the iso-node artifacts prove it (section 4).

**KV bytes, per the report's section 2.4.4 and the pinned code.** A main
entry is E2M1 over 512 channels with one E4M3 scale per 16: 288 B <!-- figure: 288 src="configs/models/candidates/deepseek-v4.1-flash.json#attention_groups[label=csa2-1-full].entry_bytes" name="main KV entry bytes" -->.
An index key is E2M1 over 128 with one E8M0 per 32: 68 B <!-- figure: 68 src="configs/models/candidates/deepseek-v4.1-flash.json#attention_groups[label=csa2-1-full].index_entry_bytes" name="index entry bytes" -->.
A window entry is E4M3 over 512 with one E8M0 per 32: 528 B <!-- figure: 528 src="configs/models/candidates/deepseek-v4.1-flash.json#attention_groups[label=csa2-1-full].window_entry_bytes" name="window entry bytes" -->.
Three encoder owners at ratio 2 and one decoder owner at ratio 1 give
3 × 356 / 2 + 356 = 890 bytes of global KV per token, the published figure.
The window adds a context-independent 40 × 128 × 528 B = 2.7 MB per user.
These widths are **read, not measured**: for V4-Flash this repository measured
the reference implementation and found it reading 1,024 B where the recipe said
583 B, and that lesson is recorded in `configs/models/deepseek-v4-flash-0731.json`
under `kv_entry_measurement`. The same measurement has not been taken here.

**Engram** is 196.6B parameters of n-gram lookup tables: immutable, addressed
by token ids, read 24 rows of 264 B per module per token, 12,672 B <!-- figure: 12,672 src="configs/models/candidates/deepseek-v4.1-flash.json#metadata.engram.lookup_bytes_per_token" name="Engram lookup bytes per token" -->
per token in total. That is a capacity problem and not a bandwidth one, and a
row-addressed immutable table is precisely what a mask ROM is. DeepSeek's own
serving stack keeps the tables in host memory and prefetches them by RDMA, so
the model is carried in two placements, applied to **both** sides of every
comparison: `DeepSeek-V4.1-Flash` stores the tables beside the weights (ROM on
the ROM side, HBM on the GPU side) and `DeepSeek-V4.1-Flash-engram-host` keeps
them in host memory on both sides. Their traffic and work are identical; only
capacity differs.

**Decode work** is inventoried from the pinned shapes in
`src/opentallas/operations.py` (`deepseek_v41_official_operator_inventory_v1`):
35.9 Gop <!-- figure: 35.9 src="results/iso-node/leading_node_market/analytical.json#points[architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash,context_tokens=8192,batch_size=1].tensor_operations_per_user_token" scale="1e-9" name="V4.1 tensor ops at 8K" -->
per token at 8K context rising to 56.5 Gop <!-- figure: 56.5 src="results/iso-node/leading_node_market/REPORT.md#Tensor ops/token" table="Exact model work" where="Model=DeepSeek-V4.1-Flash" name="V4.1 tensor ops at 1M" -->
at 1M, against 135.2 Gop <!-- figure: 135.2 src="results/iso-node/leading_node_market/REPORT.md#Tensor ops/token" table="Exact model work" where="Model=DeepSeek-V4-Flash-0731" name="V4-Flash tensor ops at 1M" -->
for V4-Flash at 1M. Only the four full scans grow with context; weighted by
precision as the report's Figure 2 does, the 4K-to-1M growth is 1.28×, which
is the "about one quarter" the report states (`tests/test_deepseek_v41_profile.py`
pins it between 1.2× and 1.35×).

## 3. The model-level screen

`results/model-traffic/sweep.csv`, batch 1, active weight bytes per step over
KV bytes read per token. This has no hardware in it.

| Model | Weights / step | KV read at 8K | at 32K | at 200K | at 1M | ρ₁ at 200K | ρ₁ at 1M |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 11.218 GB <!-- figure: 11.218 src="results/model-traffic/sweep.csv#active_weight_read_bytes_per_step" where="model=DeepSeek-V4-Flash-0731;context_tokens=200000;batch_size=1" scale="1e-9" name="V4-Flash weights per step" --> | 28.97 MB | 65.93 MB | 317.46 MB <!-- figure: 317.46 src="results/model-traffic/sweep.csv#kv_read_bytes_per_user_token" where="model=DeepSeek-V4-Flash-0731;context_tokens=200000;batch_size=1" scale="1e-6" name="V4-Flash KV read at 200K" --> | 1,520.66 MB | 35.3× <!-- figure: 35.3 src="results/model-traffic/sweep.csv#weight_to_kv_read_ratio" where="model=DeepSeek-V4-Flash-0731;context_tokens=200000;batch_size=1" name="V4-Flash rho at 200K" --> | 7.4× <!-- figure: 7.4 src="results/model-traffic/sweep.csv#weight_to_kv_read_ratio" where="model=DeepSeek-V4-Flash-0731;context_tokens=1000000;batch_size=1" name="V4-Flash rho at 1M" --> |
| DeepSeek-V4.1-Flash | 13.035 GB <!-- figure: 13.035 src="results/model-traffic/sweep.csv#active_weight_read_bytes_per_step" where="model=DeepSeek-V4.1-Flash;context_tokens=200000;batch_size=1" scale="1e-9" name="V4.1 weights per step" --> | 11.93 MB | 18.33 MB | 46.76 MB <!-- figure: 46.76 src="results/model-traffic/sweep.csv#kv_read_bytes_per_user_token" where="model=DeepSeek-V4.1-Flash;context_tokens=200000;batch_size=1" scale="1e-6" name="V4.1 KV read at 200K" --> | 182.76 MB | 278.7× <!-- figure: 278.7 src="results/model-traffic/sweep.csv#weight_to_kv_read_ratio" where="model=DeepSeek-V4.1-Flash;context_tokens=200000;batch_size=1" name="V4.1 rho at 200K" --> | 71.3× <!-- figure: 71.3 src="results/model-traffic/sweep.csv#weight_to_kv_read_ratio" where="model=DeepSeek-V4.1-Flash;context_tokens=1000000;batch_size=1" name="V4.1 rho at 1M" --> |

V4.1 streams 16% more weight bytes per token than V4-Flash (16B active against
13B) and reads 6.8× fewer KV bytes at 200K and 8.3× fewer at 1M. This is the
whole story of what follows: a ROM machine is a device for making weight bytes
free, so a model that spends fewer of its bytes on the mutable side gains more
from it.

## 4. Wafer scale: the iso-node study at the leading node

`results/iso-node/leading_node_market/`: N4-class mask ROM with HBM3e KV
against NVIDIA B300, the study whose central point the README quotes. Adding
V4.1 to it changed no existing row; every point, comparison, band and
capacity endpoint for the three prior models is byte-identical, and only the
consistency audit's check count moved.

**Capacity first.** On the central envelope (242.7 GB usable ROM per wafer)
V4.1 needs 3 <!-- figure: 3 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash,context_tokens=200000,batch_per_stage=1].wafer_stages" name="V4.1 central wafer stages" -->
wafer stages, or 2 <!-- figure: 2 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash-engram-host,context_tokens=200000,batch_per_stage=1].wafer_stages" name="engram-host central wafer stages" -->
with the Engram tables in host memory; the conservative envelope needs 6 and 4,
the aggressive 2 and 1. V4-Flash fits one central wafer. On the GPU side a
single B300 cannot hold either placement (259 GB usable against 307.5 GB
without the tables), so the smallest feasible cluster is two GPUs and the
fastest is eight.

**At 200K context, central envelope.** `GPU` is the fastest feasible B300
cluster at the same active batch; `ROM $/M` is partial TCO as
[`METHODOLOGY.md`](METHODOLOGY.md) defines it.

| Model | B/stage | Stages | ROM user tok/s | GPU | GPU user tok/s | Same-B ratio | ROM $/M tok | Resident users on the wafer set | Binding |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | 1 | 12,629.3 <!-- figure: 12,629.3 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="V4-Flash central rate" --> | B300-x8 | 1,650.7 | 7.65× <!-- figure: 7.65 src="results/iso-node/leading_node_market/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="V4-Flash central ratio" --> | 0.2096 | 938 | collective floor |
| DeepSeek-V4.1-Flash | 1 | 3 | 14,200.3 <!-- figure: 14,200.3 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=1" name="V4.1 central rate" --> | B300-x8 | 1,519.5 <!-- figure: 1,519.5 src="results/iso-node/leading_node_market/REPORT.md#GPU user tok/s" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=1" name="V4.1 GPU rate" --> | 9.35× <!-- figure: 9.35 src="results/iso-node/leading_node_market/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=1" name="V4.1 central ratio" --> | 0.1319 <!-- figure: 0.1319 src="results/iso-node/leading_node_market/REPORT.md#ROM $/M tok" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=1" name="V4.1 central TCO" --> | 12,035 <!-- figure: 12,035 src="results/iso-node/leading_node_market/analytical.json#points[architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash,context_tokens=200000,batch_size=1].max_concurrent_users" name="V4.1 resident users" --> | collective floor |
| DeepSeek-V4.1-Flash-engram-host | 1 | 2 | 14,895.9 <!-- figure: 14,895.9 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash-engram-host;B/stage=1" name="engram-host central rate" --> | B300-x8 | 1,519.5 | 9.80× <!-- figure: 9.80 src="results/iso-node/leading_node_market/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash-engram-host;B/stage=1" name="engram-host central ratio" --> | 0.1390 | 11,983 | collective floor |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 4,698.7 | B300-x16 | 1,006.3 | 4.67× | 0.0704 | 938 | KV beachfront |
| DeepSeek-V4.1-Flash | 8 | 3 | 8,661.7 <!-- figure: 8,661.7 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=8" name="V4.1 central rate B8" --> | B300-x16 | 920.4 | 9.41× <!-- figure: 9.41 src="results/iso-node/leading_node_market/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=8" name="V4.1 central ratio B8" --> | 0.0271 <!-- figure: 0.0271 src="results/iso-node/leading_node_market/REPORT.md#ROM $/M tok" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=8" name="V4.1 central TCO B8" --> | 12,035 | collective floor |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 1,490.2 | B300-x16 | 506.8 | 2.94× | 0.0555 | 938 | KV beachfront |
| DeepSeek-V4.1-Flash | 32 | 3 | 3,406.5 <!-- figure: 3,406.5 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=32" name="V4.1 central rate B32" --> | B300-x16 | 416.5 | 8.18× <!-- figure: 8.18 src="results/iso-node/leading_node_market/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=32" name="V4.1 central ratio B32" --> | 0.0173 | 12,035 | collective floor |

Three things to read off this table.

- **The binding constraint moved.** V4-Flash leaves the collective floor at
  batch 8 and is then limited by how much KV its wafer's HBM edge can stream.
  V4.1 stays on the collective floor through batch 32, because it reads 6.8×
  fewer KV bytes per token. At batch 8 the gap between the two models is
  therefore 8,661.7 against 4,698.7 tok/s per user, on the same envelope.
- **Twelve times the resident sessions.** A 200K session costs 180.7 MB of KV
  on V4.1 and about 1.4 GB on V4-Flash (author's arithmetic on the two
  profiles' `kv_traffic` storage), so the same wafer-edge HBM holds 12,035
  sessions against 938. The per-token partial TCO at batch 8 is 0.0271 $/M
  against 0.0704 $/M for the same reason.
- **The three-wafer pipeline costs one user little.** A batch-1 token still
  crosses only two inter-wafer links, 0.1 µs of the 70 µs step. The Engram
  placement is worth 5% of the per-user rate (14,895.9 against 14,200.3) and
  one wafer of capital.

**Context does not break it.** At 1M tokens V4-Flash's advantage falls to
4.59× <!-- figure: 4.59 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4-Flash-0731,context_tokens=1000000,batch_per_stage=1].same_batch_per_user_speed_ratio" name="V4-Flash 1M ratio" -->
at batch 1 and to 0.96× <!-- figure: 0.96 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4-Flash-0731,context_tokens=1000000,batch_per_stage=32].same_batch_per_user_speed_ratio" name="V4-Flash 1M B32 ratio" -->
at batch 32, where the GPU cluster is faster. V4.1 holds 8.84× <!-- figure: 8.84 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash,context_tokens=1000000,batch_per_stage=1].same_batch_per_user_speed_ratio" name="V4.1 1M ratio" -->
and 3.61× <!-- figure: 3.61 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash,context_tokens=1000000,batch_per_stage=32].same_batch_per_user_speed_ratio" name="V4.1 1M B32 ratio" -->
at the same points, at 13,369.1 tok/s per user for one user.

**The envelope band, stated because a central point is not a result.** Across
the conservative, central and aggressive ROM envelopes at 200K and batch 1 the
V4.1 per-user rate spans 1,722 <!-- figure: 1,722 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4.1-Flash,context_tokens=200000,batch_per_stage=1].rom_per_user_tokens_s_low" name="V4.1 band low" -->
to 58,181 <!-- figure: 58,181 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4.1-Flash,context_tokens=200000,batch_per_stage=1].rom_per_user_tokens_s_high" name="V4.1 band high" -->
tok/s and the same-batch ratio 1.13× <!-- figure: 1.13 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4.1-Flash,context_tokens=200000,batch_per_stage=1].same_batch_speed_ratio_low" name="V4.1 ratio low" -->
to 38.29× <!-- figure: 38.29 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4.1-Flash,context_tokens=200000,batch_per_stage=1].same_batch_speed_ratio_high" name="V4.1 ratio high" -->.
The conservative envelope is six wafers and 1,722 tok/s; the claim that
survives every envelope is only "faster than the GPU cluster", not by how much.

**The N7-class attribution study** (`results/iso-node/n7_architecture_attribution/`,
N7 ROM with HBM2e against A100 80 GB executing the packed checkpoint in BF16)
puts V4.1 at 9,359.2 <!-- figure: 9,359.2 src="results/iso-node/n7_architecture_attribution/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=1" name="V4.1 N7 rate" -->
tok/s per user against 564.5 for a 32-GPU cluster, 16.58× <!-- figure: 16.58 src="results/iso-node/n7_architecture_attribution/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4.1-Flash;B/stage=1" name="V4.1 N7 ratio" -->,
where V4-Flash is 13.10× <!-- figure: 13.10 src="results/iso-node/n7_architecture_attribution/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="V4-Flash N7 ratio" -->.

## 5. Array or wafer, at equal silicon: the roofline candidate study

`results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/`: mask ROM at TSMC
N5 against B200 packages at equal silicon area, each side choosing its own
parallelism, with the full link model and the per-layer fixed latency charged
to both. This is the study that answers the array-versus-wafer question; it is
a different contract from section 4 and its numbers must not be mixed with
them ([`METHODOLOGY.md`](METHODOLOGY.md) section 1). The candidate tree leaves
the primary artifacts untouched.

**Recommended design, by the report's own rule:** two N5 wafers, hybrid
parallel, KV in HBM. 4,069.8 <!-- figure: 4,069.8 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.per_user_tokens_s" name="V4.1 N5 recommended rate" -->
tok/s per user against 1,356.9 <!-- figure: 1,356.9 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.iso_area_gpu_per_user_tokens_s" name="V4.1 N5 iso-area GPU rate" -->
for 58 B200 packages of the same silicon, a 3.00× <!-- figure: 3.00 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.per_user_speed_ratio" name="V4.1 N5 iso-area ratio" -->
per-user ratio, holding 9,637 <!-- figure: 9,637 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.max_resident_users" name="V4.1 N5 resident sessions" -->
resident sessions against the GPU cluster's 49,172, at 19.2× <!-- figure: 19.2 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.tokens_per_joule_advantage_x" name="V4.1 N5 tokens per joule advantage" -->
the tokens per joule. The ratio grows with batch, to 9.73× <!-- figure: 9.73 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=DeepSeek-V4.1-Flash;B=32;Pick=fastest" name="V4.1 N5 ratio at B32" -->
at batch 32 and 13.20× <!-- figure: 13.20 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=DeepSeek-V4.1-Flash;B=64;Pick=fastest" name="V4.1 N5 ratio at B64" -->
at batch 64, because the GPU's per-user rate falls with batch and the ROM's
does not. Both sides bind on link latency at batch 1: the wafer on its 80
on-wafer all-reduces, the GPU on the same count over NVLink.

**The array.** The densest reticle array is 84 chips of 815 mm², tensor
parallel, at 1,633.4 <!-- figure: 1,633.4 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].class_comparison[topology_kind=array].best_by_throughput_density.per_user_tokens_s" name="V4.1 N5 array rate" -->
tok/s per user, 1.23× <!-- figure: 1.23 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].class_comparison[topology_kind=array].best_by_throughput_density.per_user_speed_ratio" name="V4.1 N5 array ratio" -->
the 43-package GPU cluster of the same silicon. Given the wafer's silicon, the
best array (110 chips) reaches 1,630.9 tok/s, 1.20× <!-- figure: 1.20 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md#speed ratio" table="DeepSeek-V4.1-Flash at 200,000 tokens" where="batch=1;class=array @ wafer area" name="V4.1 array at wafer area ratio" -->
its GPU comparator, so the wafer is 2.49× <!-- figure: 2.49 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md#Wafer/array" table="Topology choice" where="Model=DeepSeek-V4.1-Flash;B=1" name="V4.1 wafer over array at B1" -->
the array at batch 1 and about 3× from batch 4 upward. The cause is on the
page: a 510 GB checkpoint across 815 mm² reticles is 84 to 91 devices, so a
pipeline token crosses 39 hops, 51.34 µs <!-- figure: 51.34 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md#Link latency/token" table="Array or wafer" where="Design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-pipeline-x91" name="V4.1 array pipeline link latency" -->
of NVLink and InfiniBand latency per token, and a tensor-parallel token pays
80 all-reduces spanning 8 to 12 devices, 564.25 µs. The same 39 hops on a
stitched wafer cost 4.88 µs. For V4-Flash, whose checkpoint fits 30 reticles,
the primary study recommends the *array*: 2,627.4 <!-- figure: 2,627.4 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="V4-Flash N5 recommended rate" -->
tok/s per user at 1.79× <!-- figure: 1.79 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_speed_ratio" name="V4-Flash N5 recommended ratio" -->
its comparator. The larger model turns the array from the recommended machine
into the losing class, and it is the device count, not the model's work, that
does it.

**With the Engram tables in host memory** the checkpoint fits one N5 wafer:
the recommended design is a single tensor-parallel wafer at 5,037.3 <!-- figure: 5,037.3 src="results/roofline/candidates/deepseek-v41-flash-engram-host/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash-engram-host].recommended.per_user_tokens_s" name="engram-host N5 recommended rate" -->
tok/s per user, 3.90× <!-- figure: 3.90 src="results/roofline/candidates/deepseek-v41-flash-engram-host/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash-engram-host].recommended.per_user_speed_ratio" name="engram-host N5 ratio" -->
its iso-area comparator, and the best array is 51 chips at 2,058.0 tok/s.
At N6 against A100 (`results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/`)
the two-wafer design is 5.66× <!-- figure: 5.66 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.per_user_speed_ratio" name="V4.1 N6 ratio" -->
its comparator at 39.1× <!-- figure: 39.1 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4.1-Flash].recommended.tokens_per_joule_advantage_x" name="V4.1 N6 tokens per joule advantage" -->
the tokens per joule.

**Why 4,070 here and 14,200 in section 4.** They are different machines under
different contracts: section 4 sweeps three technology envelopes of an
N4-class wafer with pipeline stages and charges a collective floor; this study
fixes silicon area at N5, lets the wafer choose hybrid parallelism, and
charges a per-layer fixed latency and a full link model to both sides. The
program keeps the two pairs apart on purpose, and a reader should quote either
with its study named.

## 6. Can this project implement it?

**At the analytical layer, yes, and it did:** the profile, inventory, traffic
model, operator inventory and all three study families now carry the model.

**At the executable layer, nothing exists yet.** The V4 lane's compiler front
end, kernel IR, ABI 3.0 deployment, RTL vectors and reference oracle are all
V4-specific; none has been extended. Reading the released code against what
the ABI 3.0 operator families already cover:

| V4.1 mechanism | Nearest existing machinery | New work |
|---|---|---|
| CSA2 shared main KV and index K | the V4 CSA cache and index scan | scheduler semantics: a layer reads a cache another stage wrote; cross-stage placement of the four owners |
| Reuse-mode top-k reuse | the V4 top-k selection | none in the datapath; a selection result kept live across up to five layers |
| Hierarchical indexer candidate pool | `SELECTION` top-k | a blockwise max and a masked top-k; scored entries capped at 16,384 |
| Ratio-1 compressor | the V4 compressor | a plain BF16 projection; simpler than V4 |
| FP4 E2M1 main KV with E4M3 scale per 16 | the V4 MXFP4 index cache (E8M0 per 32) | a new numeric contract for the KV latent; dequantize before attention |
| Engram n-gram lookup and gate | `DMA.GATHER` / `EMBED_LOOKUP` for the V4 hash tables | 24 row gathers per module per token, a hash of the token ids, a normalized dot-product gate; 202.8 GB of ROM or a host path |
| Single-pass mHC | the V4 mHC projections | none; the coefficient shift is a scheduling change |
| DSpark speculative decoding | the V4 DSpark draft | none charged in these studies; speculation is a separate roofline layer |
| CED prefill and DeepSeek-ViT | -- | out of scope: this program models decode only |

No mechanism needs a new engine family. The two that need new *contracts* are
the FP4 KV latent and the Engram lookup; the one that needs new *evidence* is
the KV byte width, which for V4 turned out to differ by 1.8× from the recipe
when the released implementation was actually run.

**Where the Engram tables should live.** Three placements are possible on
the ROM machine, and only two are modelled above; the third is arithmetic on
the modelled ones and is stated as such.

| Placement | Capacity cost | Latency of the 24-row lookup | Verdict |
|---|---|---|---|
| mask ROM beside the weights | 202.8 GB of ROM: a third central N4 wafer, or 84 instead of 51 reticles at N5 | on-die, prefetchable at step start | pays a wafer of streamed-weight bandwidth for 12,672 B/token of reads; wrong use of ROM area unless the aggressive density envelope absorbs it |
| host DRAM over PCIe or RDMA, as DeepSeek serves it | none | one round trip of about 1 to 2 µs, the class this repository measures for RDMA (`links.infiniband_ndr.hop_latency_s`); the layer-1 module has only the embedding lookup and layer 0, about 1.8 µs of a 70 µs step, to hide it behind | invisible on a GPU cluster at 658 µs per token; a first-order term on a 14,200 tok/s machine, and one that grows as the machine gets faster |
| **the wafer's own edge HBM, beside the KV** | 202.8 GB of the 1,440 GB central HBM, about 1,100 sessions of 200K KV out of 11,983 (author's arithmetic: 202.8 GB / 180.7 MB) | a random HBM read of a few hundred nanoseconds, prefetchable at step start since the address is a function of the token ids alone; 12,672 B/token is under 1 GB/s at the wafer's aggregate rate against 38.75 TB/s of HBM | **the placement to design for**: no wafer added, no PCIe on the token's critical path, written once at load and never again |

The two modelled placements bracket it: `DeepSeek-V4.1-Flash-engram-host`
gives its per-user rate and stage count exactly, and the KV capacity it
gives up is the only correction. Adding it as a third modelled placement is a
one-field change to the deployment model and is the natural next step.

**What would move these numbers, in order of size.**

1. **KV precision as executed.** If a deployment reads the latent wider than
   288 B, every KV-side number in sections 3 to 5 scales with it. Measuring the
   released implementation at five contexts, as `tools/run_deepseek_v4_reference_oracle.py`
   does for V4, is the first executable step.
2. **The unpriced auxiliary paths.** Index scoring, top-k, Sinkhorn and the
   Engram gate are reported as break-even rates, not priced (`COMP-01`). The
   decoder's Full layer scans the whole context every token; at 1M that is
   one million 68-byte keys through the indexer on one layer.
3. **Wafer count and capital.** Three central wafers, or two with the tables
   in host memory, against one for V4-Flash. The partial TCO already carries
   it; the cycle model and the physical evidence do not, since no V4.1
   deployment has been compiled.
4. **The model has never produced a token here**, on any lane, at any
   precision. Everything above is arithmetic on published shapes.

## 7. What changed in the repository

- `src/opentallas/schema.py`: four cross-layer sharing fields on `AttentionGroup`; ratio 1 admitted for `compressed_sparse`; serialisation omits the fields at their defaults.
- `src/opentallas/workload.py`, `roofline.py`, `deployment.py`: honour the fields; the default path is the original arithmetic verbatim.
- `src/opentallas/profiling.py`: `deepseek_v41` adapter, the `engram_host` placement variant, per-role parameter counts and lookup-table bytes in every new inventory.
- `src/opentallas/operations.py`: `deepseek_v41_official_operator_inventory_v1`.
- `configs/models/candidates/`, `data/inventory/deepseek-v4.1-flash.json`: the generated profiles and inventory.
- `configs/hardware/technology.json`: two `array_pass_boundaries_per_layer_by_model` entries, graded `assumed` like their V4 siblings.
- `tools/run_iso_node_studies.py`, `run_model_traffic_screen.py`, `run_roofline_studies.py`: the model as extra rows, and the `results/roofline/candidates/` tree.
- `tests/test_deepseek_v41_profile.py`: the published figures the profile must reproduce, and the schema additions' refusals.
- `docs/SOURCES.md`: `SRC-DSV41-FLASH-CARD`, `-REPORT`, `-CONFIG`, `-MODEL`, `-INDEX`.
