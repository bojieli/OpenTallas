"""Actual Tcl execution: preserve gated/hard clocks, capacity and short reach."""
from pathlib import Path
import tkinter
import pytest

HELPER = Path(__file__).with_name('tap_chain_affinity.tcl')


def fixture(x0=0, x1=20, cap=4, radius=200, scalar=False):
    t=tkinter.Tcl();state={};nets={'tap0':'clk','tap1':'clk_t1','gated':'icg_GCLK'};insts={}
    for i,(stage,x,net,hard) in enumerate([(0,x0,'tap0',False),(1,x1,'tap0',False),(2,10,'gated',False),(3,10,'tap0',True)]):
        it=f'it{i}';inst=f'inst{i}';master=f'master{i}'
        state[it]=net;name=(f'u_bound.u_pd23_owner_data_225.r\\[{stage}\\]$_DFF_P_' if scalar else f'u_bound.u_d3_test.r\\[{stage}\\]\\[7\\]$_DFF_P_')
        insts[inst]={'name':name, 'xy':(x,0),'master':master,'hard':hard}
        def iterm(method,*args,it=it,inst=inst):
            if method=='getNet':return state[it]
            if method=='getInst':return inst
            if method=='isInputSignal':return 1
            if method=='isOutputSignal':return 0
            if method=='disconnect':state[it]='NULL';return ''
            if method=='connect':state[it]=args[0];return ''
            raise ValueError(method)
        def instance(method,*args,inst=inst):
            a=insts[inst]
            return {'getName':a['name'],'getLocation':a['xy'],'getMaster':a['master']}[method]
        def mast(method,*args,inst=inst):
            return int(insts[inst]['hard']) if method=='isBlock' else 'DFFHQNx1_ASAP7_75t_R'
        t.createcommand(it,iterm);t.createcommand(inst,instance);t.createcommand(master,mast)
    for net,name in nets.items():
        def ncmd(method,*args,net=net,name=name):
            if method=='getName':return name
            if method=='getITerms':return tuple(it for it,n in state.items() if n==net)
            raise ValueError(method)
        t.createcommand(net,ncmd)
    t.eval('namespace eval sta {};namespace eval ord {}')
    t.createcommand('all_registers',lambda *args:tuple(state));t.createcommand('sta::sta_to_db_pin',lambda p:p)
    t.createcommand('ord::get_db_tech',lambda:'tech');t.createcommand('tech',lambda *args:1)
    t.setvar('ct_taps',(('clk','tap0',0,0),('clk_t1','tap1',20,0)))
    t.setvar('env(OT_TAP_MAX_SINKS)',cap);t.setvar('env(OT_TAP_CHAIN_RADIUS_UM)',radius);t.setvar('env(OT_TAP_CHAIN_MAX_GROUP)',min(24,max(2,cap)))
    # Production files are sourced from an ORFS proc, not the global scope.
    t.eval('proc load_helper {file} {source $file}')
    t.call('load_helper',str(HELPER));t.call('::ot_tap_chain::capture','tap0')
    state['it1']='tap1'  # ordinary nearest-tap split between capture and affinity
    return t,state,insts


def test_bit_chain_joins_without_crossing_gate_or_hard_clock():
    t,state,_=fixture();t.call('::ot_tap_chain::apply')
    assert state['it0']==state['it1']
    assert state['it2']=='gated' and state['it3']=='tap0'
    assert int(t.getvar('::ot_tap_chain::moved'))==1


def test_capacity_is_not_exceeded():
    t,state,_=fixture(cap=2);state['filler']='tap1';t.createcommand('filler',lambda method:1 if method=='isInputSignal' else 0);before=dict(state);t.call('::ot_tap_chain::apply')
    assert state==before


def test_long_chain_does_not_grow_a_long_clock_branch():
    t,state,_=fixture(x1=600,radius=100);t.setvar('ct_taps',(('clk','tap0',0,0),('clk_t1','tap1',600,0)))
    before=dict(state);t.call('::ot_tap_chain::apply');assert state==before


def test_eligible_pin_that_moves_behind_a_gate_is_refused():
    t,state,_=fixture();state['it1']='gated'
    with pytest.raises(tkinter.TclError,match='declared source family'):t.call('::ot_tap_chain::apply')


def test_master_replacement_is_refused():
    t,state,insts=fixture();insts['inst1']['hard']=True
    with pytest.raises(tkinter.TclError,match='master changed'):t.call('::ot_tap_chain::apply')


def test_plan_exports_are_opt_in_and_cannot_expand_radius_or_capacity():
    import sys
    sys.path.insert(0,str(Path(__file__).parent))
    from gen_phys import tap_chain_affinity_exports
    assert tap_chain_affinity_exports({'clock':{}})==[]
    lines=tap_chain_affinity_exports({'clock':{'tap_radius_um':200,'tap_max_sinks':1200,'tap_chain_affinity':{'radius_um':180,'max_group':128}}})
    assert 'export OT_TAP_CHAIN_AFFINITY = 1' in lines and 'export OT_TAP_CHAIN_MAX_GROUP = 128' in lines
    for spec in [{'radius_um':201},{'max_group':1201}]:
        with pytest.raises(ValueError):tap_chain_affinity_exports({'clock':{'tap_radius_um':200,'tap_max_sinks':1200,'tap_chain_affinity':spec}})


def test_scalar_generated_delay_is_grouped_by_full_bit_prefix():
    t,state,_=fixture(scalar=True);t.call('::ot_tap_chain::apply')
    assert state['it0']==state['it1'] and state['it2']=='gated' and state['it3']=='tap0'


def test_identity_change_is_refused():
    t,state,insts=fixture();insts['inst1']['name']+='_renamed'
    with pytest.raises(tkinter.TclError,match='identity changed'):t.call('::ot_tap_chain::apply')


def test_terminal_identity_matches_exact_bit_or_scalar_prefix():
    t,_,_=fixture()
    for name,expected in [('u_bound.u_d68_test.q[452]$_DFF_P_', ('u_bound.u_d68_test.r','terminal','452')), ('u_bound.u_pd23_owner_data_225.q$_DFF_P_', ('u_bound.u_pd23_owner_data_225.r','terminal','scalar'))]:
        assert tuple(t.call('::ot_tap_chain::identity',name))==expected
    assert not t.call('::ot_tap_chain::identity','u_bound.u_d68_test.q[2][3]$_DFF_P_')

@pytest.mark.parametrize('scalar',[False,True])
def test_terminal_register_is_joined_with_its_real_preceding_chain(scalar):
    t,state,insts=fixture(scalar=scalar)
    insts['inst1']['name']=('u_bound.u_pd23_owner_data_225.q$_DFF_P_' if scalar else 'u_bound.u_d3_test.q\\[7\\]$_DFF_P_')
    state['it1']='tap0';t.call('::ot_tap_chain::capture','tap0');state['it1']='tap1'
    t.call('::ot_tap_chain::apply')
    assert state['it0']==state['it1'] and state['it2']=='gated'
