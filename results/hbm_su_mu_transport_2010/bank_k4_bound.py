import json,sys,collections
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/wt/path-hbm-r13-1026')
sys.path[:0]=[str(root/'tools/throughput'),str(root/'tools')]
import accepted_cost as A
from hgi_sim import ds_native_timing as DT
_,rs=DT.load(root/'results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json')
frames=[{'layer':int(r.src_key.split(':')[0]),'op':r.unit+'.'+r.op,'global_keys':r.imm_a} for r in rs if r.unit=='IDX' and r.op=='INDEX']
run,count=A.hbm_schedule('ds');base=run()
if abs(base-576702.4)>0.11:raise RuntimeError(('incomplete model source',base))
result={'scope':'conditional R8 one query event and one key stream per IDX.INDEX record; physical pass multiplicity not yet qualified', 'frames':frames,'records_per_token':count['IDX.INDEX'],'baseline_cycles':base,'bank_k':4,'nkeys_per_stream_upper_assumption':2736,'beats_upper':171}
for name,extra in [('rate_at_most_one_per_four',5),('one_beat_per_cycle_max171',518)]:
 cycles=run(extra=(('IDX.INDEX',None,float(extra)),))
 result[name]={'added_cycles_per_index_frame':extra,'cycles':cycles,'added_cycles':cycles-base,'tok_s':1.2e9/cycles,'loss_pct':(1-base/cycles)*100}
# A serial token upper envelope remains valid regardless of schedule overlap if the R8 frame assumption holds.
result['serial_upper_added_cycles']=len(frames)*518
Path('/srv/opentallas-scratch2/claude/codex-hbm-2001/mu_r13/bank_k4_bound.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
