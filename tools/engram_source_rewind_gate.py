#!/usr/bin/env python3
"""Actual HARD SOURCE SRAM engine→released64-user lead rewind gate; omitted-rewind mutant."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from engram_token_map_image import prepare
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv',*[R/'rtl/dsrom_sys/engram'/p for p in ['ot_dsrom_engram_lead_producer.sv','ot_dsrom_engram_token_map.sv','ot_dsrom_engram_idwin.sv','ot_dsrom_engram_idwin_protected.sv']],R/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',*[R/'physical/asap7_memory_macros'/p/(p+'.v') for p in ['ot_rom_4096x72_m8','ot_sram_1r1w_512x128_m4_r2c2']],R/'rtl/test/tb_dsrom_engram_source_rewind.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
 out=R/'results/rtl/engram_source_rewind_gate_20261009.json'
 if out.exists():raise FileExistsError(out)
 work=Path(tempfile.mkdtemp(prefix='engram-source-rewind-'));images=work/'images';prepare(images);top='tb_dsrom_engram_source_rewind'
 rec=dict(schema='opentallas.engram-source-rewind-gate.v1',retained_objects=str(work),qualification='minimum actual SOURCE event engine, HARDextra2/real SRAM RD_PIPE and released-map64user lead; native594 receive and full program/die integration separately unqualified',cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]})
 for drop in [0,1]:
  obj=work/f'obj{drop}'
  b=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,f'-GDROP_REWIND={drop}','-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True);(work/f'build{drop}.log').write_text(b.stdout+b.stderr)
  if b.returncode:
   rec.update(status='build-fail',build_error=b.stderr[-4000:]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');return 1
  r=subprocess.run([str(obj/f'V{top}'),f'+OT_ROM_DIR={images}'],capture_output=True,text=True)
  ok=(r.returncode!=0 and 'SOURCE rewind window mismatch' in r.stdout) if drop else r.returncode==0 and 'ENGRAM_SOURCE_REWIND PASS' in r.stdout
  rec['cases'][str(drop)]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,expected_observed=ok)
 rec['status']='pass' if all(v['expected_observed'] for v in rec['cases'].values()) else 'fail';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
