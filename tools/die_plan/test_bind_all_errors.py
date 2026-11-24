"""BIND-ALL-ERRORS 11-23: a strict / --all-gaps bind lists EVERY landing START stage / bus plan error of a type (and every type)
in one run instead of stopping at the first (QC C1d: SU2R-FIX3 fixed sle_su_c, then the same class surfaced on
slw_su_c__cl19bb38ef one 75-min round trip later).  Same checks, same messages; any error still FAILs."""
import json
from types import SimpleNamespace
import pytest
import bind
from clock_landings import Landings, LandingError, LandingErrors
from test_clock_landings import A_BODY, B_BODY
from test_count_straps import strap_vehicle


def writer(p, raws, xys=None):
    p['partition_types']['A'].setdefault('clock', {})['landing_writer_start'] = dict(
        depth=len(raws), branches={'x': {'stages': [dict(xy_um=(xys[i] if xys else [2. + i, 1.]), raw_reset=r)
                                                    for i, r in enumerate(raws)]}})


def reader(p, raws):
    p['partition_types']['B'].setdefault('clock', {})['landing_reader_start'] = dict(
        depth=len(raws), branches={'y': {'stages': [dict(xy_um=[3. + 3 * i, 3.], raw_reset=r) for i, r in enumerate(raws)]}})


def landings(p, t, collect):
    c = Landings(p, t)
    c.collect = collect
    return c


def test_default_still_raises_the_first_stage_only():
    p, t = strap_vehicle(); writer(p, ['bad0', 'rst_n_t0', 'bad2'])
    with pytest.raises(LandingError, match='stage|bad0') as ei:
        landings(p, t, False).type_rtl('A', A_BODY)
    assert not isinstance(ei.value, LandingErrors) and 'bad0' in str(ei.value) and 'bad2' not in str(ei.value)


def test_collect_lists_every_bad_writer_stage():
    p, t = strap_vehicle(); writer(p, ['bad0', 'rst_n_t0', 'bad2'], xys=[[2., 1.], [3., 1.], [4., 1.]])
    p['partition_types']['A']['clock']['landing_writer_start']['branches']['x']['stages'][1]['xy_um'] = [float('nan'), 1.]
    with pytest.raises(LandingErrors) as ei:
        landings(p, t, True).type_rtl('A', A_BODY)
    errs = ei.value.errors
    assert [(e['type'], e['bus'], e['side'], e['stage']) for e in errs] == [('A', 'x', 'writer', i) for i in range(3)]
    assert 'bad0 has no registered wavefront driver' in errs[0]['error']
    assert 'stage 1 needs finite xy_um' in errs[1]['error']
    assert 'bad2 has no registered wavefront driver' in errs[2]['error']
    assert '3 landing error(s)' in str(ei.value)


def test_collect_bus_level_error_and_next_bus_continue():
    p, t = strap_vehicle(); writer(p, ['rst_n_t0', 'rst_n_t0'])
    p['partition_types']['A']['clock']['landing_writer_start']['branches']['x']['stages'].pop()   # depth 2, 1 stage
    with pytest.raises(LandingErrors) as ei:
        landings(p, t, True).type_rtl('A', A_BODY)
    assert len(ei.value.errors) == 1 and ei.value.errors[0]['stage'] is None and 'exactly 2 physical stages' in str(ei.value)


def test_collect_reader_stages():
    p, t = strap_vehicle(); reader(p, ['nope_a', 'nope_b'])
    with pytest.raises(LandingErrors) as ei:
        landings(p, t, True).type_rtl('B', B_BODY)
    assert [(e['side'], e['stage']) for e in ei.value.errors] == [('reader', 0), ('reader', 1)]


def test_collect_clean_type_is_byte_identical():
    for setup, tn, body in ((lambda p: writer(p, ['rst_n_t0', 'rst_n_t0']), 'A', A_BODY),
                            (lambda p: reader(p, ['cland_reset_y', 'cland_reset_y']), 'B', B_BODY)):
        p, t = strap_vehicle(); setup(p)
        a, b = landings(p, t, False), landings(p, t, True)
        assert a.type_rtl(tn, body) == b.type_rtl(tn, body)
        assert a.reset_placements == b.reset_placements and b._type_errs is None


def test_emit_one_records_one_gap_per_error():
    errs = [dict(type='A', bus='x', side='writer', stage=i, error=f'A.x: writer START raw reset r{i} has no registered '
                 'wavefront driver') for i in range(3)]
    def boom(*a, **k):
        raise LandingErrors(errs)
    fake = SimpleNamespace(types={'A': {}}, collect_gaps=True, emit_type=lambda tn, p: ('text', []),
                           clock_landings=SimpleNamespace(type_rtl=boom))
    fake._gap = lambda msg: bind.Binder._gap(fake, msg)
    fake._emit_type_files = lambda *a: bind.Binder._emit_type_files(fake, *a)
    bind.Binder._emit_one(fake, 'A', ['pa'], None, [])
    assert fake.emit_gaps == [f'A: {e["error"]}' for e in errs]


def test_error_records_and_report(tmp_path, capsys):
    errors = ['EMIT slw_su_c__cl19bb38ef: slw_su_c__cl19bb38ef.x_ctl_o: writer START raw reset rr_t138 has no registered '
              'wavefront driver',
              'EMIT sle_su_c: sle_su_c.x_su_l0_stm_o: writer START stage 6 needs finite xy_um',
              'R8_STALE something', 'EMIT u_missing_a.rst_n: expected one bound leaf, found 0']
    recs = bind.write_all_errors(tmp_path, errors, ['slw_su_c__cl19bb38ef', 'sle_su_c'])
    assert recs[0] | {} == dict(cls='EMIT', type='slw_su_c__cl19bb38ef', bus='x_ctl_o', side='writer', stage=None, raw='rr_t138',
                                error=errors[0])
    assert (recs[1]['type'], recs[1]['bus'], recs[1]['stage']) == ('sle_su_c', 'x_su_l0_stm_o', 6)
    assert recs[2]['cls'] == 'R8_STALE' and recs[2]['type'] is None
    assert recs[3]['type'] is None
    j = json.loads((tmp_path / 'bind_errors_all.json').read_text())
    assert j['verdict'] == 'FAIL' and j['n_errors'] == 4 and j['by_class'] == {'EMIT': 3, 'R8_STALE': 1}
    assert j['by_type'] == {'slw_su_c__cl19bb38ef': 1, 'sle_su_c': 1}
    assert 'BIND_ALL_ERRORS 4 error(s) on 2 type(s)' in capsys.readouterr().out
    assert json.loads((tmp_path / 'x').mkdir() or bind.write_all_errors(tmp_path / 'x', []) or
                      (tmp_path / 'x/bind_errors_all.json').read_text())['verdict'] == 'PASS'


def test_strict_bind_collects_by_default():
    src = (bind.Path(bind.__file__)).read_text()
    assert 'B.collect_gaps = bool(getattr(a, "all_gaps", False) or getattr(a, "strict", False))' in src
    assert 'collect=B.collect_gaps)' in src


def test_stage_number_survives_to_the_record():
    p, t = strap_vehicle(); writer(p, ['rst_n_t0', 'bad1'])
    with pytest.raises(LandingErrors) as ei:
        landings(p, t, True).type_rtl('A', A_BODY)
    rec = bind.error_records([f"EMIT A: {ei.value.errors[0]['error']}"], ['A'])[0]
    assert (rec['type'], rec['bus'], rec['side'], rec['stage'], rec['raw']) == ('A', 'x', 'writer', 1, 'bad1')


def test_collected_errors_survive_a_later_plain_value_error(monkeypatch):
    p, t = strap_vehicle(); writer(p, ['bad0'])
    c = landings(p, t, True)
    def late(*a, **k):
        raise ValueError('later plan error')
    monkeypatch.setattr(c, '_ring_lite', late)
    with pytest.raises(LandingErrors) as ei:
        c.type_rtl('A', A_BODY)
    assert 'bad0' in ei.value.errors[0]['error'] and ei.value.errors[-1]['error'] == 'later plan error'


@pytest.mark.parametrize('collect', [False, True])
def test_post_landing_refusal_is_one_gap_per_type(collect):
    def boom(tn, *a):
        raise bind.BindError(f'control reset localization {tn}: nope')
    f = SimpleNamespace(collect_gaps=collect, _emit_type_files=boom)
    f._gap = lambda m: bind.Binder._gap(f, m)
    if not collect:
        with pytest.raises(bind.BindError):
            bind.Binder._emit_one(f, 'T1', ['p'], None, [])
        return
    for tn in ('T1', 'T2'):
        bind.Binder._emit_one(f, tn, ['p'], None, [])
    assert f.emit_gaps == [f'control reset localization {tn}: nope' for tn in ('T1', 'T2')]


# ---------------------------------------------------------------- R8-ALL-MEMBERS 11-24: every stale R8 member, not the first 30
def _r8b(n_main=40, n_extra=3):
    B = SimpleNamespace(errors=[], pad_stats=dict(table_sha="abc"), r8_bad=[])
    B._r8_origin = {}
    for i in range(n_main):
        m = dict(id=f"m{i}", lane=f"L{i}", source="s.q", asbuilt=5, bound=10, pad=2)
        B._r8_origin[m["id"]] = "main.json"
        for bit in range(2):
            bind.Binder._r8_bad(B, "mismatch", m, bit, "s.q", 5, 12)
    for i in range(n_extra):
        m = dict(id=f"x{i}", lane="Lx", source="t.q", asbuilt=3, bound=7, pad=0)
        B._r8_origin[m["id"]] = "pv_col.json"
        bind.Binder._r8_bad(B, "no_sink", m, None)
    return B


def test_r8_all_lists_every_member_per_table(tmp_path):
    B = _r8b()
    rows = bind.write_r8_all(tmp_path, B)
    assert len(rows) == 43
    j = json.loads((tmp_path / 'r8_stale_all.json').read_text())
    assert j['members'] == 43 and j['bits'] == 83 and j['by_table'] == {'main.json': 40, 'pv_col.json': 3}
    r = j['rows'][0]
    assert (r['table'], r['id'], r['lane'], r['rec_bound'], r['bind_bound'], r['delta'], r['bits'], r['bit_list']) == \
        ('main.json', 'm0', 'L0', 10, 12, 2, 2, [0, 1])
    tsv = (tmp_path / 'r8_stale_all.tsv').read_text().splitlines()
    assert len(tsv) == 44 and tsv[0].startswith('table\tkind\tid\tlane')
    assert B.errors == [e for e in B.errors if e.startswith(bind.R8_FAIL_FAST_PREFIXES)]
    assert B.errors[-1].startswith('R8_STALE_TOTAL 43 member(s) / 83 bit(s): main.json 40, pv_col.json 3')
    bind.write_r8_all(tmp_path, B)
    assert sum(e.startswith('R8_STALE_TOTAL') for e in B.errors) == 1


def test_r8_all_nothing_stale_writes_nothing(tmp_path):
    B = SimpleNamespace(errors=[], r8_bad=[])
    assert bind.write_r8_all(tmp_path, B) == [] and not B.errors and not (tmp_path / 'r8_stale_all.json').exists()



# ---------------------------------------------------------------- bind head: build_buses input errors collect in strict
def test_head_err_default_raises_collect_records():
    f = SimpleNamespace(collect_gaps=False, errors=[])
    with pytest.raises(bind.BindError, match='SPARE_FT bad'):
        bind.Binder._head_err(f, 'SPARE_FT bad', ValueError('bad'))
    f.collect_gaps = True
    bind.Binder._head_err(f, 'SPARE_FT bad', ValueError('bad'))
    bind.Binder._head_err(f, 'RESET_SPINE_SINK_STAGES x')
    assert f.errors == ['SPARE_FT bad', 'RESET_SPINE_SINK_STAGES x']


def test_build_buses_has_no_bare_raise_left_for_the_three_inputs():
    src = bind.Path(bind.__file__).read_text()
    assert 'raise BindError(f"SPLIT_LANE_REFERENCE {exc}")' not in src
    assert src.count('self._head_err(') >= 3


# ---------------------------------------------------------------- inside one type: every bus-loop refusal; the bound top
def test_type_bus_loop_errors_all_listed():
    p, t = strap_vehicle()
    c = landings(p, t, True)
    c.by_type['B']['inputs'] = list(c.by_type['B']['inputs']) + ['nope1', 'nope2']
    r0 = next(iter(c.type_row['B'].values()))
    c.type_row['B'].update(nope1=r0, nope2=r0)
    with pytest.raises(LandingErrors) as ei:
        c.type_rtl('B', B_BODY)
    msgs = [e['error'] for e in ei.value.errors]
    assert sum('actual bound input nope1 not found' in m for m in msgs) == 1
    assert sum('actual bound input nope2 not found' in m for m in msgs) == 1
    d = landings(p, t, False)
    d.by_type['B']['inputs'] = list(d.by_type['B']['inputs']) + ['nope1', 'nope2']
    r0 = next(iter(d.type_row['B'].values()))
    d.type_row['B'].update(nope1=r0, nope2=r0)
    with pytest.raises(LandingError, match='nope1') as e2:
        d.type_rtl('B', B_BODY)
    assert not isinstance(e2.value, LandingErrors)


def test_type_wrapper_keeps_a_follow_on_crash_after_collected_errors(monkeypatch):
    p, t = strap_vehicle(); writer(p, ['bad0'])
    c = landings(p, t, True)
    monkeypatch.setattr(c, '_ring_lite', lambda *a, **k: {}['x'])
    with pytest.raises(LandingErrors) as ei:
        c.type_rtl('A', A_BODY)
    assert 'bad0' in ei.value.errors[0]['error'] and 'KeyError' in ei.value.errors[-1]['error']
    c2 = landings(p, t, True)
    p2, t2 = strap_vehicle()
    c3 = landings(p2, t2, True)
    monkeypatch.setattr(c3, '_ring_lite', lambda *a, **k: {}['x'])
    with pytest.raises(KeyError):               # nothing collected: a tool bug surfaces unchanged
        c3.type_rtl('A', A_BODY)


def test_top_rtl_collect_off_is_unchanged_and_on_wraps():
    p, t = strap_vehicle()
    a, b = landings(p, t, False), landings(p, t, True)
    for x in (a, b):
        x.type_rtl('A', A_BODY); x.type_rtl('B', B_BODY)
    from test_count_straps import TOP
    assert a.top_rtl(TOP) == b.top_rtl(TOP) and b._type_errs is None


# ---------------------------------------------------------------- type-level checks before the bus loops
def test_type_level_config_errors_all_listed():
    p, t = strap_vehicle()
    p['partition_types']['A']['landing_status_reg'] = 'yes'
    p['partition_types']['A']['landing_guard_reg'] = 'no'
    with pytest.raises(LandingErrors) as ei:
        landings(p, t, True).type_rtl('A', A_BODY)
    msgs = [e['error'] for e in ei.value.errors]
    assert any('landing_status_reg must be a boolean' in m for m in msgs)
    assert any('landing_guard_reg must be a boolean' in m for m in msgs)
    with pytest.raises(LandingError) as e1:
        landings(p, t, False).type_rtl('A', A_BODY)
    assert not isinstance(e1.value, LandingErrors) and 'must be a boolean' in str(e1.value)


# ---------------------------------------------------------------- Landings constructor: every table row error
def test_constructor_lists_every_bad_table_row():
    import copy
    p, t = strap_vehicle()
    t = copy.deepcopy(t)
    rows = t['ports']
    assert len(rows) >= 2
    rows.append(dict(rows[0], port='ghost_1'))
    rows.append(dict(rows[0], port='ghost_2'))
    with pytest.raises(LandingError) as e1:
        Landings(p, t)
    assert not isinstance(e1.value, LandingErrors)
    with pytest.raises(LandingErrors) as ei:
        Landings(p, t, collect=True)
    msgs = [e['error'] for e in ei.value.errors]
    assert sum('ghost_1' in m for m in msgs) >= 1 and sum('ghost_2' in m for m in msgs) >= 1


def test_constructor_collect_clean_table_is_identical():
    p, t = strap_vehicle()
    a, b = Landings(p, t), Landings(p, t, collect=True)
    assert a.type_rtl('A', A_BODY) == b.type_rtl('A', A_BODY) and b._type_errs is None


# ---- BIND-ALL-ERRORS part 7: emit_type collects its in-loop refusals -------------------------------------------------
def _start_vehicle():
    from test_bind_sub_core_leaf import vehicle
    b, part = vehicle({"u_a": "u_a"})
    b.F.cells[0].ports["start_i"] = [10, 11]
    b.G.dirs[0]["start_i"] = "input"
    b.sinks[(0, "start_i", 0)] = ("start",)
    b.sinks[(0, "start_i", 1)] = ("start",)
    return b, part


def test_emit_type_default_raises_first_refusal_unchanged():
    import bind
    b, part = _start_vehicle()
    with pytest.raises(bind.BindError) as ei:
        b.emit_type("src", part)
    assert not isinstance(ei.value, bind.BindErrors)
    assert "START consumer x.u_a.start_i[0]" in str(ei.value)


def test_emit_type_collect_lists_every_refusal():
    import bind
    b, part = _start_vehicle()
    b.collect_gaps = True
    with pytest.raises(bind.BindErrors) as ei:
        b.emit_type("src", part)
    errs = ei.value.errors
    assert sum("START consumer x.u_a.start_i[0]" in e for e in errs) == 1
    assert sum("START consumer x.u_a.start_i[1]" in e for e in errs) == 1
    assert not hasattr(b, "_et_errs")


def test_emit_type_collect_clean_type_is_identical():
    from test_bind_sub_core_leaf import vehicle
    b, part = vehicle({"u_a": "u_a"})
    ref, _ = b.emit_type("src", part)
    b2, part2 = vehicle({"u_a": "u_a"})
    b2.collect_gaps = True
    got, _ = b2.emit_type("src", part2)
    assert got == ref


def test_emit_type_files_gaps_each_collected_refusal():
    b, part = _start_vehicle()
    b.collect_gaps = True
    b.emit_gaps = []
    b._emit_type_files("src", [part], None, [])
    starts = [g for g in b.emit_gaps if "START consumer" in g]
    assert len(starts) == 2 and all(g.startswith("src: ") or "src" in g for g in starts)


def test_bound_top_retains_all_landing_errors(tmp_path):
    def fail_top(text, modules):
        raise LandingErrors([dict(error="missing reset A"), dict(error="missing reset B")])

    b = bind.Binder.__new__(bind.Binder)
    b.ab = {}
    b.plan = {"die": {"name": "test"}}
    b.by_type = {}
    b.types = {}
    b.wavefront_plan = lambda: None
    b._lis_config = lambda: None
    b.emit_top = lambda: "module test; endmodule"
    b.collect_gaps = True
    b.clock_landings = SimpleNamespace(top_rtl=fail_top)

    files = b.emit(tmp_path)

    assert b.emit_gaps == ["TOP missing reset A", "TOP missing reset B"]
    assert [f.name for f in files] == ["bind_cells.sv"]
    assert not (tmp_path / "rtl" / "test_bound_top.sv").exists()
