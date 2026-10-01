import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_kv_state import capture

def test_original_two_token_publications_preserve_generation_and_produced_hashes():
    root = Path(__file__).resolve().parents[1]
    result = capture(root/'results/rtl/qwen_hbm_complete_20261001/actual_two_token_terminal_r1', root)
    rows = result['publications']
    assert {(r['position'], r['layer'], r['die']) for r in rows} == {
        (p, l, d) for p in range(2) for l in range(36) for d in range(2)}
    assert [r['publication_tag'] for r in rows] == list(range(144))
    assert result['committed_payload_bytes'] == 147456
    assert not result['encoded_KV_payload_dump_retained']
    assert result['token_cycles'] is None
