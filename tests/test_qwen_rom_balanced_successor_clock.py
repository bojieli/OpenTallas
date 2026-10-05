import gzip
import hashlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_balanced_successor_clock as B

@pytest.fixture(scope='module')
def record():return B.R.obj(B.OUT/'model-r1.json')

def test_exact_successor_endpoints_and_provider_included(record):
    assert record['successor_clock_ports']==102352
    assert record['physical_clock_pins']==102354
    assert record['successor_reset_pins']==56683
    assert record['additional_provider_clock_FFs']==2
    assert record['additional_maps']==record['numerical_runs']==0
    assert record['source_map_admission'] is False

def test_equal_depth_paid_branch_geometry_and_no_ideal_wires(record):
    base=B.R.ROOT/B.OUT
    g=json.loads(gzip.decompress((base/'balanced-clock-allocation-r1.json.gz').read_bytes()))
    assert len(g['clock_sinks'])==102353 # one provider port owns two FFs
    assert len(g['added_primitive_cells'])==record['paid_clock_buffers']
    assert record['paid_clock_buffer_area_um2']==pytest.approx(record['paid_clock_buffers']*.10206)
    assert all(0<e['length_um']<=128+1e-8 for e in g['wire_edges'])
    assert record['total_meander_reservation_um']>0
    incoming={e['sink']:e['driver'] for e in g['wire_edges']}
    depths=set()
    for row in g['clock_sinks']:
        n=row['instance'];depth=0
        while n in incoming:n=incoming[n];depth+=1
        depths.add(depth)
    assert len(depths)==1

def test_correlated_clock_characterization_keeps_admission_open(record):
    for r in record['clock_price'].values():
        assert {s['common_primary_clock_slew_ps'] for s in r['scenarios']}=={5,80}
        assert r['demanded_skew_ps']==20
        assert r['continuous_source_slew_and_extracted_skew_qualified'] is False
        for s in r['scenarios']:
            assert s['max_BUF_cap_fF']<=46.08
            assert s['max_slew_ps']<=320
    assert len(record['failed_unbalanced_evidence_preserved'])==3
    assert record['installed_CTS_precondition'] is False
    assert record['PnR'] is False

def test_manifest_hashes(record):
    base=B.R.ROOT/B.OUT
    for p,d in json.loads((base/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((B.R.ROOT/p).read_bytes()).hexdigest()==d,p
    for p,d in json.loads((base/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((base/p).read_bytes()).hexdigest()==d,p
