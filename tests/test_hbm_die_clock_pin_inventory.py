import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hbm_die_clock_pin_inventory as C


def test_full_retiled_inventory_fails_closed_on_new_collective(tmp_path):
    p=tmp_path/'sm.json'
    contract=dict(die_um=[3075.84,1131.84],packets={'ck':[
        dict(real_pin='clk',direction='input',xy_um=[1325.916,1131.84])]})
    p.write_text(json.dumps(contract))
    d,r=C.generate(p)
    assert r['consumer_endpoints']==377
    assert r['unbound_endpoints']==2
    assert {i['port'] for i in r['inventory'] if i['planned_xy_um'] is None}=={'clk_stream','clk_link'}
    assert all(i['source']=='LEF-clk-pin-center-explicit-ck-alias' for i in r['inventory'] if i['instance'].startswith('lk_'))
    assert len([i for i in r['inventory'] if i['source']=='planned-SM-top-clock-portal'])==32
    assert d['strict_clock_pins'] and r['selected'] is False
    contract['die_um'][0]+=1
    p.write_text(json.dumps(contract))
    with pytest.raises(ValueError,match='dimensions'):
        C.generate(p)
