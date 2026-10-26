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


def test_actual_released_token_map_producer_matches_legacy(tmp_path):
    import subprocess
    source=C.ROOT/'tools/engram_token_map_image.py'
    payload=C.ROOT/'results/uarch/h4_c0_ds_external_source_provenance_20261003/r1/payloads/fbc8c3ec76fc1143_L01_token_map.npy'
    if not payload.exists():pytest.skip('released tokenizer payload not in sparse checkout')
    legacy=subprocess.check_output(['git','-C',str(C.ROOT),'show','5e8ce49592:tools/engram_token_map_image.py'],text=True)
    old={'__file__':str(source),'__name__':'legacy_content_producer'}
    new={'__file__':str(source),'__name__':'current_content_producer'}
    exec(compile(legacy,str(source),'exec'),old)
    exec(compile(source.read_text(),str(source),'exec'),new)
    old['prepare'](tmp_path/'old');new['prepare'](tmp_path/'new')
    names=[f'tmap{i}.viamap.hex' for i in range(8)]+['expected.hex']
    assert all((tmp_path/'old'/n).read_bytes()==(tmp_path/'new'/n).read_bytes() for n in names)
    assert len(list((tmp_path/'new'/'.rom-personalisation').glob('*/verify.json')))==8
