"""HKV-DIE2 10-19: kv_static_params recomputes the stage-derived static KV parameters from the die NETLIST table and
fails when they disagree with what is bound / recorded (synthetic table; no die build)."""
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
