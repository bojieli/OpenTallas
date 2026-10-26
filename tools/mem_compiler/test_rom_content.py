"""Existing72/266/274-bit no-ECC content contracts stay byte-identical."""
import hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mem_compiler import rom_content as C
from mem_compiler import rom_gen


def old_text(words,bits):
    rows=[0]*512
    for a,w in words.items():
        for b in range(bits):rows[a//8]|=((w>>b)&1)<<(b*8+a%8)
    return ''.join(f'{x:0{bits*2}x}\n' for x in rows)


@pytest.mark.parametrize('bits',[72,266,274])
def test_old_new_bytes_and_wrong_bit_mutant(tmp_path,bits):
    words={0:0x123456789abcdef,7:(1<<(bits-1))|7,8:0xFEDCBA987654321,4095:(1<<(bits-2))|11}
    target=tmp_path/f'w{bits}.viamap.hex';r=C.write_viamap(target,words,f'ot_rom_4096x{bits}_m8')
    assert target.read_text()==old_text(words,bits)
    assert r['ecc']=='none' and r['verdict']=='PASS' and r['words_checked']==4096
    mf=tmp_path/r['manifest'];m=json.loads(mf.read_text());rows=target.read_text().splitlines()
    rows[0]=f'{int(rows[0],16)^1:0{bits*2}x}';target.write_text('\n'.join(rows)+'\n')
    m['instances'][0]['viamap_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();mf.write_text(json.dumps(m))
    _,sheet=C.contract(f'ot_rom_4096x{bits}_m8')
    bad=rom_gen.verify_personalisation(mf,mf.parent/'logical.hex',sheet)
    assert bad['verdict']=='FAIL' and any('words differ' in e for e in bad['errors'])


def test_rejects_overflow_and_conflicting_sparse_images(tmp_path):
    with pytest.raises(ValueError):C.write_viamap(tmp_path/'bad.viamap.hex',[1<<72],'ot_rom_4096x72_m8')
    f=tmp_path/'logical.hex';f.write_text('@0\n1234\n@0\n4321\n')
    with pytest.raises(ValueError):C.read_sparse_hex(f)
