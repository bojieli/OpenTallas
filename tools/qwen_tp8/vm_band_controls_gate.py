#!/usr/bin/env python3
"""Small, CPU-only actual fan primitive bench; not a physical or whole VM gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/qwen_sys/vm_plane_20261013'
OUT=ROOT/'results/rtl/qwen_tp8_vm_plane_20261013/vm_band_controls'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=[P/'band_controls/tb_qfd_vm_band_controls.sv',P/'band_controls/ot_qfd_vm_band_controls.sv',P/'ot_qfd_vm_xtree.sv']
    rows=[]
    with tempfile.TemporaryDirectory(prefix='vm-controls-') as tmp:
      for sm in (9,11):
       for mut in (0,1,2):
        name=f'smax{sm}_mut{mut}'
        binary=Path(tmp)/name
        build=subprocess.run(['iverilog','-g2012','-s','tb_qfd_vm_band_controls',f'-Ptb_qfd_vm_band_controls.SMAX={sm}',f'-Ptb_qfd_vm_band_controls.MUT={mut}','-o',str(binary),*map(str,files)],capture_output=True,text=True)
        assert build.returncode==0,build.stderr
        run=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
        (OUT/f'{name}.log').write_text(run.stdout+run.stderr)
        good=(run.returncode==0 and 'PASS controls ' in run.stdout) if mut==0 else (run.returncode!=0 and 'FAIL controls ' in run.stdout)
        assert good,(name,run.stdout,run.stderr)
        rows.append(dict(name=name,SMAX=sm,phases=(1<<sm)//128,mutant=mut,returncode=run.returncode,expected_result='PASS' if mut==0 else 'FAIL',log=str((OUT/f'{name}.log').relative_to(ROOT))))
        print(run.stdout.splitlines()[0])
    rec=dict(schema='opentallas.qwen.vm-band-controls-bench.v1',status='LOGICAL_FULL32_PASS_PHYSICAL_AND_END_TO_END_UNRESOLVED',NRB=64,columns=32,tagged_payload_bits_native=67,tagged_payload_bits_fallback=69,
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},runs=rows,
      bench_scope='All32 full20/28bit control payloads plus separate28bit tag bank (19native/21fallback livebits) through actual fan primitives; actual two free-running ME stages plus each fan MEREG; 640 cycles and input changes during stalls. Independent serial register reference; every live control/tag bit observed as both0and1. Both full32 delay and epoch mutants fail for both production phase counts.',
      latency=dict(control_enabled_edges=3,me_free_edges=2,fan_local_MEREG_free_edges=1,existing_source_root_enabled_edges=3,control_plus_source_root_enabled_edges=6),
      exclusions=['Does not instantiate source roots or data c_a/c_n/control consumers; source-root +3 alignment is unresolved.','Synthetic phase/epoch/valid tags exercise bit transport; no production scheduler semantics are asserted.','No assigned boundary pins, no assigned station coordinates, no per-pin physical pair timing proof.','No throughput or die timing qualification.'])
    (OUT/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
