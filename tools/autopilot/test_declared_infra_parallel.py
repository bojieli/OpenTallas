"""FLOW-KITFAIL-3 (KV-KITS-V kvs_pc d35q): a declared island-ft clock arc driven by PARALLEL buffers (mesh_driver
j >= 1 shorted onto the port net by island_ft.tcl) is recognised.  The dump writes the extra driver as an ND row; before
the fix it was dropped, the cell looked output-less and the arc failed "ambiguous buffer input/output"
(4 unregistered ft_ck pins)."""
import re

import geom_rules as G
from test_declared_infra import digest

DUMP = ('D\t0\t0\t100\t100\n'
        'C\t1\tB\tBUFx24_ASAP7_75t_R\t10\t10\t11\t11\tmp_isl0_ck0\n'
        'C\t2\tB\tBUFx24_ASAP7_75t_R\t11\t10\t12\t11\tmp_isl0_ck1\n'
        'C\t3\tB\tBUFx2_ASAP7_75t_R\t30\t30\t31\t31\tforeign\n'
        'P\t0\tft_ck_i_0\tINPUT\tSIGNAL\tM5\t0\t10\n'
        'P\t1\tft_ck_o_0\tOUTPUT\tSIGNAL\tM5\t100\t10\n'
        'N\tSIGNAL\tp0\ti1\ti2\n'
        'N\tSIGNAL\ti1\tp1\n'
        '%s')


def vehicle(tmp_path, nd='ND\ti2\n', inv=False):
    p = tmp_path / 'dump.tsv'
    p.write_text(DUMP % nd)
    decl = dict(schema='opentallas.ft_ports.v1', source='island_ft',
                ports=[dict(name='ft_ck_i_0', direction='INPUT'), dict(name='ft_ck_o_0', direction='OUTPUT')],
                arcs=[dict(source='ft_ck_i_0', sink='ft_ck_o_0', kind='clock', cells=['mp_isl0_ck0', 'mp_isl0_ck1'])])
    decl['sha256'] = digest(decl)
    model = dict(schema='opentallas.ft_interface_model.v1', ft_sha256=decl['sha256'], status='declared',
                 arcs=[dict(source='ft_ck_i_0', sink='ft_ck_o_0', kind='clock', tt_ps=None, ff_ps=None)])
    D = G.Design(p)
    if inv:
        D.cells[2] = ('B', 'INVx4_ASAP7_75t_R') + D.cells[2][2:]
    return D, model, decl


def test_parallel_drivers_on_the_port_net_are_one_declared_arc(tmp_path):
    D, M, C = vehicle(tmp_path)
    r = G.declared_infra_arcs(D, M, C)
    assert r['pins'] == ['ft_ck_i_0', 'ft_ck_o_0'], r
    assert r['arcs'][0]['status'] == 'PASS' and r['arcs'][0]['buffers'] == 2
    assert G.pin_reg_metrics(D, re.compile('^strap_'), frozenset(r['pins']))['pins_unregistered'] == 0


def test_parallel_driver_mutants_still_fail(tmp_path):
    # a foreign (out-of-cone) parallel driver, an inverting parallel driver, and the old dump (no ND row)
    for nd, inv, why in (('ND\ti2\nND\ti3\n', False, 'parallel driver outside'),
                         ('ND\ti2\n', True, ''), ('', False, 'ambiguous buffer input/output')):
        D, M, C = vehicle(tmp_path, nd, inv)
        r = G.declared_infra_arcs(D, M, C)
        assert not r['pins'] and r['arcs'][0]['status'] == 'FAIL', (nd, inv, r)
        assert why in r['arcs'][0]['why'], r


def test_single_driver_dump_has_no_parallel_nets(tmp_path):
    D, M, C = vehicle(tmp_path, '')
    assert D.multi_drv == {} and D.drives[2] == []


def test_parallel_driver_on_its_own_input_net_is_a_cycle(tmp_path):
    D, M, C = vehicle(tmp_path)
    p = tmp_path / 'dump.tsv'
    p.write_text((DUMP % 'ND\ti2\n').replace(
        'N\tSIGNAL\tp0\ti1\ti2\n', 'N\tSIGNAL\tp0\ti1\n').replace(
        'N\tSIGNAL\ti1\tp1\n', 'N\tSIGNAL\ti1\tp1\ti2\n'))
    r = G.declared_infra_arcs(G.Design(p), M, C)
    assert not r['pins'] and r['arcs'][0]['status'] == 'FAIL', r
    assert 'cycle' in r['arcs'][0]['why'], r


def test_longer_parallel_feedback_path_is_a_cycle(tmp_path):
    D, M, C = vehicle(tmp_path)
    # The third buffer feeds the first buffer's output from the second
    # buffer's output. Every master is BUF and the loop parity is even.
    text = (DUMP % 'ND\ti3\n').replace(
        'N\tSIGNAL\tp0\ti1\ti2\n', 'N\tSIGNAL\tp0\ti1\n').replace(
        'N\tSIGNAL\ti1\tp1\n',
        'N\tSIGNAL\ti1\ti2\nN\tSIGNAL\ti2\tp1\ti3\n')
    p = tmp_path / 'dump.tsv'
    p.write_text(text)
    C['arcs'][0]['cells'].append('foreign')
    C['sha256'] = digest(C)
    M['ft_sha256'] = C['sha256']
    r = G.declared_infra_arcs(G.Design(p), M, C)
    assert not r['pins'] and r['arcs'][0]['status'] == 'FAIL', r
    assert 'cycle' in r['arcs'][0]['why'], r
