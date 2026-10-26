"""TOK-QK-PRICE 2026-10-26: copy of ../rederive_edges.py (TOK-QK-QCE 1121cb654) with four opt-in extensions, outputs in
this dir:  --add ADD.json  {lane: cycles} added to landed_stages of every member of that bind lane (FE-REACH stations,
landed seam crossings);  --hop-ext  the dv-chain hop law also reads the fw->fe inter-slice lanes ch_up_i/st_dn_i/sc_dn_i
(the other direction of the same hop; 10-20 law read only ag_up_i in that direction);  --l9-stb  the L9 pair word takes
max over the st_a and st_b senders;  --cb-add N  cycles added to the CB16 path (x-in / cluster fabric / rs landed crossings);  --hop-add N  cycles added
to the dv-chain hop edge (landed seams on the inter-slice hops that cross a split line: K per crossed hop, not 11 x max);  --l9-add N  cycles added to the L9 pair word (a landed seam on the fe -> neighbour fw l9 lane).

Original doc (TOK-QK-QCE 2026-10-26): re-derive the QC token composer's die-scope ledger edges and lane ages (10-20, priced on the old
dv2f20g5r2b GEN die) from a bind's committed bus_groups (this dir: bus_groups_{ref441,v7}.json.gz) + cb16_path.json.

    python3 rederive_edges.py BUS_GROUPS.json.gz TAG [--clamp]
      -> edges_<TAG>_rederived.json      list of die edges that REPLACE every scope 'die' edge of the 10-20 ledger
         lane_ages_<TAG>_rederived.json  replacement for lane_ages_dv2f20g5r2b.json (ledger lane_ages.path)
         rederive_<TAG>.txt              per-edge old -> new table with lane names / stage counts

Laws (one per 10-20 edge, kept from the ledger; only the die values change):
  * lane age R_x = cycles from the source pin to the sink pin = landed register stages of the bind lane (the g5r2b
    'E + 1' counted the relay edges plus the landing o register: both are flops between the same two pins).
  * die edge = cycles the bound die adds over the RTL the composer's ages were measured on (QCL: the as-built s8 slice
    row, = the bind's as-built netlist) = landed_stages - asbuilt_stages of the lanes on that path (bind.py / r8.py OFFSET).
  * --clamp: conservative variant -- no die edge below 0 and no lane age below its 10-20 value.
"""
import gzip, json, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
UP = HERE.parent
import argparse
_ap = argparse.ArgumentParser(); _ap.add_argument('bg'); _ap.add_argument('tag'); _ap.add_argument('--clamp', action='store_true')
_ap.add_argument('--add'); _ap.add_argument('--hop-ext', action='store_true'); _ap.add_argument('--l9-stb', action='store_true')
_ap.add_argument('--cb-add', type=int, default=0); _ap.add_argument('--hop-add', type=int, default=0); _ap.add_argument('--l9-add', type=int, default=0); _ap.add_argument('--out', default=str(HERE / 'out')); _ap.add_argument('--cb-bind', default='v7')
A = _ap.parse_args()
OUT = Path(A.out); OUT.mkdir(parents=True, exist_ok=True)
bg_path, tag = A.bg, A.tag
clamp = A.clamp
BG = json.load(gzip.open(bg_path) if str(bg_path).endswith(".gz") else open(bg_path))  # QC-BINDPRICE: plain bind output too
CB16 = json.loads((HERE / 'cb16_path.json').read_text())  # QC-BINDPRICE: own copy incl. binds.final
CB_KEY = {'ref441': 'ref441', 'v7': 'v7', 'v7base': 'v7base'}
MEM = [(g, m) for g in BG['landing'] for m in g['members']]
ADD = json.loads(Path(A.add).read_text()) if A.add else {}
for _g, _m in MEM:
    if _m['lane'] in ADD:
        _m['landed_stages'] += ADD[_m['lane']]


def ptype(p):
    return re.sub(r'^c_[EW]\d_(\w\w)_\d+', r'c_\1', re.sub(r'^sl_[EW]\d_', 'sl_', p))


def find(src, dst, port, part_re=None):
    """members from partition type src to type dst (regexes) whose sink port matches `port` (regex, full match)"""
    out = [(g, m) for g, m in MEM if re.fullmatch(src, ptype(g['src_part'])) and re.fullmatch(dst, ptype(g['sink_part']))
           and re.fullmatch(port, m['sink_port']) and (part_re is None or re.match(part_re, g['src_part']))]
    if not out:
        raise SystemExit(f'{bg_path}: no lane {src} -> {dst}.{port}')
    return out


def off(src, dst, port, part_re=None):
    ms = find(src, dst, port, part_re)
    o = max(m['landed_stages'] - m['asbuilt_stages'] for _, m in ms)
    ev = sorted({f"{m['lane']} {m['asbuilt_stages']}->{m['landed_stages']}" for _, m in ms})
    ev = ev[:3] + ([f'... {len(ev)} lanes'] if len(ev) > 3 else [])
    return o, f'{src}->{dst}.{port} max(landed-asbuilt) {o} [{"; ".join(ev)}]'


def landed(lane):
    ms = [m for _, m in MEM if m['lane'] == lane]
    if not ms:
        raise SystemExit(f'{bg_path}: no lane {lane}')
    return max(m['landed_stages'] for m in ms), max(m['asbuilt_stages'] for m in ms)


# ---------------------------------------------------------------- lane ages (ledger lane_ages_dv2f20g5r2b.json)
OLD_AGES = dict(R_CMD=20, R_HR=20, R_SS=17, R_AG=18, R_ST=13, R_DD=20, R_DR=21, R_CTX=7)
LANES = dict(R_CMD='tt_ctlm__cmd_cmd_wi', R_HR='tt_ctlm__hr_hr_wi', R_SS='sl_W5_fw__ss_wo_ss5',
             R_AG='sl_W5_fw__ag_wo_ag5', R_ST='tt_ctlm__tl_st_wi', R_DD='sl_W5_fw__dd_wo_dd_i',
             R_DR='native59__dr_o_dr_wi', R_CTX='glue__ctx_x_ctx_x')
ages = dict(schema='opentallas.qwen.ctlm-lane-ages.v1', die=f'qwen_compute bind {tag} ({Path(bg_path).name})',
            why='TOK-QK-QCE: lane age = landed register stages of the bind lane, pin to pin (results/token_pass/qc_v7_1025/'
                'rederive_edges.py)' + (' ; CLAMPED: no age below the 10-20 g5r2b value' if clamp else ''),
            source=f'results/token_pass/qc_v7_1025/{Path(bg_path).name}', lanes={})
rows = []
for k, lane in LANES.items():
    ld, asb = landed(lane)
    v = max(ld, OLD_AGES[k]) if clamp else ld
    ages['lanes'][k] = dict(lane=lane, landed_stages=ld, asbuilt_stages=asb)
    ages[k] = v
    rows.append((f'lane age {k}', OLD_AGES[k], v, f'{lane} asbuilt {asb} landed {ld}'))
ages['XPF_TRANSPORT_EDGES'] = 1 + ages['R_HR']
rows.append(('lane age XPF_TRANSPORT_EDGES (1 + R_HR)', 21, ages['XPF_TRANSPORT_EDGES'], 'rule of lane_ages_export.py'))

# ---------------------------------------------------------------- die edges
E = []


def edge(key, old, cyc, at, label, ev, **kw):
    c = max(cyc, 0) if clamp else cyc
    E.append(dict(label=f'TOK-QK-QCE {tag}: {label}', cycles=c, scope='die', grade=kw.pop('grade', 'PRICED'), at=at,
                  source=f'results/token_pass/qc_v7_1025/price_fereach_clkland_1026/rederive_edges_ext.py on {Path(bg_path).name}: {ev}', rederive_key=key,
                  cycles_1020=old, **kw))
    rows.append((key, old, c, ev))


# (1)+(2) q3h x broadcast (+6 at pre_qkv/pre_gu) and rs reduction (+6 at pre_qk/pre_silu): on this die both are the CB16
# matvec path x-in (slice hc -> cluster bc/bcf -> tree a/b) -> c16 root -> rs lane to the first slice leaf.  cb16_path.json
# max_root_plus_rs REPLACES both (no double count) and is charged on every matvec pass (qkv, o, gu, down).
cb = dict(CB16['binds'][A.cb_bind]); cb['max_root_plus_rs'] += A.cb_add
edge('q3h x broadcast + rs reduction -> CB16 x-in/root/rs path', '6 @pre_qkv,pre_gu + 6 @pre_qk,pre_silu = 24/layer',
     cb['max_root_plus_rs'], ['pre_qkv', 'pre_o', 'pre_gu', 'pre_down'],
     f"CB16 matvec path x-in -> c16 root -> slice rs, max over 48 clusters = {cb['max_root_plus_rs']} per matvec pass x 4",
     f"cb16_path.json binds.{A.cb_bind}.max_root_plus_rs + cb_add {A.cb_add} = {cb['max_root_plus_rs']} (max_root {cb['max_root']})")

# (3) dv chain slice<->slice hops (11 x +3 at pre_r2): inter-slice lanes sl_<S>_fe -> sl_<S'>_fw / sl_<S>_fw -> sl_<S'>_fe
hop = []
for src, dst, port in (('sl_fe', 'sl_fw', 'ch_dn_i'), ('sl_fe', 'sl_fw', 'cmd_i'), ('sl_fe', 'sl_fw', 'st_up_i'),
                       ('sl_fw', 'sl_fe', 'ag_up_i')) + ((('sl_fw', 'sl_fe', 'ch_up_i'), ('sl_fw', 'sl_fe', 'st_dn_i'),
                                                          ('sl_fw', 'sl_fe', 'sc_dn_i')) if A.hop_ext else ()):
    hop.append(off(src, dst, port))
h = max(o for o, _ in hop)
edge('dv chain slice<->slice hops', 33, 11 * h + A.hop_add, ['pre_r2'], f'11 inter-slice face hops x {h} + landed seam hops {A.hop_add}',
     ' | '.join(e for _, e in hop))

# (4) native59 hardened split service +5: inside the native59 partition (no bus_groups lane); kept.
edge('native59 split service (inside native59)', 5, 5, ['pre_attn'],
     'native59 hardened split service +5 (inside the native59 partition: no die lane in the bind; 10-20 value kept)',
     'no crossing lane: partition-internal')
o, ev = off('tt_ctlm', 'native59', 'native_cmd')
edge('NEW: tt_ctlm.native_cmd -> native59 (attention command)', 0, o, ['pre_attn'],
     f'attention command lane tt_ctlm -> native59 +{o} (as-built 0-stage connection, now a crossing)', ev)
o, ev = off('native59', 'tt_ctlm', 'native_ret')
edge('NEW: native59.native_ret -> tt_ctlm (attention completion)', 0, o, ['pre_o'],
     f'attention completion lane native59 -> tt_ctlm +{o}, priced serial before the o-proj go (as the ledger ctlm8 native_ret)', ev)

# (5) attention return lane native59 -> dvs_W5 (dvw_dr_wi) +1 = R_DR(die) - R_DR(dh2 20, the die the attention pair was
# measured on); same law for the send lane dvs_W5 -> native59 (dvw_dd_wo, R_DD dh2 20, 10-20 'unchanged' = 0)
for key, lane, old, at in (('attention return lane dr (R_DR - 20)', LANES['R_DR'], 1, ['pre_o']),
                           ('attention send lane dd (R_DD - 20)', LANES['R_DD'], 0, ['pre_attn'])):
    ld, asb = landed(lane)
    edge(key, old, ld - 20, at, f'{lane} landed {ld} vs the dh2 lane age 20 the attention pair was measured with',
         f'{lane} asbuilt {asb} landed {ld}')

# (6) slice2 landed-parent forwarded lanes + taps (536 bound / 327 plan, QW-SLICE5 law tools/qwen_dv/slice5_partition.py
# b1a5accf4): pass = hops 10 x sum(passes st 2, ch 2, sc 4) x per-slice pass cost; taps = 2 x (x + ar + mv + norm) + su.
# On this die the slice is the s8 partition set sl_*_{fw,fe,ctl,sc,st_a,st_b,stm,su_c,su_l*,hc*}: each 10-20 +3 crossing
# takes the bind offset of the lanes that implement it.
P = {}
P['st'] = max(off('sl_fw', 'sl_stm', 'sw_i')[0] + off('sl_stm', 'sl_fe', 'st_up_c')[0],
              off('sl_fe', 'sl_stm', 'se_i')[0] + off('sl_stm', 'sl_fw', 'st_dn_c')[0])
P['ch'] = max(off('sl_fw', 'sl_fe', 'chr_c')[0], off('sl_fe', 'sl_fw', 'chu_q')[0])
P['sc'] = max(off('sl_fw', 'sl_sc', 'up_i')[0] + off('sl_sc', 'sl_fe', 'sc_up_c')[0],
              off('sl_fe', 'sl_sc', 'dn_i')[0] + off('sl_sc', 'sl_fw', 'sc_dn_c')[0])
passes, hops = dict(st=2, ch=2, sc=4), 10
pass_cyc = hops * sum(passes[k] * P[k] for k in passes)
T = dict(
    x=[('SU xw -> stream insert', *off('sl_su_l0', 'sl_stm', 'vm_w.*')), ('st tap -> stream', *off('sl_fw', 'sl_stm', 'sw_i')),
       ('xt -> tap (ctl)', *off('sl_stm', 'sl_ctl', 'xt_d')), ('tap -> xhead columns', *off('sl_ctl', 'sl_hc[0-3]', 'a_d')),
       ('cw_s corridor -> clusters', 0, 'in the CB16 path edge (not counted twice)')],
    ar=[('station r -> ctl', *off('sl_st_a', 'sl_ctl', 'r_d')), ('ctl own word -> out face', *off('sl_ctl', 'sl_fw', 'own_ch')),
        ('return tap -> ctl', *off('sl_fw', 'sl_ctl', 'chd_q'))],
    mv=[('rs in-slice continuation (rs_n hc1 -> station / rs_s st_a -> st_b)',
         max(off('sl_hc1', 'sl_st_a', 'rs_n_.*')[0], off('sl_st_a', 'sl_st_b', 'rs_s_.*')[0]),
         off('sl_hc1', 'sl_st_a', 'rs_n_.*')[1] + ' | ' + off('sl_st_a', 'sl_st_b', 'rs_s_.*')[1]),
        ('station -> ctl', *off('sl_st_a', 'sl_ctl', 'r_d')), ('ctl -> VM (su_c)', *off('sl_ctl', 'sl_su_c', '.*'))],
    norm=[('red psum -> sc', *off('sl_su_c', 'sl_sc', 'red_.*')), ('sc chain tap/insert', *off('sl_fw', 'sl_sc', 'up_i')),
          ('sc w1 -> VM (sc -> ctl -> su_c)', off('sl_sc', 'sl_ctl', 'sc_w._.*')[0] + off('sl_ctl', 'sl_su_c', '.*')[0],
           off('sl_sc', 'sl_ctl', 'sc_w._.*')[1] + ' + ctl->su_c')],
    su=[('SU issue ctl -> su_c', *off('sl_ctl', 'sl_su_c', '.*'))])
tsum = {k: sum(t[1] for t in v) for k, v in T.items()}
tap_cyc = 2 * (tsum['x'] + tsum['ar'] + tsum['mv'] + tsum['norm']) + tsum['su']
# L9 pair word (qkv split level 9, dv_lower_mat: sender 2t+1 -> receiver 2t): listed in the 10-20 crossing table
# (l9 in/out LAND +3) but not in its tap sum; on this die it is a station -> fe -> neighbour fw -> station path.
l9 = A.l9_add + ((max(off('sl_st_a', 'sl_fe', 'l._c')[0], off('sl_st_b', 'sl_fe', 'l._c')[0]) if A.l9_stb else off('sl_st_a', 'sl_fe', 'l._c')[0]) + off('sl_fe', 'sl_fw', 'l._i')[0] + off('sl_fw', 'sl_st_a', 'nb_d_p')[0])
sl_ev = (f"pass {hops} hops x (st {passes['st']}x{P['st']} + ch {passes['ch']}x{P['ch']} + sc {passes['sc']}x{P['sc']}) = {pass_cyc}; "
         f"taps 2x(x {tsum['x']} + ar {tsum['ar']} + mv {tsum['mv']} + norm {tsum['norm']}) + su {tsum['su']} = {tap_cyc}; "
         + '; '.join(f'{k}: ' + ', '.join(f'{n} {c}' for n, c, _ in v) for k, v in T.items()))
edge('slice2 landed-parent forwarded lanes + taps -> s8 partition crossings', '536 (plan 327)', pass_cyc + tap_cyc, ['pre_r2'],
     f'slice partition crossings, QW-SLICE5 law on the bind offsets: pass {pass_cyc} + taps {tap_cyc}', sl_ev,
     detail=dict(pass_cost_per_slice=P, passes=passes, hops=hops, taps={k: [dict(crossing=n, cycles=c, lanes=e) for n, c, e in v]
                                                                         for k, v in T.items()}))
edge('NEW: qkv L9 pair word (station -> fe -> neighbour fw -> station)', 0, l9, ['pre_qk'],
     f'L9 sender -> receiver pair word on the qkv matvec +{l9} (10-20 crossing table: l9 LAND +3, not in its tap sum)',
     ' + '.join(off(*a)[1] for a in (('sl_st_a', 'sl_fe', 'l._c'), ('sl_fe', 'sl_fw', 'l._i'), ('sl_fw', 'sl_st_a', 'nb_d_p'))))

# (7) forwarded-lane class views: 0 (types hardened once; R8 replica_unequal must be 0 -> one depth per class)
ru = BG['summary']['replica_unequal']
edge('forwarded-lane class views', 0, 0 if ru == 0 else 10 ** 6, ['pre_qkv'], f'class views: R8 replica_unequal {ru}',
     f"bus_groups summary {BG['summary']}")

# (8) XDIE pair link law X + status tail 213 (L0: X_L0 + 213): re-measured on QC v7 + KV b19 (TOK-QK-XD2,
# claude/tok-qk-xd2-1025@004bfaf96 results/token_pass/qc_kv_link_v7_1025/result.json): X 8, L0_X -214, period 7056.
edge('XDIE pair link (X + STATUS tail)', '221 (L0 -1)', 8 + 213, ['pre_o'],
     'XDIE QC v7 x KV b19 pair: X 8 + STATUS tail 213 per layer (L0 X -214 + 213 = -1); C2K 77 / K2C 77 / roundtrip 1933 / '
     'exposed 155 fit inside the period 7056 (unchanged)',
     'claude/tok-qk-xd2-1025@004bfaf96 results/token_pass/qc_kv_link_v7_1025/result.json xdie.cycles X_per_layer 8, '
     'L0_X -214, period_per_layer 7056; STATUS_DELAY 213', grade='NEWEST', cycles_l0=-214 + 213)

sfx = '_clamp' if clamp else ''
(OUT / f'edges_{tag}_rederived{sfx}.json').write_text(json.dumps(E, indent=1) + '\n')
(OUT / f'lane_ages_{tag}_rederived{sfx}.json').write_text(json.dumps(ages, indent=1) + '\n')
txt = [f'# {tag}{sfx}: 10-20 g5r2b ledger value -> re-derived (bind {Path(bg_path).name})']
for k, a, b, ev in rows:
    txt.append(f'{k} | {a} -> {b} | {ev}')
die = sum(e['cycles'] * len(e['at']) for e in E)
txt.append(f'die edges per layer (sum cycles x boundaries): {die}')
(OUT / f'rederive_{tag}{sfx}.txt').write_text('\n'.join(txt) + '\n')
print('\n'.join(txt))
