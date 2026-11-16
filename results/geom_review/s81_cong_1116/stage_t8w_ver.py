"""Stage the model's VER depth into ONLY s_0N_L1's existing parent nibble.
Reads the immutable F2s3 source; writes a distinct candidate source for F2s4.
"""
import hashlib,json,re,sys
from pathlib import Path
D=Path('/srv/opentallas-scratch2/claude/s81-leaf-plan/wt/tools/die_plan');sys.path.insert(0,str(D));import stage_lfcs_netlist as ST;import leaf_cs_depth as LCD
F=Path('/srv/opentallas-scratch2/claude/fable-fix-s81-cong');tn='ot_s81sl_leaf__t8';t=json.load(open(F/'t8w_rows.json'))[tn]
want,dis=LCD.plan_depths(t);assert want['ver']==1 and 'ver' not in dis,(want,dis)
f=F/'die_b178_lfcs_F2s3.v';s=f.read_text();hits=[m for m in ST.INST.finditer(s) if m.group('inst')=='u_s_0N'];assert len(hits)==1
m=hits[0];param=m.group('p');x=re.search(r"\.LF_CS_VER_D\(20'h([0-9a-fA-F]{5})\)",param);assert x
old=int(x.group(1),16);k=1;assert ((old>>(4*k))&15)==0,old
new=(old&~(15<<(4*k)))|(want['ver']<<(4*k));a=m.start('p')+x.start(1);b=m.start('p')+x.end(1);out=s[:a]+f'{new:05x}'+s[b:]
changed=[i for i,(u,v) in enumerate(zip(s,out)) if u!=v];assert len(out)==len(s) and len(changed)==1 and changed[0]==a+3
# Gate every other source byte and every other packed leaf nibble; negative
# control restores the old nibble and must fail the plan/source depth check.
def source_depth(text):
 match=next(z for z in ST.INST.finditer(text) if z.group('inst')=='u_s_0N');h=re.search(r"\.LF_CS_VER_D\(20'h([0-9a-fA-F]{5})\)",match.group('p'));return(int(h.group(1),16)>>(4*k))&15
assert source_depth(out)==want['ver'];assert source_depth(s)!=want['ver']
othermask=((1<<20)-1)^(15<<(4*k));assert(new&othermask)==(old&othermask)
g=F/'die_b178_lfcs_t8w_ver1.v';g.write_text(out)
rec=dict(verdict='PASS_STATIC_STAGING',negative_control='old nibble rejected',part='s_0N_L1',type=tn,source_instance='u_s_0N',parameter='LF_CS_VER_D',leaf_nibble=k,old_hex=f'{old:05x}',new_hex=f'{new:05x}',leaf_CS_VER_D=want['ver'],added_local_cycles=1,source_in=str(f),source_out=str(g),source_in_sha256=hashlib.sha256(s.encode()).hexdigest(),source_out_sha256=hashlib.sha256(out.encode()).hexdigest(),changed_bytes=len(changed),required_followup='coherent strict bind leaf_cs_depth_gate plus LATCHECK/LEC; static staging is not physical or bit-exact signoff')
json.dump(rec,open(F/'t8w_ver_source_profile.json','w'),indent=2);print(json.dumps(rec))
