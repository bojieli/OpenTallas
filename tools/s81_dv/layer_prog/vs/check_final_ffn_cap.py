"""Check actual emitted cap calendars; preserve unrelated matrix configurations."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from layer_prog.final_ffn import expert_slot,CAPTURE

root=Path(sys.argv[1])
a=json.loads((root/'cap_default.json').read_text())
b=json.loads((root/'cap_final.json').read_text())
meta=json.loads((root/'fixtures/meta.json').read_text())
assert a['faults']==b['faults']==0
assert len(a['phases'])==len(b['phases'])
changed=0
for old,new in zip(a['phases'],b['phases']):
    assert old['op']==new['op'] and old['mat']==new['mat']
    if old['op']!='ffn.down':
        assert old==new, 'unrelated capture changed'
        continue
    expert=new['mat'].split('.')[0]
    slot=expert_slot(expert,meta['experts'])
    for x,y in zip(old['slices'],new['slices']):
        cfg=y['cfg']
        assert cfg['obase']==4*(CAPTURE+16*slot) and cfg['rcnt']==80 and cfg['fmt']==2
        original=dict(x['cfg']);candidate=dict(cfg)
        original.pop('obase');candidate.pop('obase')
        assert original==candidate and x['frame_tags']==y['frame_tags']
        changed+=1
assert changed>0
print('FINAL_FFN_ACTUAL_CAP_PASS phases=%d slice_configs=%d unrelated_unchanged=1 faults=0' % (len(b['phases']),changed))
