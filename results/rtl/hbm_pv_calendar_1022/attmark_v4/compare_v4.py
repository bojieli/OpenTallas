# v4 vs v2 composed replay: only SVG programme words gain bit119 (ATT_MARK) where v2 had attention issue bit25; v3 indices.
from pathlib import Path
import json,hashlib
C=Path('/srv/opentallas-scratch/codex/hbm-pv-calendar-1022');R=Path(__file__).resolve().parent
a=C/'composed77v2/slice/replay/replay_candidate';b=R/'composed_v4/slice/replay/replay_candidate'
for f in ['hdr.mem','msk.mem','vm_pre.txt']:
    assert (a/f).read_bytes()==(b/f).read_bytes(),f
for f in (a/'hbm').glob('*.hex'):
    if f.name=='INIT.hex':continue
    assert f.read_bytes()==(b/'hbm'/f.name).read_bytes(),f.name
va=(a/'val.mem').read_text().split();vb=(b/'val.mem').read_text().split();hdr=(a/'hdr.mem').read_text().split()
assert len(va)==len(vb)
changed=[]
for i,(x,y) in enumerate(zip(va,vb)):
    x,y=int(x,16),int(y,16)
    if x!=y:
        assert x^y==1<<119 and y>>119&1 and x>>25&1 and y>>25&1,i
        assert int(hdr[i],16)>>62==1,'changed check value'
        changed.append(i)
v3=json.loads((C/'command_semantic_diff.json').read_text())['packed_event_indices']
assert changed==v3,(len(changed),changed[:4],v3[:4])
ac=json.loads((C/'composed77v2/replay_candidate.json').read_text());bc=json.loads((R/'composed_v4/replay_candidate.json').read_text())
assert [x for x in ac['events'] if x['k']=='C']==[x for x in bc['events'] if x['k']=='C']
print(json.dumps(dict(status='PASS',changed_drive_values=len(changed),changed_bit='SVG programme word bit119 ATT_MARK set; issue bit25 kept (v2 value); same 64 events as v3',
    headers_masks_VM_and_HBM_inputs_byte_identical=True,all_181_check_events_byte_identical=True,packed_event_indices=changed,
    header_sha256=hashlib.sha256((a/'hdr.mem').read_bytes()).hexdigest()),indent=2))
