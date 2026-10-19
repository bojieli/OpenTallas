#!/usr/bin/env python3
"""Small adversarial elaborated-graph fixtures (no simulator required)."""
from copy import deepcopy
from endpoint_domains import audit


def flop(clock, data, out):
    return {'type':'$_DFF_P_', 'connections':{'C':[clock], 'D':[data], 'Q':[out]}}


def fixture():
    child={'ports':{'ck':{'direction':'input','bits':[2,3]},
                    'd':{'direction':'input','bits':[4]},
                    'q':{'direction':'output','bits':[6]}},
           'netnames':{}, 'cells':{'launch':flop(2,4,5), 'capture':flop(3,5,6)}}
    top={'ports':{'ck_a':{'direction':'input','bits':[10]},
                  'ck_b':{'direction':'input','bits':[11]},
                  'd':{'direction':'input','bits':[12]}},
         'netnames':{}, 'cells':{'nested':{'type':'paramod_child',
             'connections':{'ck':[10,11], 'd':[12], 'q':[13]}}}}
    return {'modules':{'top':top,'paramod_child':child}}


def main():
    d=fixture(); roots={'ck_a':'A','ck_b':'B'}
    r=audit(d,'top',roots)
    assert not r['issues'] and r['endpoints_per_root']=={'A':1,'B':1}
    assert any(c['sink']=='top/nested/capture' and c['source_root']=='A' and c['sink_root']=='B' for c in r['crossings'])
    # Literal vector bits remain distinct through nested module port maps.
    x=deepcopy(d); x['modules']['top']['cells']['nested']['connections']['ck']=[11,10]
    r=audit(x,'top',roots)
    assert r['endpoint_owners']['top/nested/launch']['root']=='B'
    # Missing root may never inherit the other bit's region.
    r=audit(d,'top',{'ck_a':'A'})
    assert any('unowned clock' in e for e in r['issues'])
    # Inverters retain physical phase sense; they do not create a new root.
    x=deepcopy(d);m=x['modules']['paramod_child']
    m['cells']['inv']={'type':'$_NOT_','connections':{'A':[3],'Y':[7]}}
    m['cells']['capture']['connections']['C']=[7]
    r=audit(x,'top',roots)
    assert r['endpoint_owners']['top/nested/capture']['clock_inverted_from_root']==1
    assert r['endpoint_owners']['top/nested/capture']['active_phase_from_root']==1
    r=audit(x,'top',{'ck_a':'A','ck_b':'A'})
    assert any(c['source_root']=='A' and c['sink_root']=='A' and
               c['source_active_phase']==0 and c['sink_active_phase']==1 for c in r['crossings'])
    # A data mux is not an approved clock buffer, even if both inputs agree.
    m['cells']['inv']={'type':'$_MUX_','connections':{'A':[3],'B':[3],'S':[4],'Y':[7]}}
    r=audit(x,'top',roots)
    assert any('unowned clock' in e for e in r['issues'])
    # Unknown hard children need explicit pin/edge contracts.
    x=deepcopy(d);m=x['modules']['paramod_child'];m['cells']['native']={
        'type':'sram','connections':{'clk':[2],'din':[5],'dout':[8]}}
    r=audit(x,'top',roots)
    assert any('unknown leaf' in e for e in r['issues'])
    r=audit(x,'top',roots,{'sram':{'clock':'clk','edge':'posedge','outputs':['dout'],'reset':[]}})
    assert not r['issues'] and r['endpoints_per_root']['A']==2
    # Conflicting actual port aliases and width omissions reject explicitly.
    x=deepcopy(d);x['modules']['top']['ports']['ck_b']['bits']=[10]
    try:audit(x,'top',roots)
    except ValueError as e: assert 'conflicting root aliases' in str(e)
    else:raise AssertionError('conflicting aliases accepted')
    x=deepcopy(d);x['modules']['top']['cells']['nested']['connections']['ck']=[10]
    try:audit(x,'top',roots)
    except ValueError as e: assert 'port width' in str(e)
    else:raise AssertionError('missing vector bit accepted')
    print('PASS nested vector roots, swapped binding, missing root, inverter polarity, clock mux, unknown native leaf, explicit macro contract, alias conflict, width mismatch')


if __name__=='__main__':main()
