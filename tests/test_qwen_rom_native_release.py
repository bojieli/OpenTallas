import collections
import gzip
import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_native_release_audit as K
J=K.J


@pytest.fixture(scope='module')
def records():
    return J.record('model-r3.json'),K.allocation().g


def test_actual_map_and_every_reset_sink_once(records):
    m,g=records
    assert m['selected_map_sha256']==J.M.MAP_SHA
    controlled=[n for q in g['local_release_groups'] for n in q['reset_targets']]
    assert len(controlled)==len(set(controlled))==56683
    assert set(controlled)==set(g['reset_direct_sinks'])|set(g['metadata_reset_sinks'])
    assert len(g['local_release_groups'])==7133
    assert m['total_clock_pins']==102352+2*7133+2
    assert m['total_reset_pins']==56683+2*7133+2
    assert m['provider_two_FFs_separate']
    assert all(1<=len(q['reset_targets'])<=8 for q in g['local_release_groups'])


def test_all_new_raw_reset_pins_and_corners_included(records):
    m,g=records
    expected={f for q in g['local_release_groups'] for f in q['FFs']}|set(g['ACK_receiver_FFs'])
    for c,t in m['timing'].items():
        assert {r['instance'] for r in t['raw_reset_checks']}==expected
        assert len(t['controlled_reset_checks'])==56683
        assert t['raw_reset_failures']==sum(r['fail'] for r in t['raw_reset_checks'])
        assert t['controlled_reset_failures']==sum(r['fail'] for r in t['controlled_reset_checks'])
    assert set(m['timing'])=={'ss','ff'}


def test_cell_sites_no_overlap_or_rotated_standard_cells(records):
    _,g=records;rows=collections.defaultdict(list)
    for n,p in g['cell_sites'].items():
        if 'pin_CLK_rect_M4_um' in p:continue
        assert p['orientation'] in ('R0','MX')
        x,y=p['origin_um'];w,h=p['size_um']
        assert h==pytest.approx(.270)
        assert x/.054==pytest.approx(round(x/.054))
        assert y/.270==pytest.approx(round(y/.270))
        assert x>=0 and x+w<=357.696+1e-8 and y>=0 and y+h<=1360.8+1e-8
        rows[round(y/.270)].append((x,x+w,n))
    for row in rows.values():
        row.sort()
        assert all(a[1]<=b[0]+1e-8 for a,b in zip(row,row[1:]))


def test_source_capture_pin_membership_and_macro_halo(records):
    _,g=records;receipt=K.R.obj(J.A.OUT/'inputs/capture-connectivity.json')
    assert receipt['map_SHA256']==J.M.MAP_SHA
    names=[n for r in receipt['macros'] for n in r['first256_direct_capture_FF_D']]
    assert len(names)==len(set(names))==2560
    macros=[p for p in g['cell_sites'].values() if 'pin_CLK_rect_M4_um' in p]
    assert len(macros)==12
    for n in names:
        p=g['cell_sites'][n];x,y=p['origin_um'];w,h=p['size_um']
        assert all(not (x<a+b+.54 and x+w>a-.54 and y<c+d+.54 and y+h>c-.54)
            for a,c,b,d in [(q['origin_um'][0],q['origin_um'][1],q['size_um'][0],q['size_um'][1]) for q in macros])


def test_ack_topology_every_group_no_constant_ready(records):
    m,g=records;incoming=collections.defaultdict(list)
    for e in g['ACK_edges']:incoming[e['sink']].append(e['driver'])
    pending=[g['ACK_root']];seen=set()
    while pending:
        n=pending.pop()
        if n in seen:continue
        seen.add(n);pending.extend(incoming[n])
    assert {q['inversions'][1] for q in g['local_release_groups']}<=seen
    # Six reset-bearing regions; the centre provider's clock-only region is
    #not an invented seventh local reset owner.
    assert len(g['ACK_regional_roots'])==6
    assert m['physical_cell_types'][J.AND]==3583
    assert 'current' in m['startup_ACK'].lower() and 'abort' in m['startup_ACK']
    assert 'benchmark' in m['contextual_accepted_demand']


def test_area_and_cut_accounting_do_not_admit_route(records):
    m,g=records;types=collections.Counter(p['type'] for p in g['release_physical_cells'])
    area=65983.07303971479+23.80914+1.44342+len(g['added_primitive_cells'])*.10206+types[K.R.ASR]*.37908+types[J.INV]*.04374+types[J.AND]*.08748+486*.10206
    assert m['complete_reserved_cell_area_um2']==pytest.approx(area)
    assert m['field1536_cell_area_mm2']==pytest.approx(area*1536/1e6)
    assert area<125000
    assert all(c['clock']<=64 and c['reset_ACK']<=64 for c in m['cuts'].values())
    assert not any(m[k] for k in ('source_map_admission','contextual_SSFF','accepted_demand_admission','PnR','default_enabled'))
    assert m['additional_maps']==m['numerical_runs']==0
    assert all(max(s['skew_ps'] for s in t['nominal_same_source_clock_scenarios'])>20 for t in m['timing'].values())
    assert 'cell_pin_landing_vias' in m['unqualified']
    assert 'Not a completed physical provider' in m['complete_reserved_cell_area_scope']


def test_phase_is_constraint_sized_and_original_failures_preserved(records):
    m,g=records;phase=g['assert_phase_construction']
    assert phase['required_extra_SS_delay_window_ps'][0]>0
    assert phase['derived_stages']>0 and phase['wire_per_stage_um']==16
    old=J.record('model-r1.json')
    assert old['timing']['ss']['raw_reset_failures']==38
    assert old['timing']['ss']['nominal_same_source_clock_scenarios'][0]['skew_ps']>1700
    assert m['preserved_prior_model_sha256']==hashlib.sha256(J.model_bytes('model-r2.json')).hexdigest()


def test_frozen_sources_artifacts_and_cold_audit(records):
    m,_=records
    assert json.loads(json.dumps(K.price()))==m
    for name in ('sourcepins-r3.json','artifact-sha256-r3.json'):
        for p,h in K.R.obj(K.OUT/name).items():
            assert hashlib.sha256((K.R.ROOT/p).read_bytes()).hexdigest()==h


def test_lossless_archives_preserve_all_original_negative_records():
    for directory in (J.G.OUT,J.H.OUT,J.A.V.OUT,J.OUT):
        for name,record in K.R.obj(directory/'lossless-model-archives.json').items():
            raw=gzip.decompress((K.R.ROOT/name).read_bytes())
            assert len(raw)==record['decompressed_bytes']
            assert hashlib.sha256(raw).hexdigest()==record['decompressed_sha256']
