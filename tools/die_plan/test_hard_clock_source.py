"""An internal related PHY provider has a real physical output and an exact ratio."""
import pytest

import gen_phys as GP
import hard_clock_source as HCS
import sdc_lint as SL
from test_pad_clock import plan


def source_plan():
    p = plan()
    t = p.types['mid']
    t['contents'] = [dict(inst='phy', physical_inst='u_bound.u_phy', lef='phy.lef', lib='phy_tt.lib', origin_um=[60, 60], outline_um=[10, 10])]
    t['clock']['edge_clocks'] = [dict(port='clk_coll_blk', tap_um=[24, 24], period_mult=6)]
    row = dict(name='clk_ucie_fdi', source_port='clk_coll_blk', instance='u_bound.u_phy',
               pin='lclk', multiply_by=5, basis='common PLL and phase-aligned 6:5 gearbox')
    t['clock']['hard_clock_sources'] = [row]
    return p, row


def test_exact_related_hard_source_and_missing_or_weakened_constraints():
    p, row = source_plan()
    text = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    ctx = SL.kit_context(p, 'mid')
    line = HCS.sdc_line(row)
    assert './' not in line and line in text
    assert not SL.lint(text, **ctx)
    assert SL.lint(text.replace(line, ''), **ctx)
    assert SL.lint(text.replace('-multiply_by 5', '-multiply_by 6'), **ctx)
    assert SL.lint(text.replace('/lclk}', '/clk}'), **ctx)
    assert SL.lint(text.replace(line, 'create_clock -name clk_ucie_fdi -period 999.6 [get_pins {u_bound.u_phy/lclk}]'), **ctx)
    p.types['mid']['clock']['edge_clocks'][0]['cdc'] = 'synchronized'
    with pytest.raises(ValueError, match='not a synchronous edge clock'):
        HCS.sources(p, 'mid')


def test_staged_provider_must_be_a_physical_output(tmp_path):
    p, _ = source_plan()
    lef = tmp_path / 'phy.lef'
    lib = tmp_path / 'phy_tt.lib'
    lef.write_text('PIN lclk\n  DIRECTION OUTPUT ;\n  USE CLOCK ;\nEND lclk\n')
    lib.write_text('pin (lclk) {\n  direction : output;\n}\n')
    HCS.validate_macro_views(p, 'mid', tmp_path)
    lib.write_text('pin (lclk) {\n  direction : input;\n}\n')
    with pytest.raises(ValueError, match='must declare lclk output'):
        HCS.validate_macro_views(p, 'mid', tmp_path)
    lef.write_text('PIN clk\n  DIRECTION INPUT ;\n  USE CLOCK ;\nEND clk\n')
    with pytest.raises(ValueError, match='must declare lclk OUTPUT CLOCK'):
        HCS.validate_macro_views(p, 'mid', tmp_path)
