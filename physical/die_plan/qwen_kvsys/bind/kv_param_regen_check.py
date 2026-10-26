#!/usr/bin/env python3
"""KV-P5-PR 10-23: evaluate the KV parameter <-> lane rules (kv_param_rules_v35.json) on a BINDER bind dir.

    kv_param_regen_check.py BIND_DIR [--rules RULES.json] [--write-rules OUT.json] [--json OUT]

Inputs (BIND_DIR): bind_latency.json (per crossing bus: asbuilt_stages [min,max] vs bound_stages) and bus_groups.json
(landing members: per source pin -> sink leaf.port, the FULL-PATH as-built stages and the bound depth incl. forwarded
hops), rtl/kv3_*.sv (the as-built hard parameter values the partitions still carry).

Every rule is a hard static-schedule age (RTL parameter, boot register or programme constant) whose value encodes a
crossing depth.  The bound top replaces the as-built relays by plan lanes, so each age is regenerated from the bound
depths with the formula of its generator (tools/qwen_kv_die kv_static_die KVR-DERIVE / kv_static_ages / pv_trunk_gen /
ahub_ages / kv_static_programme).  Where a formula needs a value to be EQUAL across instances that the lanes no longer
keep equal (type parameters, one broadcast source, balanced trunks), the rule reports the pad flops that restore it.
Exit 1 when any rule violates an RTL bound or needs pads (a blocker for asbuilt.param_regen as-is).
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

STACKS = ('WS', 'WN', 'ES', 'EN')          # qkd_ahub_static_dw stack order (AP_OFS[16*k +: 16] = stack k)
LANDING_SEG = 8                            # qkd_static_kv_landing_seg K request -> response edges
VPORT_RT_SEG = 9                           # landing seg vreq capture 1 + VREQ 8 (kv_static_die VPORT_RT_SEG)
VPORT_RL_BASE = 4                          # qkd_pv16_vport: RL = 4 + W + DQ + RT; pair FIRST_INPUT_AGE = RL + 1
QK_WRITE_BEFORE_READ = 11                  # static_qk_calendar write-before-read
QK_ISSUE_AGE_KIT = 34                      # kv_static_ages.QK_ISSUE_AGE_KIT (attn calendar QK_CONSUME floor)


class Bind:
    def __init__(self, d):
        self.dir = Path(d)
        self.buses = json.load(open(self.dir / 'bind_latency.json'))['buses']
        self.landing = json.load(open(self.dir / 'bus_groups.json'))['landing']
        self.rtl = {f.name: f.read_text() for f in sorted((self.dir / 'rtl').glob('kv3_*.sv'))}

    def bus(self, leaf, src=None, dst=None):
        return [b for b in self.buses if re.search(leaf, ' '.join(b['leaves']))
                and (src is None or re.match(src, b['src'])) and (dst is None or re.match(dst, b['dst']))]

    def paths(self, source, sink=None, port=None):
        """landing members: dict(source, sink, port, sink_part, src_part, asb, bound, bits)"""
        out = []
        for x in self.landing:
            if sink and not re.search(sink, x['sink']):
                continue
            for m in x['members']:
                if re.search(source, m['source']) and (port is None or re.search(port, m['sink_port'])):
                    out.append(dict(source=m['source'], sink=x['sink'], port=m['sink_port'], sink_part=x['sink_part'],
                                    src_part=x['src_part'], asb=m['asbuilt_stages'], bound=m['bound_stages'],
                                    bits=sum(b - a + 1 for a, b in m['sink_bits'])))
        return out

    def param(self, module, name):
        """as-built value(s) of a leaf parameter in the partitions: {value: [file:inst]}"""
        out = collections.defaultdict(list)
        for f, t in self.rtl.items():
            for m in re.finditer(r'\b' + module + r'\s*#\s*\((.*?)\)\s*(\w+)\s*\(', t, re.S):
                v = re.search(r'\.' + name + r'\(([^)]*)\)', m.group(1))
                if v:
                    out[v.group(1)].append(f'{f}:{m.group(2)}')
        return dict(out)


def sv_int(s):
    s = s.strip()
    m = re.fullmatch(r"(\d+)'([bhd])([0-9a-fA-F_]+)", s)
    if m:
        w, b, v = int(m.group(1)), m.group(2), m.group(3).replace('_', '')
        return int(v, dict(b=2, h=16, d=10)[b]), w
    return int(s), None


def s16(x):
    x &= 0xffff
    return x - 0x10000 if x & 0x8000 else x


def delta(p):
    return p['bound'] - p['asb']


# ------------------------------------------------------------------------------------------------------------- rules
def r_ectl(B):
    rq = {b['src']: b for b in B.bus(r'ectl_\w+\.req_')}
    rs = {b['dst']: b for b in B.bus(r'slg_\w+\.krsp')}
    fr = {}
    for hg in sorted(rq):
        a, c = rq[hg], rs[hg]
        fr[hg] = dict(krq=a['bound_stages'], krs=c['bound_stages'], krq_asb=a['asbuilt_stages'][1], krs_asb=c['asbuilt_stages'][1],
                      rt=LANDING_SEG + a['bound_stages'] + c['bound_stages'], rt_asb=LANDING_SEG + a['asbuilt_stages'][1] + c['asbuilt_stages'][1],
                      krq_lane=a['lane'], krs_lane=c['lane'], krq_bits=a['width'])
    rts = sorted({v['rt'] for v in fr.values()})
    rl = max(rts)
    pads = sum((rl - v['rt']) * v['krq_bits'] for v in fr.values())
    asb = B.param('qkd_ectl3_kiss_st', 'RESPONSE_LAT')
    qk_asb = B.param('qkd_ectl3_kiss_st', 'QK_ISSUE_AGE')
    qk = max(QK_ISSUE_AGE_KIT, rl + QK_WRITE_BEFORE_READ)
    viol = [] if rl >= 1 else ['RESPONSE_LAT < 1 (qkd_static_k_issuer $fatal)']
    common = dict(module='qkd_ectl3_kiss_st', instances_regex=r'kv3_hg(_v\d)?_part(_v\d)?\.sv:u_ectl', kind='type',
                  buses=[dict(name='krq', src='hg_<st>_<r>', dst='pc_<st>_<r>', leaf_regex=r'ectl_\w+\.req_'),
                         dict(name='krs', src='pc_<st>_<r>', dst='hg_<st>_<r>', leaf_regex=r'slg_\w+\.krsp')])
    return [dict(common, param='RESPONSE_LAT', formula='8 (landing seg) + D(krq) + D(krs), identical on all 32 frames (one per hg '
                 'partition; children of qkd_ectl3_kiss_st take it as a parameter); a frame below the max pads its krq chain',
                 asbuilt=sorted(int(k) for k in asb), regen_kv35=rl, per_instance={k: v['rt'] for k, v in fr.items()},
                 asbuilt_natural=sorted({v['rt_asb'] for v in fr.values()}), pad_flops=pads, bound_ok=not viol, violations=viol,
                 note=f'bound round trips {rts} (uniform: no krq pads); as-built frames were padded to 80 (krq pad relays '
                      'removed by the bind). RTL bound RESPONSE_LAT >= 1.'),
            dict(common, param='QK_ISSUE_AGE', formula='max(34, RESPONSE_LAT + 11)  (static_qk_calendar write-before-read: write '
                 '7 + (seg + 2) + s < read age - 1 + s; 34 = attn calendar QK_CONSUME / bench ECTL A floor, kv_static_ages.derive)',
                 asbuilt=sorted(int(k) for k in qk_asb), regen_kv35=qk, bound_ok=qk >= 2 and qk >= rl + QK_WRITE_BEFORE_READ,
                 violations=[] if qk >= 2 else ['QK_ISSUE_AGE < 2'],
                 note='ot_qkd_ectl_part STATIC_QK requires QK_ISSUE_AGE >= 2; kv_static_die uses RESPONSE_LAT + 11 (= '
                      f'{rl + QK_WRITE_BEFORE_READ}, also legal); 34 keeps the compiled attention calendar D_QK floor. The compiler '
                      '(kv_static_programme qk_age / calendar_d_qk) must be re-run with the same value.'),
            dict(common, param='ROW_RETURN_LAT (localparam RRL)', formula='RESPONSE_LAT + 7 (derived inside qkd_ectl3_kiss_st; not '
                 'a bound parameter)', asbuilt=[int(k) + 7 for k in asb], regen_kv35=rl + 7, bound_ok=rl + 7 >= 1, violations=[],
                 note='follows RESPONSE_LAT automatically; listed so the compiler row_latency_for_calendar (= RL + 2) is regenerated.')]


def r_vport(B):
    rows = {}
    vq = B.bus(r'vport_\w+\.vq')
    vr = B.bus(r'slg_\w+\.rsp', dst='pv')
    for a in vq:
        vp = re.search(r'(vport_\w+?)\.vq', ' '.join(a['leaves'])).group(1)
        for c in [x for x in vr if x['src'] == a['dst'] and x['dst'] == a['src']]:
            r = rows.setdefault(vp, dict(rt=[], rt_asb=[]))
            r['rt'].append(VPORT_RT_SEG + a['bound_stages'] + c['bound_stages'])
            r['rt_asb'].append(VPORT_RT_SEG + a['asbuilt_stages'][1] + c['asbuilt_stages'][1])
    W = {p['sink']: p for p in B.paths(r'pvw_\d__u_ctl\.req_t', sink=r'^vport_', port='pr_t')}
    out = {}
    for vp, r in sorted(rows.items()):
        w = W.get(vp)
        out[vp] = dict(RT=max(r['rt']), RT_asb=max(r['rt_asb']), W=w['bound'] if w else None, W_asb=w['asb'] if w else None)
    rl_core = max(v['RT'] + v['W'] for v in out.values())
    for v in out.values():
        v['DQ'] = rl_core - (v['RT'] + v['W'])
    rt_v = [f'{k}: RT {v["RT"]} > 31' for k, v in out.items() if v['RT'] > 31]
    dq_v = [f'{k}: DQ {v["DQ"]} > 15' for k, v in out.items() if v['DQ'] > 15]
    fia = VPORT_RL_BASE + rl_core + 1
    buses = [dict(name='vq_g', src='pv_<s>_<k>', dst='pc_<st>_<g>', leaf_regex=r'vport_\w+\.vq[01]_'),
             dict(name='rs_g', src='pc_<st>_<g>', dst='pv_<s>_<k>', leaf_regex=r'slg_\w+\.rsp'),
             dict(name='W (ctl req -> vport pr_t, full path incl. forwarded hops)', src='hub_C', dst='pv_<s>_<k>',
                  leaf_regex=r'pvw_\d__u_ctl\.req_t -> vport_*.pr_t (bus_groups landing)')]
    rt_bound = B.param('qkd_pv16_vport_b', 'RT')
    dq_bound = B.param('qkd_pv16_vport_b', 'DQ')
    fia_bound = B.param('ot_qwen_tp8_pv_wide_ctl_tbf', 'FIRST_INPUT_AGE')
    pads = sum(max(0, v['DQ'] - 15) for v in out.values())
    return [dict(param='RT (boot cfg_age)', module='qkd_pv16_vport_b', instances_regex=r'kv3_pv(_v\d+)?_part(_v\d)?\.sv:u_vport_[EW]',
                 kind='boot', formula='9 + max_g(D(vq_g) + D(rs_g)) per V port (both groups); boot image value (the RTL RT '
                 'parameter is the upper bound 31)', buses=buses[:2], asbuilt={k: v['RT_asb'] for k, v in out.items()},
                 asbuilt_param_bound=sorted(int(k) for k in rt_bound), regen_kv35={k: v['RT'] for k, v in out.items()},
                 bound_ok=not rt_v, violations=rt_v, note='per instance (boot register via kvs_ctl.dcfg age_vport); RT <= 31.'),
            dict(param='DQ (boot cfg_age)', module='qkd_pv16_vport_b', instances_regex=r'kv3_pv(_v\d+)?_part(_v\d)?\.sv:u_vport_[EW]',
                 kind='boot', formula='DQ_p = max_q(W_q + RT_q) - (W_p + RT_p)  (RL = 4 + W + DQ + RT equal on all 16 ports)',
                 buses=buses, asbuilt_param_bound=sorted(int(k) for k in dq_bound),
                 asbuilt={k: None for k in out}, W_bound={k: v['W'] for k, v in out.items()}, W_asbuilt={k: v['W_asb'] for k, v in out.items()},
                 regen_kv35={k: v['DQ'] for k, v in out.items()}, pad_flops_if_dq_capped=pads * 15,
                 bound_ok=not dq_v, violations=dq_v,
                 note='DQ <= 15 (RTL bound). A port with DQ > 15 needs (DQ - 15) pad stages on its W request lane '
                      '(pr_t 14 b + pr_valid 1 b) or a plan lane change; as-built DQ values live in the old boot image (not in the bind dir).'),
            dict(param='cfg_fia (boot; FIRST_INPUT_AGE = upper bound)', module='ot_qwen_tp8_pv_wide_ctl_tbf',
                 instances_regex=r'kv3_hub_C_part\.sv:u_pv[NS]_u_ctl', kind='boot',
                 formula='4 + W + DQ + RT + 1 = 4 + max_p(W_p + RT_p) + 1 (one value, both pair controls)', buses=buses,
                 asbuilt_param_bound=sorted(int(k) for k in fia_bound), asbuilt=None, regen_kv35=fia,
                 bound_ok=1 <= fia <= 127, violations=[] if 1 <= fia <= 127 else [f'cfg_fia {fia} outside 1..127'],
                 note='boot-loaded cfg_fia[7:0]; 1 <= cfg_fia <= FIRST_INPUT_AGE (127) else a start faults. The parameter '
                      'FIRST_INPUT_AGE 127 stays (bound); only the boot image value is regenerated.')]


def r_pv_trunk(B):
    res = []
    for side, pvw in (('S', 'pvw_0'), ('N', 'pvw_1')):
        cmd = collections.defaultdict(set)
        for p in B.paths(pvw + r'__u_ctl\.cmd', port='join_go'):
            cmd[int(re.search(r'_s(\d+)_j', p['sink']).group(1))].add((p['asb'], p['bound'], p['sink_part']))
        flg = collections.defaultdict(set)
        for p in B.paths(pvw + r'__u_s\d+_j\.(y_valid|fault)', port='col_(valid|fault)'):
            flg[int(re.search(r'_s(\d+)_j', p['source']).group(1))].add((p['asb'], p['bound']))
        cols = {}
        for s in sorted(cmd):
            (ca, cb, part), = cmd[s]
            (fa, fb), = flg[s]
            cols[s] = dict(part=part, cmd_asb=ca, cmd=cb, flag_asb=fa, flag=fb, tot_asb=ca + fa, tot=cb + fb,
                           dcmd=cb - ca, dflag=fb - fa)
        res.append((side, cols))
    td = B.param('ot_qwen_tp8_pv_wide_ctl_tbf', 'TRUNK_D')
    fd = B.param('ot_qwen_tp8_pv_wide_ctl_tbf', 'FLAG_D')
    TD, FD = int(next(iter(td))), int(next(iter(fd)))
    regen, pads_cmd, pads_flag, viol, per = {}, 0, 0, [], {}
    for side, cols in res:
        c0 = cols[0]
        dc_max = max(v['dcmd'] for v in cols.values())                 # equalise the command Delta (column ages)
        pc = sum((dc_max - v['dcmd']) * 33 for v in cols.values())     # {rst_n, cmd[31:0]} per column join
        tot = {s: v['tot'] + (dc_max - v['dcmd']) for s, v in cols.items()}
        tmax = max(tot.values())
        pf = sum((tmax - t) * 2 for t in tot.values())                 # y_valid + fault per column
        trunk = TD + dc_max
        flag = tmax - (c0['tot_asb'] - FD - TD) - trunk                 # as-built pin offset (D+R - TRUNK_D - FLAG_D) kept
        regen[side] = dict(TRUNK_D=trunk, FLAG_D=flag)
        pads_cmd += pc
        pads_flag += pf
        per[side] = {s: dict(part=v['part'], dcmd=v['dcmd'], dflag=v['dflag'], tot_asb=v['tot_asb'], tot_bound=v['tot'])
                     for s, v in sorted(cols.items())}
        if trunk < 0 or flag < 0:
            viol.append(f'{side}: TRUNK_D {trunk} / FLAG_D {flag} < 0')
    same = len({json.dumps(v, sort_keys=True) for v in regen.values()}) == 1
    if not same:
        viol.append(f'pvN/pvS ctl need different TRUNK_D/FLAG_D {regen} (one partition type: straps or split)')
    buses = [dict(name='cmd trunk', src='hub_C', dst='pv_<N|S>_<r>', leaf_regex=r'pvw_\d__u_ctl\.cmd -> pvw_*_s<c>_j.join_go'),
             dict(name='column flags', src='pv_<N|S>_<r>', dst='hub_C', leaf_regex=r'pvw_\d__u_s<c>_j\.(y_valid|fault)')]
    r0 = regen['S']
    common = dict(module='ot_qwen_tp8_pv_wide_ctl_tbf', instances_regex=r'kv3_hub_C_part\.sv:u_pv[NS]_u_ctl', kind='type', buses=buses)
    note = ('pv_trunk_gen invariant: every column s sees the command D_s after the ctl pin and its flags return R_s later with '
            'D_s + R_s ONE constant (= TRUNK_D + FLAG_D + const); column outputs sit at A_s = out_age + D_s - D_0 (pvw frame '
            'localparams) and V chunks must arrive D_g - 6 after the header. The bound lanes change D_s by different amounts '
            '(per column Delta in per_column) -> NOT absorbable by TRUNK_D/FLAG_D alone: pad every column command join to the '
            'largest Delta (keeps A_s and the V/command meeting), then pad each flag return to the largest D+R. '
            f'Pads: cmd {pads_cmd} flops, flags {pads_flag} flops (both pair sides). Alternative: re-plan the lanes so '
            'Delta(cmd) is uniform and flag depths R_s = const - D_s (the v35 flag lanes 23..2 run the WRONG way: near columns '
            'need the LONGER flag lanes).')
    return [dict(common, param='TRUNK_D', formula='TRUNK_D_asb + max_s(Delta cmd_s)  (after cmd pads to the max Delta)',
                 asbuilt=TD, regen_kv35=r0['TRUNK_D'], per_column=per, pad_flops=pads_cmd, bound_ok=not viol, violations=viol, note=note),
            dict(common, param='FLAG_D', formula='max_s(D_s + R_s)_bound(after pads) - TRUNK_D - (D+R - TRUNK_D - FLAG_D)_asb',
                 asbuilt=FD, regen_kv35=r0['FLAG_D'], pad_flops=pads_flag, bound_ok=not viol, violations=viol,
                 note='COL_CHK = COL_LAT + TRUNK_D + FLAG_D; see TRUNK_D note.')]


def r_ahub(B):
    asb = B.param('qkd_ahub_static_dw', 'AP_OFS')
    v, w = sv_int(next(iter(asb)))
    ap_asb = {st: s16(v >> (16 * k)) for k, st in enumerate(STACKS)}
    fr_asb = int(next(iter(B.param('qkd_ahub_static_dw', 'FR_OFS'))))
    ap = {}
    for p in B.paths(r'astk_\w+__u_strip_u_strip_u_ctl\.ap$', sink='^ahub$'):
        ap[re.search(r'astk_(\w\w)_', p['source']).group(1)] = p
    lag = {}
    for k, st in enumerate(STACKS):
        f = B.bus(rf'seq__u_core\.f_aqm_{"w" if st[0] == "W" else "e"}')
        lag[st] = f[0]['bound_stages'] - f[0]['asbuilt_stages'][1] if f else 0
    am = {}
    for k, st in enumerate(STACKS):
        p = B.paths(rf'^ahub\.am{k}$', sink=rf'astk_{st}__u_strip_u_strip_u_ctl')
        am[st] = p[0] if p else None
    ap_new = {st: ap_asb[st] + delta(ap[st]) + lag[st] for st in STACKS}
    hexv = '{' + ', '.join(f"16'h{ap_new[st] & 0xffff:04x}" for st in reversed(STACKS)) + '}'
    viol = [f'AP_OFS {st} {x} outside int16' for st, x in ap_new.items() if not -32768 <= x < 32768]
    intra = [b for b in B.bus(r'kvs_attn\.(ahs|pvfst|pvst)|pvfin\.|ahub\.fr') if b['src'] != b['dst']]
    am_lag = {st: (delta(am[st]) - lag[st]) if am[st] else None for st in STACKS}
    common = dict(module='qkd_ahub_static_dw', instances_regex=r'kv3_hub_C_part\.sv:u_ahub', kind='type')
    return [dict(common, param='AP_OFS[stack]', formula='AP_OFS_s = 2 + L_s + D(ap_s) - D(ks_ahs) -> AP_OFS_asb_s + Delta D(ap_s) + '
                 'Delta L_s; L_s = stack start lag = the seq core -> fan aq path (f_aqm_w/e); D(ks_ahs) is intra hub_C (u_d51_kvs_attn_ahs) = unchanged',
                 buses=[dict(name='ap_s', src='hub_Wo|hub_Eo', dst='hub_C', leaf_regex=r'astk_<st>__u_strip_u_strip_u_ctl\.ap'),
                        dict(name='f_aqm (L_s)', src='hub_C', dst='hub_Wo|hub_Eo', leaf_regex=r'seq__u_core\.f_aqm_[we]')],
                 asbuilt=ap_asb, regen_kv35=ap_new, regen_hex=hexv, bound_ok=not viol, violations=viol,
                 note='16-bit two\'s complement per stack (stack order WS WN ES EN = AP_OFS[15:0]..[63:48]); one hub instance -> no '
                      'replica constraint. kv_static_params AHUB_OFS_BOUND must compare against this table, and the hub kit '
                      'qkd_ahub_sdw is re-synthesised at it (G3).'),
            dict(common, param='FR_OFS', formula='D(ks_pvfst) - PV_LEAD - D(ks_ahfr) - D(ks_ahs) - 1; every term is intra hub_C',
                 buses=[], asbuilt=fr_asb, regen_kv35=fr_asb, bound_ok=not intra, violations=[f'crossing on an FR_OFS path: {[b["lane"] for b in intra]}'] if intra else [],
                 note='kvs_attn, ahub, pvfin, pv ctl all sit in hub_C: no lane on any FR_OFS path -> unchanged.'),
            dict(param='am_lag_edges[stack] (compiler EXP_START)', module='kv_static_programme (compiler) / astk cal EXP base',
                 instances_regex='boot image (acal word)', kind='boot', formula='L_h + D(am_s) - L_s -> asb + Delta D(am_s) - Delta L_s',
                 buses=[dict(name='am_s', src='hub_C', dst='hub_Wo|hub_Eo', leaf_regex=r'ahub\.am<k>')],
                 asbuilt=None, regen_kv35_delta=am_lag, regen_kv35=None, bound_ok=True, violations=[],
                 note='programme constant: the compiler EXP_START must cover the new lag (Delta per stack listed); re-run '
                      'ahub_ages with the bound relay table.')]


def r_rows(B):
    out = []
    for name, src, port, w in (('kg', r'kvs_hroot_\w+\.o_kg', 'kgo', 23), ('ectl->hgi e/t', r'ectl_\w+\.(e\d|t\d)', r'^(e_a|ti_a)', None)):
        per = collections.defaultdict(dict)
        bits = collections.defaultdict(int)
        for p in B.paths(src, port=port):
            st = re.search(r'_(EN|ES|WN|WS)_', p['sink_part'] + '_').group(1)
            per[st][p['sink_part']] = delta(p)
            bits[(st, p['sink_part'])] += p['bits']
        pads, sk = 0, {}
        for st, d in per.items():
            mx = max(d.values())
            sk[st] = dict(sorted(d.items()))
            pads += sum((mx - x) * (w or bits[(st, k)]) for k, x in d.items())
        out.append((name, sk, pads))
    (n1, kg, kgp), (n2, eh, ehp) = out
    kg_spread = {st: max(d.values()) - min(d.values()) for st, d in kg.items()}
    eh_spread = {st: max(d.values()) - min(d.values()) for st, d in eh.items()}
    return [dict(param='row start (o_kg broadcast) per-row skew', module='kvs_hroot_<st> o_kg -> ectl frames (qkd_ectl3_kiss_st kg)',
                 instances_regex=r'hg_<st>_<r>:u_ectl', kind='instance',
                 formula='Delta_r = bound - asbuilt full-path depth hroot.o_kg -> ectl_<st>_<f>.kgo per row; one broadcast source '
                         'and type-parameter frames -> the as-built relative row timing is kept only if every row gets the same Delta',
                 buses=[dict(name='kg', src='hroot_<st>|hg_<st>_<r>', dst='hg_<st>_<r>', leaf_regex=r'o_kg')],
                 asbuilt=None, regen_kv35=None, delta_per_row=kg, spread_edges=kg_spread, pad_flops=kgp,
                 bound_ok=False, violations=[f'kg row Delta spread {kg_spread} edges: no parameter absorbs it'],
                 note='NOT absorbable by a parameter (o_kg is ONE source word per stack, ECTL ages are type params, partition '
                      f'types are shared across rows): pad each row kg landing to the stack max Delta = {kgp} flops (23 b kg x '
                      'sum of row deficits), OR prove the row start skew is free (the e-read chain/astk calendar would then need '
                      'the per-row starts recompiled; no such per-row boot register exists).'),
            dict(param='ectl -> hgi (e/t words) per-row skew', module='ectl_<st>_<f> e/t -> hst heads (hgi)', instances_regex=r'hgi_<st>_<r>',
                 kind='instance', formula='Delta_r of ectl.e*/t* -> hst.e_a/ti_a; uniform Delta is absorbed by the head start',
                 buses=[dict(name='e/t', src='hg_<st>_<r>', dst='hgi_<st>_<r>', leaf_regex=r'ectl_\w+\.(e\d|t\d|kf)')],
                 asbuilt=0, regen_kv35=None, delta_per_row=eh, spread_edges=eh_spread, pad_flops=ehp,
                 bound_ok=all(v == 0 for v in eh_spread.values()), violations=[] if all(v == 0 for v in eh_spread.values()) else ['e/t skew'],
                 note='as-built 0-stage (abutted) -> bound 2 on every frame: uniform +2, no pads; the head and K paths shift '
                      'together (compiler D_QK +2).')]


def r_prog(B):
    o_hr = {re.search(r'o_hroot_(\w\w)', p['source']).group(1): p for p in B.paths(r'kvs_ctl\.o_hroot_\w\w$', sink=r'kvs_hroot')}
    hr_c = {re.search(r'hroot_(\w\w)', p['source']).group(1): p for p in B.paths(r'kvs_hroot_\w\w\.o_ctl$', sink='^kvs_ctl$')}
    d2d = collections.defaultdict(set)
    for p in B.paths(r'^d2d_kv\.|^dcal\.tok_start', sink=r'^(kvs_ctl|kvs_attn|seq__u_core)$'):
        d2d[p['sink']].add((p['asb'], p['bound']))
    tx = [b for b in B.bus(r'kvs_attn\.attn__tx', src='hub_C', dst='sys_c')]
    kv_seq = B.paths(r'd2d_kv\.kvn_word_valid', sink='^seq__u_core$')[0]
    kv_ctl = B.paths(r'd2d_kv\.kvn_word_valid', sink='^kvs_ctl$')[0]
    rx_att = B.paths(r'd2d_kv\.att_rx_v', sink='^kvs_attn$')[0]
    a0 = int(next(iter(B.param('qkd_seq_core_static_s', 'KVN_A0'))))
    kvn = a0 + delta(kv_seq) - delta(rx_att)
    return [dict(param='down[s] / ret (kvs_ctl o_hroot / hroot o_ctl)', module='kv_static_programme (emb_fill, writer_die) + '
                 'kvjc3_pc_chain writer ages', instances_regex='boot image (kvs_ctl programme)', kind='boot',
                 formula='die relays of kvs_ctl.o_hroot_s -> hroot.i_ctl (+ hroot chain) per stack; hroot.o_ctl -> kvs_ctl',
                 buses=[dict(name='o_hroot', src='hub_C', dst='hroot_<st>', leaf_regex=r'kvs_ctl\.o_hroot_<st>'),
                        dict(name='hroot_ctl', src='hroot_<st>', dst='hub_C', leaf_regex=r'kvs_hroot_<st>\.o_ctl')],
                 asbuilt={st: [o_hr[st]['asb'], hr_c[st]['asb']] for st in STACKS},
                 regen_kv35={st: [o_hr[st]['bound'], hr_c[st]['bound']] for st in STACKS}, bound_ok=True, violations=[],
                 note='programme constants (per-stack lists in the compiler) -> regenerate the kvs_ctl boot programme; all paths '
                      'got shorter (emb fill margin grows); no RTL parameter.'),
            dict(param='d2d ages (sys_c <-> hub_C): programme_start, d2d_to_attention_rx, d2d_to_writer, attention tx',
                 module='kv_static_programme link ages / d2d link calendar (boot__link_cfg TX/RX images)',
                 instances_regex='boot image (kvs_ctl -> d2d link_cfg)', kind='boot',
                 formula='bound depth of d2d_kv.* / dcal.tok_start -> {kvs_ctl, kvs_attn, seq__u_core}; attn__tx -> d2d_kv',
                 buses=[dict(name='rx', src='sys_c', dst='hub_C', leaf_regex=r'd2d_kv\.(rx_payload|kvn_word|att_rx|engine_result)'),
                        dict(name='tx', src='hub_C', dst='sys_c', leaf_regex=r'kvs_attn\.attn__tx')],
                 asbuilt={k: sorted(v) for k, v in d2d.items()} | {'tx': [b['asbuilt_stages'] for b in tx]},
                 regen_kv35={k: sorted({x[1] for x in v}) for k, v in d2d.items()} | {'tx': [b['bound_stages'] for b in tx]},
                 bound_ok=True, violations=[],
                 note='as-built the three sinks saw the d2d words at DIFFERENT depths (kvs_ctl 4-6, kvs_attn 9-11, seq core 7-14); '
                      'bound they are all 32 (tx 31): the writer (kvs_ctl) no longer leads the seq core by 8 edges on KVN words '
                      '-> re-check the writer write-before-read (kv_static_programme writer_die) after the programme regen. '
                      '+0.24 %/token accepted (KV-P5 17:05).'),
            dict(param='KVN_A0', module='qkd_seq_core_static_s', instances_regex=r'kv3_hub_C_part\.sv:u_seq_u_core', kind='type',
                 formula='KVN_A0_asb + Delta D(d2d kvn_word_valid -> seq core) - Delta D(d2d att_rx -> kvs_attn)  (age counter a '
                         'starts at the attention programme request, which kvs_attn issues off the att_rx stream)',
                 buses=[dict(name='kvn', src='sys_c', dst='hub_C', leaf_regex=r'd2d_kv\.kvn_word_(valid|tag)'),
                        dict(name='att_rx', src='sys_c', dst='hub_C', leaf_regex=r'd2d_kv\.att_rx_v')],
                 asbuilt=a0, regen_kv35=kvn, bound_ok=0 <= kvn and kvn + 4 < 256, violations=[] if 0 <= kvn else ['KVN_A0 < 0'],
                 note=f'kvn {kv_seq["asb"]}->{kv_seq["bound"]}, att_rx {rx_att["asb"]}->{rx_att["bound"]} (kvs_ctl kvn '
                      f'{kv_ctl["asb"]}->{kv_ctl["bound"]}). ANCHOR ASSUMPTION: prg_req_v follows att_rx at a fixed in-hub_C age; '
                      'if the attention programme is started by dcal.tok_start instead, use Delta(tok_start -> kvs_ctl) (+29). '
                      'Confirm in the token bench (seq fault f_kvn) before G3.')]


def r_unchanged(B):
    pvf = B.param('qkd_pv_fin_s', 'SKEW')
    rh = {p['port']: p for p in B.paths(r'pvw_0__u_T\dQ\d_45_r0\.b', sink='pvw_0__u_RH_r0')}
    a_d, b_d = delta(rh['a0']), delta(rh['b0'])
    return [dict(param='PV_LEAD / F_DLY / STATUS_DELAY / FR_OFS-side ages', module='qkd_kvs_attn_fl (hub_C)',
                 instances_regex=r'kv3_hub_C_part\.sv:u_kvs_attn', kind='type',
                 formula='PV_LEAD = D(ks_pvst); F_DLY = 1 + D(ks_pvfst) - PV_LEAD + D(ks_pvfin): all intra hub_C (u_d38/u_d45/u_d46 '
                         'kept stages)', buses=[], asbuilt='kit values', regen_kv35='unchanged', bound_ok=True, violations=[],
                 note='kvs_attn, pv ctl, pvfin in one partition -> no lane; STATUS_DELAY 213 is the KV-HEALTH status kit value, not a crossing.'),
            dict(param='RH a/b stream alignment (pvw result trunk -> RH)', module='qkd_pv_rs_hd_f (hub_C u_pv[NS]_u_RH_r0)',
                 instances_regex=r'kv3_hub_C_part\.sv:u_pv[NS]_u_RH_r0', kind='instance',
                 formula='Delta(T1Q*_45.b -> RH.b*) - Delta(T0Q*_45.b -> RH.a*) must be 0 (no age parameter on the RH)',
                 buses=[dict(name='T*Q*_45.b', src='pv_<N|S>_7', dst='hub_C', leaf_regex=r'pvw_\d__u_T\dQ\d_45_r0\.b')],
                 asbuilt=dict(a=rh['a0']['asb'], b=rh['b0']['asb']), regen_kv35=dict(a=rh['a0']['bound'], b=rh['b0']['bound']),
                 pad_flops=(a_d - b_d) * 258 * 2 * 2 if a_d > b_d else 0, bound_ok=a_d == b_d,
                 violations=[] if a_d == b_d else [f'b streams arrive {a_d - b_d} edges early vs a (as-built offset lost)'],
                 note='R8 landing group (bus_groups aligned_by_lanes=false): BINDER3 landing pads (2 stages x 258 b x b0,b1 x 2 '
                      'sides) restore it; no parameter.  The deeper T*Q* b chain hops (as-built [2, 3..9]) are the same R8 class.'),
            dict(param='ot_dp_efault AGE (plan efault cells)', module='ot_dp_efault', instances_regex=r'kv3_*:u_u_efault', kind='instance',
                 formula='generated by tools/die_plan/bind.py from the BOUND lane depths', buses=[], asbuilt='n/a', regen_kv35='already bound',
                 bound_ok=True, violations=[], note='bind-generated (plan cells), not as-built: not stale.'),
            dict(param='qkd_pv_fin_s SKEW / dcal EP_SKEW', module='qkd_pv_fin_s / qkd_d2d_cal_seq_pin_bc4', instances_regex='hub_C:u_pvfin, sys_c:u_dcal',
                 kind='type', formula='internal (P0/P1 from the two RH in hub_C; EP_SKEW fixed 3 by RTL $error)', buses=[],
                 asbuilt={'SKEW': sorted(pvf), 'EP_SKEW': 3}, regen_kv35='unchanged', bound_ok=True, violations=[],
                 note='P0_AGE / P1_AGE themselves are cal words (compiler): shift with the trunk regen (TRUNK_D rule).')]


RULES = (r_ectl, r_vport, r_pv_trunk, r_ahub, r_rows, r_prog, r_unchanged)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('bind_dir')
    ap.add_argument('--write-rules', type=Path)
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    B = Bind(a.bind_dir)
    rules = [r for f in RULES for r in f(B)]
    bad = 0
    for r in rules:
        flag = 'OK ' if r['bound_ok'] and not r.get('pad_flops') else 'BLK'
        bad += flag == 'BLK'
        rv = r['regen_kv35'] if r.get('regen_kv35') is not None else r.get('regen_kv35_delta', r.get('delta_per_row'))
        s = json.dumps(rv)
        print(f"[{flag}] {r['kind']:8s} {r['module'][:40]:40s} {r['param'][:44]:44s} asb={json.dumps(r.get('asbuilt'))[:60]} "
              f"regen={s[:160]}" + (f" pads={r['pad_flops']}" if r.get('pad_flops') else '') +
              (f" VIOL={r['violations']}" if r.get('violations') else ''))
    doc = dict(schema='opentallas.die_plan.kv_param_rules.v1', die='qwen_kvsys', plan='lat_v35 (kv35)', bind_dir=str(B.dir),
               generator='physical/die_plan/qwen_kvsys/bind/kv_param_regen_check.py',
               note='KV parameter <-> lane rules for BINDER3 asbuilt.param_regen (KV-P5 decision 10-23 17:05: regenerate, '
                    'do not pad krq). D(x) = bound depth (bind_latency bound_stages / bus_groups landing bound_stages); '
                    'Delta = bound - as-built full-path stages. kind: type = partition-type RTL parameter (equal on every '
                    'replica of the type), instance = per instance (strap or pads), boot = boot image / programme constant.',
               rules=rules)
    if a.write_rules:
        a.write_rules.write_text(json.dumps(doc, indent=1, default=str) + '\n')
    if a.json:
        a.json.write_text(json.dumps(doc, indent=1, default=str) + '\n')
    print(f'{len(rules)} rules, {bad} blockers')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
