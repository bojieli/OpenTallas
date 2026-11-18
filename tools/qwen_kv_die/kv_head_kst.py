#!/usr/bin/env python3
"""KV-KT-E0 2026-11-18 (FABLE-FIX-KV-HG fix #2, KV event D25): the head kt input stations as ONE number.

A native KV head adds its 16 lanes in one K-tree (u_kt) that sits in the eighth core e0; the other seven eighths send
their lanes' stk outputs (kp 32 + kpv + gf) 1.1 - 1.8 mm across the hg / hgi parent, unregistered (192+ setup ends at
-251 ps).  The fix is a uniform register depth KST on ALL 16 lanes between u_stk and u_kt:

  RTL      ot_qkh_head_native_r4*_kst #(.KT_ST(KST)): two named leaves a lane, g_t[t].u_kst0 / u_kst1
           (ot_qkh_head_kst_native; tools/qwen_kv_die/head_st_rtl.py generates the heads)
  die      physical/die_plan/qwen_kvsys/bind/kv45/kv_head_kst_netlist.py derives the bound netlist with the leaves
           head_<st>_<e>_<h>__g_t_<t>__u_kst<k> (lanes 2..15: hg / hgi parent cells; lanes 0, 1: members of e0)
  e0 core  gen_core_kit_kv.py --head-kst KST (the two in-core lanes)

The score sc_d / sc_f / g_f then leaves the head KST edges later, and two constants follow (laws below; lock-step
rtl/test/qwen_kv_die/tb_qkh_kst_ectl.sv: tags and scores meet again, KST edges later, only with HXK + KST):

  HXK      the control tile's score tag depth (qkd_ectl3_kiss_st HXK, ECTLK quarter cores): + KST
  D_QK     the attention calendar's QK half (LMAX .. HUB_PUB += D_QK, boot word cfg_cal): + KST

Both are read through kv_qkh_safe32.capture_hxk() / calendar_d_qk(), which add depth() to the QKH safe32 data edges (the
same law: edges on the lane -> score path).  Selected by OT_KV_HEAD_KST (default 0 = byte-identical outputs everywhere).
"""
import os

FLAG = 'OT_KV_HEAD_KST'
DEPTHS = (0, 1, 2)             # the head RTL fails elaboration on anything else
LANES = 16
E0_LANES = (0, 1)              # the lanes whose stk sits in the eighth core that holds u_kt
BITS = 34                      # kp 32 + kpv + gf
STAGES = ('u_kst0', 'u_kst1')
# sited by the relay-chain placer (tools/die_plan/gen_phys.py RELAY_MID_RE_KV + this alternative): group = the lane's chain
RELAY_MID_RE_ALT = r'.*[._]u_head[0-9]+_g_t_[0-9]+_u_kst[0-9]+'


def depth(env=None):
    """the kt station depth selected by OT_KV_HEAD_KST (0 when unset)"""
    v = (os.environ if env is None else env).get(FLAG, '0')
    try:
        d = int(v)
    except ValueError:
        raise ValueError(f'{FLAG}={v!r}: an integer in {DEPTHS}')
    if d not in DEPTHS:
        raise ValueError(f'{FLAG}={d}: the head stations are {DEPTHS} stages')
    return d


def hxk(base, kst=None):
    """control-tile score tag depth for a head with kst stations"""
    return base + (depth() if kst is None else kst)


def d_qk(base, kst=None):
    """attention calendar D_QK for a head with kst stations"""
    return base + (depth() if kst is None else kst)


def leaves(kst):
    """[(lane, stage leaf name, in_e0)] of one head at depth kst, in lane / stage order"""
    if kst not in DEPTHS:
        raise ValueError(f'kt station depth {kst} not in {DEPTHS}')
    return [(t, STAGES[k], t in E0_LANES) for t in range(LANES) for k in range(kst)]


def flops(kst, heads=1):
    """{'parent': n, 'e0': n} register bits the stations add for `heads` heads"""
    lv = leaves(kst)
    return dict(parent=BITS * heads * sum(1 for _, _, e in lv if not e), e0=BITS * heads * sum(1 for _, _, e in lv if e))


if __name__ == '__main__':
    import json
    d = depth()
    print(json.dumps(dict(flag=FLAG, depth=d, hxk_bound_die=hxk(13), d_qk_delta=d_qk(0), flops_per_head=flops(d),
                          relay_mid_re_alt=RELAY_MID_RE_ALT), indent=1))
