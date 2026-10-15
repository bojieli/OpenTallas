#!/usr/bin/env python3
"""Full5052-macro source-exact component build/test. Run through ot-run."""
import argparse,hashlib,json,pathlib,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCES=[*sorted((ROOT/'rtl/dsrom_sys/s81_embedding').glob('ot_s81_embed_full*.sv')),
 ROOT/'rtl/dsrom_sys/s81_embedding/ot_s81_embed_rom_home.sv',ROOT/'rtl/dsrom_sys/s81_embedding/ot_s81_embed_rom_tree.sv',ROOT/'rtl/dsrom_sys/s81_embedding/ot_s81_embed_expand.sv',
 ROOT/'rtl/dsrom_sys/s81_embedding/tb_s81_embed_full_table.sv',
 ROOT/'physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v',
 ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--images',type=pathlib.Path,required=True);ap.add_argument('--fixtures',type=pathlib.Path,required=True);ap.add_argument('--work',type=pathlib.Path,required=True);ap.add_argument('--mutants',type=int,nargs='+',default=[0,1,2]);a=ap.parse_args()
 a.work.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((a.images/'manifest.json').read_text())
 if not manifest['complete_full_vocab'] or len(manifest['macros'])!=5052:raise ValueError('full resident image manifest required')
 for record in manifest['macros']:
  if sha(a.images/record['path'])!=record['sha256']:raise ValueError(record)
 record=dict(fixtures_sha256={p:sha(a.fixtures/p) for p in ['expected.mem','tokens.mem','fixtures.json']},sources={str(p.relative_to(ROOT)):sha(p) for p in SOURCES},image_manifest_sha256=sha(a.images/'manifest.json'),image_macros=5052,
  images_validated=True,runs={},scope='Full-resident macro functional component; physical inter-HEAD/link/VM composition and native reset/phi-R not qualified')
 for mutant in a.mutants:
  obj=a.work/f'obj_m{mutant}';run=a.work/f'run_m{mutant}';run.mkdir(parents=True,exist_ok=True)
  cmd=['verilator','--binary','--timing','-j','4','-O1','-CFLAGS','-O0','--output-split','10000','-Wno-fatal','-Wno-WIDTH','-Wno-UNSIGNED','--top-module','tb_s81_embed_full_table',f'-GMUTANT={mutant}','--Mdir',str(obj),'-o','tb',*map(str,SOURCES)]
  with (a.work/f'build_m{mutant}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  proc=subprocess.run([str(obj/'tb'),f'+OT_ROM_DIR={a.images}',f'+EXPECTED={a.fixtures/"expected.mem"}',f'+TOKENS={a.fixtures/"tokens.mem"}',f'+OUT={run}'],capture_output=True,text=True)
  (a.work/f'run_m{mutant}.log').write_text(proc.stdout+proc.stderr)
  record['runs'][str(mutant)]={'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
  (a.work/'record.partial.json').write_text(json.dumps(record,indent=2)+'\n')
  if (proc.returncode==0)!=(mutant==0):raise RuntimeError((mutant,proc.returncode,proc.stdout[-2000:]))
  if mutant==0 and 'S81_FULL_EMBED PASS' not in proc.stdout:raise RuntimeError('missing whole table completion')
  shutil.rmtree(obj)
 record['pass']=True;(a.work/'record.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
