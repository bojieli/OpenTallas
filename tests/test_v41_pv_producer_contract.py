from tools.v41_pv_producer_contract import replay, report

def test_actual_preload_is_scalar_and_dominates_stream():
    a,b=replay(pwords=1),replay(pwords=2)
    assert a['preload_issue_cycles']==b['preload_issue_cycles']==2560
    assert a['accepted_beats']==320 and b['accepted_beats']==160
    assert a['lower_bound_preload_plus_stream']==2880
    assert b['lower_bound_preload_plus_stream']==2720

def test_two_row_banks_cannot_supply_four_rows_per_head():
    assert replay(pwords=2,row_banks=2)['stream_bank_conflicts']>0
    r=replay(pwords=2,row_banks=4)
    assert r['stream_bank_conflicts']==r['preload_bank_conflicts']==0

def test_partial_blocks_nonzero_payload_and_backpressure():
    for rows in (1,2,3,31,32,33,639,640):
        for width in (1,2):
            r=replay(rows=rows,pwords=width,stall_period=3)
            assert r['exact_nonzero_elements']==16*rows
            assert r['stream_elapsed_cycles']>r['accepted_beats']

def test_claim_scope():
    r=report()
    assert 'not_rtl' in r['status'] and r['unresolved']
    assert len(r['source_pins'])==3
