"""Actual native programme inventory, refusing stale per-layer source maps."""
import collections,hashlib,json,sys
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity')
sys.path[:0]=[str(p/'tools/hbm_next'),str(p/'tools'),'/home/ubuntu/OpenTallas/tools']
import image_check as IC
source=(p/'a122.hgi1r').read_bytes();rr=IC.decode_all(source);meta=json.loads((p/'emitter.json').read_text());sha=hashlib.sha256(source).hexdigest();match=sha==meta['token']['sha256']
ops=collections.Counter(f'{r.unit}.{r.op}'for _,r,x,_ in rr)
loops=[i for i,(_,r,x,_)in enumerate(rr)if(r.unit,r.op)==('CTL','LOOP')and r.param&(1<<17)]
expert=[i for i,(_,r,x,_)in enumerate(rr)if x and x.rsel and r.unit!='ATT']
att=[i for i,(_,r,x,_)in enumerate(rr)if x and x.rsel and r.unit=='ATT']
idx=[dict(record=i,unit=r.unit,op=r.op,operand=k,space=d.space)for i,(_,r,x,_)in enumerate(rr)for k,d in r.desc.items()if d.indexed or d.n_sel]
result=dict(actual_source_sha256=sha,native_records=len(rr),bytes=len(source),unit_ops=dict(ops),runtime_loop_records=loops,expert_rsel_records=expert,attention_plan_records=att,dynamic_operands=idx,source_map_matches=match,mapped_layer_records=None if not match else meta['token']['segments'],source_map_mismatch=dict(expected_sha256=meta['token']['sha256'],expected_records=meta['token']['records'],expected_bytes=meta['token']['bytes'])if not match else None,historical_model_only=dict(transformer_layers=40,layers_original_sixrow_schedule_over_old_vm=sum(v['c4_peak']>262144 for k,v in meta['segments'].items()if k!='head'),minimum_peak_words=min(v['c4_peak']for k,v in meta['segments'].items()if k!='head'),maximum_peak_words=max(v['c4_peak']for k,v in meta['segments'].items()if k!='head')),whole_programme_executable=False,full_programme_fits=None,interpretation='Actual source dynamic obligations counted without assuming historical emitter offsets are valid. Previous offset-derived census is rejected because emitter.json hashes do not match a122. Historical40layer original-schedule VM peaks motivate whole-programme phases, but cannot establish exact current perlayer fit or spill traffic. Need actual source map before quoting whole-token traffic.')
print(json.dumps(result,indent=1))
