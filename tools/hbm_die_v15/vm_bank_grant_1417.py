#!/usr/bin/env python3
"""Source-exact diagnostic bank grants, deliberately separate from die adoption."""
import hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_die_views as views
REF='5384ecd1f'
def blob(p):return subprocess.check_output(['git','-C',str(ROOT),'show',REF+':'+p])
reqpath='results/arch/hbm_vm_bank_static_1015/local_identity_status_1425/diagnostic_grant_request.json'
req=json.loads(blob(reqpath));C=json.loads((ROOT/'results/arch/hier_contract_1015/hbm_v15.json').read_text());P=json.loads((ROOT/'results/arch/hbm_die_v15/compact660_v5/compact.P.json').read_text())
slots=[]
for rec in req['ports']:
    q={4:'SE',5:'SW',6:'NW'}[rec['rg']];parent='vmb_'+q+'0'; window=P[parent];w,h=req['candidate_outline_request_um']; groups={f:[] for f in 'NSEW'};ports={}
    assert hashlib.sha256(blob(rec['source'])).hexdigest()==rec['sha256']
    for d in rec['port_declarations']:
        m=re.fullmatch(r'(input|output) wire (?:\[(\d+):0\] )?(\w+),?',d);assert m,d
        direction,bits,name=m[1],int(m[2] or 0)+1,m[3];ports[name]=dict(direction=direction,bits=bits)
        if re.fullmatch(r'r[qr]\d+',name): face='WENS'[int(name[2:])%4]
        elif re.fullmatch(r'wq(?:_done)?\d+',name): face='WEN'[int(re.search(r'\d+',name)[0])%3]
        elif name.startswith(('clk','rst','bid','sid','rslot','wslot','status')):face='N'
        else:face={'dq':'S','dq_done':'S','kq':'N','kq_done':'N','xq':'W','xq_done':'W','xq2':'E','xq2_done':'E','eg':'E','pq':'S','pr':'S'}[name]
        groups[face].append((name,bits))
    with tempfile.TemporaryDirectory() as td:
        f=Path(td)/'bank.sv';f.write_bytes(blob(rec['source']))
        parsed=views.L.parse_module(str(f),rec['top'])['ports']
        assert {n:dict(direction=d,bits=b) for n,(d,b) in parsed.items()}==ports
    pins=[];ranges={};density={}
    for face,items in groups.items():
        length=w if face in 'NS' else h; used=sum(b for _,b in items)*.096;density[face]=used/length;assert density[face]<=.60
        offset=(length-used)/2
        for name,bits in items:
            lo=round(offset,6);hi=round(offset+bits*.096,6);assert 2<=lo<hi<=length-2
            pins.append(dict(name=name if bits==1 else f'{name}[{bits-1}:0]',face=face,layer='M5' if face in 'NS' else 'M4',offset=round((lo+hi)/2,6),span_um=[lo,hi],offset_pending_view=False));ranges[name]=[lo,hi];offset=hi
    deps={p:hashlib.sha256(blob(p)).hexdigest() for p in [rec['source'],rec['core'],rec['additional_source']]}
    slots.append(dict(name='vmb_'+q+'0_local_status_diagnostic',cell=rec['top'],kind='tile',parent=parent,source=rec['source'],source_prerequisite=REF,source_sha256=rec['sha256'],source_dependencies_sha256=deps,params={},outline=dict(w=w,h=h),origin=dict(x=(window['w']-w)/2,y=0,orient='R0'),pins=pins,pin_ranges=ranges,face_density=density,clock_entry=dict(pin='clk',face='N',layer='M5',offset=next(p['offset'] for p in pins if p['name']=='clk')),pg_layer='M5',strap_layer='M6',signal_max_layer='M5',layer_cap='M5',layer_rule='tile',io_budget=dict(in_delay_frac=.2,out_delay_frac=.2),version=5,grant='independent_bank_local_status_diagnostic_1417',parent_plan_window=window,diagnostic_only=True,source_graph_adopted=False,parent_and_die_qualified=False,status_cycles_added=1,data_cycles_added=0,scope='One representative per actual RG/WG master, no32bank adoption. New source-specific assignments use four faces; current-source clock/CTS/native checks mandatory. Actual hub+8bank incident pin paths/fixed returns and internal macro/PG access remain unqualified; no historical VSH1 pins or views reused.'))
out=dict(schema='opentallas.hier_contract.v1',die='hbm_v15',version=5,rules=C['rules'],clock_period_ps=C['clock_period_ps'],slots=slots,scope='Three source-exact diagnostic alternatives only. Parent windows are planning rectangles; bank/hub partition and full source graph remain OPEN.',source_request_sha256=hashlib.sha256(blob(reqpath)).hexdigest(),clock_architecture=req['clock_architecture'],required_keep_hook=req['required_keep_hook'],canonical_die_contract_mutated=False)
f=ROOT/'results/arch/hbm_die_v15/vm_bank_local_status_grants_1417.json';f.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps([dict(cell=s['cell'],port_bits=sum((int(p['name'].split('[')[1].split(':')[0])+1) if '[' in p['name'] else 1 for p in s['pins']),max_face_density=max(s['face_density'].values())) for s in slots]))
