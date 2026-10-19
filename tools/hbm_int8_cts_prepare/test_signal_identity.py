"""Tiny deterministic checker adversaries; no synthesis or RTL execution."""
from copy import deepcopy
from check_signal_identity import check

def cell(master,connections):
    return {'type':master,'connections':{p:[n] for p,n in connections.items()},'port_directions':{p:'output' if p in ('Q','Y') else 'input' for p in connections},'pin_signal_types':{p:'SIGNAL' for p in connections}}
native={'FF':{'ff':{'clocked_on':'CK'},'latch':None,'pins':{'CK':{'clock':True}}},'BUF':{'ff':None,'latch':None,'pins':{'A':{'direction':'input','function':None},'Y':{'direction':'output','function':'A'}}},'TIE':{'ff':None,'latch':None,'pins':{}}}
cells={'f':cell('FF',{'CK':1,'D':2,'R':3,'Q':4}),'t':cell('TIE',{'Y':3})}
ports={p:{'direction':d,'signal_type':'SIGNAL','bits':[n]} for p,n,d in [('clk',1,'input'),('data',2,'input'),('out',4,'output')]}
b={'no_exclusions':True,'modules':{'test':{'cells':cells,'ports':ports,'net_metadata':{str(i):{'name':str(i),'signal_type':'SIGNAL'} for i in range(1,5)}}},'native_master_pins':{}}
for c in cells.values():b['native_master_pins'][c['type']]={p:{'direction':c['port_directions'][p],'signal_type':'SIGNAL'} for p in c['connections']}
a=deepcopy(b);a['modules']['test']['net_metadata']['5']={'name':'5','signal_type':'SIGNAL'};m=a['modules']['test'];m['cells']['f']['connections']['CK']=[5];m['cells']['buf']=cell('BUF',{'A':1,'Y':5});a['native_master_pins']['BUF']={p:{'direction':r,'signal_type':'SIGNAL'} for p,r in [('A','input'),('Y','output')]}
bp={'units':1000,'die':[0,0,100,100],'rows':[[0,0,100,1]],'bterms':{'clk':[[0,1,2,3]]},'insts':{n:{'master':c['type'],'location':[1,2],'orient':'R0'} for n,c in cells.items()}};ap=deepcopy(bp)
assert check(b,a,bp,ap,native)['signal_identity_PASS']
def reject(name,mut):
    bb,aa,pp,qq=map(deepcopy,(b,a,bp,ap));mut(bb,aa,pp,qq)
    try:check(bb,aa,pp,qq,native)
    except ValueError as e:print('EXPECTED_REJECTION',name,str(e));return
    raise AssertionError('accepted '+name)
def pin(p,n):return lambda b,a,pb,pa:a['modules']['test']['cells']['f']['connections'].__setitem__(p,[n])
reject('data',pin('D',3));reject('reset',pin('R',2));reject('tie',lambda b,a,p,q:a['modules']['test']['cells']['t']['connections'].__setitem__('Y',[2]))
reject('BTerm',lambda b,a,p,q:a['modules']['test']['ports']['out'].__setitem__('bits',[2]))
reject('master',lambda b,a,p,q:a['modules']['test']['cells']['f'].__setitem__('type','BUF'))
reject('moved',lambda b,a,p,q:q['insts']['f'].__setitem__('location',[2,2]))
reject('orient',lambda b,a,p,q:q['insts']['f'].__setitem__('orient','MX'))
reject('clock_data_mixed',pin('D',5))
reject('new_FF',lambda b,a,p,q:a['modules']['test']['cells'].__setitem__('extra',deepcopy(a['modules']['test']['cells']['f'])))
reject('removed',lambda b,a,p,q:a['modules']['test']['cells'].pop('f'))
reject('BTerm_geometry',lambda b,a,p,q:q.__setitem__('bterms',{}))
reject('net_metadata',lambda b,a,p,q:a['modules']['test']['net_metadata']['2'].__setitem__('name','renamed'))
reject('clock_cycle',lambda b,a,p,q:a['modules']['test']['cells']['buf']['connections'].__setitem__('Y',[1]))
reject('die_geometry',lambda b,a,p,q:q.__setitem__('die',[0,0,200,100]))
reject('new_unused_net',lambda b,a,p,q:a['modules']['test']['net_metadata'].__setitem__('6',{'name':'junk','signal_type':'SIGNAL'}))
print('SIGNAL_IDENTITY_FIXTURE_PASS positive=1 negative=15')
