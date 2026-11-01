#!/usr/bin/env python3
"""Prepare exact approved PC/HHP call mappings; emit no RTL until die-owned FT mapping exists."""
import argparse,json,re,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();R=a.root
source=R/'native_kitrtl/kv3_pc__cl5a95b461_bound.sv';text=source.read_text();records=[]
FT={'ft_ck_i_0','ft_ck_i_1','ft_ck_o_0','ft_ck_o_1'}
DROP={'hck','pc__front_hbm_data','pc__return_hbm_data'}
def sl(expr,hi,lo):
 m=re.fullmatch(r'([A-Za-z_$][\w.$]*)\[(\d+):(\d+)\]',expr.strip());assert m,(expr,'require exact existing vector connection')
 assert int(m[3])<=lo<=hi<=int(m[2]),(expr,hi,lo)
 return f'{m[1]}[{hi}:{lo}]'
for i in range(4):
 mod='qkd_kvs_pc_h_head_p' if i==0 else 'qkd_kvs_pc';inst='u_kvpc'+str(i)
 pat=rf'(?m)^    {mod} {inst} \((.*?)\n    \);';m=re.search(pat,text,re.S);assert m,(mod,inst)
 body=m[1];pairs=re.findall(r'\.([A-Za-z_]\w*)\(([^()]*)\)',body)
 rest=re.sub(r'\.([A-Za-z_]\w*)\(([^()]*)\)\s*,?', '',body);assert not rest.strip(),rest
 raw=dict(pairs);assert len(raw)==len(pairs);assert DROP<=raw.keys()
 bound={k:v.strip() for k,v in pairs if k not in DROP}
 bound['pc__land_er']=sl(raw['pc__land_er'],0,0);bound['pc__land_er_259']=sl(raw['pc__land_er'],260,259)
 if i==0:
  bound['pc__ki']=sl(raw['pc__ki'],0,0);bound['pc__ki_15']=sl(raw['pc__ki'],20,15);bound['pc__ki_31']=sl(raw['pc__ki'],32,31)
 folder=R/('current_hhp' if i==0 else 'current_pc');bb=next(folder.glob('*.bb.v'));bt=bb.read_text()
 ports=set(re.findall(r'\b(?:input|output)\s+wire\s+(?:\[[^\]]+\]\s+)?([A-Za-z_]\w*)',bt))
 assert ports-bound.keys()==FT,(inst,'unmapped or unknown',ports-bound.keys())
 assert not bound.keys()-ports,(inst,'unknown bound ports',bound.keys()-ports)
 records.append({'instance':inst,'module':mod,'raw_named_ports':raw,'approved_clock_alias_removals':sorted(DROP),'approved_live_slice_bindings':{k:v for k,v in bound.items() if k=='pc__land_er' or k.startswith('pc__land_er_') or (i==0 and k.startswith('pc__ki'))},'exact_non_FT_bindings':bound,'unresolved_die_owned_FT_ports':sorted(FT),'bb_sha256':hashlib.sha256(bb.read_bytes()).hexdigest(),'normalization':'kvspc_face_ports.wrapper approved clock aliases + dead/live slices; private/core-clock source policies are unchanged in the actual current child view; no new latency change'})
assert len(records)==4
a.out.write_text(json.dumps({'status':'PREP only; no RTL emitted, parent PLACE HELD for actual die mesh FT mapping','source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'contracts':['physical/die_plan/qwen_kvsys/cores/harden/kvspc_face_ports.py','physical/die_plan/qwen_kvsys/cores/harden/kvspc_private_ports.py','physical/die_plan/qwen_kvsys/cores/harden/kvspc_core_clock.py'],'instances':records},indent=1)+'\n')
print('PREP PASS four exact approved non-FT mappings; all16 die-owned FT pins remain explicitly unresolved; no RTL/P&R')
