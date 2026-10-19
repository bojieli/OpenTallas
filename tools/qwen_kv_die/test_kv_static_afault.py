"""RTL-BUILD-KV/FAULT 10-18 (lanes/RTL-BUILD-KV.md P7 / P8): the attention unit-fault tree and the capability bit on the
static KV die are wired exactly as the fleet bench vehicles assume (rtl/test/qwen_static_kv/tb_qkd_attn_fault_tree.sv,
tb_kv_die_cfg_boot.sv CAP=1).  Needs the static die env (kvj-g2-env.sh + OT_KV_HROOT=1 OT_KV_FANFOLD=1); skipped otherwise."""
import os
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kv_static_die as S  # noqa: E402

pytestmark = pytest.mark.skipif(not S.AFAULT, reason='needs OT_KV_STATIC_DIE=1 + PVFIN + OT_KV_HROOT=1 OT_KV_FANFOLD=1')


class _Stop(Exception):
    pass


@pytest.fixture(scope='module')
def die():
    import kv_die as K
    keep = K._relays
    box = {}

    def stop(m):
        box['m'] = m
        raise _Stop()
    K._relays = stop
    K.HOST_V14.update(on=True, north=True, trees=True)
    K.V143['on'] = True
    try:
        K.build(K.R, kv_wq_leaves=True, kv_wq_binary=True, kv_wq_leaf_s=True, kv_wq_wide=True, kv_wq_mirror=True, split=True)
    except _Stop:
        pass
    finally:
        K._relays = keep
    return box['m']


def test_graph_nodes_and_face():
    I = S.ins()
    for st in S.STACKS:
        for s_, g in enumerate(S.ORDER):
            n = I[f'af_{st}_{g}']
            assert n['module'] == 'qkd_kv_cfault_node' and n['parameters'] == dict(R=2 if s_ == 0 else 3, STAGES=1, MUT=0)
            assert S.cluster_of(n['name']) == (f'slg_{st}_{g}', 'grp', 'af')
    assert I['afr']['parameters'] == dict(ND=8, NC=4, MUT=0)
    assert I['attn_face']['inputs']['unit_fault'] == [dict(instance='afr', port='unit_fault', lo=0, width=10)]
    for n in ('attention_programme', 'attn_root'):     # P8
        assert I[n]['inputs']['fused_program_capability'] == [dict(instance='diecfg', port='fused_program_capability',
                                                                   lo=0, width=1)]


def test_tile_rtl_wiring():
    txt = (S.ROOT / S.RTL_FILE).read_text()
    mods = dict(re.findall(r'module (\w+) \((.*?)endmodule', txt, re.S))
    grp, grh, attn = mods['qkd_kvs_grp'], mods['qkd_kvs_grp_h'], mods['qkd_kvs_attn']
    assert 'qkd_kv_cfault_node #(.R(3), .STAGES(1), .MUT(0)) u_af (.ck(af__ck), .rst_n(rst_n), .fault_in({afu, afv, afk}), ' \
           '.fault(w_af__fault));' in grp
    assert 'qkd_kv_cfault_node #(.R(2), .STAGES(1), .MUT(0)) u_af (.ck(af__ck), .rst_n(rst_n), .fault_in({afv, afk}), ' \
           '.fault(w_af__fault));' in grh
    for t in (grp, grh):
        assert 'assign af__fault = w_af__fault;' in t
    assert ('qkd_attn_fault_root #(.ND(8), .NC(4), .MUT(0)) u_afr (.ck(afr__ck), .rst_n(rst_n), .d({uff, ufp1, ufp0, ufh, '
            'ufs_EN, ufs_ES, ufs_WN, ufs_WS}), .c({ufk_EN, ufk_ES, ufk_WN, ufk_WS}), .unit_fault(w_afr__unit_fault));') in attn
    assert '.unit_fault(w_afr__unit_fault[9:0])' in attn
    assert re.search(r'wire \[0:0\] attn__fused_program_capability = i_ctl\[\d+:\d+\];', attn)   # P8: from kvs_ctl
    assert attn.count('.fused_program_capability(attn__fused_program_capability)') == 2           # programme + root
    rec = S.record(dict(relay_stages={}, static_die={}))
    assert not [o for o in rec['open_tile_inputs'] if o['master'] in ('qkd_kvs_attn', 'qkd_kvs_grp', 'qkd_kvs_grp_h')]


def test_die_buses_match_the_bench_vehicle(die):
    B = {b[0]: b for b in die['buses']}
    fk = die['forks']
    for st in S.STACKS:
        for s_, g in enumerate(S.ORDER):
            gd = f'slg_{st}_{g}'
            assert B[f'ks_afk_{st}_{g}'][3] == [(f'ectl_{st}_{S.ectl_frame(g)}', 'kf'), (gd, 'afk')]
            if s_:
                assert B[f'ks_afc_{st}_{s_}'][3] == [(f'slg_{st}_{S.ORDER[s_ - 1]}', 'af__fault'), (gd, 'afu')]
        for k in range(4):
            assert B[f'ks_afv_{st}_{k}'][3] == [(f'vport_{st}_{k}', 'f'), (f'slg_{st}_{2 * k}', 'afv')]
            assert fk[f'ks_afv_{st}_{k}'] == [(f'slg_{st}_{2 * k + 1}', 'afv')]
        assert B[f'ks_afe_{st}'][3] == [(f'slg_{st}_{S.ORDER[7]}', 'af__fault'), ('kvs_attn', f'ufk_{st}')]
        assert ('kvs_attn', f'ufs_{st}') in fk[f'af_{st}'] and B[f'af_{st}'][3][0] == (f'astk_{st}', 'af')
    assert ('kvs_attn', 'ufh') in fk['hf'] and B['hf'][3][0] == ('ahub', 'hf')
    assert B['ks_af_ufp0'][3] == [('pvw_0', 'pf'), ('kvs_attn', 'ufp0')]
    assert B['ks_af_ufp1'][3] == [('pvw_1', 'pf'), ('kvs_attn', 'ufp1')]
    assert B['ks_af_uff'][3] == [('pvfin', 'ff'), ('kvs_attn', 'uff')]
    import kv_die as K
    assert K.SPLIT_BINDINGS['qkd_pvw_s']['ports']['pf'] == ['fault']        # 1-b pair fault word
    # every source reaches exactly one lane; the latency formula is complete once stages exist
    m = dict(die, relay_stages={b: 1 for b in B}, fork_stages={f'{b}__f{i}': 1 for b, v in fk.items() for i in range(len(v))})
    lat = S.afault_latency(m)
    assert len(lat['leaves']) == 56 and all(v['latency'] is not None for v in lat['leaves'].values())
    assert sorted({v['lane'] for v in lat['leaves'].values()}) == list(range(10))
