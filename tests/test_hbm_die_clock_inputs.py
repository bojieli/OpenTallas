import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import hbm_accel_die_fp as H
import hbm_die_clock_inputs as C


def test_explicit_roots_preserve_domains_and_real_collective_consumers(tmp_path):
    m=C.apply(H.build(H.R24SM3,network_probe=True))
    clock_buses={b[0]:b for b in m['buses'] if b[1]=='clock_trunk'}
    assert set(clock_buses)=={f'clk_{d}' for d in C.DOMAINS}
    for domain in C.DOMAINS:
        eps=clock_buses[f'clk_{domain}'][3]
        assert eps[0]==('TOP',f'clk_{domain}')
        assert not any(p.startswith('pll_') for _,p in eps)
        assert (('hb_coll',f'clk_{domain}') in eps) == (domain in ('stream','link'))
    assert C.PERIOD_NS['stream']/C.PERIOD_NS['serial']==pytest.approx(3/4)
    assert C.PERIOD_NS['hbm']==1.024
    H.write_netlist(m,1,tmp_path/'die.v')
    H.write_def_floorplan(m,tmp_path/'die.def')
    C.write_sdc(m,tmp_path/'inputs.sdc')
    rtl=(tmp_path/'die.v').read_text();sdc=(tmp_path/'inputs.sdc').read_text()
    assert 'input wire clk_stream' in rtl and '.pll_stream(' not in rtl
    assert 'PINS 8 ;' in (tmp_path/'die.def').read_text()
    assert '-multiply_by 3 -divide_by 4' in sdc
    assert 'set_clock_groups' not in sdc and 'set_false_path' not in sdc
    assert m['external_clock_inputs']['clock_pad_or_receiver_area_um2'] is None
    for p in m['top_input_ports'].values():
        x,y=p['center_um'];w,h=p['size_um']
        assert 0<=x-w/2<x+w/2<=m['geo']['W']
        assert 0<=y-h/2<y+h/2<=m['geo']['H']
        assert (x-.012)/.048==pytest.approx(round((x-.012)/.048))
    with pytest.raises(ValueError,match='already applied'):
        C.apply(m)


def test_missing_historical_root_cannot_be_silently_reassigned():
    m=H.build(H.R24SM3,network_probe=True)
    for index,(bid,cls,bits,eps) in enumerate(m['buses']):
        if bid=='clk_stream':
            m['buses'][index]=(bid,cls,bits,eps[1:])
            break
    with pytest.raises(ValueError,match='exactly one historical root'):
        C.apply(m)
