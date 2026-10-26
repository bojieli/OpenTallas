#!/usr/bin/env python3
"""Grant distinct source-specialized bank candidates, no parent/view aliases."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import hbm_die_views as V
REF='2de820027'
def blob(path):return subprocess.check_output(['git','-C',str(ROOT),'show',REF+':'+path])
mpath='results/arch/hbm_vm_bank_static_1015/local_identity_status_1425/source_specialized_masters.json'
manifest=json.loads(blob(mpath));template=json.loads((ROOT/'results/arch/hbm_die_v15/vm_bank_local_status_grants_1417.json').read_text());P=json.loads((ROOT/'results/arch/hbm_die_v15/compact660_v5/compact.P.json').read_text());slots=[]
assert len(manifest['masters'])==32
for m in manifest['masters']:
    assert hashlib.sha256(blob(m['source'])).hexdigest()==m['sha256']
    original=next(s for s in template['slots'] if s['cell'].endswith(f"rg{m['rg']}wg{m['wg']}"));s=json.loads(json.dumps(original))
    q=('SW','SE','NW','NE')[m['sid']];parent=f"vmb_{q}{m['bid']}";window=P[parent]
    s['pins']=[p for p in s['pins'] if p['name'].split('[')[0] not in ('sid','bid')];s['pin_ranges']={n:x for n,x in s['pin_ranges'].items() if n not in ('sid','bid')}
    with tempfile.TemporaryDirectory() as td:
        f=Path(td)/'bank.sv';f.write_bytes(blob(m['source']));ports=V.L.parse_module(str(f),m['top'])['ports']
    assert not(set(ports)&{'sid','bid'});assert {p['name'].split('[')[0] for p in s['pins']}==set(ports)
    for p in s['pins']:
        n=p['name'].split('[')[0];width=ports[n][1];assert abs(p['span_um'][1]-p['span_um'][0]-width*.096)<1e-5
    # Spread each vector over the ACTUAL legal routing tracks of its face (M4 rows for W/E, M5 columns for N/S:
    # first track 0.012 um, pitch 0.048 um, ASAP7 tech LEF) and keep every M5 centre clear of the projection of the
    # tile's full-height M5 PG stripes (pdn.tcl: width 0.12, VSS/VDD pair spacing 0.072, pitch 5.4, pair centre at
    # core_x + 0.300; plus half pin width 0.012 and M5 spacing 0.024). Explicit per-bit centres replace the uniform
    # bit-pitch rule: 5.4 um is not a whole number of 0.048 um tracks, so no uniform pitch can stay PG-clear.
    W_,H_=s['outline']['w'],s['outline']['h'];CORE=2.16;T0,TP=.012,.048
    pg=[];k=0
    while CORE+.3+5.4*k-.06<W_:
        a=CORE+.3+5.4*k-.06;pg+=[(a,a+.12),(a+.192,a+.312)];k+=1
    def legal(face,lo,hi):
        out=[];i=max(0,int((lo-T0)/TP)-1)
        while T0+i*TP<=hi+1e-9:
            c=round(T0+i*TP,6);i+=1
            if c<lo-1e-9:continue
            if face in 'NS' and any(c+.036>a-1e-9 and c-.036<b+1e-9 for a,b in pg):continue
            out.append(c)
        return out
    used=set()
    spread=[]; ranges={}
    def region(items,face,lo,hi):
        if not items:return
        count=sum(ports[p['name'].split('[')[0]][1] for p in items)
        T=[c for c in legal(face,lo,hi) if (face,c) not in used]
        assert len(T)>=2*count,(m['top'],face,count,len(T))
        stride=len(T)/count;first=(len(T)-stride*(count-1)-1)/2
        sel=[T[int(round(first+j*stride))] for j in range(count)]
        assert len(set(sel))==count and all(b-a>=.096-1e-9 for a,b in zip(sel,sel[1:])),(m['top'],face)
        j=0
        for pin in items:
            n=pin['name'].split('[')[0];width=ports[n][1];cs=sel[j:j+width];j+=width
            gaps=[round(b-a,6) for a,b in zip(cs,cs[1:])]
            pin.update(offset=round((cs[0]+cs[-1])/2,6),span_um=[round(cs[0]-.048,6),round(cs[-1]+.048,6)],bit_centres_um=cs,
                       bit_pitch_um=min(gaps) if gaps else .096,bit_centres_rule='explicit bit_centres_um[bit_index] (actual track, PG-clear)')
            for c in cs:used.add((face,c))
            spread.append(pin);ranges[n]=pin['span_um']
    mid0=W_/2
    for face in 'WES':region([p for p in s['pins'] if p['face']==face],face,2,(W_ if face=='S' else H_)-2)
    north=[p for p in s['pins'] if p['face']=='N' and p['name'] not in ('clk','rst_n')]
    half=sum(ports[p['name'].split('[')[0]][1] for p in north)/2;left=[];right=[];nleft=0
    for pin in north:
        width=ports[pin['name'].split('[')[0]][1]
        if nleft+width<=half:left.append(pin);nleft+=width
        else:right.append(pin)
    TN=legal('N',mid0-2,mid0+2);mid=min(TN,key=lambda c:abs(c-mid0));rmid=min((c for c in TN if c>=mid+.192-1e-9),key=lambda c:c-mid)
    region(left,'N',2,mid-2);region(right,'N',rmid+2,W_-2)
    for n,center in [('clk',mid),('rst_n',rmid)]:
        pin=next(p for p in s['pins'] if p['name']==n);a,b=round(center-.048,6),round(center+.048,6);pin.update(offset=center,span_um=[a,b],bit_centres_um=[center],bit_pitch_um=.096,bit_centres_rule='explicit bit_centres_um[bit_index] (actual track, PG-clear)');spread.append(pin);ranges[n]=[a,b];used.add(('N',center))
    s['pins']=spread;s['pin_ranges']=ranges;s['clock_entry']['offset']=mid
    s['minimum_nonclock_bit_pitch_um']=min(p['bit_pitch_um'] for p in spread if p['name'] not in ('clk','rst_n'))
    s['pin_assignment_note']='Supersedes spread 2ba5e0351 (3068 centres off-track, 95 N/S PG projections in the q1 native gate): every bit on an actual M4/M5 routing track, M5 centres clear of the M5 PG stripe projections, explicit per-bit centres, occupancy <=0.50; clock on the N centre track. Exact per-bit centers and actual ODB pin rectangles must match; no native/route qualification inherited.'
    deps=[m['source'],manifest['core'],'rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv']
    s.update(name=parent+'_identity_diagnostic',parent=parent,cell=m['top'],source=m['source'],source_sha256=m['sha256'],source_prerequisite=REF,source_dependencies_sha256={p:hashlib.sha256(blob(p)).hexdigest() for p in deps},parent_plan_window=window,origin=dict(x=(window['w']-s['outline']['w'])/2,y=0,orient='R0'),compile_time_identity=dict(SLICE_ID=m['sid'],BANK_ID=m['bid']),grant='source_specialized_bank_identity_diagnostic_1417',scope='Distinct source and independently qualified view required for each identity. Candidate physical slot only; actual production slice still binds old dynamic bank. No constant SID/BID port tie, falsepath, case analysis or inherited view. Actual bank/hub packing and all incident paths remain OPEN.')
    s['face_density']['N']-=5*.096/s['outline']['w'];slots.append(s)
assert len({s['cell'] for s in slots})==32
out=dict(schema='opentallas.hier_contract.v1',die='hbm_v15',version=5,rules=template['rules'],clock_period_ps=template['clock_period_ps'],slots=slots,source_manifest_sha256=hashlib.sha256(blob(mpath)).hexdigest(),source_provenance=manifest['source_provenance'],distinct_masters=32,diagnostic_only=True,canonical_die_contract_mutated=False,production_binding_adopted=False,qualification=False,scope='Actual compile-time identities from parent source; all32candidate windows fit their planning rectangles. No area/cycle/native/clock/route qualification inherited; CE status +1 diagnostic edge, data calendars unchanged.')
f=ROOT/'results/arch/hbm_die_v15/vm_identity_grants_1417.json';f.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(distinct_masters=32,ports_by_profile={str(s['cell']):len(s['pins']) for s in slots[:1]},qualified=False)))
