"""KV calendar ROM address ABI and actual via-map read-back controls."""
import hashlib
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_dcal_profile as p
import rom_gen


def profile(seed=0):
    return {"START": [0]+[seed+i*105 for i in range(1,36)], "PERIOD":10000, "TX_SEG1":2, "RX_SEG1":4, "TX_SEG2":9, "RX_SEG2":10, "ADM_OFS":72, "ADM_LEN":1100, "FIRST_OFS":1176}


def test_exact_address_abi_and_two_contents(tmp_path):
    hashes = {x.name: rom_gen.asap7.sha256_file(x) for x in p.MACRO.parent.iterdir()}
    a, b = p.personalise(profile(7), tmp_path/'a'), p.personalise(profile(9), tmp_path/'b')
    wa = rom_gen.read_hex(tmp_path/'a'/a['image'])
    assert wa[:36] == profile(7)['START']
    assert wa[36:44] == [profile(7)[k] for k in p.SCALARS]
    assert wa[44:] == [0]*20
    assert a['check']['verdict'] == b['check']['verdict'] == 'PASS'
    assert a['check']['words_checked'] == b['check']['words_checked'] == 64
    assert (tmp_path/'a'/a['viamap']).read_bytes() != (tmp_path/'b'/b['viamap']).read_bytes()
    assert hashes == {x.name: rom_gen.asap7.sha256_file(x) for x in p.MACRO.parent.iterdir()}
    assert not str(tmp_path) in (tmp_path/'a'/a['manifest']).read_text()


def test_wrong_via_caught_even_with_updated_hash(tmp_path):
    out = p.personalise(profile(7), tmp_path)
    vm = tmp_path/out['viamap']
    rows = vm.read_text().splitlines()
    rows[0] = f"{int(rows[0],16)^1:016x}"
    vm.write_text('\n'.join(rows)+'\n')
    mf = tmp_path/out['manifest'];m=json.loads(mf.read_text())
    m['instances'][0]['viamap_sha256'] = hashlib.sha256(vm.read_bytes()).hexdigest()
    mf.write_text(json.dumps(m))
    bad = rom_gen.verify_personalisation(mf,tmp_path/out['image'],p.MACRO)
    assert bad['verdict'] == 'FAIL'
    assert any('words differ' in e for e in bad['errors'])


def test_profile_rejects_truncation_and_missing_values():
    for key,value in [('START',[0]*35),('PERIOD',1<<32),('TX_SEG1',-1)]:
        x=profile();x[key]=value
        with pytest.raises(ValueError): p.pack_profile(x)
    x=profile();x['START'][0]=1<<20
    with pytest.raises(ValueError): p.pack_profile(x)
    x=profile();del x['FIRST_OFS']
    with pytest.raises(ValueError): p.pack_profile(x)


def test_rejects_prefetch_collisions_and_init_overlap():
    for key,value in [("START",[0,1]+list(range(10,350,10))), ("PERIOD",100), ("ADM_OFS",66), ("FIRST_OFS",1172)]:
        x=profile();x[key]=value
        with pytest.raises(ValueError): p.pack_profile(x)


def test_literal_sv_extractor():
    x=profile(7);v=sum(w << (20*i) for i,w in enumerate(x["START"]))
    text=f"localparam [719:0] D2D_CAL_START = 720'h{v:x};\n"
    for key in p.SCALARS:
        name={"PERIOD":"D2D_TOKEN_PERIOD","FIRST_OFS":"D2D_FIRST_TOKEN","ADM_OFS":"D2D_ADM_OFS","ADM_LEN":"D2D_ADM_LEN"}.get(key,"D2D_CAL_K_"+key)
        text+=f"localparam integer {name} = {x[key]};\n"
    assert p.extract_sv(text) == x
    with pytest.raises(ValueError): p.extract_sv(text.replace("= 10000;", "= UNKNOWN;"))
