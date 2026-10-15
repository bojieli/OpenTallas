"""Numeric source identity and fail-closed ABI checks for current parallel writeback."""
from dataclasses import dataclass
from collections import Counter
import pytest
from qwen_split import res_train_bind as rtb
from qwen_split.source_pin_plan import rtl_ports


@dataclass
class Inst:
    name: str
    master: str
    x: float = 100
    y: float = 100
    w: float = 777.6
    h: float = 518.4
    orient: str = 'R0'
    kind: str = 'spine'
    region: str = 'spine'
    domain: str = 'stream'


def _model():
    insts = [Inst(f'sp_res_ser_{b}', 'qfd_sp_res_ser', y=100+600*b) for b in range(3)]
    insts += [Inst(f'sp_port_tiles_{b}', f'qfd_port_tiles_{b}', x=1200, y=100+600*b) for b in range(3)]
    insts += [Inst('tt_ctlm', 'qfd_tt_ctlm_static_s', x=2500),
              Inst('sp_su64_sfu', 'qfd_sp_su64_sfu', x=3500),
              Inst('sp_vector_memory', 'qfd_sp_vector_memory', x=4500),
              Inst('peer', 'peer', x=5500)]
    buses = [('clk', 'clock_trunk', 1, [('tt_ctlm','ck_me_sched')]+[(f'sp_res_ser_{b}', 'ck') for b in range(3)]),
             ('rst_spine', 'reset', 1, [('tt_ctlm','rsi')]+[(f'sp_res_ser_{b}', 'rst_n') for b in range(3)])]
    for b in range(3):
        buses += [(f'rq_{b}', 'tree_spine', 4425, [(f'sp_port_tiles_{b}', 'rq'), (f'sp_res_ser_{b}', 'i')]),
                  (f'rs_{b}', 'tree_spine', 551, [(f'sp_res_ser_{b}', 'o'), ('sp_vector_memory', f'rb{b}')]),
                  (f'o4_me_en_rs{b}', 'spine_local', 1, [('tt_ctlm', f'mer{b}'), (f'sp_res_ser_{b}', 'me_en')]),
                  (f'rs_fault_{b}', 'spine_local', 1, [(f'sp_res_ser_{b}', 'fault'), ('tt_ctlm', f'rf{b}')])]
    # Real presegmented join source, including an existing alias on the peer.
    buses += [('tag0', 'spine_local', 100, [('tt_ctlm','c1__0_99'), ('peer','tag__0_99')]),
              ('tag1', 'spine_local', 241, [('tt_ctlm','c1__100_340'), ('peer','tag__100_340')]),
              ('cmd', 'spine_local', 380, [('tt_ctlm','ib'), ('peer','cmd')])]
    return dict(insts=insts, buses=buses, die=dict(w=10000,h=5000),
                port_join={'qfd_tt_ctlm_static_s': {'c1__0_99':('c1',list(range(100))),
                            'c1__100_340':('c1',list(range(100,341)))},
                           'peer': {'tag__0_99':('tag',list(range(100))),
                            'tag__100_340':('tag',list(range(100,341)))}})


def _bits(m, inst, port, width):
    mst = next(i.master for i in m['insts'] if i.name == inst)
    return m.get('port_join',{}).get(mst,{}).get(port, (port,list(range(width))))


def test_wrapper_ports():
    for b in range(3):
        p = rtl_ports(rtb.ROOT / rtb.SOURCE, rtb.master(b))
        assert p['rq'] == (4425, 'input') and p['rb'] == (551, 'output')
        assert p['slot_count'] == (4,'input')
        assert all(p[c] == (1, 'input') for c in rtb.CLOCKS)


def test_apply_rewires_and_preserves_numeric_bit_identity():
    m = _model()
    rec = rtb.apply(m)
    assert [i.master for i in m['insts'][:3]] == [rtb.master(b) for b in range(3)]
    assert rec['retired']['buses'] == [f'o4_me_en_rs{b}' for b in range(3)]
    assert all(not v for v in rec['open_inputs'].values())
    assert rec['issue']['command_bits'] == 42
    assert rec['issue']['TRAIN_EDGES'] is None
    assert rec['issue']['fault']['status'] == 'OPEN'
    assert rec['mapped_inventory']['status'] == 'stale_architecture'
    assert m['master_params']['qfd_sp_vector_memory']['PAR_RB'] == 1
    pairs = {}
    src_counts = Counter()
    for bus, cls, width, es in m['buses']:
        source = next(((p,_bits(m,i,p,width)) for i,p in es if i=='tt_ctlm' and _bits(m,i,p,width)[0] in ('ib','c1')),None)
        if source:
            sp,(real,bits) = source
            for b in bits: src_counts[real,b] += 1
            for i,p in es:
                if i in ('peer',rtb.ISSUE):
                    target,tbits = _bits(m,i,p,width)
                    for a,b in zip(bits,tbits):
                        pairs[i,target,b] = real,a
        if bus.startswith('rsi_') and any(i==rtb.ISSUE and p in rtb.COMMAND for i,p in es):
            assert len(es) == 4
    for target,(real,lo,hi) in rtb.TAPS.items():
        for bit in range(hi-lo+1):
            assert pairs[rtb.ISSUE,target,bit] == (real,lo+bit)
    for real,target,n in [('ib','cmd',380),('c1','tag',341)]:
        for bit in range(n):
            assert pairs['peer',target,bit] == (real,bit)
            assert src_counts[real,bit] == 1
    # All physical aliases partition the original source/peer ports exactly.
    for mst,real,n in [('qfd_tt_ctlm_static_s','ib',380),('qfd_tt_ctlm_static_s','c1',341),('peer','tag',341)]:
        bits = [b for r,bs in m['port_join'][mst].values() if r==real for b in bs]
        assert sorted(bits) == list(range(n))
    clk = next(e for b,c,n,e in m['buses'] if b == 'clk')
    assert len([1 for i,p in clk if i.startswith('sp_res_ser')]) == 75
    assert (rtb.ISSUE,'ck') in clk


def test_unconnected_external_ib_uses_actual_source_bits():
    m = _model()
    m['buses'] = [b for b in m['buses'] if b[0]!='cmd']
    rtb.apply(m)
    al = m['port_join']['qfd_tt_ctlm_static_s']
    assert sorted(b for r,bs in al.values() if r=='ib' for b in bs)==list(range(380))


@pytest.mark.parametrize('mutant',['width','overlap','missing_source','clock','duplicate_bits'])
def test_malformed_mutants_refused(mutant):
    m = _model()
    if mutant=='width':
        m['buses'] = [(b,c,4424 if b=='rq_0' else n,e) for b,c,n,e in m['buses']]
    elif mutant=='overlap':
        m['buses'].append(('bad','spine_local',100,[('tt_ctlm','c1__0_99')]))
    elif mutant=='missing_source':
        next(i for i in m['insts'] if i.name=='tt_ctlm').master='absent_tt'
    elif mutant=='clock':
        m['buses'] = [b for b in m['buses'] if b[1]!='clock_trunk']
    else:
        m['port_join']['qfd_tt_ctlm_static_s']['c1__0_99']=('c1',[0]*100)
    with pytest.raises(ValueError):
        rtb.apply(m)


def test_segmented_command_input_installs_real_pins():
    from qwen_split.direct_up4 import partition_master
    class Master:
        def __init__(self,name,w,h,*args):
            self.name,self.w,self.h=name,w,h
            self.ports={}
            self.order=[]
    m=_model()
    m['buses']=[b for b in m['buses'] if b[0]!='cmd']
    m['port_join']['qfd_tt_ctlm_static_s'].update({
        'ib__0_27':('ib',list(range(28))),
        'ib__28_379':('ib',list(range(28,380)))})
    m['buses'] += [('cmd0','spine_local',28,[('tt_ctlm','ib__0_27')]),
                   ('cmd1','spine_local',352,[('tt_ctlm','ib__28_379')])]
    rtb.apply(m)
    mats={}
    rtb.install_masters(mats,m,Master,partition_master)
    a=m['port_join'][rtb.ISSUE_MASTER]
    assert a['me_tiles__0_8']==('me_tiles',list(range(9)))
    assert a['me_tiles__9_17']==('me_tiles',list(range(9,18)))
    assert mats[rtb.ISSUE_MASTER].ports['me_tiles__9_17'][1]==9
    # Native assignment keeps every numeric pin once even with fragmented input.
    assert len(mats[rtb.ISSUE_MASTER].assigned_fragment_rects['me_tiles__0_8'])==9
    mats[rtb.ISSUE_MASTER].ports['me_tiles__9_17']=('xy',8,None,None,1)
    with pytest.raises(ValueError):
        rtb.validate_case_masters(mats,m)
