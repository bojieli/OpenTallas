#!/usr/bin/env python3
"""Emit a real hard-master source with die identity and authorization burned in.
Run in an admitted remote snapshot before synthesis. The generated top has the
same native pins; it has no parameters that can override the hardened identity.
"""
import argparse, hashlib, json, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--role',choices=['layer','source','head'],required=True)
p.add_argument('--my-id',type=int,required=True);p.add_argument('--src-lo',type=int,required=True);p.add_argument('--src-hi',type=int,required=True)
p.add_argument('--type-mask',type=lambda s:int(s,0),default=None);p.add_argument('--vm-return-valid',action='store_true');p.add_argument('--out-depth',type=int,default=4);p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.type_mask is None:a.type_mask=4 if a.role=='source' else 10
if a.out_depth<4 or a.out_depth&(a.out_depth-1):p.error('out-depth must be power of two >=4')
if not(0<=a.my_id<=4094 and 0<=a.src_lo<=a.src_hi<=4094 and 0<=a.type_mask<=65535):p.error('invalid die identity or authorization')
root=Path(__file__).resolve().parents[2]
old={'layer':'dsfd_sp_ctrl','source':'dsfd_sp_ctrl_src','head':'dsfd_sp_ctrl_h'}[a.role]
template=root/'physical/s81_ctrl/rtl'/f'{old}.sv';s=template.read_text()
new=f'{old}_id{a.my_id:04d}_src{a.src_lo:04d}_{a.src_hi:04d}_rv{int(a.vm_return_valid)}_q{a.out_depth}'
s,n=re.subn(r'module\s+'+old+r'\s*#\(.*?\)\s*\(',f'module {new} (',s,count=1,flags=re.S)
if n!=1:raise SystemExit('parameterized native shell declaration missing')
s=s.replace('.USE_VM_RVALID(USE_VM_RVALID)',f'.USE_VM_RVALID({int(a.vm_return_valid)})').replace('.OUT_DEPTH(OUT_DEPTH)',f'.OUT_DEPTH({a.out_depth})')
s=s.replace('.MY_ID(MY_ID)',f'.MY_ID({a.my_id})').replace('.SRC_LO(SRC_LO)',f'.SRC_LO({a.src_lo})').replace('.SRC_HI(SRC_HI)',f'.SRC_HI({a.src_hi})').replace('.TYPE_MASK(TYPE_MASK)',f".TYPE_MASK(16'h{a.type_mask:04x})")
a.out.mkdir(parents=True,exist_ok=True);target=a.out/(new+'.sv');target.write_text(s)
(a.out/(new+'.json')).write_text(json.dumps(dict(master=new,role=a.role,vm_return_valid=a.vm_return_valid,out_depth=a.out_depth,my_id=a.my_id,src_lo=a.src_lo,src_hi=a.src_hi,type_mask=a.type_mask,template=str(template.relative_to(root)),template_sha256=hashlib.sha256(template.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(s.encode()).hexdigest(),qualification='requires synthesis/route of this exact specialized top; generic role master cannot prove this identity'),indent=2)+'\n')
print(target)
