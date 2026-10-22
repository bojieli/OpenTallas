from copy import deepcopy
from types import SimpleNamespace as I
from qwen_split.reset_region_capture import finalize


def model():
    return dict(insts=[I(name=n,master=m,kind=k) for n,m,k in [
        ('p','qfd_rst_rep','reset_rep'),('leaf','qfd_rst_rep','reset_rep'),
        ('a','blk','block'),('b','blk','block'),('h','qfd_rlyh0_1_EN','relay')]],
        buses=[('up','reset',1,[('p','q0'),('leaf','d')]),
               ('out','reset',1,[('leaf','q0'),('a','rst_n'),('h','en')])])


def test_final_root_overrides_stale_follow_and_column_split():
    m=model();per={0:[('p','clk'),('leaf','clk')],1:[('a','ck'),('h','ck')]}
    r=finalize(m,per)
    assert ('leaf','clk') in per[1] and ('leaf','clk') not in per[0]
    assert r['moved'][0]['clock']=='clk_r1'
    assert r['sync_candidates'][0]['pin']=='leaf/d'
    assert not r['qualified'] and r['calendar'].startswith('HOLD')
    # Repeating final clock refiling never changes this exact ownership.
    assert not finalize(m,per)['moved']


def test_every_output_is_checked_no_majority_or_unplaced_clone():
    m=model();m['buses'].append(('other','reset',1,[('leaf','q1'),('b','rst_n')]))
    per={0:[('p','clk'),('leaf','clk')],1:[('a','ck'),('h','ck')],2:[('b','ck')]}
    original=deepcopy(per);before=len(m['insts'])
    r=finalize(m,per)
    assert per==original and len(m['insts'])==before
    assert r['split_required'][0]['receiving_roots']==['clk_r1','clk_r2']


def test_one_frame_enable_uses_sender_not_reader_clock():
    m=model();m['insts'][-1].master='qfd_landh0_1_EN'
    per={0:[('p','clk'),('leaf','clk')],1:[('a','ck'),('h','ck_s')],2:[('h','ck')]}
    r=finalize(m,per)
    assert r['moved'][0]['clock']=='clk_r1' and not r['split_required']


def test_unknown_or_multiple_child_clock_cannot_be_assumed_equal():
    m=model();per={0:[('p','clk'),('leaf','clk')],1:[('h','ck')]}
    assert finalize(m,per)['unresolved']
    m=model();per={0:[('p','clk'),('leaf','clk')],1:[('a','ck'),('h','ck')],2:[('a','ck_other')]}
    assert finalize(m,per)['split_required']


def test_declared_per_port_clock_selects_real_child_region():
    m=model();m['dv_cluster_clocks']=dict(master='blk',related_pins=dict(rst_n=['ck']))
    per={0:[('p','clk'),('leaf','clk')],1:[('a','ck'),('h','ck')],2:[('a','ck_other')]}
    r=finalize(m,per)
    assert r['moved'][0]['clock']=='clk_r1'
