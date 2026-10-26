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


def test_hcx_actual_builder_matches_legacy_across_page_boundary(tmp_path):
    import subprocess
    source=C.ROOT/'tools/s81_ftok/hcx_rank_images.py'
    legacy=subprocess.check_output(['git','-C',str(C.ROOT),'show','5e8ce49592:tools/s81_ftok/hcx_rank_images.py'],text=True)
    old={'__file__':str(source),'__name__':'legacy_hcx_producer'}
    new={'__file__':str(source),'__name__':'current_hcx_producer'}
    exec(compile(legacy,str(source),'exec'),old)
    exec(compile(source.read_text(),str(source),'exec'),new)
    #Minimum HCX vehicle: same hu_hbm/hu_case formats, early and last43-set addresses,
    #all8banks/4payload lanes/2pages, and final rank/leaf identity.
    row=23;sources=[]
    for layer in(0,42):
        d=tmp_path/f'set{layer}';d.mkdir();records={};cases=[]
        for block,base in enumerate((0,4096)):
            cases.append('0'*56+f'{base<<397:x}')
            for bank in range(8):
                for run in range(80):
                    for lane in range(4):
                        a=base+4+(8*row+bank)*320+run*4+lane
                        v=((layer<<28)|(block<<27)|(bank<<20)|(run<<8)|lane)+1
                        records[a]=(1<<255)|(v*0x123456789abcdef)
        (d/'hu_hbm.mem').write_text(''.join(f'{a:010x}{v:064x}\n' for a,v in records.items()))
        (d/'hu_case.mem').write_text('\n'.join(cases)+'\n');sources.append((layer,d))
    old['sets']=lambda root:iter(sources);new['sets']=lambda root:iter(sources)
    before=old['build'](tmp_path,tmp_path/'old',[row])
    after=new['build'](tmp_path,tmp_path/'new',[row])
    assert before==after and len(after)==64
    assert all((tmp_path/'old'/n).read_bytes()==(tmp_path/'new'/n).read_bytes() for n in before)
    assert len(list((tmp_path/'new'/'.rom-personalisation').glob('*/verify.json')))==64
