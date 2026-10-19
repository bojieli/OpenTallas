#!/usr/bin/env python3
"""Finite read-only source ledger and arithmetic witness; no RTL elaboration/simulation."""
import pathlib, subprocess, re, hashlib, json, sys
ROOT=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/home/ubuntu/wt/codex-kv-host-mu-binding-model-1019')
OUT=pathlib.Path(__file__).resolve().parent
HI='rtl/qwen_sys/host_integrated_20261014/'
MU='rtl/qwen_sys/mu_qwen_20261018/'
paths=['tools/qwen_kv_die/kv_die.py','rtl/qwen_sys/split_20261014/qkd_host_root_admission.sv','rtl/physical/ot_qwen_host_ctl.sv','rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv','rtl/qwen_sys/host_20261013/qkd_host_ctl_service_pins.sv']
paths += [HI+x+'.sv' for x in ['qkd_host_control_packet_admission','qkd_host_packet_bundle_admission','qkd_host_control_prompt_observed','qkd_host_fullcontrol_observed','qkd_host_if_pins_observed','ot_host_if_pb2_observed','qkd_host_native_token_endpoint_cancel','qkd_host_tp8_coordinator','qkd_host_peer_coordinator_codec','qkd_host_ctrl_token_service_packet_collected','qkd_host_coordinator_services','qkd_host_lifecycle_collected','qkd_host_post_collector']]
paths += ['rtl/qwen_sys/redesign_qwen/'+x+'.sv' for x in ['ot_qwen_tp8_token_epoch_allocator','ot_qwen_tp8_token_cohort']]
paths += [MU+x+'_mu.sv' for x in ['qkd_host_native_token_endpoint_cancel','qkd_host_tp8_coordinator','qkd_host_peer_coordinator_codec','qkd_host_ctrl_token_service_packet_collected','qkd_host_coordinator_services','qkd_host_lifecycle_collected','qkd_host_post_collector','ot_qwen_tp8_token_epoch_allocator','ot_qwen_tp8_token_cohort']]
src={};manifest=[]
for p in paths:
    b=subprocess.check_output(['git','-C',str(ROOT),'show','5f2ce19bc:'+p]); src[p]=b.decode()
    dest=OUT/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
    manifest.append(dict(path=p,revision='5f2ce19bc',sha256=hashlib.sha256(b).hexdigest(),current_checkout_same=(ROOT/p).exists() and (ROOT/p).read_bytes()==b))
(OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Guard every arithmetic witness with the literal source predicates it represents.
def need(p,t):
    assert t in src[p],(p,t)
need('tools/qwen_kv_die/kv_die.py','parameters=dict(ENABLE_SERVICE=1, ENABLE_NATIVE=1, ENABLE_TOKEN=1, NL=2)')
need(HI+'qkd_host_control_packet_admission.sv','PROMPT_BIND_LATENCY(PROMPT_BIND_LATENCY),.ENABLE_SERVICE(ENABLE_SERVICE))u_control')
need(HI+'qkd_host_control_prompt_observed.sv','.MU(MU),.NSLOT(MU!=0?4:1),.PLB(MU!=0?11:13)')
need(HI+'ot_host_if_pb2_observed.sv',"step_pos<=18'(eng_pos)")
need(HI+'ot_host_if_pb2_observed.sv',"step_retire_pos<=18'(d_pos)")
need(HI+'ot_host_if_pb2_observed.sv',"cq_pos<=18'(eh_pos)")
need(MU+'qkd_host_post_collector_mu.sv','ui=step_pos[17:16],ur=step_retire_pos[17:16],uc=cq_pos[17:16]')
need('rtl/physical/ot_qwen_host_ctl.sv',"{kv_base[11:10],pos[15:0]}")
need(HI+'qkd_host_native_token_endpoint_cancel.sv','hc_q[17:13]==0')
need(MU+'qkd_host_native_token_endpoint_cancel_mu.sv','hc_q[15:13]==0&&epoch_q[1:0]==u_in')
rows=[]
for uid in range(4):
    pos=17;kvbase=uid*1024;hcpos=((kvbase>>10)&3)<<16 | pos;epoch=(7<<2)|uid
    rows.append(dict(slot=uid,raw_observer_pos=pos,HC_pos=hcpos,epoch=epoch,TAG_user=epoch&3,scalar_endpoint_accept_range=(hcpos>>13)==0,MU_endpoint_user=hcpos>>16,MU_endpoint_range_and_epoch=((hcpos>>13)&7)==0 and (epoch&3)==hcpos>>16,existing_MU_POST_issue_user=pos>>16,existing_MU_POST_retire_user=pos>>16,existing_MU_POST_CQ_user=pos>>16,POST_uid_agrees=(pos>>16)==uid,proposed_checked_slot_uid=uid,proposed_adapter_pos=(uid<<16)|pos))
assert sum(r['POST_uid_agrees'] for r in rows)==1
assert sum(r['scalar_endpoint_accept_range'] for r in rows)==1
assert all(r['MU_endpoint_range_and_epoch'] for r in rows)
# Four-user contract arithmetic, not simulated acceptance. Bad witnesses rejected exactly.
def contract(slot,pos,ep,taguser,kind='private'):
    return 0<=slot<4 and 0<=pos<8192 and slot==(ep&3)==taguser and kind=='private'
checks=[]
for uid in range(4):checks.append(dict(case='valid_uid'+str(uid),accepted=contract(uid,17,28+uid,uid),expected=True))
for name,args in [('wrong_epoch',(2,17,29,2)),('wrong_tag',(2,17,30,1)),('out_of_range_slot',(4,17,28,0)),('out_of_range_position',(2,8192,30,2)),('raw_public_abi_used_as_encoded',(2,17,30,2,'public'))]:
    checks.append(dict(case=name,accepted=contract(*args),expected=False))
assert all(x['accepted']==x['expected'] for x in checks)
(OUT/'binding_witness.json').write_text(json.dumps(dict(kind='SOURCE_GUARDED_ARITHMETIC_ONLY_NO_RTL_SIM',current={'die_MU':1,'HOST_MU':0,'NSLOT':1,'ENG_CTX':1,'NW':18,'PLB':13,'MQ':1},target={'HOST_MU':1,'NSLOT':4,'ENG_CTX':4,'NW':18,'PLB':11,'MQ':4},users=rows,checks=checks),indent=2)+'\n')
# Exact declared reg ledger, classed by actual nonblocking LHS occurrence. Source-level, not synthesis.
led=[]
for p in paths:
    if not p.endswith('.sv'):continue
    s=re.sub(r'/\*.*?\*/|//[^\n]*','',src[p],flags=re.S)
    s=s[s.index(');')+2:]  # Internal declarations only; ANSI ports are separately priced by ABI.
    if p.startswith(MU) and 'g_mu' in s:s=s[s.index('g_mu'):]
    nba=set(re.findall(r'\b([A-Za-z_]\w*)\s*(?:\[[^;\n]*?\])?\s*<=',s))
    for match in re.finditer(r'\breg\s*(\[[^\]]+\])?\s*([^;]+);',s):
        width=(match.group(1) or '[0:0]').strip('[]');a,b=width.split(':')
        def val(x):
            for k,v in {'NW':18,'D':8,'ND':8,'AW':24,'NSLOT':4,'SB':2,'MQ':4,'MQB':2,'EVQ':4,'EQD':16,'EVW':116}.items():x=re.sub(r'\b'+k+r'\b',str(v),x)
            return eval(x,{'__builtins__':{}},{}) if re.fullmatch(r'[0-9+*() /-]+',x.strip()) else None
        try:w=abs(val(a)-val(b))+1
        except Exception:w=None
        for item in match.group(2).split(','):
            m=re.fullmatch(r'\s*(\w+)\s*(?:\[\s*([^:]+):([^\]]+)\])?\s*',item)
            if not m:continue
            try:d=abs(val(m[2])-val(m[3]))+1 if m[2] else 1
            except Exception:d=None
            led.append(dict(source=p,name=m[1],width=w,depth=d,bits=w*d if w is not None and d is not None else None,NBA_LHS_in_source=m[1] in nba,interpretation='declaration/NBA candidate; synthesis and context-dependent pruning unmeasured'))
(OUT/'declared_state_ledger.json').write_text(json.dumps(led,indent=2)+'\n')
print(json.dumps(dict(source_files=len(manifest),source_assertions='PASS',binding_cases=len(checks),binding_checks='PASS',reg_declarations=len(led),RTL_simulation=False)))
