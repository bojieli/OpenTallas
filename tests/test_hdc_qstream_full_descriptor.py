import sys
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_qstream_descriptor as D

def entry(**kw):
    d=dict.fromkeys(D.FIELDS,0);d.update(n=65536,hbm=1<<25,rom=1<<26,ibase=1<<27);d.update(kw);return d

def test_reduced_layout_compatibility_and_all_field_bounds():
    e=entry(n=123,hbm=1234,rom=456,ibase=789,istride=900,grp=4,ind=1,fp4=1,pred=2)
    expected=e['hbm']|e['rom']<<24|e['n']<<48|e['fp4']<<64|e['pred']<<65|e['ind']<<67|e['ibase']<<68|e['istride']<<92|e['grp']<<116
    assert D.encode(e)==expected
    import hdc_program_v41 as program
    assert program.encode_list([e])==[expected,0]
    assert program.encode_list([entry()],profile='full_shape')==D.encode_list([entry()],'full_shape')
    for profile in D.WIDTHS:
        for f,w in zip(D.FIELDS,D.WIDTHS[profile]):
            for invalid in (-1,1<<w):
                d=dict.fromkeys(D.FIELDS,0);d[f]=invalid
                with pytest.raises(ValueError):D.encode(d,profile)
        with pytest.raises(ValueError):D.decode(1<<sum(D.WIDTHS[profile]),profile)

@pytest.fixture(scope='module')
def binary(tmp_path_factory):
    d=tmp_path_factory.mktemp('qstream_descriptor');exe=d/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb_hdc_qstream_full_descriptor','-o',str(exe),
        str(ROOT/'rtl/hdc/hbm/ot_hdc_qstream.sv'),str(ROOT/'rtl/test/tb_hdc_qstream_full_descriptor.sv')],check=True,capture_output=True)
    return exe

@pytest.mark.parametrize('case',['direct','indirect','reserved','base_overflow','stride_overflow','rom_overflow'])
def test_actual_walker_descriptor(binary,tmp_path,case):
    e=entry();ident=0;bad=case not in ('direct','indirect')
    if case=='indirect':e.update(ind=1,istride=1<<20);ident=3
    if case=='stride_overflow':e.update(ind=1,istride=1<<24);ident=63
    if case=='base_overflow':e['hbm']=(1<<30)-1
    if case=='rom_overflow':e['rom']=(1<<30)-1
    word=D.encode(e,'full_shape') | ((1<<159) if case=='reserved' else 0)
    (tmp_path/'entry.hex').write_text(f'{word:040x}\n')
    addr=(1<<28)+e['hbm']+ident*e['istride']*17
    rom=e['rom']+ident*e['istride']
    r=subprocess.run(['vvp',str(binary),f'+FAULT={int(bad)}',f'+ID={ident}',f'+ADDR={addr}',
       f'+ROM={rom}',f'+COUNT={e["n"]}',f'+IBASE={e["ibase"]}'],cwd=tmp_path,capture_output=True,text=True,timeout=20)
    assert r.returncode==0,r.stdout+r.stderr
    assert ('QSTREAM_DESCRIPTOR_FAULT_PASS' if bad else 'QSTREAM_DESCRIPTOR_PASS') in r.stdout


def test_registered_issue_credit_does_not_double_spend(tmp_path):
    exe=tmp_path/'credit'
    subprocess.run(['iverilog','-g2012','-s','tb_hdc_qstream_issue_credit','-o',str(exe),
        str(ROOT/'rtl/hdc/hbm/ot_hdc_qstream.sv'),str(ROOT/'rtl/test/tb_hdc_qstream_issue_credit.sv')],check=True,capture_output=True)
    r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True,timeout=20)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'QSTREAM_ISSUE_CREDIT_PASS' in r.stdout
