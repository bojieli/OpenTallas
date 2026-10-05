import hashlib
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w19_payload_loader as L


def fixture(tmp_path,records):
    source=tmp_path/'logical.hex'
    source.write_text(''.join(f'{int.from_bytes(r,"little"):0272x}\n' for r in records))
    return source,hashlib.sha256(source.read_bytes()).hexdigest()

@pytest.mark.parametrize('count',[1,3,4,24,32])
def test_sector_bytes_preserve_record_order_and_exponents(tmp_path,count):
    records=[bytes((i*136+j)*17%256 for j in range(136)) for i in range(count)]
    source,pin=fixture(tmp_path,records)
    out=tmp_path/'sectors.hex'
    result=L.load_image(source,out,expected_sha256=pin,payloads=count,expert_id=383)
    data=b''.join(int(line,16).to_bytes(32,'little') for line in out.read_text().splitlines()[1:])
    expected=b''.join(records)
    assert data[:len(expected)]==expected
    assert data[len(expected):]==bytes(result['physical_bytes']-len(expected))
    assert out.read_text().splitlines()[0]==f"@{result['first_sector']:06x}"

@pytest.mark.parametrize('defect',['missing','extra','source_pin','stride','address','expert'])
def test_loader_rejects_bad_input_and_leaves_no_image(tmp_path,defect):
    source,pin=fixture(tmp_path,[bytes(136)])
    kw=dict(expected_sha256=pin,payloads=1,expert_id=0)
    if defect=='missing':kw['payloads']=2
    if defect=='extra':source,pin=fixture(tmp_path,[bytes(136)]*2);kw['expected_sha256']=pin
    if defect=='source_pin':kw['expected_sha256']='0'*64
    if defect=='stride':kw.update(expert_stride_lines=1)
    if defect=='address':kw.update(base_line=1<<22)
    if defect=='expert':kw['expert_id']=384
    out=tmp_path/'sectors.hex'
    with pytest.raises(ValueError):L.load_image(source,out,**kw)
    assert not out.exists()


def test_existing_image_is_immutable(tmp_path):
    source,pin=fixture(tmp_path,[bytes(136)])
    out=tmp_path/'sectors.hex';out.write_text('previous failed image')
    with pytest.raises(FileExistsError):L.load_image(source,out,expected_sha256=pin,payloads=1,expert_id=0)
    assert out.read_text()=='previous failed image'

@pytest.mark.parametrize('text',['00\n','g'*272+'\n','0'*274+'\n'])
def test_loader_rejects_malformed_logical_records(tmp_path,text):
    source=tmp_path/'bad.hex';source.write_text(text)
    pin=hashlib.sha256(source.read_bytes()).hexdigest()
    out=tmp_path/'sectors.hex'
    with pytest.raises(ValueError):L.load_image(source,out,expected_sha256=pin,payloads=1,expert_id=0)
    assert not out.exists()


def test_loader_places_offset_segment_without_touching_other_experts(tmp_path):
    records=[bytes(range(136))]
    source,pin=fixture(tmp_path,records)
    out=tmp_path/'sectors.hex'
    meta=L.load_image(source,out,expected_sha256=pin,payloads=1,expert_id=17,
                      base_line=100,expert_stride_lines=40,sm_offset_lines=12)
    assert meta['first_sector']==(100+17*40+12)*4
    assert meta['cfg_lines']==2 and meta['sector_count']==8
    assert len(out.read_text().splitlines())==9


def test_candidate_loader_cli_is_off_by_default(tmp_path):
    import subprocess
    source,pin=fixture(tmp_path,[bytes(136)])
    out=tmp_path/'sectors.hex';record=tmp_path/'record.json'
    result=subprocess.run([sys.executable,str(ROOT/'tools/w19_payload_loader.py'),
        '--source',str(source),'--source-sha256',pin,'--payloads','1','--expert-id','0',
        '--out',str(out),'--record',str(record)],capture_output=True,text=True)
    assert result.returncode!=0 and '--enable required' in result.stderr
    assert not out.exists() and not record.exists()


def test_descriptor_count_bound_is_enforced_before_loading(tmp_path):
    source,pin=fixture(tmp_path,[bytes(136)])
    with pytest.raises(ValueError):
        L.load_image(source,tmp_path/'sectors.hex',expected_sha256=pin,payloads=L.MAX_PAYLOADS+1,expert_id=0)
