#!/usr/bin/env python3
"""Immutable minimum native boundary burst gate, including negative controls."""
import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path
from hbm_loader_native_service_model import native_burst_model
R=Path(__file__).resolve().parents[1]
D=R/'rtl/hbm_accel/loader/service_native'

def simulate(lease, boundary, temporary, *, burst=1, mode=0, enable=1):
    exe=temporary/'sim'
    cmd=['iverilog','-g2012','-s','tb_loader_service_burst',
         f'-Ptb_loader_service_burst.BURST={burst}',f'-Ptb_loader_service_burst.NATIVE_ENABLE={enable}','-o',str(exe),
         str(lease),str(boundary),str(D/'tb_loader_service_burst.sv')]
    cp=subprocess.run(cmd,capture_output=True,text=True)
    if cp.returncode:
        return dict(passed=False,compile=cp.stdout+cp.stderr)
    cp=subprocess.run(['vvp',str(exe),f'+mode={mode}'],capture_output=True,text=True)
    measured=re.search(r'MEASURE sectors=(\d+) commands=(\d+) cycles=(\d+) bytes=(\d+) last_burst_beat_span=(\d+)',cp.stdout)
    result=dict(passed=cp.returncode==0 and 'PASS' in cp.stdout,output=cp.stdout+cp.stderr)
    if measured:
        result['measurement']=dict(zip(('sectors','commands','cycles','bytes','last_burst_beat_span'),map(int,measured.groups())))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    lease=D/'ot_hbm_loader_pc_service_lease.sv';boundary=D/'ot_hbm_loader_service_boundary.sv'
    with tempfile.TemporaryDirectory(prefix='native-burst-gate-') as t:
        td=Path(t)
        cases=[dict(name='opt_in_all_lengths_and_stream',**simulate(lease,boundary,td)),
               dict(name='default_single_sector',**simulate(lease,boundary,td,burst=0)),
               dict(name='disabled_passthrough',**simulate(lease,boundary,td,enable=0))]
        for mode,name in ((1,'wrong_tag'),(2,'out_of_range_beat'),(3,'duplicate_beat')):
            cases.append(dict(name=name,**simulate(lease,boundary,td,mode=mode)))
        definitions=[
            ('ignore_response_identity',lease,'wire native_match=kr_tag=={1\'b1,tag_q}&&kr_beat==received_q;','wire native_match=1;',1),
            ('ignore_beat_identity',lease,'kr_beat==received_q','1\'b1',3),
            ('force_single_sector',lease,'assign k_len=is_normal?normal_len:len_q;','assign k_len=is_normal?normal_len:4\'d1;',0),
            ('release_boundary_first_beat',boundary,'if(native_rsp_v&&native_rsp_rdy&&native_rsp_beat==len_q-1)active<=0;','if(native_rsp_v&&native_rsp_rdy)active<=0;',0),
            ('release_lease_first_beat',lease,'if(received_q+1==len_q)state<=REPLY;','state<=REPLY;',0),
            ('ignore_read_debt',lease,'is_normal&&read_debt==0&&write_debt==0','is_normal&&write_debt==0',0),
            ('ignore_write_debt',lease,'is_normal&&read_debt==0&&write_debt==0','is_normal&&read_debt==0',0),
            ('ignore_pending_write',lease,'&&!normal_pending_write&&!sticky','&&!sticky',0),
            ('ignore_response_backpressure',lease,'&&(!reply_full||native_rsp_rdy)','',0),
        ]
        mutants=[]
        for name,src,before,after,mode in definitions:
            raw=src.read_text();assert raw.count(before)==1,(name,before)
            path=td/(name+'.sv');path.write_text(raw.replace(before,after))
            result=simulate(path if src==lease else lease,path if src==boundary else boundary,td,mode=mode)
            mutants.append(dict(name=name,detected=not result['passed'],**result))
    ok=all(c['passed'] for c in cases) and all(m['detected'] for m in mutants)
    files=[lease,boundary,D/'tb_loader_service_burst.sv',D/'ot_hbm_svc_core_native.sv',
           R/'tools/hbm_loader_service_boundary_build.py',R/'tools/hbm_loader_service_core_bind.py',
           R/'tools/hbm_loader_native_service_model.py',Path(__file__),
           *[D/n for n in ('tb_hfd_loader_kport.sv','tb_loader_service_core_native.sv','tb_loader_service_iks.sv','tb_loader_service_kvs.sv')]]
    result=dict(verdict='PASS_NATIVE_BURST_BOUNDARY' if ok else 'FAIL',model=native_burst_model(),cases=cases,mutants=mutants,
        source_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        source_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
        physical_admitted=False,token_credit=False,
        limitations=['minimum boundary vehicle with ready PHY responses; actual PHY service, floorplan and host load not measured',
                     'caller must provide a PC-local sector burst; global mapped contiguous runs must split at every PC mapping boundary',
                     'one active transaction per stack remains; native burst alone does not establish 90% HBM bandwidth',
                     'no RTL route, timing closure, adoption or token-rate claim'])
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['verdict'])
    for m in mutants:
        if not m['detected']:print('UNDETECTED',m['name'])
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
