#!/usr/bin/env python3
"""DS V4.1-Flash single-user context capacity/bandwidth check (risk audit 2026-10-03).

Derives per-user DECODE state and per-token HBM reads from the released config and the
released inference/model.py semantics, using the repo's byte constants
(tools/arch_budget_v41.py:201-203), and checks them against the per-die HBM of the ROM
array and the DS HBM comparator (results/arch/arch_budget_v41.json hbm_comparator).
"""
import glob, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import arch_budget_v41 as A  # noqa: E402

snap = sorted(glob.glob(str(Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/*/")))[0]
cfg = json.load(open(Path(snap) / "config.json"))["text_config"]
L = cfg["num_hidden_layers"]
ratios = cfg["compress_ratios"]                 # 43 entries: 40 backbone + 3 MTP
kv_src = cfg["kv_source_layer_ids"]             # [2, 8, 14, 20]: own compress_kv_cache and index k_cache
idx_src = cfg["index_source_layer_ids"]         # [2, 8, 14, 20, 24, 28, 32, 36]: run the indexer
cand_src = cfg["candidate_source_layer_id"]     # 20
CAND_POS = cfg["candidate_topk_blocks"] * cfg["candidate_block_size"]   # 16,384 positions scanned by 24..36
TOPK, WIN = cfg["index_topk"], cfg["sliding_window"]
CKV, IDX, WINB = A.CKV_ROW_B, A.IDX_KEY_B, A.WIN_ROW_B   # 288, 68, 528 B (FP4/FP4/FP8 + scales)
CKV_BF16, IDX_BF16 = cfg["head_dim"] * 2, cfg["index_head_dim"] * 2   # unpacked upper bound

bud = json.load(open(ROOT / "results/arch/arch_budget_v41.json"))
hb = bud["hbm_comparator"]
EFF = 0.9
STACK_B, STACK_BPS = hb["stack_capacity_B"], hb["stack_bw_Bps"] * 0.9
ROM_STACKS = A.ROM_DIE_HBM_STACKS
ROM_DIE_USABLE = EFF * ROM_STACKS * STACK_B
HBM_DIE_USABLE = EFF * hb["hbm_stacks_per_die"] * STACK_B - hb["weights_B"] / hb["dies"]
GROUP = 4                 # a layer group's dies (capacity_limit: state split over the group's 4 dies)
READER_BPC, CLK = 60 * 32, 1.2e9   # measured four-stack index reader (tools/uarch_model.py:125); streaming clock


def state(N):
    per = {}
    for l in kv_src:
        r = ratios[l]
        rows = N // r
        per[f"L{l}"] = dict(ratio=r, rows=rows, compressed_kv_B=rows * CKV, index_keys_B=rows * IDX,
                            compressed_kv_bf16_B=rows * CKV_BF16, index_keys_bf16_B=rows * IDX_BF16)
    win = len(ratios) * WIN * WINB                       # one 128-row ring per attention layer (40 + 3 MTP)
    comp_tail = sum(2 * r * cfg["head_dim"] * 4 for l in kv_src if (r := ratios[l]) > 1)  # kv_state+score_state fp32
    engram_hist = (cfg["engram_max_ngram_size"] - 1) * 8  # last 3 compressed token ids (reference keeps a max_seq_len int64 log)
    packed = sum(v["compressed_kv_B"] + v["index_keys_B"] for v in per.values()) + win + comp_tail + engram_hist
    bf16 = sum(v["compressed_kv_bf16_B"] + v["index_keys_bf16_B"] for v in per.values()) + len(ratios) * WIN * cfg["head_dim"] * 2 + comp_tail + engram_hist
    l20 = per[f"L{cand_src}"]
    busiest_die = (l20["compressed_kv_B"] + l20["index_keys_B"]) / GROUP + 2 * WIN * WINB
    return dict(N=N, per_source_layer=per, window_rings_B=win, compressor_tail_B=comp_tail,
                engram_history_B=engram_hist, total_packed_B=packed, total_bf16_upper_B=bf16,
                busiest_rom_die_B=busiest_die,
                worst_case_all_state_on_one_die_B=packed)


def token_reads(N):
    scans = {}
    for l in idx_src:
        src = max(s for s in kv_src if s <= l)          # shared_attn.index_k = the latest owner's k_cache
        keys = N // ratios[src]
        if l > cand_src:
            keys = min(keys, CAND_POS)                   # level two scans only the 2,048 candidate blocks
        scans[f"L{l}"] = dict(source=src, keys=keys, bytes=keys * IDX)
    scan_B = sum(s["bytes"] for s in scans.values())
    gather_layers = sum(1 for l in range(L) if ratios[l])        # every compressed layer gathers top-512 rows
    gather_B = gather_layers * min(TOPK, N) * CKV
    l20_die = scans[f"L{cand_src}"]["bytes"] / GROUP
    return dict(N=N, scans=scans, scan_B=scan_B, gather_layers=gather_layers, gather_B=gather_B,
                total_B=scan_B + gather_B,
                l20_die_scan_B=l20_die,
                l20_die_scan_us_at_hbm=l20_die / (ROM_STACKS * STACK_BPS) * 1e6,
                l20_die_scan_us_at_measured_reader=l20_die / READER_BPC / CLK * 1e6,
                all_scans_serial_us_at_measured_reader=sum(s["bytes"] / GROUP / READER_BPC / CLK * 1e6 for s in scans.values()),
                decode_score_row_fp32_B=(N // ratios[cand_src]) * 4,
                candidate_mask_row_u8_B=N // ratios[cand_src],
                artefact_declared_score_B_bf16=262144 * 262144 * 2)


def prefill(N, chunk=8192):
    ih = cfg["index_n_heads"] * cfg["index_head_dim"]
    idx = 0
    for l in idx_src:
        src = max(s for s in kv_src if s <= l)
        r = ratios[src]
        idx += ih * (CAND_POS * N if l > cand_src else N * N / (2 * r))
    dense = bud["workload"]["8192"]["totals"]["macs_total"] - bud["workload"]["8192"]["totals"]["macs"]["indexer:fp4"]
    return dict(N=N, chunk=chunk, indexer_macs=idx, other_macs=dense * N, total_macs=idx + dense * N,
                materialised_chunk_score_B_bf16_L20=chunk * (N // ratios[cand_src]) * 2,
                materialised_chunk_score_B_per_die=chunk * (N // ratios[cand_src]) * 2 / GROUP,
                streamed_chunk_topk_B=chunk * TOPK * 4)


out = dict(schema="risk_ds_context_capacity/1", hf_snapshot=snap,
           per_die=dict(rom_stacks=ROM_STACKS, stack_B=STACK_B, rom_die_usable_B=ROM_DIE_USABLE,
                        rom_die_Bps=ROM_STACKS * STACK_BPS, hbm_comparator_dies=hb["dies"],
                        hbm_comparator_stacks=hb["hbm_stacks_per_die"], hbm_die_usable_after_weights_B=HBM_DIE_USABLE,
                        measured_index_reader_Bps=READER_BPC * CLK),
           contexts={})
for N in (200_000, 1_048_576):
    s, t, p = state(N), token_reads(N), prefill(N)
    s["rom_busiest_die_fraction"] = s["busiest_rom_die_B"] / ROM_DIE_USABLE
    s["rom_one_die_worst_fraction"] = s["total_packed_B"] / ROM_DIE_USABLE
    s["rom_one_die_worst_bf16_fraction"] = s["total_bf16_upper_B"] / ROM_DIE_USABLE
    s["hbm_comparator_one_die_worst_fraction"] = s["total_packed_B"] / HBM_DIE_USABLE
    out["contexts"][str(N)] = dict(state=s, token=t, prefill=p)
json.dump(out, sys.stdout, indent=1)
