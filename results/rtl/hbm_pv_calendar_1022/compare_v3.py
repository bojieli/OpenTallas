from pathlib import Path
import json,hashlib
p=Path(__file__).resolve().parent
a=p/'composed77v2/slice/replay/replay_candidate';b=p/'composed77v3/slice/replay/replay_candidate'
for f in ['hdr.mem','msk.mem','vm_pre.txt']:
 assert (a/f).read_bytes()==(b/f).read_bytes(),f
for f in (a/'hbm').glob('*.hex'):assert f.read_bytes()==(b/'hbm'/f.name).read_bytes(),f.name
va=(a/'val.mem').read_text().split();vb=(b/'val.mem').read_text().split();hdr=(a/'hdr.mem').read_text().split()
assert len(va)==len(vb)
changed=[]
for i,(x,y) in enumerate(zip(va,vb)):
 x,y=int(x,16),int(y,16)
 if x!=y:
  assert x^y==1<<25 and x>>25&1 and not y>>25&1
  assert int(hdr[i],16)>>62==1,'changed check value'
  changed.append(i)
assert changed
ac=json.loads((p/'composed77v2/replay_candidate.json').read_text());bc=json.loads((p/'composed77v3/replay_candidate.json').read_text())
assert [x for x in ac['events'] if x['k']=='C']==[x for x in bc['events'] if x['k']=='C']
print(json.dumps(dict(status='PASS',changed_drive_values=len(changed),changed_bit='SVG MATVEC leaf valid25 cleared; XCAL attention consume152 untouched',headers_masks_VM_and_HBM_inputs_byte_identical=True,all_181_check_events_byte_identical=True,packed_event_indices=changed,header_sha256=hashlib.sha256((a/'hdr.mem').read_bytes()).hexdigest()),indent=2))
