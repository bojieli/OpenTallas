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
    # Synchronous and asynchronous set/reset control sources remain visible.
    x=deepcopy(d);c=x['modules']['paramod_child']['cells']['capture']
    c['type']='$_SDFFE_PP0P_';c['connections'].update(R=[5],E=[4])
    r=audit(x,'top',roots)
    assert any(c['sink_pin']=='R' and c['pin_role']=='reset_set' and
               c['source_root']=='A' for c in r['crossings'])
    # Unoptimized word flops preserve explicit clock polarity and reset/enable
    # provenance; word arithmetic propagates conservatively through every bit.
    x=deepcopy(d);m=x['modules']['paramod_child']
    m['cells']['launch']={'type':'$dff','parameters':{'CLK_POLARITY':'1'},
        'connections':{'CLK':[2],'D':[4,4],'Q':[5,9]}}
    m['cells']['add']={'type':'$add','port_directions':{'A':'input','B':'input','Y':'output'},
        'connections':{'A':[5],'B':[9],'Y':[10]}}
    m['cells']['capture']={'type':'$adffe','parameters':{'CLK_POLARITY':'0'},
        'connections':{'CLK':[3],'D':[10,9],'Q':[6,8],'ARST':[5],'EN':[4]}}
    r=audit(x,'top',roots)
    assert not r['issues'] and r['endpoint_owners']['top/nested/capture']['active_phase_from_root']==1
    assert r['word_endpoint_widths']=={'top/nested/launch':2,'top/nested/capture':2}
    assert any(c['sink_pin']=='ARST' and c['pin_role']=='reset_set' and c['source_root']=='A' for c in r['crossings'])
    m['cells']['inv']={'type':'$not','connections':{'A':[3],'Y':[7]}}
    m['cells']['capture']['connections']['CLK']=[7]
    r=audit(x,'top',roots)
    assert r['endpoint_owners']['top/nested/capture']['active_phase_from_root']==0
    m['cells']['capture']['parameters']['CLK_POLARITY']='x'
    try:audit(x,'top',roots)
    except ValueError as e:assert 'polarity' in str(e)
    else:raise AssertionError('unknown word clock polarity accepted')
    # Legal output aliases include wires and repeated constant outputs. They
    # canonicalize every parent consumer, rather than being treated as inputs.
    x=deepcopy(d);m=x['modules']['paramod_child']
    x['modules']['wire_child']={'ports':{'d':{'direction':'input','bits':[2]},
        'q':{'direction':'output','bits':[2]},'zero':{'direction':'output','bits':['0','0']}},'cells':{},'netnames':{}}
    m['cells']['wire']={'type':'wire_child','connections':{'d':[5],'q':[9],'zero':[8,10]}}
    m['cells']['capture']['connections']['D']=[9]
    r=audit(x,'top',roots)
    assert not r['issues'] and any(c['sink']=='top/nested/capture' and c['source_root']=='A' for c in r['crossings'])
    m['cells']['wire']['connections']['zero']=[]
    r=audit(x,'top',roots)
    assert not r['issues'] and r['unconnected_child_output_ports']==[{'port':'top/nested/wire.zero','width':2}]
    m['cells']['wire']['connections']['d']=[4]
    r=audit(x,'top',roots)
    assert any(c['sink']=='top/nested/capture' and c['source_root']=='INPUT:d' for c in r['crossings'])
    x['modules']['wire_child']['ports']['other']={'direction':'input','bits':[2]}
    m['cells']['wire']['connections']['other']=[4]
    try:audit(x,'top',roots)
    except ValueError as e:assert 'aliased child inputs' in str(e)
    else:raise AssertionError('conflicting child inputs accepted through output alias')
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
    print('PASS word FF polarity, async reset/enable domains, conservative arithmetic and unknown-polarity rejection')
    print('PASS repeated constant outputs, input-to-output wire aliases, conflicting child-input rejection')


if __name__=='__main__':main()
