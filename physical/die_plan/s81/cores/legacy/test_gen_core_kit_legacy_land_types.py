"""Legacy landing wrappers preserve actual hierarchy types across ODB flattening."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import gen_core_kit_legacy as G
sys.path.insert(0,str(G.TOOL))
import test_face_guard as V


def test_typed_slot_descriptor_preserved_and_bad_contract_rejected():
    rec=dict(land_slots=dict(d=dict(D=4,form='hold_mux')),why_land_slots='existing slots')
    payload,wrapper=G.land_slot_contract(rec,['d'])
    assert payload['buses']==rec['land_slots']
    assert payload['why']=='existing slots'
    assert G.land_slot_contract(dict(land_slots=dict(d=4)),['d'])[0]['buses']==dict(d=4)
    for slots in [dict(missing=4),dict(d=dict(D=1,form='hold_mux')),dict(d=dict(D=4,form='unknown'))]:
        with pytest.raises(SystemExit):G.land_slot_contract(dict(land_slots=slots),['d'])


def test_generated_wrapper_proves_mapped_rotation_and_rejects_mutants(tmp_path):
    payload,wrapper=G.land_slot_contract(dict(land_slots=dict(d=dict(D=4,form='hold_mux'))),['d'])
    (tmp_path/'land_slots.json').write_text(json.dumps(payload))
    (tmp_path/'pins.json').write_text(json.dumps([dict(bus='d',bit=None)]))
    (tmp_path/'face_guard_core.py').write_text(wrapper)
    shutil.copyfile(G.TOOL/'face_guard.py',tmp_path/'face_guard.py')
    hier=V._registered_onehot_vehicle()
    raw=tmp_path/'1_2_yosys.v';raw.write_text(hier)
    post=tmp_path/'1_synth.v'
    def run(text):
        post.write_text(V._flat_like_odb(text))
        cp=subprocess.run([sys.executable,'-I',str(tmp_path/'face_guard_core.py'),str(post),'top',
                           '^(?:fclk|rst_n)$',str(tmp_path/'pins.json'),str(tmp_path/'out.json')],capture_output=True,text=True)
        result=json.loads((tmp_path/'out.json').read_text())
        return cp,result
    cp,r=run(hier)
    assert cp.returncode==0,(cp.stdout,cp.stderr,r)
    assert r['verdict']=='PASS' and r['registered_onehot']['local']['cycle']==4
    # Type evidence alone never excuses a changed mapped reset or rotation equation.
    for mutant in ['rotation','two_reset_bits','clock']:
        cp,r=run(V._registered_onehot_vehicle(mutant))
        assert cp.returncode!=0 and r['verdict']=='FAIL',(mutant,r)
    raw.unlink()
    cp,r=run(hier)
    assert cp.returncode!=0 and r['verdict']=='FAIL'
