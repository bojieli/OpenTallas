# Replay: DeepSeek-V4.1 single-user context capacity risk check (2026-10-03)

```
python3 results/uarch/risk_ds_context_capacity_20261003/compute.py > results/uarch/risk_ds_context_capacity_20261003/capacity.json
```

Inputs:
- the released config `~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a.../config.json`;
- the byte constants in `tools/arch_budget_v41.py:201-203`;
- `results/arch/arch_budget_v41.json` (`hbm_comparator`, `workload`).

The script is CPU-only and needs no download. The cross-checks it reproduces are:
- `per_user_bytes_busiest_die` (93,458,432 B at 1M);
- `workload.1048576.totals.bytes.idx` (182,714,368 B).

Semantics were read from the released `inference/model.py`:
- `Compressor` (lines 429-486);
- `Indexer.forward` (527-590);
- `select_candidate_blocks` (593-610);
- `Attention` buffers (663-681);
- `NgramHashState.cache` (`inference/engram.py:155-172`).

`verdict.json` holds the verdict, the conditions and the defect list (file:line).
