"""Finite source-only existing lo_q/hi_q homes, selected actual/reference LEF pins.

This proves only P-ring->existing capture->PF macro geometry. The other mux
predecessor dpr_q and controls are expressly unqualified; no source/EDA pass.
"""
import json, math, re, sys
from pathlib import Path
B=Path(__file__).resolve().parent/'candidate2'
def pins(path):
    text=Path(path).read_text(); out={}
    for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n',text,re.S):
        if m[1] in ['VDD','VSS']:continue
        rs=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',m[2]);assert len(rs)==1,m[1]
        a,b,c,d=map(float,rs[0]);out[m[1]]=[(a+c)/2,(b+d)/2]
    return out
fold=pins(sys.argv[1]);ring=pins(sys.argv[2]);r=json.loads((B/'CANDIDATE_REVIEW.json').read_text())
macros=r['macros'];pf=[m for m in macros if '.g_pf['in m['inst']];prs=[m for m in macros if '.u_pring.'in m['inst']];assert len(pf)==4 and len(prs)==2
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
tasks=[]
for j,m in enumerate(pf):
    for kind,off in [('lo_q',0),('hi_q',128)]:
        for bit in range(128):
            k=128*j+bit;pp=fold[f'src[{off+bit}]'];dest=[m['origin_um'][0]+pp[0],m['origin_um'][1]+pp[1]]
            rp=ring[f'rd_out[{k}]'];sources=[[h['origin_um'][0]+rp[0],h['origin_um'][1]+rp[1]]for h in prs]
            col=(j*256+off+bit)%16;x=205.92+col*1.296
            lo=max(y-(405-abs(x-z))for z,y in sources+[dest]);hi=min(y+(405-abs(x-z))for z,y in sources+[dest])
            assert lo<=hi,(kind,k,lo,hi)
            tasks.append(dict(register=f'{kind}[{k}]',x=x,col=col,lo=lo,hi=hi,sources=sources,destination=dest))
# Conservative physical cell pitch:1.296x0.54um, larger than native~1.08x0.27FF.
used=set();rows=[]
for t in sorted(tasks,key=lambda x:x['hi']):
    available=[q for q in range(math.ceil(t['lo']/.54),math.floor(t['hi']/.54)+1)if(t['col'],q)not in used]
    assert available,t
    target=(t['lo']+t['hi'])/2;row=min(available,key=lambda q:abs(q*.54-target));used.add((t['col'],row));pt=[t['x'],row*.54]
    distances=[man(a,pt)for a in t['sources']];d=man(pt,t['destination']);assert max(distances+[d])<=405+1e-7
    rows.append(dict(register=t['register'],proposed_center_um=pt,pring_bank_read_pin_um=t['sources'],pring_to_capture_um=distances,fold_src_pin_um=t['destination'],capture_to_fold_um=d))
out=dict(status='SOURCE_ONLY_PARTIAL_GEOMETRY',actual_existing_registers=1024,unique_pitch_sites=len(used),cell_pitch_um=[1.296,.54],max_pring_to_capture_um=max(max(t['pring_to_capture_um'])for t in rows),max_capture_to_fold_um=max(t['capture_to_fold_um']for t in rows),added_registers=0,added_functional_edges=0,rows=rows,scope='Both actual P-ring SRAM read pins to1024 existing lo_q/hi_q bit captures and then matching actual/reference PFsrc pins. Actual reference fold pins do not qualify a current view.',unqualified=['Other lo/hi mux predecessor dpr_q and select/enable control; exact codec/source endpoints must join before source credit','All PFoutput/XF/S-ring/R-ring/codec reader graphs','New current fold physical/function/source/reset/clock qualification','Full perbit clock/reset/boot/START and parent bus/programme price'])
(B/'PF_CAPTURE_PARTIAL_GEOMETRY.json').write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps({k:v for k,v in out.items()if k not in ['rows','unqualified']}))
