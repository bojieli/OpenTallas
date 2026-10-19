#!/usr/bin/env python3
import copy,json,re
from pathlib import Path
from check_emitted import check
p=Path('cold');e=json.loads((p/'generated/graph.json').read_text());c=json.loads((p/'roundtrip.json').read_text());s=(p/'generated/parent.sv').read_text();r=json.loads((p/'generated/receipt.json').read_text());check(e,c,s)
passed=[]
def bad(label,cc,ss):
 try:check(e,cc,ss)
 except (AssertionError,KeyError):passed.append(label);return
 raise AssertionError('emission corruption accepted '+label)
m=e['modules']['qfd_sys_face_control_safe'];cells=sorted(m['cells'].items())
_,g=next((n,g) for n,g in cells if g['type']=='$_AND_' and all(isinstance(g['connections'][p][0],int) for p in ['A','B']) and g['connections']['A']!=g['connections']['B'])
y=g['connections']['Y'][0];ss,count=re.subn(r'(assign n'+str(y)+r' = [^;]+)&',lambda x:x[1]+'|',s);assert count==1;bad('wrong_boolean_operator',copy.deepcopy(c),ss)
cc=copy.deepcopy(c);root=cc['modules']['qfd_sys_face_control_safe'];idx=next(i for i,(n,g) in enumerate(cells) if n==r['copies'][0]['cell']);root['cells']['f'+str(idx)]['connections']['D']=root['ports']['ck']['bits'];bad('copied_D_pin',cc,s)
cc=copy.deepcopy(c);root=cc['modules']['qfd_sys_face_control_safe'];sub=cc['modules'][root['cells']['f'+str(idx)]['type']];primitive=next(x for x in sub['cells'].values() if 'DFF' in x['type']);primitive['type']='$_DFF_P_';bad('wrong_reset_enable_kind',cc,s)
cc=copy.deepcopy(c);root=cc['modules']['qfd_sys_face_control_safe'];macro=next(x for x in root['cells'].values() if x['type']=='ot_rom_4096x72_m8');macro['type']='fake_rom';bad('wrong_macro_master',cc,s)
print('SYSFACE_SAFE_EMITTED_GUARDS_PASS positives1 negatives4 '+','.join(passed))
