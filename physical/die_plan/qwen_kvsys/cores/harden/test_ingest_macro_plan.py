import json
from pathlib import Path


def test_ingest_macro_plan_matches_all_sram_banks_and_keeps_clock_channel_clear():
    h=Path(__file__).resolve().parent
    p=json.load(open(h/'qkd_hr_ingest_eng_macro_plan.json'))
    assert p['module']=='qkd_hr_ingest_eng' and p['outline_um']==[362.88,362.88] and p['added_cycles']==0
    expected={f'u_eng.g_qp.g_bm.g_mb[{b}].u_m{k}' for b in range(16) for k in ('k','v')}
    assert {b['inst'] for b in p['blocks']}==expected
    rects=[]
    for b in p['blocks']:
        x,y=b['x'],b['y'];assert abs(x/8.64-round(x/8.64))<1e-8 and abs((y-.012)/8.64-round((y-.012)/8.64))<1e-8;r=(x-4.32,y-4.32,x+51.408+4.32,y+20.79+4.32)
        assert 0<=r[0]<r[2]<=362.88 and 0<=r[1]<r[3]<=362.88
        assert not(r[0]<=181.464<=r[2] and r[1]<=181.44<=r[3])
        for q in rects:
            assert min(r[2],q[2])-max(r[0],q[0])<1e-8 or min(r[3],q[3])-max(r[1],q[1])<1e-8
        rects.append(r)
    rec=json.load(open(h/'recipes_kv.json'))['qkd_hr_ingest_eng']
    assert rec['hard_children'].endswith('qkd_hr_ingest_eng_macro_plan.json')
