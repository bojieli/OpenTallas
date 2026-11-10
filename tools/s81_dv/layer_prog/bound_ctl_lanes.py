"""S81-PLAN-1 (11-10): bound depths for the S81 statically scheduled CONTROL lanes.

S81 control is a static schedule (no ready, no back-pressure; violations are sticky faults), so every compiler term that
dates a control word across a die lane must use the lane's BOUND depth: the stages the strict bind actually emits
(plan boundary flops + feed-through stations + relay_bay built stations + clock landing), never an as-built or legacy
constant.  This module (layer_prog/bound_ctl_lanes.py) is the one place those depths are read for the 30 control lanes that TYPE-SAFE-5 (11-10 06:25)
found with no bind reader.  It reads ONE bind_latency.json and fails closed when a lane is missing, unbound, or its
bound stages differ from the plan cycles the bind was made from.

Readers (who consumes each age):
  idx / TP4 / query (lower_bk):  tree legs (tl + ca/cb), query fan-out offset (qc + ql), TP4 per-hop ages (tp x4),
                                 index-score chain arrival (idx__svc_14__bk_sel) and iq frame arrival (idx__s_3S_C__iqf)
  MU HWIN (native_hwin_calendar): mu_c / mu_rc out to each end LP (unit__seqhost__s_*_LP) and the mu_rt return
                                 (ctrl__s_0N_LP__seqhost, unit__s_7N_LP__seqhost): the consumer booking's
                                 transport_edges and the RX live-window check
  svc unit (lower_svc):          j / jd ages also come from the bound die links (dv_layer_compile --bound-data,
                                 bound_data.rebind_links jw_*/jd_*); bound_ctl cross-checks them against the bind
  seqhost <-> hub C / gunit / eng: dv_layer_compile --bound-data re-ages the legacy die links (hbc_forward_*, cw_seqhost,
                                 eks_7N); this module lists them so the class map is complete
"""
from __future__ import annotations

import json
from pathlib import Path

LEG_CORE = 729        # lower_bk.LEG: the legacy cross-die idx leg, measured with every on-die idx lane at depth 0

# lane -> (reader, role).  Every lane here is statically scheduled control or a 1-bit level.
LANES = {
    'tl__bk_sel__s_0N_LP': ('lower_bk tree leg', 'child tree beat bk_sel -> s_0N lep'),
    'ca__s_0N_LP__bk_sel': ('lower_bk tree leg', 'parent: pair-B frames -> ca (child lane 2)'),
    'cb__s_0N_LP__bk_sel': ('lower_bk tree leg', 'parent: pair-A frames -> cb (child lane 3)'),
    'qc__iqf__s_0N_LP': ('lower_bk query fan-out', 'root iqf Q word -> lep Q frame'),
    'ql__s_0N_LP__iqf': ('lower_bk query fan-out', 'received Q word lep -> iqf'),
    'tp__bk_sel__s_7N_LP': ('lower_bk TP4 hop', 'bk_sel tpn_o -> s_7N lep tp_i'),
    'tp__bk_sel__s_7S_LP': ('lower_bk TP4 hop', 'bk_sel tps_o -> s_7S lep tp_i'),
    'tp__s_0S_LP__s_0N_LP': ('lower_bk TP4 hop', 's_0S lep tp_o -> s_0N lep tm'),
    'tp__s_7N_LP__bk_sel': ('lower_bk TP4 hop', 's_7N lep tp_o -> bk_sel tpn_i'),
    'idx__svc_14__bk_sel': ('lower_bk index chain', 'score chain tail u_irg_07.so -> bk_sel vi_idx'),
    'idx__s_3S_C__iqf': ('lower_bk index chain', 'iq frames s_3S hub -> iqf'),
    'unit__seqhost__s_0N_LP': ('native_hwin_calendar transport', 'mu_c / mu_rc -> s_0N'),
    'unit__seqhost__s_0S_LP': ('native_hwin_calendar transport', 'mu_c / mu_rc -> s_0S'),
    'unit__seqhost__s_7N_LP': ('native_hwin_calendar transport', 'mu_c / mu_rc -> s_7N (rides ht_7N)'),
    'unit__seqhost__s_7S_LP': ('native_hwin_calendar transport', 'mu_c / mu_rc -> s_7S'),
    'ctrl__s_0N_LP__seqhost': ('native_hwin_calendar RX window', 'mu_rt s_0N -> seqhost'),
    'unit__s_7N_LP__seqhost': ('native_hwin_calendar RX window', 'mu_rt / f_lf s_7N -> seqhost (rides hf_7N)'),
    'unit__seqhost__s_0N_C': ('dv_layer_compile --bound-data (hbc_reverse_l0)', 't_kd / hb starter / alive -> s_0N hub'),
    'ctrl__s_0N_C__seqhost': ('dv_layer_compile --bound-data (hbc_forward_l*)', 'f_host / ks_descriptor -> seqhost'),
    'unit__seqhost__gunit': ('dv_layer_compile --bound-data (cw_seqhost)', 'gunit cw_a/d/v'),
    'unit__seqhost__eng': ('dv_layer_compile --bound-data (eks_7N)', 'engram_f_ks'),
    'unit__seqhost__svc_5': ('lower_svc j_w (jw_W_l*)', 's_hw / s_j -> svc_5'),
    'unit__seqhost__svc_11': ('lower_svc j_e (jw_E_l*)', 's_hw / s_j -> svc_11'),
    'unit__svc_5__seqhost': ('lower_svc jd_w (jd_W)', 'hc / st_rg / jd svc_5 -> seqhost'),
    'unit__svc_11__seqhost': ('lower_svc jd_e (jd_E)', 'hc / st_rg / jd svc_11 -> seqhost'),
    'attn__svc_5__s_3S_C': ('pv_v valid-qualified (compose svc_to_hub)', 'pv_v / pv_d / pv_x -> hub'),
    'attn__svc_11__s_4S_C': ('pv_v valid-qualified (compose svc_to_hub)', 'pv_v / pv_d / pv_x -> hub'),
    'flt__gunit__s_3N_C': ('level (sticky fault)', 'fault level'),
    'vid_svc_1__seqhost': ('level (fault relay fo)', 'fault relay level'),
    'vid_seqhost__svc_0': ('level (vid_ro alive)', 'alive level'),
}
TIMED = {k for k, (r, _) in LANES.items() if not r.startswith(('level', 'pv_v valid'))}


def load(bind):
    """{lane: bound_stages} from a bind out dir, a bind_latency.json path or its parsed dict (fail closed)"""
    if isinstance(bind, (str, Path)):
        p = Path(bind)
        bind = json.loads((p / 'bind_latency.json' if p.is_dir() else p).read_text())
    out = {}
    for b in bind.get('buses', []):
        lane = b.get('lane')
        if lane in LANES:
            st, pc = b.get('bound_stages'), b.get('plan_cycles')
            if type(st) is not int or st != pc:
                raise ValueError(f'{lane}: bound_stages {st} != plan_cycles {pc} (bind not made from this plan)')
            out[lane] = st
    miss = sorted(set(LANES) - set(out))
    if miss:
        raise ValueError(f'bind lacks control lanes {miss[:6]}')
    return out


def idxnet(ages, link_core=LEG_CORE):
    """the idx / TP4 / query schedule terms lower_bk compiles from (all in edges)"""
    a = ages
    return dict(
        tree_legs={2: link_core + a['tl__bk_sel__s_0N_LP'] + a['ca__s_0N_LP__bk_sel'],
                   3: link_core + a['tl__bk_sel__s_0N_LP'] + a['cb__s_0N_LP__bk_sel']},
        # the query reaches a die at depth h hop by hop: each hop = parent iqf -> qc -> lep, link core, lep -> ql -> iqf
        # (the per-hop relay form: a lep cut-through would be shorter; the static start is then late, never early)
        query_lane=a['qc__iqf__s_0N_LP'] + a['ql__s_0N_LP__iqf'],
        tp4_hops={k: a[k] for k in ('tp__bk_sel__s_7N_LP', 'tp__bk_sel__s_7S_LP', 'tp__s_0S_LP__s_0N_LP',
                                    'tp__s_7N_LP__bk_sel')},
        idx_chain=dict(vi_idx=a['idx__svc_14__bk_sel'], iq=a['idx__s_3S_C__iqf']),
        link_core=link_core)


def tp4_on_die(terms):
    """on-die TP4 transport the all-gather adds around the cross-die merge window: the longest bk_sel -> end-lep out hop
    plus the longest end-lep -> bk_sel in path (s_7N lep -> bk_sel tpn_i, or s_0S lep -> s_0N lep tm).  Static: the
    final select issues after the slowest copy lands."""
    h = terms['tp4_hops']
    return (max(h['tp__bk_sel__s_7N_LP'], h['tp__bk_sel__s_7S_LP']) +
            max(h['tp__s_7N_LP__bk_sel'], h['tp__s_0S_LP__s_0N_LP']))


def query_offset(terms, depth):
    """edges from the root's reader start to a depth-h die's reader start (0 at the root)"""
    return depth * (terms['link_core'] + terms['query_lane'])


def mu_transport(ages):
    """per end LP: mu_c / mu_rc transport (seqhost pin -> LP) and the mu_rt return where it has its own lane"""
    out = {ep: dict(out=ages[f'unit__seqhost__s_{ep}_LP']) for ep in ('0N', '0S', '7N', '7S')}
    out['0N']['ret'] = ages['ctrl__s_0N_LP__seqhost']
    out['7N']['ret'] = ages['unit__s_7N_LP__seqhost']
    return out


def hwin_bound_transport(ages):
    """native_hwin_calendar.check_consumer_book(bound_transport=...): {'s_0N': edges, ...}"""
    return {'s_' + ep: t['out'] for ep, t in mu_transport(ages).items()}


def check_rx_window(mu_t, turnaround, return_latency):
    """the mu_rt of a kind-0 event must be sampled inside (KS, KS + return_latency): out + turnaround + ret + 1 < RL"""
    bad = {}
    for ep, t in mu_t.items():
        if 'ret' in t and t['out'] + turnaround + t['ret'] + 1 > return_latency - 1:
            bad[ep] = t['out'] + turnaround + t['ret'] + 1
    return bad


SVC_LINKS = dict(jw_W_l0='unit__seqhost__svc_5', jw_W_l1='unit__seqhost__svc_5', jw_E_l0='unit__seqhost__svc_11',
                 jw_E_l1='unit__seqhost__svc_11', jd_W='unit__svc_5__seqhost', jd_E='unit__svc_11__seqhost')


def svc_cross_check(ages, die_links):
    """lower_svc reads j / jd from the die links that bound_data.rebind_links re-aged from this bind: every one must be
    re-aged (a blocked link would leave the legacy constant 34 / 24 / 32 / 25), and its age may not exceed the lane's
    bound depth (age = bound depth - in-instance stages >= 0).  Returns {link: problem}."""
    bad = {}
    for lk, lane in SVC_LINKS.items():
        L = die_links.get(lk)
        if L is None:
            bad[lk] = 'link missing'
            continue
        got = L.get('age_edges') if 'age_edges' in L else None
        if got is None or 'legacy_age_edges' not in L:
            bad[lk] = 'not re-aged from the bind (blocked or legacy)'
        elif not 0 <= got <= ages[lane]:
            bad[lk] = f'age {got} outside [0, bound depth {ages[lane]}]'
    return bad
