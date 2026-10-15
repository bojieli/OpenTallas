#!/usr/bin/env python3
"""Source-exact lifecycle boundary test and observed failing safety mutants."""
import hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
LEAF='rtl/qwen_sys/host_lifecycle_20261014/qkd_host_lifecycle.sv'
ALLOC='rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv'
COHORT='rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_cohort.sv'
TB='rtl/test/qwen_host/lifecycle_1014/tb_qkd_host_lifecycle.sv'
MUTANTS={
 'terminal_identity':(ALLOC,'terminal_tag == expected_terminal','1\'b1'),
 'participant_aggregate':(COHORT,'(&accepted_ranks)','(|accepted_ranks)'),
 'drain_missing_rank':(LEAF,'.terminal_host_drained(&host_drained)',".terminal_host_drained(1'b1)"),
 'post_barrier':(LEAF,'warm_ready && !post_pending','warm_ready'),
 'cancel_ack':(LEAF,'assign cancel_accepted[r] = terminal_accepted && cancel_valid[r]',"assign cancel_accepted[r] = 1'b0 && terminal_accepted && cancel_valid[r]"),
 'wrap_unlock':(ALLOC,"if (next_epoch == 16'hffff) wrap_locked <= 1;","if (next_epoch == 16'hffff) wrap_locked <= 0;"),
 'recovery_missing_rank':(LEAF,'(&reset_witness) && (&train_witness)','(|reset_witness) && (|train_witness)'),
}
def main():
 result={'scope':'Component boundary only; real allocator/cohort RTL; no die/timing qualification',
 'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [LEAF,ALLOC,COHORT,TB]},'runs':{}}
 for name,mutation in [('positive',None),*MUTANTS.items()]:
  with tempfile.TemporaryDirectory(prefix='q-host-lifecycle-') as tmp:
   paths=[]
   for p in [TB,LEAF,ALLOC,COHORT]:
    text=(ROOT/p).read_text()
    if mutation and p==mutation[0]:
     assert mutation[1] in text,mutation
     text=text.replace(mutation[1],mutation[2])
    dest=pathlib.Path(tmp)/pathlib.Path(p).name;dest.write_text(text);paths.append(str(dest))
   exe=str(pathlib.Path(tmp)/'sim')
   subprocess.run(['iverilog','-g2012','-s','tb_qkd_host_lifecycle','-o',exe,*paths],check=True,capture_output=True,text=True)
   proc=subprocess.run(['vvp',exe],capture_output=True,text=True,timeout=30)
   assert (proc.returncode==0)==(mutation is None),(name,proc.stdout,proc.stderr)
   result['runs'][name]={'returncode':proc.returncode,'output':proc.stdout.strip()}
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
