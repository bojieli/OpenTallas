"""HKV-DIE2 10-19: kv_static_params recomputes the stage-derived static KV parameters from the die NETLIST table and
fails when they disagree with what is bound / recorded (synthetic table; no die build)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kv_static_params as KSP  # noqa: E402
import kv_static_die as KSD  # noqa: E402

STACKS = KSD.STACKS


def rec(src, dst, stages, nets, age='stages'):
    r = dict(id=f'{src} -> {dst}', src=dict(inst=src.split('.')[0], port=src.split('.')[1]),
             dst=dict(inst=dst.split('.')[0], port=dst.split('.')[1]), width=1, stages=stages, domain='stream_1p2',
             eq_age_group=None, src_nets=nets)
    r['age_edges'] = stages if age == 'stages' else age
    return r


def model(rs, plan=None, hub_params=None):
    m = dict(schema=KSP.SCHEMA_MODEL, relay_stages=rs, fork_stages={}, forks={},
             seq_kvn=dict(rx='srx', prg='ks_prg', kw='seqst_kw', land=1, bundle=None),
             hub=dict(inst='ahub', master='qkd_ahub_static_dw', parameters=hub_params or {}),
             plan=plan or {}, flags=dict(ahub_static=True, afault=False))
    return m


def table(stations=0, kw=17, lane_age=None):
    b = [rec('kvs_attn.ahs', 'ahub.hs_start', 46, ['n_ks_ahs']), rec('ahub.fr_valid', 'pvfin.rz_valid', 0, ['n_ks_ahfr']),
         rec('pvfin.st', 'pvw_0.start', 3, ['n_ks_pvfst']),
         rec('d2d_kv.att_rx_v', 'kvs_attn.d2d__srx__0_0', 11, ['n_srx']),
         rec('kvs_attn.prg', 'seq.prg_req_v', 5, ['n_ks_prg']),
         rec('d2d_kv.kvn_word_valid', 'seq.kvn_word_valid', kw, ['n_seqst_kw'])]
    for k, st in enumerate(STACKS):
        b.append(rec(f'astk_{st}.ap', f'ahub.ap{k}', 8 + (stations if st == 'EN' else 0), [f'n_ap_{st}'],
                     age=None if (lane_age and st == 'WS') else 'stages'))
        b.append(rec(f'ahub.am{k}', f'astk_{st}.am', 8, [f'n_am_{st}']))
    return dict(buses=b, digest='sha256:x', plan=dict(id='t'))


RS = dict(ks_ahs=46, ks_ahfr=0, ks_pvfst=3, srx=11, ks_prg=5, seqst_kw=17,
          **{f'ap_{s}': 8 for s in STACKS}, **{f'am_{s}': 8 for s in STACKS})


def test_recompute_matches_plan_when_the_table_is_the_plan():
    m = model(dict(RS))
    m['plan'] = dict(ahub_ages=KSD.ahub_ages(dict(relay_stages=RS)))
    need = m['plan']['ahub_ages']
    r = KSP.run(dict(m, hub=dict(parameters=dict(AP_OFS=need['AP_OFS'], FR_OFS=need['FR_OFS']))), table())
    ids = [f['id'] for f in r['fails']]
    assert 'PLAN_PARAMS_STALE' not in ids and 'SEQ_KVN_TORN' not in ids and 'UNRESOLVED_STAGE' not in ids
    assert r['params']['seq_kvn']['aligned'] is True
    assert r['params']['ahub_ages']['AP_OFS'] == [2 + 8 - 46] * 4


def test_stations_change_ap_ofs_and_the_plan_record_is_stale():
    m = model(dict(RS))
    m['plan'] = dict(ahub_ages=KSD.ahub_ages(dict(relay_stages=RS)))
    r = KSP.run(m, table(stations=2))
    assert r['params']['ahub_ages']['AP_OFS'][STACKS.index('EN')] == 2 + 10 - 46
    stale = next(f for f in r['fails'] if f['id'] == 'PLAN_PARAMS_STALE')
    assert any(d['param'] == f'AP_OFS[{STACKS.index("EN")}]' for d in stale['diffs'])


def test_hub_bound_defaults_fail_against_the_table():
    r = KSP.run(model(dict(RS)), table())
    assert any(f['id'] == 'AHUB_OFS_BOUND' for f in r['fails'])       # the kit / RTL default {4{2}} != 2 + 8 - 46


def test_seq_kvn_pads_removed_is_torn():
    r = KSP.run(model(dict(RS)), table(kw=4))
    f = next(f for f in r['fails'] if f['id'] == 'SEQ_KVN_TORN')
    assert 'S_kw 4' in f['what'] and r['params']['seq_kvn']['aligned'] is False


def test_landed_lane_age_from_fwd_lanes_else_unresolved():
    r = KSP.run(model(dict(RS)), table(lane_age=True))
    assert any(f['id'] == 'UNRESOLVED_STAGE' and 'ap_WS' in f['what'] for f in r['fails'])
    fwd = dict(lanes=[dict(stations=['rly_ap_WS_7__s0'], landed=11.0)])
    r = KSP.run(model(dict(RS)), table(lane_age=True), fwd)
    assert not any(f['id'] == 'UNRESOLVED_STAGE' for f in r['fails'])
    assert r['params']['ahub_ages']['relays']['ap_WS'] == 10


def test_ap_ofs_hex_parse():
    assert KSP._ap_list("{16'hffdc, 16'hffdd, 16'hffde, 16'hffdf}") == [-33, -34, -35, -36]


def test_face_land_binding_must_match_the_flag(tmp_path):
    v = tmp_path / 'die.v'
    v.write_text('module qkd_die;\n  qkd_kvs_attn_fl kvs_attn (.ck(n_ck));\nendmodule\n')
    m = model(dict(RS))
    m['face_land'] = dict(enabled=False, tiles=KSD.FACE_LAND_TILES)
    r = KSP.run(m, table(), die_v=v)
    assert any(f['id'] == 'FACE_LAND_BINDING' for f in r['fails'])
    m['face_land']['enabled'] = True
    r = KSP.run(m, table(), die_v=v)
    assert not any(f['id'] == 'FACE_LAND_BINDING' for f in r['fails'])


def test_face_land_compiler_ages():
    import os
    import importlib
    os.environ['OT_KV_FACE_LAND'] = '1'
    try:
        sys.path.insert(0, str(HERE.parents[1]))
        from tools.qwen_kv_die import kv_static_die as K2
        importlib.reload(K2)
        import kv_static_programme as C
        fl = C._face_land()
        assert fl['enabled'] and fl['i_ctl'] == 1 and fl['F_DLY_delta'] == 1 and fl['rst_release_max'] == 5   # KV-BIND3: astk rc1 (2 landing + 3 relay)
        assert fl['rst_release'] == dict(kvs_attn=3, astk_rly_296=5, hr_core_queue=3)
    finally:
        os.environ.pop('OT_KV_FACE_LAND')
        importlib.reload(K2)


# ---- HKV-DIE3 10-19 ------------------------------------------------------------------------------------------------
def test_face_land_per_tile_by_master(tmp_path):
    v = tmp_path / 'die.v'
    v.write_text('module qkd_die;\n  qkd_astk_rly_296_fl astk_WS__g_owner_0__u_r (.ck(n_ck));\n'
                 '  qkd_astk_rly_296_fl astk_WN__g_owner_0__u_r (.ck(n_ck));\n  qkd_kvs_attn kvs_attn (.ck(n_ck));\nendmodule\n')
    m = model(dict(RS))
    m['face_land'] = dict(enabled=True, selected=['astk_rly_296'], tiles=KSD.FACE_LAND_TILES)
    assert not any(f['id'] == 'FACE_LAND_BINDING' for f in KSP.run(m, table(), die_v=v)['fails'])
    m['face_land']['selected'] = ['astk_rly_296', 'kvs_attn']          # kvs_attn selected but bound unlanded
    assert any(f['id'] == 'FACE_LAND_BINDING' for f in KSP.run(m, table(), die_v=v)['fails'])
    m['face_land'] = dict(enabled=False, selected=[], tiles=KSD.FACE_LAND_TILES)   # landed relays, tile not selected
    assert any(f['id'] == 'FACE_LAND_BINDING' and 'astk_rly_296' in f['what'] for f in KSP.run(m, table(), die_v=v)['fails'])


def test_ahub_ofs_binding_literal_and_json(tmp_path):
    b = KSD.ahub_ofs_bound('-36,-36,-34,-35:-7')
    assert b['AP_OFS'] == [-36, -36, -34, -35] and b['FR_OFS'] == -7 and KSP._ap_list(b['AP_OFS_hex']) == b['AP_OFS']
    p = tmp_path / 'sp.json'
    p.write_text(json.dumps(dict(params=dict(ahub_ages=dict(AP_OFS=[1, 2, 3, 4], FR_OFS=-9)))))
    assert KSD.ahub_ofs_bound(str(p))['FR_OFS'] == -9 and KSD.ahub_ofs_bound('') is None
    m = model(dict(RS), hub_params=dict(AP_OFS=b['AP_OFS_hex'], FR_OFS=b['FR_OFS']))
    r = KSP.run(m, table())
    assert any(f['id'] == 'AHUB_OFS_BOUND' and 'generator binding' in f['what'] for f in r['fails'])   # != table values


def test_attention_checks_hub_margin_and_pair_skew():
    sys.path.insert(0, str(HERE.parents[1]))
    from tools.qwen_kv_die import kv_static_programme as KP
    pr = KP.profile('die', json.loads((KP.ROOT / KP.AGES).read_text()))
    assert KP.rz_margin(dict(fr_ofs=-7)) == 10 and KP.rz_margin(dict(fr_ofs=None)) == KP.AC.RZ_MARGIN
    c = KP.attention_calendar(8192, dict(pr, fr_ofs=-7))                       # minimal R: hub export exactly after pub
    assert c['PV_START'] + c['R'] - 7 >= c['HUB_PUB'] + KP.HUB_EXPORT_AFTER_PUB
    r = KP.attention_checks(pr, None, -7, Ts=(1, 300, 1000, 8192))
    ids = {f['id']: f for f in r['fails']}
    assert 'HUB_FR_EXPORT' not in ids
    assert ids['PVFIN_PAIR_SKEW']['contexts'] == 2 and r['worst']['pvfin_skew'] == 32   # T 1 (32), T 300 (16)
    r = KP.attention_checks(dict(pr, d_rl=pr['d_rl']), None, -7, pvfin_skew=32, Ts=(1, 300))
    assert not r['fails']
