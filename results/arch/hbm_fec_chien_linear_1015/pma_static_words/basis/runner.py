#!/usr/bin/env python3
"""Run admitted exact old/new PMA proof; no production adoption or area claim."""
import argparse,hashlib,json,pathlib,subprocess,time

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--basis',action='store_true');ap.add_argument('--mutant',choices=['none','lastword','write_decode','read_wire'],default='none');a=ap.parse_args()
 source=a.source.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);files={p.name:p for p in source.glob('*.sv')};assert len(files)==3
 pins={n:sha(p) for n,p in files.items()};candidate=files['ot_hbm_pma_block_gearbox_static_words.sv'];text=candidate.read_text();mut=0
 if a.mutant=='lastword':mut=1
 elif a.mutant=='write_decode':
  before='assign write_word_sel[w]=(wi==w);';assert text.count(before)==1;text=text.replace(before,'assign write_word_sel[w]=(wi==((w==0)?1:w));')
 elif a.mutant=='read_wire':
  before='assign bank_read[g]=tree[0];';assert text.count(before)==1;text=text.replace(before,"assign bank_read[g]=tree[0] ^ {{(WO-1){1'b0}},1'b1};")
 if text!=candidate.read_text():candidate=out/'actual_gate_mutant.sv';candidate.write_text(text)
 command=['iverilog','-g2012','-s','tb_pma_static_words',f'-Ptb_pma_static_words.DMUT={mut}','-o',str(out/'sim'),str(files['ot_hbm_pma_block_gearbox.sv']),str(candidate),str(files['tb_pma_static_words.sv'])]
 if a.basis:
  command=['verilator','--binary','--timing','--top-module','tb_pma_static_words','-Wno-fatal','--Mdir',str(out/'obj'),'-j','4','-GRUN_BASIS=1',f'-GDMUT={mut}',str(files['ot_hbm_pma_block_gearbox.sv']),str(candidate),str(files['tb_pma_static_words.sv'])]
 start=time.monotonic()
 with (out/'compile.log').open('w') as log:build=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 if build.returncode==0:
  with (out/'sim.log').open('w') as log:run=subprocess.run([str(out/'obj/Vtb_pma_static_words')] if a.basis else ['vvp',str(out/'sim')],stdout=log,stderr=subprocess.STDOUT)
 else:run=None
 passed=run is not None and run.returncode==0 and 'PMA_STATIC_WORDS_PASS' in (out/'sim.log').read_text()
 accepted=passed if a.mutant=='none' else run is not None and run.returncode!=0 and 'FATAL:' in (out/'sim.log').read_text()
 assert {n:sha(p) for n,p in files.items()}==pins
 r={'scope':('ACTUAL_OLD_NEW_VERILATOR_PMA_ALL8704_BLOCK_BIT_BASIS_PROOF' if a.basis else 'ACTUAL_OLD_NEW_FOUR_STATE_PMA_STATIC_WORDS_PROTOCOL_PROOF'),'source_sha256':pins,'runner_sha256':sha(pathlib.Path(__file__)),'mutant':a.mutant,'actual_mutant_source_sha256':sha(candidate) if a.mutant!='none' else None,'compile_exit':build.returncode,'simulation_exit':run.returncode if run else None,'basis_enabled':a.basis,'positive_pass':passed,'expected_verdict_pass':accepted,'elapsed_seconds':time.monotonic()-start,'compile_log_sha256':sha(out/'compile.log'),'sim_log_sha256':sha(out/'sim.log') if run else None,'physical_qualified':False,'new_cycles':0,'baseline_modified':False}
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if accepted else 1
if __name__=='__main__':raise SystemExit(main())
