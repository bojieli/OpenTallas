"""Actual native NL3 table relocation, list-order golden and negative controls."""
import copy,importlib.util,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];t=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools')
sys.path[:0]=[str(t/'hbm_next'),str(t),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC
spec=importlib.util.spec_from_file_location('ATT',root/'tools/hbm_next/vm_attention_phase.py');ATT=importlib.util.module_from_spec(spec);spec.loader.exec_module(ATT)
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
packet=json.loads((Path(__file__).parent/'attention/attention.json').read_text())
rng=np.random.default_rng(2249);checked=0;controls=[]
for info in packet['phases']:
    blob=(Path(__file__).parent/'attention'/info['fragment']).read_bytes();native=IC.decode_all(blob)
    assert len(native)==6 and info['nl']==3
    producer=native[0][1];table=producer.desc['R'].base;lane_map=producer.desc['D'].base
    assert table==info['mapped_table'] and table%32==0
    for _,r,x,_ in native:
        if r.unit=='ATT':assert x.n==3 and x.slot0==info['group_slot0'] and x.rtab==table
    for case in ('overlap','disjoint','identical','short'):
        k=9 if case=='short' else 512
        base=sorted(rng.choice(4096,k,replace=False).tolist());sels=[]
        for l in range(3):
            if case=='identical':sel=base
            elif case=='disjoint':sel=list(range(l*1024,l*1024+k))
            elif case=='short':sel=list(range(l,l+k))
            else:
                keep=base[:k//2];others=sorted(set(rng.choice(4096,k*3,replace=False).tolist())-set(keep));sel=sorted(keep+others[:k-len(keep)])
            sels.append(sel)
        lanes=IR.att_lanes_from(sels,[70000+info['group_slot0']+l for l in range(3)],128,False)
        plan=IR.kv_union_plan(lanes);R,D=IR.plan_words(plan)
        vm=np.zeros(262144,np.uint32);vm[table:table+len(R)]=R;vm[lane_map:lane_map+len(D)]=D
        got=IR.plan_lane_lists(vm[table:table+10240],vm[lane_map:lane_map+400],3,lanes)
        assert got==[lane['win']+lane['sel']for lane in lanes]
        checked+=sum(len(x)for x in got)
        if case=='overlap':
            for name in ('wrong_table','oversized_header','wrong_lane_map'):
                tt=table;mut=vm.copy()
                if name=='wrong_table':tt+=32
                elif name=='oversized_header':mut[table]=257
                else:mut[lane_map+16]=mut[lane_map+16+128]
                try:bad=IR.plan_lane_lists(mut[tt:tt+10240],mut[lane_map:lane_map+400],3,lanes)
                except (ValueError,IndexError,KeyError,IR.RangeFault):controls.append(f'{info["group_slot0"]}:{name}')
                else:
                    assert bad!=[lane['win']+lane['sel']for lane in lanes],name+' escaped'
                    controls.append(f'{info["group_slot0"]}:{name}')
    # The consumer table pointer must come from the actual KVUNION producer.
    bad=copy.deepcopy(rr);i=1530+info['group_slot0']//3;bad[i][2].rtab+=32
    try:ATT.construct(bad,info['group_slot0'],IR)
    except ValueError:controls.append(f'{info["group_slot0"]}:producer_pointer_mismatch')
    else:raise AssertionError('orphan plan pointer escaped')
try:ATT.construct(rr,3,IR,reserve=245000)
except ValueError:controls.append('external_reserve_overflow')
else:raise AssertionError('oversized external reserve escaped')
print(json.dumps(dict(native_records=12,expanded_rows=32,plan_words=20480,lane_words_compared=checked,controls=controls)))
