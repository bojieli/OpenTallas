#!/usr/bin/env python3
"""One actual full K512 publisher/mux/four-stack backend gate; no token claim."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='f6df84e14c2bc5908bdbf85b2bd95cd56b1f5520'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--jobs',type=int,default=2);ap.add_argument('--verilator',required=True);ap.add_argument('--two-positions',action='store_true')
 a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 git=lambda *v:subprocess.check_output(['git',*v],cwd=ROOT)
 if git('status','--porcelain').strip():raise SystemExit('long gate requires clean pinned source')
 model=json.loads((ROOT/'results/uarch/dsrom_c8_publication_20261003/model.json').read_text())
 assert model['admission']['isolated_actual_backend_functional']
 paths=git('show',PIN+':tools/w17_current_fastpp_l20_window_owner_safe_sources.txt').decode().split()
 files=[];pins={}
 headers=[p for p in git('ls-tree','-r','--name-only',PIN,'rtl/hdc/v41').decode().splitlines() if p.endswith('.svh')]
 for path in headers:
  blob=git('show',PIN+':'+path);q=out/'original'/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(blob);pins[path]=hashlib.sha256(blob).hexdigest()
 for path in paths:
  blob=git('show',PIN+':'+path);q=out/'original'/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(blob)
  files.append(str(q));pins[path]=hashlib.sha256(blob).hexdigest()
 current=['rtl/dsrom_sys/c8/ot_hdc_v41x_idx_hbm_c8.sv','rtl/dsrom_sys/c8/ot_chip_v41x_kv_reqmux_c8.sv','rtl/dsrom_sys/c8/ot_chip_v41x_kv_rope_reqmux_c8.sv','rtl/dsrom_sys/c8/ot_chip_v41x_ckv_die_service_c8.sv','rtl/dsrom_sys/c8/ot_dsrom_c8_write_journal.sv','rtl/test/dsrom_sys/c8/tb_dsrom_c8_native.sv']
 top='tb_dsrom_c8_two_positions' if a.two_positions else 'tb_dsrom_c8_native'
 if a.two_positions:current[-1]='rtl/test/dsrom_sys/c8/tb_dsrom_c8_two_positions.sv'
 for path in current:
  q=ROOT/path;files.append(str(q));pins[path]=hashlib.sha256(q.read_bytes()).hexdigest()
 cmd=[a.verilator,'--binary','--timing','--top-module',top,'--Mdir',str(out/'obj'),'-j',str(a.jobs),'-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-Wno-MODDUP','-Wno-UNOPTFLAT',f"-I{out/'original/rtl/hdc/v41'}",*files]
 rec=dict(source_commit=git('rev-parse','HEAD').decode().strip(),original_pin=PIN,source_sha256=pins,command=cmd,scope='native publisher/transport/readback only; actual two-position engine and physical/protected-state unqualified',pass_=False)
 (out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 t=time.monotonic()
 with (out/'compile.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 rec['compile_exit']=rc
 if rc==0:
  with (out/'run.log').open('w') as f:rc=subprocess.call([str(out/'obj'/('V'+top))],stdout=f,stderr=subprocess.STDOUT)
  rec['run_exit']=rc;rec['terminal']=(out/'run.log').read_text();rec['pass_']=rc==0 and ('PASS C8_TWO_POSITIONS' if a.two_positions else 'PASS C8_ACTUAL_CWRITER') in rec['terminal']
 rec['elapsed_seconds']=time.monotonic()-t
 rec['log_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}
 (out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2));return 0 if rec['pass_'] else 1
if __name__=='__main__':raise SystemExit(main())
