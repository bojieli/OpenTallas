"""Conservative static future-boundary obligations; dynamic reads remain open."""
import importlib.util,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];t=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools')
sys.path[:0]=[str(t/'hbm_next'),str(t),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC
spec=importlib.util.spec_from_file_location('REG',root/'tools/hbm_next/vm_phase_region.py');REG=importlib.util.module_from_spec(spec);spec.loader.exec_module(REG)
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
written=[];needed=[];dynamic=[];first={}
for i in range(1474,len(rr)):
    _,r,x,_=rr[i]
    if x and x.rsel:
        dynamic.append(dict(record=i,reason='row selection'));continue
    for slot,row in (IR.expand(r,x)if x else[(r.slot,r)]):
        wo=IR.written_operands(row);writes=[]
        for k,d in row.desc.items():
            if d.space!='VM':continue
            if any(getattr(d,f,0)for f in ('indexed','dyn_sel','n_sel','lstride','l1stride')):
                dynamic.append(dict(record=i,slot=slot,operand=k,reason='dynamic descriptor'));continue
            ivs=REG.addresses(d)
            if k in wo:writes+=ivs
            else:
                for a,b in ivs:
                    for lo,hi in REG.uncovered(a,b,written):
                        needed.append([lo,hi]);first.setdefault((lo,hi),i)
        written=REG.merge_intervals(written+writes)
needed=REG.merge_intervals(needed)
regions=json.loads(Path(__file__).with_name('region').joinpath('region.json').read_text())
region_writes=REG.merge_intervals([iv for ph in regions['phases']for iv in ph['written_source_intervals']])
carry=REG.merge_intervals([piece for a,b in needed for piece in REG.uncovered(a,b,region_writes)])
# These are boundary obligations at region exit; some are outputs of the region,
# some pass-through state. They cannot be silently overwritten by a local remap.
result=dict(schema='opentallas.hbm.vm_region_boundary_census.v1',
            status='STATIC_LINEAR_DESCRIPTOR_CENSUS_ONLY',executable=False,
            source_region_exit=1473,future_records=len(rr)-1474,
            known_boundary_intervals=needed,known_boundary_words=sum(b-a for a,b in needed),
            known_pass_through_intervals=carry,known_pass_through_words=sum(b-a for a,b in carry),
            unresolved_dynamic_obligation_count=len(dynamic),
            unresolved_dynamic_examples=dynamic[:12],
            limitations=['control loops/predicates and dynamic addressing need programme semantic composition; static census is neither full upper nor lower bound',
                         'region outputs need transfer to the addresses required by later consumers',
                         'original boundary addresses are logical source values, not permission to reuse them'])
Path(__file__).with_name('future_boundary.json').write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps(dict(known_boundary_words=result['known_boundary_words'],known_intervals=len(needed),known_pass_through_words=result['known_pass_through_words'],dynamic_obligations=len(dynamic))))
