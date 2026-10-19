"""KVR-DERIVE 10-19: the attention-path static schedule derived from the relay plan / netlist table, checked against the
closed tiles' hard ages and the die's bindings; slg identity straps; relay clock = launching pin domain.  Every check has
a mutant that must FAIL (synthetic tables / netlists; no die build)."""
import copy
import sys
from collections import namedtuple
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kv_pin_repair as KPR  # noqa: E402
import kv_static_die as KSD  # noqa: E402
import kv_static_params as KSP  # noqa: E402

STACKS = KSD.STACKS
# a die that meets these tile ages exactly: K round trip 8 + 70 + 2, V port sides 2 + 2 (RT 13), W 80 -> RL 97, age 98,
# PV_LEAD 5 on both pairs, pvfin start 5 + 4, F_DLY 1 + 4 + 10
TILE = dict(ECTL_RESPONSE_LAT=80, ECTL_QK_ISSUE_AGE=91, VPORT_RT=13, VPORT_DQ=0, PV_FIRST_INPUT_AGE=98, PV_LEAD=5, F_DLY=15)


def paths(**over):
    p = {}
    for st in STACKS:
        for g in range(8):
            p[f'krq_{st}_{g}'], p[f'krs_{st}_{g}'] = 70, 2
        for k in range(4):
            for g in (0, 1):
                p[f'pvvq_{st}_{k}_{g}'], p[f'pvrs_{st}_{k}_{g}'] = 1, 3
            p[f'pvrq_{st}_{k}'], p[f'O_{st}_{k}'] = 50, 30
    p.update(pvst_0=5, pvst_1=5, pvp_0=4, pvp_1=4, pvfst=9, fin=10)
    p.update(over)
    return p


def bound(**over):
    b = dict(ectl={e: dict(RESPONSE_LAT=80, QK_ISSUE_AGE=91) for e in KSP.schedule(paths())['ectl']},
             vport={v: dict(RT=13, DQ=0) for v in KSP.schedule(paths())['vport']}, pv_ctl_age=98,
             attn=dict(PV_LEAD=5, F_DLY=15))
    b.update(over)
    return b


def ids(p=None, b=None, tile=TILE):
    return sorted({f['id'] for f in KSP.schedule_check(KSP.schedule(p or paths()), tile, b if b is not None else bound())})


def test_matching_die_passes():
    assert ids() == []
    s = KSP.schedule(paths())
    assert s['pv']['FIRST_INPUT_AGE'] == 98 and s['attn']['F_DLY'] == 15 and s['vport']['vport_WS_0']['RT'] == 13


def test_ectl_round_trip_mutant_fails():
    assert ids(paths(krq_ES_3=71)) == ['ECTL_RESPONSE_LAT']


def test_vport_unequal_sides_fail():
    assert 'VPORT_SIDES' in ids(paths(pvrs_WN_2_1=4))


def test_vport_rt_off_the_kit_fails():
    # both sides longer: equal sides, but RT 15 != kit 13 (and the pair age moves with it)
    got = ids(paths(pvrs_EN_1_0=5, pvrs_EN_1_1=5))
    assert 'VPORT_RT' in got and 'PV_FIRST_INPUT_AGE' in got and 'VPORT_SIDES' not in got


def test_unequal_w_fails_the_pair_age():
    assert ids(paths(O_WS_2=31)) == ['PV_FIRST_INPUT_AGE']


def test_pair_start_skew_fails_pv_lead():
    got = ids(paths(pvst_1=0))
    assert 'PV_LEAD' in got


def test_pvfin_start_misaligned_fails():
    got = ids(paths(pvfst=8, fin=11))          # F_DLY still 15, but pvfin starts one edge early
    assert got == ['PVFIN_START_ALIGN']


def test_pvfst_pad_aligns_pvfin_start():
    """KV-PVFST: the generator pads ks_pvfst by -min(align) (kv_k_rt_eq.pvfin_pads); the padded die derives align 0"""
    import kv_k_rt_eq as KRT
    p = paths(pvfst=8, fin=11)                 # the MU-DIE-KV GEN shape: start word one edge early
    n, before = KRT.pvfin_pads(p)
    assert (n, before) == (1, [-1, -1])
    p['pvfst'] += n                            # what equalize_pvfin_start adds to relay_stages['ks_pvfst']
    assert KSP.schedule(p)['attn']['pvfin_start_align'] == [0, 0]
    assert 'PVFIN_START_ALIGN' not in ids(p)
    # the KVR-DERIVE base numbers: PV_LEAD 37 (pair 0), pvp 4, pvfst 40 -> one pad, align 0; F_DLY follows (1 + 4 + fin)
    q = paths(pvst_0=37, pvst_1=0, pvp_0=4, pvp_1=4, pvfst=40, fin=45)
    n, before = KRT.pvfin_pads(q)
    assert (n, before) == (1, [-1, -1])
    q['pvfst'] += n
    s = KSP.schedule(q)['attn']
    assert s['pvfin_start_align'] == [0, 0] and s['F_DLY'] == 1 + 4 + 45
    # mutant: no pad -> FAIL; a late start word (align > 0) is never padded on pvfst (recorded FAIL)
    assert 'PVFIN_START_ALIGN' in ids(paths(pvfst=8, fin=11))
    assert KRT.pvfin_pads(paths(pvfst=10, fin=9)) == (0, [1, 1])
    assert KRT.pvfin_pads(paths(pvp_0=None))[0] is None


def test_f_dly_fails():
    assert ids(paths(fin=11)) == ['F_DLY']


def test_bindings_mutants_fail():
    b = bound()
    b['ectl']['ectl_WS_0'] = dict(RESPONSE_LAT=14)
    assert ids(b=b) == ['ECTL_BOUND']
    b = bound()
    b['vport']['vport_ES_1'] = dict(RT=9, DQ=0)
    assert ids(b=b) == ['VPORT_BOUND']
    assert ids(b=bound(pv_ctl_age=96)) == ['PV_AGE_BOUND']
    assert ids(b=bound(attn=dict(PV_LEAD=0, F_DLY=15))) == ['PV_LEAD_BOUND']


def rec(src, dst, age, net):
    return dict(id=f'{src} -> {dst}', src=dict(inst=src.split('.')[0], port=src.split('.')[1]),
                dst=dict(inst=dst.split('.')[0], port=dst.split('.')[1]), width=1, stages=age, age_edges=age,
                src_nets=[net])


def table_from(p):
    """a netlist table whose records carry exactly the path ages p (expanded pvw / pvfork children, like die_bound.v)"""
    b = []
    for key, (bid, dst, must) in KSP.path_keys().items():
        d = dst if not dst.endswith('_') else 'pvw_0'
        if must:
            d = d + must
        b.append(rec(f'x.{key}', f'{d}.fin' if bid == 'ks_pvfin' else f'{d}.p', p[key], f'n_{bid}'))
        if key.startswith('O_'):                   # the fork's chunk taps reach other pvw leaves deeper: not the header
            b.append(rec(f'x.{key}', 'pvw_0__u_CL0_0_r0.p', p[key] + 30, f'n_{bid}'))
    return dict(buses=b, digest='sha256:t', plan=dict(id='t'))


def test_table_paths_resolve_and_torn_is_reported():
    p = paths()
    got, probs = KSP.table_paths(table_from(p))
    assert probs == [] and got == p
    t = table_from(p)
    t['buses'].append(rec('x.y', 'slg_WS_0.kreq', 99, 'n_krq_WS_0'))      # a second, different age on one path
    _, probs = KSP.table_paths(t)
    assert [x['id'] for x in probs] == ['TORN_PATH']
    t = table_from(p)
    t['buses'] = [r for r in t['buses'] if r['src_nets'] != ['n_ks_pvfin']]
    _, probs = KSP.table_paths(t)
    assert [x['id'] for x in probs] == ['UNRESOLVED_PATH']


def straps(swap=None, bound_form=False):
    lines = []
    for si, st in enumerate(STACKS):
        for g in range(8):
            sv, gv = si, g
            if swap == (st, g):
                gv = (g + 1) % 8
            if bound_form:
                lines.append(f"  qkd_kvs_grp slg_{st}_{g} (.slg__cfg_stack({{1'b{sv >> 1 & 1}, 1'b{sv & 1}}}), "
                             f".slg__cfg_group({{1'b{gv >> 2 & 1}, 1'b{gv >> 1 & 1}, 1'b{gv & 1}}}), .ck(n_clk));")
                continue
            for i in range(2):
                lines.append(f"assign n_kvsid_slg_{st}_{g}__slg__cfg_stack[{i}] = 1'b{sv >> i & 1};")
            for i in range(3):
                lines.append(f"assign n_kvsid_slg_{st}_{g}__slg__cfg_group[{i}] = 1'b{gv >> i & 1};")
    return '\n'.join(lines) + '\n'


def test_slg_identity(tmp_path):
    for bf in (False, True):
        f = tmp_path / f'die{bf}.v'
        f.write_text(straps(bound_form=bf))
        assert KSP.slg_identity(f)[0] == []
        f.write_text(straps(swap=('ES', 3), bound_form=bf))
        assert sorted(x['id'] for x in KSP.slg_identity(f)[0]) == ['SLG_IDENTITY', 'SLG_IDENTITY_DUP']


Inst = namedtuple('Inst', 'name master')


def test_relay_trunk_takes_the_launching_pin_domain():
    by = {'slg_WS_4': Inst('slg_WS_4', 'qkd_kvs_grp'), 'ectl_WS_4': Inst('ectl_WS_4', 'qkd_ectlk'),
          'kvpc_WS_1': Inst('kvpc_WS_1', 'qkd_kvs_pc'), 'kvpc_WS_2': Inst('kvpc_WS_2', 'qkd_kvs_pc')}
    buses = [('clk_hbm_WS', 'clock_trunk', 1, [('pll', 'o'), ('slg_WS_4', 'hck'), ('kvpc_WS_1', 'hck'), ('kvpc_WS_2', 'hck')]),
             ('clk_core_WS', 'clock_trunk', 1, [('pll', 'o'), ('slg_WS_4', 'ck'), ('kvpc_WS_1', 'ck'), ('kvpc_WS_2', 'ck')]),
             ('clk_core_c', 'clock_trunk', 1, [('pll', 'o'), ('ectl_WS_4', 'ck')])]
    # krsp (the K response, measured ck): core even though the first trunk listing slg is the HBM one (the old rule)
    j, d = KPR.relay_trunk(buses, by, ('slg_WS_4', 'krsp'), ('ectl_WS_4', 'rs'))
    assert (buses[j][0], d) == ('clk_core_WS', 'core')
    j, d = KPR.relay_trunk(buses, by, ('kvpc_WS_1', 'o_next'), ('kvpc_WS_2', 'i_prev'))
    assert (buses[j][0], d) == ('clk_core_WS', 'core')
    j, d = KPR.relay_trunk(buses, by, ('kvpc_WS_1', 'pc__ko'), ('kvpc_WS_2', 'pc__ki'))     # the kc chain: hck
    assert (buses[j][0], d) == ('clk_hbm_WS', 'hbm')
    j, d = KPR.relay_trunk(buses, by, ('slg_WS_4', 'o_pc0'), ('kvpc_WS_2', 'i_grp'))       # mixed bundle -> core
    assert (buses[j][0], d) == ('clk_core_WS', 'mixed')


def test_relay_domain_audit(tmp_path):
    model = dict(bus_src={'krs_WS_4': ['slg_WS_4', 'krsp', 'ectl_WS_4', 'rs'], 'kck_WS_1': ['kvpc_WS_1', 'pc__ko', 'kvpc_WS_2', 'pc__ki']},
                 masters={'slg_WS_4': 'qkd_kvs_grp', 'kvpc_WS_1': 'qkd_kvs_pc', 'kvpc_WS_2': 'qkd_kvs_pc', 'ectl_WS_4': 'qkd_ectlk'})
    good = ("  qkd_rlys_528 rly_pinfix_krs_WS_4_0__s0 (.ck(n_clk_core_WS), .a(n_krs_WS_4[527:0]), .b(n_x[527:0]));\n"
            "  qkd_rlys_36 rly_pinfix_kck_WS_1_0__s0 (.ck(n_clk_hbm_WS), .a(n_kck_WS_1[32:0]), .b(n_y[32:0]));\n")
    f = tmp_path / 'die.v'
    f.write_text(good)
    fails, info = KSP.relay_domains(f, model)
    assert fails == [] and info['relays_checked'] == 2
    f.write_text(good.replace('.ck(n_clk_core_WS), .a(n_krs', '.ck(n_clk_hbm_WS), .a(n_krs'))
    fails, _ = KSP.relay_domains(f, model)
    assert [x['id'] for x in fails] == ['RELAY_DOMAIN'] and fails[0]['rows'][0]['bus'] == 'krs_WS_4'


def test_attn_tile_params_parse():
    txt = ('module qkd_kvs_attn (input ck);\n  qkd_attn_result_face_s #(.NF(10), .RESULT_RELAY(0), .F_DLY(46), .CAL_PIPE(1)) '
           'u_attn_face (.ck(ck));\n  qkd_attn_service_root #(.PV_LEAD(37), .CAL_PIPE(1)) u_attn_root (.ck(ck));\nendmodule\n')
    assert KSD.attn_tile_params(txt) == dict(PV_LEAD=37, F_DLY=46)


def test_plan_paths_header_and_fork():
    m = dict(relay_stages={'pvin_WS_0': 28, 'pvh_WS_0': 2, 'ks_pvst': 37, 'krq_WS_0': 70},
             fork_stages={'ks_pvst__f0': 0}, forks={'ks_pvst': [('pvw_1', 'st')]})
    p = KSP.plan_paths(m)
    assert p['O_WS_0'] == 31 and p['pvst_0'] == 37 and p['pvst_1'] == 0 and p['krq_WS_0'] == 70
    assert 'PV_LEAD' in {f['id'] for f in KSP.schedule_check(KSP.schedule(p), dict(TILE, PV_LEAD=37))}
