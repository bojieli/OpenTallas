import json,shutil
from pathlib import Path
root=Path('/srv/opentallas-scratch/claude/layerbench-hbm/sw5e');src=root/'slice/replay/ds_l0_fixture';out=Path('/srv/opentallas-scratch/claude/token-producer-fix-1019/native_prefix')
b=json.loads((root/'slice/boundary.json').read_text());ins=[e for e in b['inputs'] if e['driver'].split('.')[0]!='<die_pin>']; arr=[[int(x,16) for x in (src/f'{n}.mem').read_text().split()] for n in ('hdr','val','msk')];ev=list(zip(*arr));new=[]; changed=[]
for h,v,m in ev:
 if h>>62==1:
  name=ins[(h>>44)&65535]['name'];cy=h&0xffffffff
  if name.startswith('su_prog__') and cy<=2670:
   old=(h,v,m)
   h=(h&~0xffffffff)|(cy-4)
   if name=='su_prog__r_bank' and v%32>=1:v+=3
   changed.append(dict(port=name,old_cycle=cy,new_cycle=cy-4,old_value=f'{old[1]:x}',new_value=f'{v:x}'))
 new.append((h,v,m))
new.sort(key=lambda x:((x[0]>>60)&3,x[0]&0xffffffff,x[0]>>62))
out.mkdir(exist_ok=False)
for j,n in enumerate(('hdr','val','msk')):(out/f'{n}.mem').write_text(''.join(f'{e[j]:x}\n' for e in new))
shutil.copyfile(src/'vm_pre.txt',out/'vm_pre.txt')
(out/'changes.json').write_text(json.dumps(dict(scope='first_record_native_producer_ABI_fix',qualifies_full_token=False,checks_byte_values_unchanged=True,preload_unchanged=True,physical_index_banks=4,old_image_index_banks=1,consumer_startup=9,old_startup=5,changes=changed),indent=2)+'\n')
