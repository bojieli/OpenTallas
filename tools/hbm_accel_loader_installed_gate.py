#!/usr/bin/env python3
"""One actual upper-BAR/host64/STORE roundtrip bench; compute hosts only.
Reuse the retained loader host image/CRC. No model inference or full-token run.
"""
import argparse,ast,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sources():
    # Reuse the exact existing HA3 system dependency inventory, without running
    # emit/prepare/golden or importing a numerical model.
    tree=ast.parse((ROOT/'tools/gpu_sys/run_system.py').read_text())
    deps=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEP_SRC' for t in n.targets))
    paths=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'rtl/gpu_sys').glob('*.sv'))+deps
    paths += ['rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv','rtl/hbm_accel/collective/ot_hbm_accel_coll_port.sv']
    paths += ['rtl/hbm_accel/loader/'+n+'.sv' for n in ['ot_hbm_accel_loader','ot_hbm_accel_store','ot_hbm_accel_dma64','ot_hbm_accel_loader_host','ot_hbm_accel_hbm_system_loader']]
    return list(dict.fromkeys(paths+['rtl/test/hbm_accel/tb_hbm_accel_loader_installed.sv']))

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--host-image',type=Path,required=True);p.add_argument('--crc4k',required=True);p.add_argument('--jobs',type=int,default=16);p.add_argument('--mem-period-ns',type=float,default=1.0);p.add_argument('--mem-phase-ns',type=float,default=0.0);p.add_argument('--dma-delay',type=int,default=400);a=p.parse_args()
    if not 1<=a.jobs<=16: p.error('jobs must be 1..16 for this remote recipe')
    a.work.mkdir(parents=True,exist_ok=True)
    # Select only the actual first 4 KiB; preserve the full immutable source input.
    image=a.work/'host4k.hex'
    with a.host_image.open() as f: words=[next(f).strip() for _ in range(128)]
    image.write_text('\n'.join(words)+'\n')
    cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-O1','-j',str(a.jobs),'-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH','--x-assign','0','--x-initial','0','--top-module','tb_hbm_accel_loader_installed','--Mdir',str(a.work/'obj')]+[str(ROOT/s) for s in sources()]
    (a.work/'build_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    record={'source_pin':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'host_image':str(a.host_image),'selected_image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'runtime_clocks':{'host_period_ns':1.0,'mem_period_ns':a.mem_period_ns,'mem_phase_ns':a.mem_phase_ns,'DMA_response_delay_host_cycles':a.dma_delay},'scope':'installed LOAD_VERIFY/STORE real checkpoint 4KiB roundtrip with actual host BAR, 64-bit DMA/RLAST/B, per-die clientNCL, no preload, no token simulation','sources':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources()}}
    t=time.monotonic()
    with (a.work/'build.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    record['build_rc']=r.returncode;record['build_seconds']=time.monotonic()-t
    if r.returncode:record['verdict']='FAIL_BUILD'
    else:
        t=time.monotonic()
        with (a.work/'run.log').open('w') as f:r=subprocess.run([str(a.work/'obj/Vtb_hbm_accel_loader_installed'),'+HOSTIMG='+str(image),'+CRC4K='+a.crc4k,'+MEM_HALF_NS='+str(a.mem_period_ns/2),'+MEM_PHASE_NS='+str(a.mem_phase_ns),'+DMA_DELAY='+str(a.dma_delay)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        text=(a.work/'run.log').read_text();record.update(run_rc=r.returncode,run_seconds=time.monotonic()-t,terminal_lines=[l for l in text.splitlines() if l.startswith(('INSTALLED','FEASIBILITY','ROUNDTRIP','PASS','%Error'))],verdict='PASS' if r.returncode==0 and 'PASS installed_loader_roundtrip' in text else 'FAIL_FUNCTIONAL')
    (a.work/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(record['verdict'],flush=True)
    return 0 if record['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
