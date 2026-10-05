import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qwen_rom_q2_g0_packet import ROOT, digest, verify_snapshot, finite_service_scenarios


def test_serialized_refill_cannot_inherit_aggregate_bandwidth():
    r = finite_service_scenarios((ROOT / 'rtl/hdc/kv/ot_hdc_hbm_model.sv').read_text())
    assert r['row_hit']['service_ps'] == 33524
    assert r['row_hit']['cycles_at_1p2GHz'] == 41
    assert r['row_hit']['serialized_service_only_cycles_per_4MiB_layer'] == 5373952
    assert r['row_conflict_plus_refresh']['cycles_at_1p2GHz'] > r['row_conflict']['cycles_at_1p2GHz']


def test_portable_replay_rejects_changed_provider(tmp_path):
    raw = b'provider source'
    (tmp_path / 'source.sv').write_bytes(raw)
    (tmp_path / 'provider_manifest.json').write_text(json.dumps({'files': [dict(
        source_path='rtl/provider.sv', snapshot='source.sv', sha256=digest(raw))]}))
    verify_snapshot(tmp_path)
    (tmp_path / 'source.sv').write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        verify_snapshot(tmp_path)
