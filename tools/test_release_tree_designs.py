#!/usr/bin/env python3
"""COUNT PER DESIGN (OWNER 12.22 (3), lane COUNT-REP-1 2026-10-30): release_tree_plan.py counts hard cores per design
(module + outline + pin table without strap_* pins); copies are credited when their design is signed off; no false
credit across pin-table variants of one module.  Run: python3 -m pytest -q"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

PA = [dict(name='a[0]', layer='M4', x=0.096, y=2.184), dict(name='clk', layer='M5', x=10.0, y=20.0)]
PB = [dict(name='a[0]', layer='M4', x=0.096, y=30.0), dict(name='clk', layer='M5', x=10.0, y=20.0)]   # moved pin
PS = PA + [dict(name='strap_lane_id[0]', layer='M4', x=0.0, y=5.0)]                                  # + strap pin
FILES = {'a.json': PA, 'b.json': {'pins': PB}, 's.json': PS}


def plan(entries):
    T = {'t%d' % i: dict(hard_cores=[e]) for i, e in enumerate(entries)}
    parts = [dict(name='p%d_%d' % (i, j), type='t%d' % i) for i in range(len(entries)) for j in range(2)]
    return dict(partition_types=T, partitions=parts)


def designs(entries):
    return R.plan_designs(plan(entries), '/nonexistent', read=lambda f: FILES[f])


def core(module, pins, outline=(100.0, 50.0), **kw):
    return dict(module=module, outline_um=list(outline), pins_file=pins, inst='u', **kw)


def test_copies_one_design_orient_and_declared_straps_ignored():
    D, _ = designs([core('m', 'a.json'), core('m', 'a.json', orient='MX'),
                    core('m', 's.json', parent_id_straps={'lane_id': {'value': 3, 'width': 2}})])
    assert list(D) == ['m']
    g = D['m']
    assert g['entries'] == 3 and g['instances'] == 6 and sorted(g['orients']) == ['MX', 'R0'] and g['strap_variants'] == 1


def test_bus_bit_form_equals_name_form():
    kit = [dict(bus='a', bit=0, layer='M4', x=0.096, y=2.184, face='W'), dict(bus='clk', bit=None, layer='M5', x=10.0, y=20.0)]
    assert R.canon_pin_rows(kit) == R.canon_pin_rows(PA) == R.canon_pin_rows(PS)


def test_two_pin_tables_are_two_designs():
    D, rows = designs([core('m', 'a.json'), core('m', 'b.json'), core('n', 'a.json')])
    ms = sorted(D)
    assert len(ms) == 3 and 'n' in D and all(k.startswith('m#100x50/') for k in ms if k != 'n')
    # different module names are never merged, even with the same outline + pins
    assert D['n']['pins_sha'] == next(g['pins_sha'] for k, g in D.items() if k != 'n' and rows[k] == R.canon_pin_rows(PA))


def test_outline_variant_is_a_design():
    D, _ = designs([core('m', 'a.json'), core('m', 'a.json', outline=(100.0, 60.0))])
    assert len(D) == 2


def rec(host='intel1', pins='/k/pins.json'):
    return dict(scan_host=host, pins_path=pins)


def test_single_design_module_credits_every_copy():
    D, rows = designs([core('m', 'a.json'), core('m', 'a.json', orient='MY')])
    rp = {('intel1', '/k/pins.json'): dict(rows=R.canon_pin_rows(PA), outline_nm=(100000, 50000))}
    s, u = R.credit_designs(D, rows, {'m': [('ref1', rec())]}, rp)
    assert s == {'m': ['ref1 DESIGN-MATCH pins']} and u == {}
    c = R.design_counts(dict(designs=D, signed_designs=s, signed_types={}))
    assert (c['cores'], c['signed_cores'], c['instances'], c['signed_instances']) == (1, 1, 4, 4)


def test_multi_design_module_credits_only_matching_design():
    D, rows = designs([core('m', 'a.json'), core('m', 'b.json')])
    kit = [dict(bus='a', bit=0, layer='M4', x=0.0, y=2.184), dict(bus='clk', bit=None, layer='M5', x=10.0, y=20.0)]  # 96 nm edge snap
    rp = {('intel1', '/k/pins.json'): dict(rows=R.canon_pin_rows(kit), outline_nm=(100000, 50000))}
    s, u = R.credit_designs(D, rows, {'m': [('ref1', rec())]}, rp)
    (did,) = s
    assert rows[did] == R.canon_pin_rows(PA) and s[did] == ['ref1 DESIGN-MATCH pins'] and u == {}
    c = R.design_counts(dict(designs=D, signed_designs=s))
    assert (c['cores'], c['signed_cores'], c['instances'], c['signed_instances']) == (2, 1, 4, 2)


def test_multi_design_no_false_credit():
    D, rows = designs([core('m', 'a.json'), core('m', 'b.json')])
    far = [dict(name='a[0]', layer='M4', x=0.096, y=15.0), dict(name='clk', layer='M5', x=10.0, y=20.0)]
    cases = [{},                                                                                    # pins not readable
             {('intel1', '/k/pins.json'): dict(rows=R.canon_pin_rows(far), outline_nm=None)},       # pins match none
             {('intel1', '/k/pins.json'): dict(rows=R.canon_pin_rows(PA), outline_nm=(90000, 50000))}]  # outline differs
    for rp in cases:
        s, u = R.credit_designs(D, rows, {'m': [('ref1', rec())]}, rp)
        assert s == {} and list(u) == ['m'], rp


def test_layer_or_name_set_difference_no_match():
    a = R.canon_pin_rows(PA)
    assert not R.pins_close(a, R.canon_pin_rows([dict(PA[0], layer='M6'), PA[1]]))
    assert not R.pins_close(a, R.canon_pin_rows(PA[:1]))
    assert R.pins_close(a, R.canon_pin_rows([dict(PA[0], x=0.296), PA[1]]))       # 200 nm = PIN_TOL_NM
    assert not R.pins_close(a, R.canon_pin_rows([dict(PA[0], x=0.297), PA[1]]))


def test_replica_sample_one_in_ten():
    D = {'m': dict(instances=21)}
    assert R.replica_sample(D, {'m': ['r']}) == [('m', 2), ('m', 12)]
    assert R.replica_sample(D, {}) == []


def test_die_counts_designs_and_legacy_cache():
    D, rows = designs([core('m', 'a.json'), core('m', 'b.json')])
    new = dict(die='hbm', types=1, hard_cores=['m'], signed_cores={'m': ['ref']}, designs=D, signed_designs={}, design_unmatched={'m': ['ref (pins match no plan design)']})
    old = dict(die='hbm', types=1, hard_cores=['m'], signed_cores={'m': ['ref']})
    (rn,) = R.die_counts(dict(plans={'x': new}), 'hbm')
    (ro,) = R.die_counts(dict(plans={'x': old}), 'hbm')
    assert (rn['cores'], rn['signed_cores'], rn['modules'], rn['signed_modules'], rn['design_unmatched']) == (2, 0, 1, 1, ['m'])
    assert (ro['cores'], ro['signed_cores']) == (1, 1) and 'instances' not in ro


def test_unreadable_pins_files_keyed_by_full_name():
    long = 'cores/ot_hbm_hc_bank128_pair_core__250.56x267.84__'
    D, _ = R.plan_designs(plan([core('m', long + 'canon.json'), core('m', long + 'weight_E.json'), core('m', long + 'canon.json', orient='MX')]),
                          '/nonexistent', read=lambda f: (_ for _ in ()).throw(FileNotFoundError(f)))
    assert len(D) == 2 and sorted(g['entries'] for g in D.values()) == [1, 2]


def test_single_design_module_needs_its_pins_and_outline_too():
    # FLOW-12 10-30 (COORD, SIGNOFF-SPRINT-8 ASK): one plan design no longer credits any record unchecked
    D, rows = designs([core('m', 'a.json')])
    far = [dict(name='a[0]', layer='M4', x=0.096, y=15.0), dict(name='clk', layer='M5', x=10.0, y=20.0)]
    cases = [{},                                                                                    # pins not readable
             {('intel1', '/k/pins.json'): dict(rows=R.canon_pin_rows(far), outline_nm=None)},       # old pin table
             {('intel1', '/k/pins.json'): dict(rows=R.canon_pin_rows(PA), outline_nm=(90000, 50000))}]  # outline differs
    for rp in cases:
        s, u = R.credit_designs(D, rows, {'m': [('ref1', rec())]}, rp)
        assert s == {} and list(u) == ['m'], rp


def test_rec_pins_reads_signed_lef_when_pins_file_is_gone(tmp_path):
    # FLOW-12 10-30: kit pins.json pruned/retired -> the signed abstract beside the record is the pin evidence
    import subprocess
    (tmp_path / 'm.lef').write_text('MACRO m\n  SIZE 100 BY 50 ;\n  PIN a[0]\n    PORT\n      LAYER M4 ;\n        RECT 0.054 2.142 0.138 2.226 ;\n'
                                    '    END\n  END a[0]\n  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M5 ;\n        RECT 0 0 1 1 ;\n    END\n  END VDD\n'
                                    '  PIN clk\n    PORT\n      LAYER M5 ;\n        RECT 9.96 19.96 10.04 20.04 ;\n    END\n  END clk\nEND m\n')
    sp = str(tmp_path / 'signoff.json')
    r = subprocess.run(['python3', '-c', R.REC_PINS_PY], input=json.dumps([['/gone/pins.json', sp]]), capture_output=True, text=True)
    d = json.loads(r.stdout)['/gone/pins.json']
    assert d['die_area'] == [0.0, 0.0, 100.0, 50.0]
    assert R.pins_close(R.canon_pin_rows(d['doc']), R.canon_pin_rows([dict(name='a[0]', layer='M4', x=0.096, y=2.184),
                                                                     dict(name='clk', layer='M5', x=10.0, y=20.0)]))


def test_rec_pins_reads_lef_under_views(tmp_path):
    import subprocess
    v = tmp_path / 'rec' / 'views' / 'rec'; v.mkdir(parents=True)
    (v / 'm.lef').write_text('MACRO m\n  SIZE 10 BY 5 ;\n  PIN clk\n    PORT\n      LAYER M5 ;\n        RECT 1 1 1.2 1.2 ;\n    END\n  END clk\nEND m\n')
    r = subprocess.run(['python3', '-c', R.REC_PINS_PY], input=json.dumps([['/gone', str(tmp_path / 'rec' / 'signoff.json')]]),
                       capture_output=True, text=True)
    d = json.loads(r.stdout)['/gone']
    assert d['die_area'] == [0.0, 0.0, 10.0, 5.0] and R.canon_pin_rows(d['doc']) == {'clk': ('M5', 1100, 1100)}
