"""Exact QC TX/RX macro packing and via-map read-back, including64entryimages."""
import hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qc_dcal_profile as p
import rom_gen


def profile(n=32,seed=0):
    return {'TX':[seed+i for i in range(n)],'RX':[0x80000000+seed+7*i for i in range(n)]}


def test_word_order_and_full64content(tmp_path):
    for n in(32,64):
        x=profile(n,3);d=tmp_path/str(n);r=p.personalise(x,d)
        words=rom_gen.read_hex(d/r['image'])
        assert words[:n]==[a|(b<<32) for a,b in zip(x['TX'],x['RX'])]
        assert words[n:]==[0]*(64-n)
        assert r['check']['verdict']=='PASS' and r['check']['words_checked']==64


def test_content_changes_only_via_and_mutant_rejected(tmp_path):
    hashes={f.name:rom_gen.asap7.sha256_file(f) for f in p.MACRO.parent.iterdir()}
    a=p.personalise(profile(seed=3),tmp_path/'a');b=p.personalise(profile(seed=7),tmp_path/'b')
    assert(tmp_path/'a'/a['viamap']).read_bytes()!=(tmp_path/'b'/b['viamap']).read_bytes()
    assert hashes=={f.name:rom_gen.asap7.sha256_file(f) for f in p.MACRO.parent.iterdir()}
    vm=tmp_path/'a'/a['viamap'];rows=vm.read_text().splitlines();rows[0]=f'{int(rows[0],16)^1:032x}'
    vm.write_text('\n'.join(rows)+'\n');mf=tmp_path/'a'/a['manifest'];m=json.loads(mf.read_text())
    m['instances'][0]['viamap_sha256']=hashlib.sha256(vm.read_bytes()).hexdigest();mf.write_text(json.dumps(m))
    r=rom_gen.verify_personalisation(mf,tmp_path/'a'/a['image'],p.MACRO)
    assert r['verdict']=='FAIL' and any('words differ' in e for e in r['errors'])


def test_prefix_extraction_and_fail_closed_values():
    x=profile();tx=sum(v<<(32*i) for i,v in enumerate(x['TX']));rx=sum(v<<(32*i) for i,v in enumerate(x['RX']))
    text=f"localparam [1023:0] OVL_C_TX_IMG=1024'h{tx:x};\nlocalparam [1023:0] OVL_C_RX_IMG=1024'h{rx:x};"
    assert p.extract_sv(text,'OVL_C')==x
    with pytest.raises(ValueError):p.extract_sv(text)
    with pytest.raises(ValueError):p.pack_profile({'TX':[0]*32,'RX':[0]*64})
    x=profile();x['TX'][0]=1<<32
    with pytest.raises(ValueError):p.pack_profile(x)
