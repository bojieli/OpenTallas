#!/usr/bin/env python3
"""Focused actual-source control lowering checks; no global/retirement claim."""
import copy,hashlib,json,sys
from pathlib import Path
from layer_prog.selected_entry_norm import EmittedNormSource,compile_selected,check_control,check_host
from layer_prog.bound_control import retime_norm
from layer_prog.entry_norm import compile_norm
from layer_prog.entry_write_calendar import encode_unsealed
base=Path(sys.argv[1]);inv=Path(sys.argv[2])
die=EmittedNormSource(inv)
entry=json.loads((base/'L14/entry_inputs.json').read_text())
program=json.loads((base/'L14/norm_control.json').read_text())
words=[int(line,16)for line in (base/'L14/norm.unsealed.host_boot.memh').read_text().splitlines()]
check_control(program,die);check_host(program,words)
recompiled=compile_selected(die,entry,int(program['eps_fp32_bits'],16),20)
assert recompiled['rows']==program['rows'] and recompiled['templates']==program['templates']
controls={}
def reject(name,fn):
    try:fn()
    except (ValueError,KeyError)as exc:controls[name]=str(exc)
    else:raise AssertionError('control escaped: '+name)
def mutated_entry(key,value):
    e=copy.deepcopy(entry)
    if key=='die_sha256':e[key]=value
    else:e['readers'][0][key]=value
    return lambda:compile_selected(die,e,int(program['eps_fp32_bits'],16),20)
reject('stale_source',mutated_entry('die_sha256','c0921732840ab202f28f5ed8337b7cb142eae5a816dd298fd59a091f660f3ff8'))
reject('wrong_global_beat',mutated_entry('global_beat',999))
reject('wrong_delayed_pre_row',mutated_entry('normr_a0',1007))
reject('counter_overflow',lambda:compile_selected(die,entry,int(program['eps_fp32_bits'],16),(1<<24)-52))
r=copy.deepcopy(die.source_record);r['slices'][0]['params_raw']['PDSK']="15'b000000000000000";r['slices'][0]['params_integer']['PDSK']=0
r['source_view_sha256']=hashlib.sha256(json.dumps({k:v for k,v in r.items()if k!='source_view_sha256'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
reject('rehashed_false_pdsk_source',lambda:EmittedNormSource(r))
bad=copy.deepcopy(die.deskew);bad[next(iter(bad))]=[0]*5
reject('invalid_control_deskew',lambda:retime_norm(compile_norm(die,entry,int(program['eps_fp32_bits'],16),20),die,deskew_by_slice=bad))
p=copy.deepcopy(program);p['templates'][0]['payload186']=f"{int(p['templates'][0]['payload186'],16)^(1<<30):047x}"
reject('payload_corruption',lambda:check_control(p,die))
p=copy.deepcopy(program);p['rows'][0]['row76']=f"{int(p['rows'][0]['row76'],16)^1:019x}"
reject('calendar_corruption',lambda:check_control(p,die))
w=words.copy();w[1]^=1<<33
reject('host_PW_corruption',lambda:check_host(program,w))
w=words.copy();w[-1]^=1<<30
reject('host_payload_corruption',lambda:check_host(program,w))
w=words.copy();w[0]=(w[0]&~(255<<1))|(0x15<<1)
reject('unexpected_MU_operation',lambda:check_host(program,w))
assert encode_unsealed(program)==words
result=dict(verdict='PASS_SOURCE_CONTROL_ONLY',control_check=program['control_check'],controls_rejected=controls,
    fresh_entry_rows=entry['row_count'],source_top_sha256=die.die_sha,source_view_sha256=die.source_record['source_view_sha256'],
    norm_eps_bits=program['eps_fp32_bits'],host_words=len(words),host_local_five_edge_reservation=5*len(words),
    source_files_sha256=die.source_record['source_files_sha256'],
    full_stage=False,full_token=False,transport_qualified=False,go_readiness_qualified=False,
    added_rtl_cycles=0,native_sealed=False)
(base/'qualification.json').write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps(result,sort_keys=True))
