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
    # Spread each vector over real usable face length rather than packing at minimum pitch.
    spread=[]; ranges={}
    def region(items,face,lo,hi):
        if not items:return
        count=sum(ports[p['name'].split('[')[0]][1] for p in items)
        pitch=int((hi-lo)/count/.096)*.096
        assert pitch>=.192-1e-8, (m['top'],face,count,pitch)
        cursor=(lo+hi-count*pitch)/2
        for pin in items:
            n=pin['name'].split('[')[0];width=ports[n][1];a,b=round(cursor,6),round(cursor+width*pitch,6)
            pin.update(offset=round((a+b)/2,6),span_um=[a,b],bit_pitch_um=round(pitch,6),bit_centres_rule='lo + (bit_index + 0.5) * bit_pitch_um')
            spread.append(pin);ranges[n]=[a,b];cursor=b
    for face in 'WES':region([p for p in s['pins'] if p['face']==face],face,2,(s['outline']['w'] if face=='S' else s['outline']['h'])-2)
    north=[p for p in s['pins'] if p['face']=='N' and p['name'] not in ('clk','rst_n')]
    half=sum(ports[p['name'].split('[')[0]][1] for p in north)/2;left=[];right=[];nleft=0
    for pin in north:
        width=ports[pin['name'].split('[')[0]][1]
        if nleft+width<=half:left.append(pin);nleft+=width
        else:right.append(pin)
    mid=s['outline']['w']/2
    region(left,'N',2,mid-2);region(right,'N',mid+2,s['outline']['w']-2)
    for n,center in [('clk',mid),('rst_n',mid+.192)]:
        pin=next(p for p in s['pins'] if p['name']==n);a,b=round(center-.048,6),round(center+.048,6);pin.update(offset=center,span_um=[a,b],bit_pitch_um=.096);spread.append(pin);ranges[n]=[a,b]
    s['pins']=spread;s['pin_ranges']=ranges;s['clock_entry']['offset']=mid
    s['minimum_nonclock_bit_pitch_um']=min(p['bit_pitch_um'] for p in spread if p['name'] not in ('clk','rst_n'))
    s['pin_assignment_note']='Supersedes packed5afa: four-face vectors spread with local occupancy <=0.50; clock centered N. Exact per-bit centers and actual ODB pin rectangles must match; no native/route qualification inherited.'
    deps=[m['source'],manifest['core'],'rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv']
    s.update(name=parent+'_identity_diagnostic',parent=parent,cell=m['top'],source=m['source'],source_sha256=m['sha256'],source_prerequisite=REF,source_dependencies_sha256={p:hashlib.sha256(blob(p)).hexdigest() for p in deps},parent_plan_window=window,origin=dict(x=(window['w']-s['outline']['w'])/2,y=0,orient='R0'),compile_time_identity=dict(SLICE_ID=m['sid'],BANK_ID=m['bid']),grant='source_specialized_bank_identity_diagnostic_1417',scope='Distinct source and independently qualified view required for each identity. Candidate physical slot only; actual production slice still binds old dynamic bank. No constant SID/BID port tie, falsepath, case analysis or inherited view. Actual bank/hub packing and all incident paths remain OPEN.')
    s['face_density']['N']-=5*.096/s['outline']['w'];slots.append(s)
assert len({s['cell'] for s in slots})==32
out=dict(schema='opentallas.hier_contract.v1',die='hbm_v15',version=5,rules=template['rules'],clock_period_ps=template['clock_period_ps'],slots=slots,source_manifest_sha256=hashlib.sha256(blob(mpath)).hexdigest(),source_provenance=manifest['source_provenance'],distinct_masters=32,diagnostic_only=True,canonical_die_contract_mutated=False,production_binding_adopted=False,qualification=False,scope='Actual compile-time identities from parent source; all32candidate windows fit their planning rectangles. No area/cycle/native/clock/route qualification inherited; CE status +1 diagnostic edge, data calendars unchanged.')
f=ROOT/'results/arch/hbm_die_v15/vm_identity_grants_1417.json';f.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(distinct_masters=32,ports_by_profile={str(s['cell']):len(s['pins']) for s in slots[:1]},qualified=False)))
