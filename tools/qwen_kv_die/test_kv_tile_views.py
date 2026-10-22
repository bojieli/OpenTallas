"""KV-FACELAND-WIRE 10-19: kv_tile_views unit checks (identity text, effective face edges, check())."""
import kv_tile_views as T


def test_module_text_ignores_comments_and_space():
    a = 'module qkd_kvs_x (input ck); // c\n  foo u (.a(b));\nendmodule\nmodule y; endmodule'
    b = 'module   qkd_kvs_x (input ck);\n/* x */ foo u (.a(b));   endmodule'
    assert T.module_text(a, 'qkd_kvs_x') == T.module_text(b, 'qkd_kvs_x')
    assert T.module_text(a, 'qkd_kvs_z') is None


def test_effective_edges_and_wrapper():
    assert T.effective(dict(recipe=3, kind='tile', pin_regs=dict(enable=False)))['pin_in'] == 0
    e = T.effective(dict(recipe=3, kind='tile', reset_ports=['rst_n']))          # ref_tile defaults: pin regs + landing
    assert (e['pin_in'], e['pin_out'], e['reset_landing_stages']) == (1, 1, 2)
    e = T.effective(dict(recipe=3, kind='tile', pin_regs=dict(enable=True), reset_landing=dict(enable=False, reason='x')))
    assert (e['pin_in'], e['reset_landing_stages']) == (1, 0)
    hdr = ('//   reset rst_n: rtl/lib/ot_rst_relay.sv (async assert, release +3 ck edges, zero steady-state cycles)\n'
           '//   landed buses: fin +1, i_ctl +1 (rtl/lib/ot_pin_land.sv, one capture flop per bit at the face)\n')
    assert T.wrapper_edges(hdr) == ({'fin': 1, 'i_ctl': 1}, 3)


def test_check_flags_unbound_and_wrong_module(tmp_path):
    rec = dict(fails=[], tiles={'qkd_kvs_attn': dict(verdict='BIND', face_land=True, bind=dict(view='v/qkd_kvs_attn_fl')),
                                'qkd_kvs_emb': dict(verdict='BIND', face_land=False, bind=dict(view='v/emb'))})
    views = dict(views={'qkd_kvs_attn': dict(bound=True, view='v/qkd_kvs_attn_fl', module='qkd_kvs_attn_fl'),
                        'qkd_kvs_emb': dict(bound=False, view='v/emb', reason='interface')})
    dv = tmp_path / 'die_bound.v'
    dv.write_text('module top;\n  qkd_kvs_attn kvs_attn (.ck(c));\nendmodule\n')
    ids = sorted(f['id'] for f in T.check(rec, views, dv))
    assert ids == ['FACE_LAND_NETLIST', 'TILE_VIEW_NOT_BOUND']
    dv.write_text('module top;\n  qkd_kvs_attn_fl kvs_attn (.ck(c));\nendmodule\n')
    views['views']['qkd_kvs_emb']['bound'] = True
    assert T.check(rec, views, dv) == []
