#!/usr/bin/env python3
"""Pinned minimum full-shape protected re-index parent component gates."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 macro='physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v'
 src=['rtl/dsrom_sys/reindex_parent/ot_dsrom_reindex_list_macro.sv','rtl/dsrom_sys/reindex_parent/tb_dsrom_reindex_list_macro.sv',macro]
 pins=src+['tools/dsrom_reindex_parent_gate.py','tools/dsrom_reindex_parent_model.py','tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py']
 record=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},component='fullshape list16macros',threads=4)
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'dirty source worktree'
 v=os.environ.get('OT_VERILATOR','verilator')
 cmd=[v,'--binary','--timing','--build','-j','4','-Wno-fatal','-Wno-WIDTH','--top-module','tb_dsrom_reindex_list_macro','--Mdir',str(a.out.resolve()/'obj'),*[str(ROOT/f) for f in src]]
 with (a.out/'build.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 record['build_exit']=r.returncode
 if r.returncode==0:
  with (a.out/'run.log').open('w') as f:r=subprocess.run([str(a.out.resolve()/'obj/Vtb_dsrom_reindex_list_macro')],stdout=f,stderr=subprocess.STDOUT)
  record['run_exit']=r.returncode
  record['pass']=r.returncode==0 and '\nPASS\n' in (a.out/'run.log').read_text()
 else:record['pass']=False
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
 if not record['pass']:raise SystemExit(1)
if __name__=='__main__':main()
