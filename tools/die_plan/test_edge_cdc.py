"""DIE-KV-84 11-06 (COORD 16:2x(b)): opt-in asynchronous edge clock (edge_clocks[].cdc = synchronized + cdc_evidence).
Absent: byte-identical SDC; declared: exactly 4 lines edge <-> clk (max delay T/2, latency ignored; no hold), lint-clean;
any other or partial exception fails sdc_lint; the declaration fails closed."""
import json
from pathlib import Path

import pytest

import gen_phys as GP
import schema
import sdc_lint as SL


def plan(**cdc):
    raw = json.loads(Path(__file__).with_name('examples').joinpath('tiny_plan.json').read_text())
    p = schema.Plan(raw)
    p.types['mid'].setdefault('clock', {})['edge_clocks'] = [dict(port='clk_phy', tap_um=[10.0, 10.0], **cdc)]
    return p


EV = dict(cdc='synchronized', cdc_evidence='test: crossings only in async FIFOs + 2-flop synchronisers')


def test_absent_is_byte_same_and_declared_appends_the_four_lines():
    base = plan(); text = GP.sdc(base, 'mid', GP.type_pins(base, 'mid'))
    assert GP.edge_cdc(base, 'mid') == {} and 'set_max_delay' not in text and 'edge_clock_cdc' not in SL.kit_context(base, 'mid')
    assert not SL.lint(text, **SL.kit_context(base, 'mid'))
    p = plan(**EV); decl = GP.sdc(p, 'mid', GP.type_pins(p, 'mid'))
    half = GP.t_lib(0.5 * float(p.die['period_ps']))
    lines = [f'set_max_delay -ignore_clock_latency {half:.4f} -from [get_clocks clk_phy] -to [get_clocks clk]',
             f'set_max_delay -ignore_clock_latency {half:.4f} -from [get_clocks clk] -to [get_clocks clk_phy]',
             'set_false_path -hold -from [get_clocks clk_phy] -to [get_clocks clk]',
             'set_false_path -hold -from [get_clocks clk] -to [get_clocks clk_phy]']
    for ln in lines:
        assert decl.count(ln + '\n') == 1, ln
    assert decl.replace(''.join(ln + '\n' for ln in lines), '').count('set_max_delay') == 0
    assert 'set_clock_groups' not in decl
    ctx = SL.kit_context(p, 'mid')
    assert ctx['edge_clock_cdc'] == {'clk_phy': 0.5 * float(p.die['period_ps'])}
    assert not SL.lint(decl, **ctx), SL.lint(decl, **ctx)


def test_lint_rejects_partial_wrong_or_undeclared():
    p = plan(**EV); decl = GP.sdc(p, 'mid', GP.type_pins(p, 'mid')); ctx = SL.kit_context(p, 'mid')
    hold = 'set_false_path -hold -from [get_clocks clk] -to [get_clocks clk_phy]\n'
    half = GP.t_lib(0.5 * float(p.die['period_ps']))
    for bad in [decl.replace(hold, ''), decl + hold,
                decl.replace(f'{half:.4f} -from [get_clocks clk_phy]', f'{2 * half:.4f} -from [get_clocks clk_phy]'),
                decl + 'set_false_path -hold -from [get_clocks clk_phy] -to [get_clocks vclk]\n',
                decl + 'set_clock_groups -asynchronous -group [get_clocks clk_phy] -group [get_clocks clk]\n']:
        assert SL.lint(bad, **ctx), bad[-160:]
    base = plan()
    assert SL.lint(decl, **SL.kit_context(base, 'mid'))          # the same lines on an undeclared edge clock


@pytest.mark.parametrize('bad', [dict(cdc='synchronized'), dict(cdc='synchronized', cdc_evidence=' '),
                                 dict(cdc='async', cdc_evidence='x'),
                                 dict(cdc='synchronized', cdc_evidence='x', period_mult=2)])
def test_declaration_fails_closed(bad):
    with pytest.raises(ValueError):
        GP.edge_cdc(plan(**bad), 'mid')
