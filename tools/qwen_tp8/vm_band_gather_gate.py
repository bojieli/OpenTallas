#!/usr/bin/env python3
"""Logical fullfan + proxydata alignment + full32 gather; no physical gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/qwen_sys/vm_plane_20261013'
OUT=ROOT/'results/rtl/qwen_tp8_vm_plane_20261013/vm_band_gather'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=[P/'band_gather/tb_qfd_vm_band_gather.sv',P/'band_gather/ot_qfd_vm_band_gather.sv',P/'band_controls/ot_qfd_vm_band_controls.sv',P/'ot_qfd_vm_xtree.sv',P/'ot_qfd_vm_xplane.sv']
    source_hash={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    rows=[]
    with tempfile.TemporaryDirectory(prefix='vm-gather-') as tmp:
      frozen=[]
      for p in files:
       copy=Path(tmp)/p.name;copy.write_bytes(p.read_bytes());frozen.append(copy)
      for sm in (9,11):
       for lat in (1,3):
        for mut in (0,1,2,3,4):
         name=f'smax{sm}_lat{lat}_mut{mut}';binary=Path(tmp)/name
         build=subprocess.run(['iverilog','-g2012','-s','tb_qfd_vm_band_gather',f'-Ptb_qfd_vm_band_gather.SMAX={sm}',f'-Ptb_qfd_vm_band_gather.LAT={lat}',f'-Ptb_qfd_vm_band_gather.MUT={mut}','-o',str(binary),*map(str,frozen)],capture_output=True,text=True)
         assert build.returncode==0,build.stderr
         run=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
         (OUT/f'{name}.log').write_text(run.stdout+run.stderr)
         good=(run.returncode==0 and 'PASS gather ' in run.stdout) if mut==0 else (run.returncode!=0 and 'FAIL gather ' in run.stdout)
         assert good,(name,run.stdout,run.stderr)
         rows.append(dict(name=name,SMAX=sm,phases=(1<<sm)//128,LAT=lat,mutant=mut,returncode=run.returncode,expected_result='PASS' if mut==0 else 'FAIL',log=str((OUT/f'{name}.log').relative_to(ROOT))))
         print(name,run.stdout.splitlines()[0],flush=True)
    assert source_hash=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'source changed during gather gate; rerun final sources'
    rec=dict(schema='opentallas.qwen.vm-band-gather-bench.v1',status='LOGICAL_FULL32_PASS_PHYSICAL_AND_ROOT_DELIVERY_UNMEASURED',NRB=64,columns=32,roots=32,data_bits=4096,
      input_order='plane_data[128*column+4*root+element]',output_order='root_words[128*root+32*element+column]',tag_source='rootr receives columnr phase +epoch16+valid; actual assigned source/station remains pending',
      source_sha256=source_hash,runs=rows,
      bench_scope='actual full116fan controls/ME composition + EXACTLY logicalproxyalignment (three actual W512/MEREG1 relay stages) + parameterized gather; compare all4096data bits and32tags perclock under stalls. Every live data/tag bit observed as0and1; all4/16phases observed. Adversarial column-specific epoch salt proves designated-column tagselection. Source data changes even during stalls.',
      mutants={'1':'wrong transpose rootword[4*col+k]','2':'one512bit relay bank ignores stalls','3':'root13 wrong epoch','4':'wrong designated tag source column'},
      latency=dict(logicalproxyalignment_enabled_edges=3,gather_tested_enabled_edges=[1,3],free_me_edges=2,local_MEREG_free_edges=1),
      exclusions=['Does not instantiate actual xcol_roots/sourceconsumer/line_store; source-root+3 semantics NOT proved.','LAT1/LAT3 are logical parameter checks; neither is physical routeintent.','No final boundary pins, rootstation coordinates, physical per-bit paths or clockpair timing.','Rootdelivery latency and production throughput/price UNMEASURED; no qualification.'])
    (OUT/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
