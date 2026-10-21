"""KV-AHUB8 10-20: fixed-offset hub binding (OT_KV_AHUB_PAD): bundle members / offsets and the pad arithmetic on the
d22bu post-station stage table (ks_ahs 47, ks_ahfr 0, ks_pvfst 42, ap 5/5/7/6) against the closed a7 view's offsets."""
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kv_bundle_eq as B  # noqa: E402

A7 = dict(AP_OFS=[-36, -36, -34, -35], FR_OFS=-7)          # kit qkd_ahub_sdw @c6c412b4c PARAMS (64'hffddffdeffdcffdc, -7)
D22BU = dict(ks_ahs=47, ks_ahfr=0, ks_pvfst=42, ap_WS=5, ap_WN=5, ap_ES=7, ap_EN=6)


def _m():
    insts = [NS(name=n, kind='tile', master=n) for n in ('ahub', 'kvs_attn', 'pvfin', 'astk_WS', 'astk_WN', 'astk_ES', 'astk_EN')]
    insts.append(NS(name='r0', kind='relay', master='qkd_rly_165'))
    buses = [(f'ap_{s}', 'kv_oneway', 43, [(f'astk_{s}', 'ap'), ('ahub', f'ap_{s}')]) for s in B.AHUB_STACKS]
    buses += [('ks_ahs', 'kv_oneway', 165, [('kvs_attn', 'ahs'), ('r0', 'a')]),
              ('ks_ahs__r0', 'kv_oneway', 165, [('r0', 'b'), ('ahub', 'hs')])]
    return dict(insts=insts, buses=buses), {i.name: i for i in insts}


def test_check_d22bu_vs_a7():
    miss = B.ahub_check(D22BU, A7)
    assert miss == ['AP_OFS WS -40 != -36', 'AP_OFS WN -40 != -36', 'AP_OFS ES -38 != -34', 'AP_OFS EN -39 != -35',
                    'FR_OFS -6 != -7']


def test_ap_bundle_members():
    m, by = _m()
    b = B.ahub_ap_bundle(m, by, A7)['A.hub_ap']
    assert b[0] == ('kvs_attn', 'ahs', 'ahub', 0)
    assert b[1:] == [('astk_WS', 'ap', 'ahub', 38), ('astk_WN', 'ap', 'ahub', 38), ('astk_ES', 'ap', 'ahub', 36),
                     ('astk_EN', 'ap', 'ahub', 37)]


def test_fr_bundle_offset_uses_walked_hs_depth():
    m, by = _m()
    b = B.ahub_fr_bundle(m, by, A7)['A.hub_fr']
    assert b == [('kvs_attn', 'pvfst', 'pvfin', 0), ('ahub', 'fr', 'pvfin', 1 + 1 - 7)]


def test_pads_close_d22bu():
    st = dict(D22BU)
    ap = B.plan({'h': st['ks_ahs'], **{s: st[f'ap_{s}'] for s in B.AHUB_STACKS}},
                {'h': 0, **{s: 2 - t for s, t in zip(B.AHUB_STACKS, A7['AP_OFS'])}})
    assert ap == {'h': 0, 'WS': 4, 'WN': 4, 'ES': 4, 'EN': 4}
    for s in B.AHUB_STACKS:
        st[f'ap_{s}'] += ap[s]
    st['ks_ahs'] += ap['h']
    fr = B.plan({'p': st['ks_pvfst'], 'f': st['ks_ahfr']}, {'f': st['ks_ahs'] + 1 + A7['FR_OFS']})
    assert fr == {'p': 0, 'f': 1}
    st['ks_pvfst'] += fr['p']
    st['ks_ahfr'] += fr['f']
    assert B.ahub_check(st, A7) == []


def test_pads_when_hs_is_shorter():
    st = dict(D22BU, ks_ahs=30)              # a stack is the longer side: hs waits, then fr re-balances on the new depth
    ap = B.plan({'h': 30, **{s: st[f'ap_{s}'] for s in B.AHUB_STACKS}},
                {'h': 0, **{s: 2 - t for s, t in zip(B.AHUB_STACKS, A7['AP_OFS'])}})
    st['ks_ahs'] += ap['h']
    for s in B.AHUB_STACKS:
        st[f'ap_{s}'] += ap[s]
    fr = B.plan({'p': st['ks_pvfst'], 'f': st['ks_ahfr']}, {'f': st['ks_ahs'] + 1 + A7['FR_OFS']})
    st['ks_pvfst'] += fr['p']
    st['ks_ahfr'] += fr['f']
    assert B.ahub_check(st, A7) == []


def test_a7_kit_spec_offsets_read(monkeypatch):
    """the a7 kit spec carries sized literals (64'hffddffdeffdcffdc / 32'hfffffff9): hub_bound must read -36,-36,-34,-35/-7"""
    import kv_static_params as P
    monkeypatch.delenv('OT_KV_AHUB_KIT_SPEC', raising=False)
    (how, got), = P.hub_bound({}, None)
    assert got == A7 and 'physical/ref_tile/qkd_ahub_sdw/spec.json' in how
    assert P._int_lit("32'hfffffff9") == -7 and P._int_lit('-6') == -6 and P._int_lit(3) == 3
