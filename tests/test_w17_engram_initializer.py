from tools.w17_engram_initializer import build

def test_physical_streams_and_serialization():
    r=build(); t=r['transport']
    assert r['arithmetic']['vectors']*1024==20480
    assert t['input_flits_per_vector']*t['link_bits_per_fast_cycle']==4*1024*32
    assert t['output_flits_per_vector']*1024==1024*32
    assert t['required_corridors']*1153>=t['total_tracks']>2*1153

def test_storage_lifetime_and_failed_closed():
    r=build()
    for p in r['points']:
        assert p['resident_bytes_per_home']+p['spare_bytes_per_home']==524288
        assert p['complete_initialization_us'] is None and not p['admission']
    assert r['points'][1]['resident_bytes_per_home']==491520
    assert not r['scratch']['existing_VM_tail_safe']
    assert not r['lifetime']['runtime_ROM_write_possible']
    assert r['full_token_cycles'] is None and not r['admission']

def test_no_overlap_calendar_and_source_hashes():
    r=build(); c=r['calendar']
    assert c['ticks_per_layer']==12+20*sum(x['ticks'] for x in c['per_vector_events'])
    assert len(r['source_pins'])==6
    assert all(len(x['sha256'])==64 for x in r['source_pins'])
