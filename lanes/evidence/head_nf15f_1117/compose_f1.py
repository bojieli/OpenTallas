"""HEAD-R3 11-17 NF15f-func: functional compose of the hop-halving stage tuple on the gated final75r2 geometry.
PIN 4->6, POUT 4->8, TXI 1221->2442, KTX 0000->1111, KRX 1330->2660 (lane nibbles 3..0).
New stage groups are FUNCTIONAL PLACEHOLDERS: each new stage shares tag+rect of the last existing stage of its chain
(KTX lane i: the lane's KRX s0 anchor, lane 0: txi0_s0).  The real anchors are the relay sites of
hr3/w_final_knobF_g60.json in the +181.44 corridor (geometry event, not this candidate).  Separate dir, no adoption.
"""
from pathlib import Path
import json,sys,copy,hashlib,re
L=Path('/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10');R=L/'code';P=L/'stage/prep_f1'
sys.path[:0]=[str(R/'tools/s81_head'),str(R/'tools/die_plan'),str(R/'tools/s81_head/lep_calendar_1113')]
import head_cland_stage_delta as C
from lep_calendar import Stages,provider_port_contract
pp=P/'source_plan.json';raw=json.loads(pp.read_text());t=raw['partition_types']['hd_lep0N'];c=t['contents'][0];n=t['clock']['landing_contract']['native_stage_groups']
old=Stages(ktx=0,krx=0x1330,txi=0x1221,pin=4,pout=4,plw=3,col0=2);new=Stages(ktx=0x1111,krx=0x2660,txi=0x2442,pin=6,pout=8,plw=3,col0=2)
assert old.params()==c['params'],(old.params(),c['params'])
gs=n['groups'];IDX=lambda k:r'g_s\\\[%d\\\]'%k
def clones(stem_re,old_n,new_n,lane_sub=None,name_sub=None,src_last=None):
    out=[]
    last=old_n-1 if src_last is None else src_last
    src=[g for g in gs if (stem_re+IDX(last)) in g['prefix']]
    assert src,(stem_re,last)
    for j in range(old_n,new_n):
        for g in src:
            h=copy.deepcopy(g);h['prefix']=g['prefix'].replace(IDX(last),IDX(j))
            if lane_sub:h['prefix']=h['prefix'].replace(*lane_sub)
            if name_sub:
                for a,b in name_sub:h['prefix']=h['prefix'].replace(a,b)
            assert h['prefix']!=g['prefix'];out.append(h)
    return out
add=[]
add+=clones(r'g_pin\.',4,6);add+=clones(r'g_pout\.',4,8)
KL=lambda i:r'g_kl\\\[%d\\\]'%i;TX=lambda i:r'g_tx\\\[%d\\\]'%i
for lane in range(4):
    o,nw=old.lane('txi',lane),new.lane('txi',lane);add+=clones(TX(lane)+r'\.g_txi\.',o,nw)
for lane,(o,nw) in {1:(3,6),2:(3,6),3:(1,2)}.items():
    for d in ['g_rxf','g_rxr']:add+=clones(KL(lane)+'\\.'+d+'\\.',o,nw)
for lane in range(4):   # KTX 0 -> 1
    src_lane=lane if lane else 1
    for d,e in [('g_rxf','g_txf'),('g_rxr','g_txr')]:
        h=clones(KL(src_lane)+'\\.'+d+'\\.',0,1,src_last=0,lane_sub=(KL(src_lane),KL(lane)),name_sub=[(d,e)]) if lane else None
        if lane:add+=h
        else:
            g=next(g for g in gs if (KL(1)+'\\.'+d+'\\.'+IDX(0)) in g['prefix']);a=next(g for g in gs if g['tag']=='stage:txi0_s0')
            k=copy.deepcopy(g);k['prefix']=g['prefix'].replace(KL(1),KL(0)).replace(d,e);k['tag']=a['tag'];k['rect_um']=a['rect_um'];add.append(k)
have={g['prefix'] for g in gs};assert not any(g['prefix'] in have for g in add) and len({g['prefix'] for g in add})==len(add)
gs.extend(add);c['params']=new.params();n['params']=copy.deepcopy(new.params())
t['note']=t.get('note','')+' | NF15f-func (HEAD-R3): hop-halving stage tuple PIN6 POUT8 TXI2442 KTX1111 KRX2660; new stage groups are functional placeholders on existing anchors.'
before_sha=hashlib.sha256(pp.read_bytes()).hexdigest();pp.write_text(json.dumps(raw,indent=1)+'\n')
before=json.load((P/'wave_prepare.json').open());C.republish(P,R,['hd_lep0N'],P/'source_sidecar.json')
rec=dict(schema='opentallas.native_provider_calendar.v1',params=new.params(),legs=new.legs(),added_vs_parent={k:v-old.legs()[k] for k,v in new.legs().items()},state_bits=new.state_bits(),added_state_bits=new.state_bits()-old.state_bits(),provider_port_contract=provider_port_contract(raw,new),qualifier='Register-leg prices only; transport LATCHECK separate.')
(P/'native_provider_calendar_nf15f.json').write_text(json.dumps(rec,indent=1)+'\n')
a=json.load((P/'wave_prepare.json').open());changed=[k for k,v in before['published_wrappers'].items() if a['published_wrappers'][k]!=v]
print('COMPOSED base',before_sha[:12],'new',hashlib.sha256(pp.read_bytes()).hexdigest(),'groups_added',len(add),'changed',changed,'added_state',rec['added_state_bits'],'added_legs',{k:v for k,v in rec['added_vs_parent'].items() if v},flush=True)
