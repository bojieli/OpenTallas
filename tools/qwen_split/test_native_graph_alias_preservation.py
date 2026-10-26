"""Source-backed physical fragments must retain their native producers."""
import pytest
from qwen_rom_fulldie import Inst
from qwen_split import native_graph_bind as n


def model(real='uf'):
    names=[('tt_ctlm','qfd_tt_ctlm_static_s'),('seq_su','qfd_seq_su_static'),
           ('sp_su64_sfu','qfd_sp_su64_sfu'),('sp_vector_memory','qfd_sp_vector_memory'),
           ('io_collective','qfd_collective_static_io_production')]
    insts=[Inst(a,b,1000+2000*k,1000,1000,1000) for k,(a,b) in enumerate(names)]
    insts += [Inst(f'upper{k}','ot_qfd_band_upper',1000+200*k,4000,100,100) for k in range(4)]
    buses=[('clock','clock_trunk',1,[(i.name,'ck') for i in insts]),
           ('reset','reset',1,[(i.name,'rst_n') for i in insts])]
    buses += [(f'fault{k}','spine_local',1,[(f'upper{k}','fault'),('tt_ctlm',f'uf_l{k}')]) for k in range(4)]
    return dict(die=dict(w=30000,h=30000),insts=insts,buses=buses,
                native_static_io_bind={'qualified':False},
                port_join={'qfd_tt_ctlm_static_s':{f'uf_l{k}':(real,[k]) for k in range(4)}})


def test_source_alias_faults_survive_native_join_replacement():
    m=model();r=n.apply(m)
    faults=[b for b in m['buses'] if b[0].startswith('fault')]
    assert len(faults)==4
    assert 'uf' not in r['open_inputs'].get('tt',[])
    assert [b[3] for b in faults]==[[(f'upper{k}','fault'),('tt_ctlm',f'uf_l{k}')] for k in range(4)]


def test_unknown_real_port_remains_an_explicit_gap():
    m=model('wrong_real_port');r=n.apply(m)
    assert not any(b[0].startswith('fault') for b in m['buses'])
    assert 'uf' in r['open_inputs']['tt']
