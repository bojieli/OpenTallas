#!/usr/bin/env python3
"""Exact minimum SOURCE + two-edge token store successor, old pinned files unchanged."""
import argparse,json,sys
from pathlib import Path
import dsrom_mtp_rom_bench as B
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 B.COMMON += ['rtl/dsrom_sys/mtp/ot_dsrom_wfc_tok_r3.sv','rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv']
 base=B.cases(); rec=[]
 for name in ('s0_tr_dspark','s0_tr_forced','s0_tr_forced_w16','s0_hash_u3','s0_hash_u1_fast','s0_neg_noepoch'):
  spec=dict(base[name]);spec['tb']='tb_mtp_rom_s0_tokpipe'
  # run_case uses the original top only to label output, so map the successor
  # bench module through a small temporary alias in its own output directory.
  d=a.out/name;d.mkdir(parents=True,exist_ok=True)
  cfg=spec.get('trace');metadata=B.trace_hex(ROOT/B.TRACES/f'{cfg}.cfg.json',d/'trace.hex') if cfg else None
  sources=[str(ROOT/s) for s in B.COMMON]+[str(ROOT/'rtl/dsrom_sys/mtp/tb/tb_mtp_rom_s0_tokpipe.sv')]
  import subprocess
  cmd=['iverilog','-g2012','-s',spec['tb'],'-o',str(d/'sim.vvp')]+[f'-D{x}' for x in spec.get('defines',[])]+[f'-P{spec["tb"]}.{k}={v}' for k,v in spec.get('params',{}).items()]+sources
  r=subprocess.run(cmd,text=True,capture_output=True);(d/'build.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('compile failed '+name)
  r=subprocess.run(['vvp','-n',str(d/'sim.vvp')],cwd=d,text=True,capture_output=True);(d/'run.log').write_text(r.stdout+r.stderr)
  want='MTP_S0 PASS' if spec['expect']=='pass' else 'MTP_S0 FAIL'
  ok=want in r.stdout
  rec.append(dict(case=name,expected=spec['expect'],pass_=ok,trace=metadata,log=name+'/run.log'))
  if not ok:raise RuntimeError(name+' '+r.stdout[-2000:])
 (a.out/'summary.json').write_text(json.dumps(dict(all_ok=all(r['pass_'] for r in rec),source='approved+1prompt cut matchedSOURCE metadata',cases=rec),indent=2)+'\n')
 print(json.dumps(rec))
if __name__=='__main__':main()
