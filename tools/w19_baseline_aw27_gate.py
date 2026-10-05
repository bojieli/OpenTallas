#!/usr/bin/env python3
"""Bounded actual-resident accepted256B fetch/SM address gate; no token claim."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import pickle
import shlex
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/'results/uarch/w19_baseline_aw27_prebuild.json'
OWNER='c98db4d2b21d8f9b691978dcd4891a2aa787aeae'
SM='000ba0898f5120a66d5905ccff333ebbbe28394d'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(pin,path):return subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
def owner_module(name,work):
    p=work/(name+'.py');p.write_bytes(blob(OWNER,'tools/'+name+'.py'))
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable-wide',action='store_true');ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--record',type=Path,required=True);ap.add_argument('--stimulus',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path);ap.add_argument('--host',required=True)
    ap.add_argument('--ssh-key',type=Path,required=True);ap.add_argument('--remote-work',required=True)
    a=ap.parse_args()
    if not a.enable_wide:ap.error('Candidate OFF; explicit --enable-wide required')
    if a.record.exists() or a.work.exists():ap.error('Fresh record and work required')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():ap.error('Clean committed source required')
    a.work.mkdir(parents=True)
    r=dict(schema='opentallas.w19.baseline_aw27_actual_resident_gate.v1',status='fail',cases=[],fault_controls=[],
           source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           prebuild_sha256=sha(PRE),prebuild=json.loads(PRE.read_text()),owner_source_commit=OWNER,SM_snapshot=SM,
           stimulus_sha256=sha(a.stimulus),full_resident_admitted=False,full_token=False,adoption=False,
           model_headlines='UNCHANGED',timing_scope='833ps bench clock; original finiteHBM CLK_PS833 REQ/RSP15ns and3.9us refresh. Preloads and6000-cycle refresh warmup excluded from diagnostic operation timing; no500ns loaded/shared-service or token-rate claim.',
           claim_boundary='Three actual rank0 resident routed descriptor fragments at L13/L26/L33 and full K. Real checkpoint weights/fresh golden; retained L0 input activation stimulus. Existing finite fetch and padded512-tag bench join into historical W13 SM. No compact adapter, runtime router, connected activations, all32SM/96rank arithmetic, collectives, attention/KV/SU/SFU or current hardware/SSFF qualification.')
    ssh=['ssh','-i',str(a.ssh_key),a.host];scp=['scp','-q','-i',str(a.ssh_key)]
    def remote(cmd):return subprocess.run(ssh+[cmd],capture_output=True,text=True,timeout=180)
    def checked(cmd):
        p=remote(cmd)
        if p.returncode:raise ValueError(p.stdout+p.stderr)
        return p.stdout
    def send(paths,dest):subprocess.run(scp+list(map(str,paths))+[a.host+':'+dest+'/'],check=True,timeout=90)
    try:
        # Evaluate only the pre-committed, additive historical model helper.
        pre=r['prebuild'];raw=blob(pre['model_source_commit'],'tools/uarch_model.py')
        assert hashlib.sha256(raw).hexdigest()==pre['model_source_sha256']
        fn=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==pre['model_symbol'])
        assert hashlib.sha256(ast.dump(fn,include_attributes=False).encode()).hexdigest()==pre['model_symbol_ast_sha256']
        ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned_model','exec'),ns)
        assert ns[fn.name](27)==pre['address_model']
        r['model_prebuild_verified']=True
        w16=ROOT/'results/uarch/w16_w19_address_prerequisite_20261001/prerequisite_r2.json'
        assert sha(w16)==pre['w16_prerequisite_sha256']
        sys.path.insert(0,str(ROOT/'tools'))
        import numpy as np
        import w19_baseline_address as B
        import w19_sm_real_ops as S
        import hdc_golden_v41 as V
        C=owner_module('w19_checkpoint_stream',a.work);H=owner_module('w19_sparse_hbm',a.work)
        ck=C.LC.Checkpoint(a.checkpoint or C.LC.HF)
        r['checkpoint_index_sha256']=sha(ck.snap/'model.safetensors.index.json')
        r['dependencies_sha256']={str(Path(m.__file__).relative_to(ROOT)):sha(m.__file__) for m in (S,V,S.G,S.S,C.LC)}
        r['owner_companions_sha256']={n:sha(a.work/(n+'.py')) for n in ('w19_checkpoint_stream','w19_sparse_hbm')}
        hist=json.loads((ROOT/'results/rtl/w19_fetch_sm.json').read_text())
        assert hist['sm_snapshot']['commit']==SM
        sources=[];r['sources_sha256']={}
        for p,h in hist['sm_snapshot']['source_sha256'].items():
            dest=a.work/Path(p).name;dest.write_bytes(blob(SM,p));assert sha(dest)==h
            sources.append(dest);r['sources_sha256'][p]=h
        for p in ('rtl/gpu/ot_gpu_expert_fetch.sv','rtl/test/tb_w19_baseline_aw27.sv'):
            dest=a.work/Path(p).name;dest.write_bytes((ROOT/p).read_bytes());sources.append(dest);r['sources_sha256'][p]=sha(dest)
        dest=a.work/'ot_hdc_hbm_sparse_model.sv';r['sparse_controller_proof']=H.generate(ROOT/'rtl/hdc/kv/ot_hdc_hbm_model.sv',dest);sources.append(dest)
        r['sources_sha256']['generated/'+dest.name]=sha(dest)
        for p in ('tools/w19_baseline_address.py','tools/w19_baseline_aw27_gate.py','tests/test_w19_baseline_address.py'):
            r['sources_sha256'][p]=sha(ROOT/p)
        assert len({p.name for p in sources})==len(sources)
        check=remote('test ! -e '+shlex.quote(a.remote_work))
        if check.returncode:raise ValueError('Fresh remote directory required')
        checked('mkdir -p '+shlex.quote(a.remote_work));send(sources,a.remote_work)
        r['host']=a.host;r['remote_work']=a.remote_work;r['simulator']=checked('iverilog -V 2>/dev/null | head -1')
        r['resource_receipt']=checked('uptime; free -m; df -h /home/ubuntu')
        tb='tb_w19_baseline_aw27'
        compile_cmd='cd '+shlex.quote(a.remote_work)+' && nice -n 15 iverilog -g2012 -s '+tb+' -P'+tb+'.NC=1 '
        compile_src=' '.join(shlex.quote(p.name) for p in sources)
        for name,aw,enabled in [('sim',27,1),('default24',24,0),('off27',27,0)]:
            log=checked(compile_cmd+'-P'+tb+'.HBM_AW='+str(aw)+' -P'+tb+'.ENABLE_WIDE='+str(enabled)+' -o '+name+'.vvp '+compile_src+' 2>&1')
            (a.work/(name+'.compile.log')).write_text(log)
        r['executable_sha256']={n:checked('sha256sum '+shlex.quote(a.remote_work+'/'+n+'.vvp')).split()[0] for n in ('sim','default24','off27')}
        stimulus=pickle.loads(a.stimulus.read_bytes())
        for ci,case in enumerate(pre['cases']):
            row=case['descriptor'];e=case['expert_id'];family=row['family'];L=row['layer']
            name=f'layers.{L}.ffn.experts.{e}.{family}.weight';scale=name[:-6]+'scale'
            codes,dt=C.raw_view(ck,name);scales,sd=C.raw_view(ck,scale)
            assert dt=='I8' and sd=='F8_E8M0';lo,hi=row['rows'];cs=codes[lo:hi].copy()
            ex=scales[lo:hi].copy() if len(scales)==len(codes) else scales[np.arange(lo,hi)//32].copy()
            del codes,scales;C.close_mappings(ck)
            q=np.stack((V.E2M1[cs&15],V.E2M1[cs>>4]),axis=-1).reshape(hi-lo,row['K'])
            w=V.Q8(q,ex.astype(np.int32)-127)
            key=next(k for k,v in stimulus.items() if v['tag']=='expert slot 0 '+family)
            x=stimulus[key]['x'];assert len(x)==row['K'];capture={}
            def fixture_only(params,d):capture.update(params=params,d=d);return {},{}
            _,gold,meta=S.smv_real(name,'v41_fp4',w,[x],workdir=a.work,sim_runner=fixture_only)
            d=capture['d'];logical_pin=sha(d/'lines.hex')
            raw_proof=C.write_logical(ck,name,row['rows'],row['K'],'fp4',d/'raw_lines.hex')
            assert raw_proof['logical_sha256']==logical_pin and raw_proof['payloads']==row['payloads']
            expected=[f'{i} {int(bits):08x}' for i,bits in enumerate(gold[0].view(np.uint32))]
            (d/'golden.txt').write_text('\n'.join(expected)+'\n')
            desc=B.load_fragment(d/'raw_lines.hex',d,row,e,expected_sha256=logical_pin,enable=True,address_bits=27)
            assert desc['first_sector']*32==case['first_byte']
            base_cfg=(d/'cfg.hex').read_text().splitlines();base_cfg[6]=f'{e:08x}'
            base_cfg += [f"{row['cfg_exp_lines']:08x}",f"{row['cfg_off']:08x}",f"{row['cfg_base_line']:08x}"]
            for stall in (0,1):
                cfg=list(base_cfg);cfg[7]=f'{stall:08x}';(d/'cfg.hex').write_text('\n'.join(cfg)+'\n')
                target=a.remote_work+f'/case{ci}_{stall}';checked('mkdir -p '+shlex.quote(target))
                send([d/p for p in ('cfg.hex','lines.hex','x.hex','sparse_keys.hex','sparse_values.hex','golden.txt')],target)
                run=remote('cd '+shlex.quote(target)+' && nice -n 15 vvp -n ../sim.vvp +DIR=. > sim.log 2>&1')
                log=checked('cat '+shlex.quote(target+'/sim.log'));(a.work/f'case{ci}_{stall}.sim.log').write_text(log)
                out=checked('cat '+shlex.quote(target+'/out.txt'));(a.work/f'case{ci}_{stall}.out').write_text(out)
                actual=[line for line in out.splitlines() if not line.startswith('#')]
                same=actual==expected;entry=dict(layer=L,family=family,expert_id=e,rank=row['rank'],stack=row['stack'],sm=row['sm'],rows=row['rows'],K=row['K'],stall=stall,first_byte=case['first_byte'],boundary_bytes=case['boundary_bytes'],descriptor=desc,raw_proof=raw_proof,stimulus_key=key,x_sha256=hashlib.sha256(x.tobytes()).hexdigest(),golden_sha256=sha(d/'golden.txt'),fixture_sha256={p:sha(d/p) for p in ('cfg.hex','x.hex','lines.hex','sparse_keys.hex','sparse_values.hex')},output_sha256=sha(a.work/f'case{ci}_{stall}.out'),exit_code=run.returncode,exact_FP32=same,exact_BF16=False,pass_case=False)
                if same:
                    acc=np.array([int(v.split()[1],16) for v in actual],dtype=np.uint32).view(np.float32)
                    entry['exact_BF16']=bool(np.array_equal(S.S.bf16_bits(acc),S.S.bf16_bits(V.linear_q(w,x))))
                entry['pass_case']=run.returncode==0 and same and entry['exact_BF16'] and 'FATAL' not in log and 'refreshes 0' not in out
                r['cases'].append(entry);print('case',ci,'stall',stall,'PASS' if entry['pass_case'] else 'FAIL',flush=True)
                if not entry['pass_case']:raise ValueError('Connected actual-resident arithmetic gate failed')
            # AW24, opt-in and full-address sparse alias controls on each resident fragment.
            target=a.remote_work+f'/case{ci}_0'
            for exe,reason in (('default24','AW_BOUNDARY_OVERFLOW'),('off27','WIDE_DEFAULT_OFF')):
                run=remote('cd '+shlex.quote(target)+' && nice -n 15 vvp -n ../'+exe+'.vvp +DIR=. > '+exe+'.log 2>&1')
                log=checked('cat '+shlex.quote(target+'/'+exe+'.log'));(a.work/f'case{ci}_{exe}.log').write_text(log)
                ok=run.returncode!=0 and reason in log;r['fault_controls'].append(dict(case=ci,control=exe,pass_control=ok,log_sha256=sha(a.work/f'case{ci}_{exe}.log')))
                if not ok:raise ValueError('Narrow/default-off control failed')
            alias=a.remote_work+f'/alias{ci}';checked('mkdir -p '+shlex.quote(alias))
            # All keys retain only low24 bits; never supply actual high resident addresses.
            keys=d/'alias_keys.hex';keys.write_text(''.join(f'{int(s,16)&((1<<24)-1):08x}\n' for s in (d/'sparse_keys.hex').read_text().splitlines()))
            send([d/p for p in ('cfg.hex','lines.hex','x.hex','sparse_values.hex')],alias);send([keys],alias)
            checked('mv '+shlex.quote(alias+'/alias_keys.hex')+' '+shlex.quote(alias+'/sparse_keys.hex'))
            run=remote('cd '+shlex.quote(alias)+' && nice -n 15 vvp -n ../sim.vvp +DIR=. > sim.log 2>&1')
            log=checked('cat '+shlex.quote(alias+'/sim.log'));(a.work/f'case{ci}_alias.log').write_text(log)
            ok=run.returncode!=0 and 'SPARSE_HBM_UNMAPPED_ADDRESS' in log;r['fault_controls'].append(dict(case=ci,control='low24_alias',pass_control=ok,log_sha256=sha(a.work/f'case{ci}_alias.log')))
            if not ok:raise ValueError('Missing full-address alias control failed')
        r['status']='pass'
    except Exception as e:r['error']=str(e)
    finally:
        a.record.parent.mkdir(parents=True,exist_ok=True)
        with a.record.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(r['status'].upper(),a.record,flush=True)
    return 0 if r['status']=='pass' else 1

if __name__=='__main__':raise SystemExit(main())
