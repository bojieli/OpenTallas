#!/usr/bin/env python3
"""Pin g2e root source; bind its view only at exact unpadded computed timing."""
import argparse,ast,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import d4g_bank_latency as L
VIEW='physical/ref_tile/hidx_rootctl_am_g2e_1020/views/ot_hbm_idx_rootctl_static_am'
SPEC=Path(__file__).resolve().parents[3]/'physical/ref_tile/hidx_rootctl_am_g2e_1020/spec.json'
RECORD='eba0f5911d485dcc33f02773dff4ec37be971bb2'
PARAMS=dict(VM_RT=65,CR_RT=36,SEL_LAT=30,RSTL=1,FAN32=1)
def apply(c, latency_report=None):
    i=c['instances']['hb_idx__ctl'];assert i['master']=='ot_hbm_idx_rootctl_static_am'
    spec=json.loads(SPEC.read_text());i['source']=spec['sources'][0];i['rtl_deps']=spec['sources'][1:]
    i.pop('physical_view',None);i.pop('closed_record',None);i['force_synth']=True
    if latency_report is None:
        i.setdefault('params',{}).update(PARAMS)
        return dict(selected='SOURCE_ONLY',params=i['params'],reason='timing computed after current S4/S8; hard view deferred',record=RECORD)
    rows,_=L.check(c);rs=[r for r in rows if r['client']=='hb_idx__ctl']
    pads=[p for p in latency_report.get('pads',[]) if p['at'].startswith('hb_idx__ctl.')]
    seg=[s for s in latency_report.get('segments',[]) if s['name'] in ('ctl_cq_cr','ctl_sel')]
    reasons=[]
    if i['params']!=PARAMS:reasons.append('parameters differ from exact closed tuple')
    if not rs or any(r['status']!='PASS' or r.get('unresolved') for r in rs):reasons.append('VM path fails exact resolved latency check')
    if len(seg)!=2 or any(s['pads'] or s.get('fwd_e8_extra') or any(ast.literal_eval(k)[1] for k in s['back']) for s in seg):reasons.append('control paths need padding or unresolved landing timing')
    if pads:reasons.append('root timing has deliberate pads; hard binding deferred pending explicit proof/pricing')
    if not reasons:
        i.pop('force_synth');i['physical_view']=VIEW;i['closed_record']=RECORD
    return dict(selected='SOFT' if reasons else 'EXACT_CLOSED',params=i['params'],reasons=reasons,root_rows=rs,root_pads=pads,segments=seg,record=RECORD)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--latency-report',type=Path);a=p.parse_args()
    c=json.loads(a.input.read_text());r=apply(c,None if a.latency_report is None else json.loads(a.latency_report.read_text()));a.output.write_text(json.dumps(c,indent=1)+'\n');a.report.write_text(json.dumps(r,indent=1)+'\n');print('ROOTCTL_SELECTION',r['selected'])
