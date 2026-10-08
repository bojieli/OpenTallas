"""Candidate clock plans must preserve real roots, periods and pin completeness."""
import gzip
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/budgets'))
import clock_plan as P


def model():
    domains = dict(stream=5/6, serial=10/9, hbm=1.024, link=5/6)
    return dict(die='hbm', outline_um=[100,100], regions=[], strict_clock_pins=True,
        top_input_ports={f'clk_{k}': dict(center_um=[10+i*10,.042], use='CLOCK',
            direction='input', period_ns=v) for i,(k,v) in enumerate(domains.items())},
        insts=[['sink','macro','block','','',20,20,10,10,'R0']],
        ports={'macro': {'clk': [5,10]}},
        buses=[[f'clk_{k}','clock_trunk',1,[['TOP',f'clk_{k}'],['sink','clk']]] for k in domains])


def test_emit_preserves_four_periods_and_input_root(tmp_path):
    d=model(); path=tmp_path/'die.json.gz'
    with gzip.open(path,'wt') as f: json.dump(d,f)
    P.emit(SimpleNamespace(die_model=path,out=tmp_path/'case',group='trunk',name='inputs',buffer_um=100))
    sdc=(tmp_path/'case/clocks.sdc').read_text()
    assert 'clk_serial -period 1111.111111111' in sdc
    assert 'clk_hbm -period 1024.000000000' in sdc
    assert 'clk_stream -period 833.333333333' in sdc
    assert 'clk_link -period 833.333333333' in sdc
    d['by']={i[0]:i for i in d['insts']}
    trees,_=P.plan_groups(d)
    assert P.clock_root_xy(d,('TOP','clk_stream')) == (10,.042)
    assert P.clock_period_ps(d,trees,'REGION:clk_serial:region.1') == pytest.approx(10000/9)
    del d['ports']['macro']['clk']
    with pytest.raises(ValueError,match='unbound clock sinks'):
        P.validate_clock_pins(d,trees)


def test_bad_source_rejected_before_case_written(tmp_path):
    d=model();d['by']={i[0]:i for i in d['insts']}
    trees,_=P.plan_groups(d)
    del d['top_input_ports']['clk_hbm']
    with pytest.raises(ValueError,match='missing physical clock input'):
        P.validate_clock_pins(d,trees)
    d=model();d['by']={i[0]:i for i in d['insts']}
    d['top_input_ports']['clk_hbm']['center_um']=[101,0]
    with pytest.raises(ValueError,match='outside die'):
        P.validate_clock_pins(d,trees)
    d['top_input_ports']['clk_hbm']['center_um']=[10,.042]
    d['top_input_ports']['clk_hbm']['period_ns']=0
    with pytest.raises(ValueError,match='invalid clock period'):
        P.validate_clock_pins(d,trees)
