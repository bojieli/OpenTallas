"""Reject partial arithmetic joins and macro capacity/source misqualification."""
import base64
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_integration_preflight as P

ROOT=Path(__file__).resolve().parents[1]


def package():
 return json.loads((ROOT/'results/rtl/qwen_rom_sidecar_20261002/tp4_capture_v2.json').read_text())


def test_real_connected_companion_missing_whole_arithmetic_chain():
 r=P.prepare(package())
 for name in P.ARITH:
  row=r['arithmetic_chain'][name]
  assert row['tile_declared'] and row['spine_declared']
  assert row['tile_forwarded_to_engine'] and row['spine_forwarded_to_engine']
  assert row['die_declared'] and row['generated_core_declared_and_forwarded']
  assert not row['driver_tile_flag']  # Static direct-flag gate stays blocked; opt-in execution is refused.
 assert r['status']=='blocked' and not r['build_ready'] and not r['adoption']
 assert r['kv_connection']['driver_forces_global'] and r['kv_connection']['host_reads_global_kv']
 assert not r['kv_connection']['local_macro_fill_connected']
 assert set(r['source_reconciliation'])==set(P.MAPPING)


def test_runtime_source_tamper_is_rejected():
 p=package();key='source/rtl/hdc/ot_qwen_rom_tile.sv'
 p['files'][key]['base64']=base64.b64encode(b'module wrong; endmodule').decode()
 with pytest.raises(ValueError,match='pin mismatch'):P.source_reconcile(p,ROOT)


def test_pinned_physical_arithmetic_prices_the_multiplier_cut():
 # Exact full-tree event-time contract in the retained partition bench.
 bench=(ROOT/'rtl/test/tb_qwen_me_partition_w12.sv').read_text()
 assert '(MUL_LAT - 5) + (ACC_LAT - 5) + $clog2(GT) * (TREE_LAT - 3)' in bench
 r=P.prepare(package())
 assert P.latency_extra(6144,7,7,5)==54
 assert P.latency_extra(6144,7,7,6)==55
 assert r['model']['unpriced_cycles_per_me']==1
 assert not r['build_ready']


def test_tp4_actual_macro_slice_capacity_and_region_extremes():
 r=P.kv_geometry();heads=2;prk=6144>>7
 # Enumerate all head/position-tile K indices independently of the region formula.
 k={t//prk*heads+h for t in range(8192//16) for h in range(heads)}
 assert max(k)==21 and len(k)==r['K_local_words']==22
 assert r['V_local_words']==22 and r['total_local_words']==44 and r['capacity_fits']
 assert r['KV_VB']==131072 and r['macro_count_per_die']==3072
 assert r['macro_capacity_bytes_per_die']==12*1024*1024


def test_larger_legal_address_window_can_still_exceed_real_macro_capacity():
 assert P.kv_geometry(context=16384)['capacity_fits']
 r=P.kv_geometry(context=32768)
 assert not r['capacity_fits'] and r['total_local_words']==172


@pytest.mark.parametrize('kw', [dict(tp=3),dict(context=0),dict(context=8191),dict(groups=4)])
def test_invalid_geometry_never_supplies_sizing(kw):
 with pytest.raises(ValueError):P.kv_geometry(**kw)


def test_missing_module_parameter_header_is_not_a_join():
 with pytest.raises(ValueError,match='Missing actual module'):P.declared('module different; endmodule','target')
