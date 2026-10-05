#!/usr/bin/env python3
"""Standalone frozen-input I66 retirement replay and runtime verifier.

No old owner-compiler imports. Replays the completion correction from archived
premeasurement root/upstream calendars; does not regenerate their full-product
allocator ancestry or grant full-core/physical-provider qualification.
"""
import argparse,collections,gzip,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'results/rtl/dsrom_I66_standalone_calibration_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]

def source_contract():
    s=A/'source_snapshot/pinned'
    spine=(s/'rtl/v41die/ot_v41_spine_w17w10.sv').read_text()
    adapter=(s/'rtl/v41die/ot_v41_rom_adapt.sv').read_text()
    assert "else rows_left <= rows_left - 19'($countones(r_v));" in spine
    assert "S_RUN: if (rows_left == 19'd0 && !sm_run && !ld_run) begin" in spine
    assert "st <= S_IDLE; phase_cycles <= cyc;" in spine
    assert "S_WAIT: if (!s_go && s_idle) st <= S_IDLE;" in adapter
    assert 'assign idle = st == S_IDLE && s_idle;' in adapter
    return {p:sha(s/p) for p in ['rtl/v41die/ot_v41_spine_w17w10.sv','rtl/v41die/ot_v41_rom_adapt.sv']}

def completion(root_events,nrow,upstream_idle):
    ret=collections.Counter(x['edge'] for x in root_events)
    debt=nrow;si=False;ai=False;trace=[]
    for t in range(max(ret)+10):
        old_debt=debt;old_si=si;old_ai=ai
        if old_si and not old_ai:ai=True
        if old_debt==0 and t>=upstream_idle:si=True
        debt-=ret[t]
        if debt<0:raise ValueError('excess returns')
        if t>=min(ret):trace.append(dict(edge=t,rows_left_pre=old_debt,returns=ret[t],rows_left_post=debt,spine_idle_pre=old_si,adapter_idle_pre=old_ai))
        if old_ai:return next(x['edge'] for x in trace if x['spine_idle_pre']),t,trace
    raise ValueError('retirement absent')

def generate(out):
    pins=source_contract();prior=A/'input_prediction_r1'
    shutil.copytree(prior,out)
    model=load(out/'prediction.json');root=rows(out/'root_prediction.jsonl');up=rows(out/'upstream_prediction.jsonl')
    idle_bound=max(x['edge'] for x in up)+1
    si,ai,trace=completion(root,model['prediction_counts']['root_rows'],idle_bound)
    model['schema']='opentallas.dsrom.PAR2.current-native-consumer-calibration.v2'
    model['absolute_edges'].update(spine_idle_preedge=si,adapter_retire_preedge=ai)
    model['completion_source_contract']=dict(source_sha256=pins,upstream_idle_bound=idle_bound,rule='S_RUN tests old rows_left; adapter S_WAIT tests old s_idle; preedge observations follow committed NBA state',observer_rule='phase accepted AND spine busy observed before subsequent idle')
    model['prior_prediction_sha256']=sha(prior/'prediction.json')
    model['new_host_sha256']=sha(A/'host_r2.cpp');model['hardware_changes']=False
    (out/'prediction.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    (out/'retirement_prediction.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in trace))

def expected(p):
    m=load(p/'prediction.json');es=[]
    for x in rows(p/'upstream_prediction.jsonl'):
        k=x['kind'];e=x['edge']
        if k in ('cfg_ROM_read_accept','cfg_element_write_accept'):
            for g in range(m['compiled']['logical_NP']):es.append((k,e,g,x['word']))
        elif k=='VM_read_accept':es.append((k,e,x['address'],64))
        elif k=='EID_VM_read_accept':es.append((k,e,x['address'],-1))
        elif k=='AQ_input_accept':es.append((k,e,x['first_element'],-1))
        elif k=='AQ_output_capture':es.append((k,e,-1,-1))
        elif k in ('field_cfg_accept','op_accept','phase_accept'):es.append((k,e,m['case']['phase'],-1))
        elif k=='field_go_accept':es.append((k,e,-1,-1))
        elif k=='activation_field_accept':es.append((k,e,(x['word']>>1)&255,(x['word']>>9)&7))
        elif k in ('stream_ROM_advance','stream_have_stall'):es.append((k,e,x['index'],-1))
    for x in rows(p/'CE_prediction.jsonl'):
        e=x['edge'];g=x['pair'];ad=x['logical_address']
        es.extend([('main_CE_accept',e,g,ad),('bank_capture',e+2,g,ad&1),('lane_consumer_sample',e+3,g,-1)])
        for mb in (0,1):es.append(('macro_read_accept',e,g,(mb<<14)|ad))
    for x in rows(p/'root_prediction.jsonl'):es.append(('root_row_accept',x['edge'],x['root'],x['row']))
    for x in rows(p/'VM_write_prediction.jsonl'):es.extend([('VM_write_accept',x['edge'],x['port'],x['address']),('final_destination_visible',x['edge'],x['address'],-1)])
    es.extend([('spine_idle',m['absolute_edges']['spine_idle_preedge'],-1,-1),('phase_retire',m['absolute_edges']['adapter_retire_preedge'],-1,-1)])
    return sorted(es)

def compare(p,events):
    target=expected(p);kinds={x[0] for x in target};obs=[]
    for x in events:
        k=x['kind'];a=x['a'];b=x['b']
        if k not in kinds:continue
        if k in ('AQ_output_capture','spine_idle','phase_retire'):a=b=-1
        if k in ('stream_ROM_advance','stream_have_stall'):b=-1
        if k=='main_CE_accept':b=x['c']
        if k=='macro_read_accept':b=(b<<14)|x['c']
        obs.append((k,x['edge'],a,b))
    aa=collections.Counter(target);bb=collections.Counter(obs);missing=aa-bb;extra=bb-aa
    bad=[x for x in events if x['kind'] in ('root_row_accept','VM_write_accept','final_destination_visible') and x['c']!=0x45a00000]
    return dict(result='PASS' if not missing and not extra and not bad else 'FAIL',expected_events=sum(aa.values()),observed_events=sum(bb.values()),missing_events=sum(missing.values()),extra_events=sum(extra.values()),nonzero_oracle_mismatches=len(bad),first_missing=list(missing.items())[:12],first_extra=list(extra.items())[:12],categories={k:dict(missing=sum(v for x,v in missing.items() if x[0]==k),extra=sum(v for x,v in extra.items() if x[0]==k)) for k in sorted({x[0] for x in missing}|{x[0] for x in extra})})

def events(which):return [json.loads(l) for l in gzip.decompress((A/which/'actual.jsonl.gz').read_bytes()).splitlines()]

def verify():
    manifest=load(A/'archive_manifest.json')
    for path,h in manifest.items():assert sha(A/path)==h,path
    pins=load(A/'source_snapshot/sources.json')
    for path,h in pins.items():assert sha(A/'source_snapshot/pinned'/path)==h,path
    source_contract()
    result={}
    for pred,runtime in [('input_prediction_r1','r1_FAIL'),('prediction_r2','r2_PASS')]:
        rec=load(A/runtime/'record.json');ev=events(runtime);cal=compare(A/pred,ev)
        assert json.loads(json.dumps(cal))==rec['calibration'],runtime
        assert sha_raw(A/runtime/'actual.jsonl.gz')==rec['actual_journal_sha256']
        result[runtime]=cal
    assert result['r1_FAIL']['result']=='FAIL' and result['r2_PASS']['result']=='PASS'
    return result

def sha_raw(p):return hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--generate',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.generate:generate(a.generate)
    if a.verify:print(json.dumps(verify(),indent=2,sort_keys=True))
