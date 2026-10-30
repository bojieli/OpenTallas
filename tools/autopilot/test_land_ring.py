"""Declared landing ring = registered capture (COORD 2026-10-29 11:09, GEOM-59): config of pin_reg, not a new check."""
import json
import re
import geom_rules as G

LAND = {"schema": "land_slots/3", "buses": {"i": {"D": 2, "form": "hold_mux"},
                                             "go_i": {"form": "ring_start", "ring": "i"}}}
GUARD = {"verdict": "PASS", "flops": {"i[0]": "u_ring.s_d[1][0]$_DFFE_PP_"}, "clock_exports": {"fclk_o": "clk"}}


def dump(tmp_path, *, slots=2, far=40):
    """i[0] -> AND2 -> AO21 -> slot flop, per slot (write mux); go_i -> AND2 -> flop; fclk_o driven by a buffer."""
    L = ['D\t0\t0\t600\t100',
         'P\t0\ti[0]\tINPUT\tSIGNAL\tM4\t0\t10',
         'P\t1\tgo_i\tINPUT\tSIGNAL\tM4\t0\t50',
         'P\t2\tfclk_o\tOUTPUT\tSIGNAL\tM4\t600\t50',
         'C\t90\tB\tBUFx2_ASAP7_75t_R\t300\t50\t301\t50\tfb',
         'N\tSIGNAL\ti90\tp2']
    first = []
    for k in range(slots):
        a, o, f = 10 + 3 * k, 11 + 3 * k, 12 + 3 * k
        x = 10 if k == 0 else far
        L += [f'C\t{a}\tL\tAND2x2_ASAP7_75t_R\t5\t10\t6\t10\tand{k}',
              f'C\t{o}\tL\tAO21x1_ASAP7_75t_R\t6\t10\t7\t10\tao{k}',
              f'C\t{f}\tS\tDFFHQNx1_ASAP7_75t_R\t{x - .5}\t9.5\t{x + .5}\t10.5\tu_ring.s_d\\[{k}\\]\\[0\\]$_DFFE_PP_',
              f'N\tSIGNAL\ti{a}\ti{o}', f'N\tSIGNAL\ti{o}\ti{f}']
        first.append(f'i{a}')
    L.append('N\tSIGNAL\tp0\t' + '\t'.join(first))
    L += ['C\t50\tL\tAND2x2_ASAP7_75t_R\t5\t50\t6\t50\tgand', 'C\t51\tS\tDFF\t9.5\t49.5\t10.5\t50.5\tgff',
          'N\tSIGNAL\tp1\ti50', 'N\tSIGNAL\ti50\ti51']
    p = tmp_path / 'dump.tsv'
    p.write_text('\n'.join(L) + '\n')
    return G.Design(p)


def reg(D, land=LAND, guard=GUARD):
    r = G.land_ring_captures(D, land, guard)
    m = G.pin_reg_metrics(D, re.compile('^strap_'), frozenset(r['clock_exports']), r['caps'])
    return r, m


def test_declared_ring_via_mux_registers_at_farthest_slot(tmp_path):
    r, m = reg(dump(tmp_path))
    assert list(r['caps']) == ['i[0]'] and not r['errors'] and r['clock_exports'] == ['fclk_o']
    assert m['pins_land_ring'] == 1 and m['pins_unregistered'] == 1 and m['unregistered_sample'] == ['go_i']
    assert m['pin_reg_max'] == 40  # farthest slot, not the nearest (10)
    r, m = reg(dump(tmp_path, far=400))
    assert m['pin_reg_max'] == 400 and m['pin_reg_max'] > G.PINREG_HARD  # distance still judged


def test_core_kit_v1_declaration_uses_the_same_capture_checks(tmp_path):
    land = dict(LAND, schema="opentallas.land_slots.v1")
    D = dump(tmp_path, far=400)
    assert reg(D, land=land) == reg(D)  # includes the farthest-slot distance gate
    rejected, m = reg(D, land=land, guard=dict(GUARD, verdict="FAIL"))
    assert rejected["errors"] and not rejected["caps"] and m["pins_unregistered"] == 3
    rejected, _ = reg(D, land=dict(land, schema="opentallas.land_slots.v2"))
    assert rejected["errors"] and not rejected["caps"]


def test_undeclared_mux_input_and_ring_start_stay_unregistered(tmp_path):
    D = dump(tmp_path)
    _, m = reg(D, land={"schema": "land_slots/3", "buses": {}}, guard=GUARD)
    assert m['pins_unregistered'] == 2 and m['pins_land_ring'] == 0
    m = G.pin_reg_metrics(D, re.compile('^strap_'))
    assert m['pins_unregistered'] == 3  # no land map: exactly the old rule (fclk_o not exempt either)


def test_named_flop_outside_cone_or_wrong_slot_count_is_rejected(tmp_path):
    D = dump(tmp_path)
    g = dict(GUARD, flops={"i[0]": "u_other/q$_DFF_P_"})
    r, m = reg(D, guard=g)
    assert not r['caps'] and 'not in cone' in r['rejected'][0] and m['pins_unregistered'] == 2
    r, m = reg(dump(tmp_path, slots=3))
    assert not r['caps'] and '3 slot flops' in r['rejected'][0] and m['pins_unregistered'] == 2


def test_missing_or_invalid_metadata_grants_nothing(tmp_path):
    D = dump(tmp_path)
    for land, guard in ((LAND, dict(GUARD, verdict="FAIL")), ({"buses": {}}, GUARD), (LAND, None), (None, GUARD)):
        r, m = reg(D, land, guard)
        assert r['errors'] and not r['caps'] and not r['clock_exports'] and m['pins_unregistered'] == 3
    dump(tmp_path)
    m = G.metrics(str(tmp_path / 'dump.tsv'), land_slots=str(tmp_path / 'nope.json'), face_guard=str(tmp_path / 'nope2.json'))
    assert m['land_ring']['errors'] and m['land_ring']['pins'] == 0 and m['pins_unregistered'] == 3
    (tmp_path / 'l.json').write_text(json.dumps(LAND)); (tmp_path / 'g.json').write_text(json.dumps(GUARD))
    m = G.metrics(str(tmp_path / 'dump.tsv'), land_slots=str(tmp_path / 'l.json'), face_guard=str(tmp_path / 'g.json'))
    assert m['land_ring']['pins'] == 1 and m['pins_unregistered'] == 1 and m['pin_reg_max'] == 40


def test_declared_clock_export_resolves_only_a_singleton_actual_bit_zero(tmp_path):
    dump(tmp_path)
    p = tmp_path / 'dump.tsv'
    p.write_text(p.read_text().replace('P\t2\tfclk_o\t', 'P\t2\tfclk_o[0]\t'))
    r, m = reg(G.Design(p))
    assert r['clock_exports'] == ['fclk_o[0]']
    assert m['pins_unregistered'] == 1 and m['unregistered_sample'] == ['go_i']
    # A declared scalar cannot excuse either bit of a real vector.
    p.write_text(p.read_text() + 'P\t3\tfclk_o[1]\tOUTPUT\tSIGNAL\tM4\t600\t60\n')
    r, m = reg(G.Design(p))
    assert r['clock_exports'] == [] and m['pins_unregistered'] == 3
