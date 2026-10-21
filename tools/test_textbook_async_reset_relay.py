"""Mapped ASR reset relay recognition: clock, polarity, isolation and depth."""
import textbook_lint as T


def graph():
    text = 'module top(clk, other, rst_n); input clk, other, rst_n;\n'
    text += 'wire s0n,s0,s1n,s1,r0n,r0,r1n,r1,c0n,c1n;\n'
    for name, d, q in [('s0', "1'b1", 's0n'), ('s1', 's0', 's1n'),
                       ('r0', 's1', 'r0n'), ('r1', 's1', 'r1n')]:
        text += f'DFFASRHQNx1_ASAP7_75t_R {name}(.CLK(clk),.D({d}),.QN({q}),.RESETN(rst_n),.SETN(1\'b1));\n'
        text += f'INVx1_ASAP7_75t_R i{name}(.A({q}),.Y({name}));\n'
    for i in range(2):
        text += f'DFFASRHQNx1_ASAP7_75t_R c{i}(.CLK(clk),.D(1\'b0),.QN(c{i}n),.RESETN(r{i}),.SETN(1\'b1));\n'
    return T.flatten(T.parse_verilog(text + 'endmodule'), 'top')[0]


def proof(g):
    return T.async_reset_relay_proof(g, T.build(g, None), g.ports['rst_n'][1])


def pin(g, name, p, net):
    next(c for c in g.cells if c[1] == name)[2][p] = [g.net(net)]


def test_exact_three_edge_relay_and_report():
    g = graph()
    r = proof(g)
    assert r['pass'] and r['raw_clear_loads'] == 4 and r['release_edges'] == 3
    assert r['regional_leaves'] == 2 and r['max_regional_loads'] == 1
    out = T.analyse(g, None, dict(T.THRESHOLDS))
    assert 'reset_landing' not in out['findings']
    assert out['metrics']['reset_landing'][0]['async_relay_proof'] == r


def test_wrong_clock_at_every_stage_and_consumer_refuses():
    for name in ['s0', 's1', 'r0', 'c0']:
        g = graph(); pin(g, name, 'CLK', 'other')
        assert not proof(g)['pass'], name


def test_raw_functional_reset_or_data_bypass_refuses():
    for p in ['RESETN', 'D']:
        g = graph(); pin(g, 'c0', p, 'rst_n')
        assert not proof(g)['pass'], p


def test_insufficient_release_depth_refuses():
    for name, value in [('r0', 's0'), ('s1', "1'1"), ('r0', "1'1")]:
        g = graph(); pin(g, name, 'D', value)
        assert not proof(g)['pass'], (name, value)


def test_incorrect_sync_or_regional_polarity_refuses():
    for name, value in [('s1', 's0n'), ('r0', 's1n'), ('c0', 'r0n')]:
        g = graph(); pin(g, name, 'RESETN' if name == 'c0' else 'D', value)
        assert not proof(g)['pass'], name


def test_inactive_set_and_constant_start_are_proven():
    for name, p, value in [('s0', 'SETN', "1'0"), ('r0', 'SETN', 'other'),
                            ('s0', 'D', "1'0"), ('s0', 'D', 'other')]:
        g = graph(); pin(g, name, p, value)
        assert not proof(g)['pass'], (name, p, value)


def test_early_sync_export_and_regional_feedback_refuse():
    for net in ['s0', 's1', 'r0']:
        g = graph(); g.ports['illegal_export'] = ('output', g.net(net))
        assert not proof(g)['pass'], net
    g = graph(); pin(g, 's0', 'D', 'r0')
    assert not proof(g)['pass']


def test_unknown_flop_polarity_cannot_claim_recognition():
    g = graph()
    ci = next(i for i, c in enumerate(g.cells) if c[1] == 's0')
    _, name, pins = g.cells[ci]
    g.cells[ci] = ('FOREIGN_ASR', name, pins)
    assert not proof(g)['pass']


def test_unknown_consumer_clear_and_buffer_polarity_refuse():
    for name, typ in [('c0', 'DFF_UNKNOWN'), ('is0', 'BUF_UNKNOWN')]:
        g = graph()
        ci = next(i for i,c in enumerate(g.cells) if c[1] == name)
        _, nm, pins = g.cells[ci]
        g.cells[ci] = (typ, nm, pins)
        assert not proof(g)['pass'], (name, typ)


def test_tied_or_derived_common_clock_cannot_claim_input_clock():
    for ck in ("1'0", 'derived'):
        g = graph()
        if ck == 'derived':
            g.cells.append(('BUFx1_ASAP7_75t_R', 'clockbuf', {'A': [g.net('clk')], 'Y': [g.net(ck)]}))
        for ci, (typ, nm, pins) in enumerate(g.cells):
            if 'CLK' in pins:
                pins['CLK'] = [g.net(ck)]
        assert not proof(g)['pass'], ck
