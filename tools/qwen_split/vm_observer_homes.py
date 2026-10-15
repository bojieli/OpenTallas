"""Extend exact copy-zero observer homes to union banks24..62, no bank moves."""
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def build():
    p=ROOT/'results/arch/qwen_tp8_1012/vm_region_nx_spec_claude.json'
    old=json.loads((ROOT/'results/arch/qwen_native_memory_1014/observer_homes.json').read_text())
    plan=json.loads(p.read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==old['parent_plan_sha256']
    entries=copy.deepcopy(old['entries'])
    for bank in range(7):
        entry=copy.deepcopy(next(e for e in entries if e['region']==6 and e['bank_local']==bank))
        entry['region']=7;entry['bank_global']=56+bank
        origin=plan['origins_in_vm_um']['7'];r=entry['observer_relative_rect_um']
        entry['observer_vm_rect_um']=[round(origin[0]+r[0],4),round(origin[1]+r[1],4),r[2],r[3]]
        for key in ('bank_rtl_path','observer_rtl_path'):
            entry[key]=entry[key].replace('g_t[6]','g_t[7]')
        entry['bank_clock_pin']=entry['bank_clock_pin'].replace('ck_r6_','ck_r7_')
        entry['observer_clock_pin']=f'ck_r7_{56+bank}'
        entries.append(entry)
    assert [e['bank_global'] for e in entries]==list(range(24,63))
    for e in entries:
        x,y,w,h=e['observer_relative_rect_um']
        assert x>=0 and y>=0 and x+w<=1123.2 and y+h<=1080
        gaps=[max(x-(c['x']+c['w']), c['x']-(x+w), y-(c['y']+c['h']), c['y']-(y+h)) for c in plan['children']]
        assert min(gaps)>=20-1e-6,(e['bank_global'],min(gaps))
        e['minimum_axis_channel_to_existing_um']=round(min(gaps),4)
    clocks=['ck']+[f'ck_r{r}_{k}' for r in range(8) for k in range(56)]
    clocks += [e['observer_clock_pin'] for e in entries]
    assert len(clocks)==len(set(clocks))==488
    return dict(schema='opentallas.qwen.vm-rawcommit-homes.v1',source_home_commit='03f0b9574',
                parent_plan=old['parent_plan'],parent_plan_sha256=old['parent_plan_sha256'],
                parent_rectangle_um=old['parent_rectangle_um'],count=39,clock_count=488,
                status='ASSIGNED_HOMES; raw ABI native kit and actual clock R still pending',
                coverage='Actual SRAM consume valid/line8/mask16 for banks24..62; runtime coverage is not numerical-data validation',
                entries=entries,scalar_clock_ports=clocks,
                qualification='Exact data-at-consume and macro readback/wrongdata mutant required; no duplicate512data observer or fabricated fence')
if __name__=='__main__':
    p=ROOT/'results/arch/qwen_split_compute_1014/vm_rawcommit';p.mkdir(exist_ok=True)
    d=build();(p/'observer_homes39.json').write_text(json.dumps(d,indent=1)+'\n')
    print('PASS39homes, unchanged448leaves, >=20um axis channel,488unique scalar roots')
