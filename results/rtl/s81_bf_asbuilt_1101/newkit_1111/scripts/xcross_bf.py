"""(e): BF unit (dsfd_bf_col / dsfd_bf_front_roots) input pins: arrival labels/depths with plain vs bound seams"""
import json,sys,collections
from pathlib import Path
D=Path('/srv/opentallas-scratch2/claude/s81-bfasb-1111')
sys.path[:0]=[str(D/'code/tools/s81_dv'),str(D/'code/tools/s81_dv/layer_prog'),str(D/'code/tools/die_plan')]
import frame_schedule_asb as F
F.SROOT[0]=D/'root'
res={}
for m,v in (('col_h9','x'),('col_h9','nx'),('col_h10','x')):
    top=f'{m}_l4_lp_asb_{v}'
    p=D/f'fsaw/{m}_{v}/{top}.selected.json'
    out={}
    for tag,ex in (('plain',None),('bound',{'u_s01':9,'u_s12':4})):
        mod,cells,kind,labels=F.trace(json.loads(p.read_text()),top,ex)
        for cn,k in kind.items():
            if k.split('$')[0] in ('dsfd_bf_col','dsfd_bf_front_roots'):
                inst=cn.lstrip('\\')
                for port in cells[cn]['connections']:
                    if cells[cn].get('port_directions',{}).get(port)!='input':continue
                    out.setdefault(f'{inst}.{port}',{})[tag]=sorted(F.pin_labels(cells,labels,cn,port))
    ch={k:v_ for k,v_ in out.items() if v_.get('plain')!=v_.get('bound')}
    print('==',top,'BF input pins',len(out),'changed',len(ch))
    insts=collections.defaultdict(list)
    for k in out:insts[k.rsplit('.',1)[0]].append(k)
    for i in sorted(insts):
        c=[k for k in insts[i] if k in ch]
        print('  ',i,'pins',len(insts[i]),'changed',len(c))
        for k in c[:6]:
            pl=sorted({(a,d) for a,d in out[k]['plain']}) ; bd=sorted({(a,d) for a,d in out[k]['bound']})
            print('     ',k.rsplit('.',1)[1],pl[:3],'->',bd[:3])
    res[top]=out
json.dump(res,open(D/'leaflat/bf_inputs_plain_vs_bound.json','w'),indent=0)
