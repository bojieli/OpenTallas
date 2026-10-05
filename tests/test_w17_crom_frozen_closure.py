from tools.w17_crom_frozen_closure import build

def test_retained_layout_hole_and_padding():
    r=build();l=r['layout']
    assert l['L14_span'][0]==l['invalid_source_hole'][1]
    assert l['padding_span'][0]==l['L14_span'][1]
    assert l['padded_words']==45*4096*3
    for x in r['ranks']:
        assert len(x['banks'])==45 and sum(b['bytes'] for b in x['banks'])==552960*8
        assert x['complete_image_sha256'] is None and not x['complete']
        assert [b['source_valid'] for b in x['bindings']]==[False,True]
        assert all(b['actual_encoded_base'] is None for b in x['bindings'])
    assert not r['hardware_admission'] and not r['complete_frozen_image']

def test_finite_ports_not_instant_fanout():
    r=build();s=r['finite_service']
    assert s['gamma_floor_fast_cycles']*16==414720
    assert s['gamma_home_selected_output_floor_cycles']*16==5120
    assert s['burst_drain_cycles']*16>=135
    assert not s['instantaneous_1024_lane_gamma_delivery']
