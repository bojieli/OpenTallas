from tools.qwen_g4_trace_banks import check

def test_broadcast_word_can_serve_several_scalar_lanes():
    r=check([{'cycle':0,'code_addr':0,'vm_reads':[{'group':g,'addr':g} for g in range(4)]}])
    assert not r['problems']

def test_different_words_same_bank_need_arbitration():
    r=check([{'cycle':0,'vm_reads':[{'group':0,'addr':0},{'group':1,'addr':64}]}])
    assert r['problems'][0][1]=='vm_read_port'

def test_same_cycle_rw_not_assumed_safe():
    r=check([{'cycle':0,'vm_reads':[{'group':0,'addr':0}], 'vm_writes':[{'group':0,'addr':0,'mask':1}]}])
    assert r['problems'][0][1]=='vm_read_during_write_unqualified'

def test_depth_and_scale_ports_checked():
    r=check([{'cycle':1,'code_addr':8192,'scale_reads':[{'group':0,'addr':0},{'group':0,'addr':1}]}])
    assert {x[1] for x in r['problems']}=={'code_depth','scale_port'}

def test_source_trace_rejects_simple_modulo_banking():
    from pathlib import Path
    from tools.qwen_g4_trace_banks import load_csv
    p=Path(__file__).resolve().parents[1]/'results/contracts/qwen_g4_boundary_trace.csv.gz'
    r=check(load_csv(p))
    assert r['cycles_examined']==5208
    assert len(r['problems'])==192
    assert {x[1] for x in r['problems']}=={'vm_read_port','vm_write_port'}
