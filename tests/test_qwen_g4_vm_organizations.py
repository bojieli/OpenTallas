from tools.qwen_g4_vm_organizations import evaluate, report

def test_skew8_fits_supplied_trace_without_replication():
    x=report()['candidates'][4]
    assert x['unchanged_trace_ports_fit'] and x['storage_replication']==1
    assert x['max_distinct_reads_per_bank']==x['max_distinct_writes_per_bank']==1

def test_four_banks_need_read_replication_after_write_skew():
    a,b=report()['candidates'][2:4]
    assert a['events']['read_conflict_cycles']==64
    assert not a['events']['write_conflict_cycles']
    assert b['unchanged_trace_ports_fit'] and b['storage_replication']==2

def test_disjoint_same_word_writes_merge_but_overlap_rejected():
    def row(mask):return [{'vm_reads':[], 'vm_writes':[{'addr':0,'mask':1},{'addr':0,'mask':mask}]}]
    assert evaluate(row(2))['unchanged_trace_ports_fit']
    assert not evaluate(row(1))['unchanged_trace_ports_fit']

def test_lane_banks_do_not_fix_full_word_stride_conflict():
    x=report()['candidates'][1]
    assert x['events']['write_conflict_cycles']==128

def test_skew8_capacity_mapping_is_bijective():
    locations={((word^(word>>2))&7,word>>3) for word in range(4096)}
    assert len(locations)==4096
    assert max(row for bank,row in locations)==511
