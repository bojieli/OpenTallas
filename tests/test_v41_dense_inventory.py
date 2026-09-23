from tools.audit_v41_dense_inventory import category


def test_shared_experts_are_not_routed_experts_or_router():
    assert category('layers.0.ffn.shared_experts.w1.weight') == 'shared_expert'
    assert category('layers.0.ffn.gate.bias_vl') == 'router'


def test_window_projection_and_shared_cache_producers_remain_distinct():
    assert category('layers.0.attn.wkv.weight') == 'attention_projection_and_norm'
    assert category('layers.2.attn.compressor.wkv.weight') == 'attention_compressor'
    assert category('layers.2.attn.indexer.wq_b.weight') == 'attention_indexer'


def test_engram_projection_is_not_table_service():
    assert category('layers.1.engram.wkv.weight') == 'engram_projection_and_gate'
    assert category('head.weight') == 'head'


def test_v41_header_reconciliation_and_conditional_bias():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    audit = json.loads((root/'results/architecture/v41_dense_inventory.json').read_text())
    inv = json.loads((root/'data/inventory/deepseek-v4.1-flash.json').read_text())
    assert sum(r['bytes'] for r in audit['tensor_rows']) == inv['decode_dense_bytes']
    assert len({r['name'] for r in audit['tensor_rows']}) == len(audit['tensor_rows'])
    assert audit['text_no_image_mask_known_inactive_bias_bytes'] == 40 * 384 * 4
    assert sum(inv[k] for k in ('decode_dense_bytes','decode_routed_bytes','draft_dense_bytes','draft_routed_bytes','resident_only_bytes')) == inv['checkpoint_bytes']
