#!/usr/bin/env python3
"""KV-FUNC-OPENS 10-19 (fork KVFO-MISC): exact per-instance output pads for structurally unused KV die outputs whose role is
proven from pinned source text AND from the bound die's own connectivity.  Fail-closed: any source drift, any condition that
does not hold on the die, or any candidate bit that is read / already spare refuses (no partial admission of a class).

Classes (each bit must be a strict-unread driven output bit: no reader, not a top output, not already a declared spare):
  KPV_LOCKSTEP   ot_qkh_head_stk_native.kpv_o of lanes t != 0: the K-tree reduction valid is lane 0's (ktree .kpv_in(kpv_k[0]));
                 lanes 1..15 carry the same fixed-depth registered q-valid (lane8 kpv <= k3v) for data that IS consumed (kp_o).
  ECTL_ER_ADDR   qkd_ectl3_kiss_st.so[12:1] = engine er_addr: payload written only with er_valid_g (ot_qkd_ectl_part); the only
                 reader of so[0] (er_valid) is qkd_astk_er_owner_st.eso_v, which the owner treats as a sticky FAULT predicate
                 (static ABI: no e-read service on the engine face), so the qualified address has no functional consumer.
  ER_TAIL_NEXT   qkd_astk_er_owner_st.next_addr/next_v of the chain-tail owner (registered copies of da[0]/dv[0]); every other
                 owner's next_* is read, exactly one tail per chain.
  ER_TAIL_RESP   qkd_astk_er_owner_st.response_addr/response_v of the chain tail whose response_data IS read; the chain's 8
                 owner_id straps are exactly {0..7}, so every valid request is served by one owner (collision -> fault) and
                 response_v/addr are fixed-latency copies of the request the static schedule already places.
  ASTK_LT        qkd_astk_ctl_s.lt = {aq_q[20:1], start}: registered copy of command bits; also unconnected in the selected
                 static reference composition (ot_qwen_tp8_attention_native_stack_cal).
  EP_ZO_TOK      qkd_astk_ep_s.zo[1] (zo_tok, next-slice trigger) of the last slice: strip_st drops zo[8][1] from both ro[8]
                 and zn[0] (no next slice).
  SEQ_HS         qkd_seq_core_static_s.hs (legacy hub start): the die's qkd_ahub_static_dw starts on hs_start driven by the
                 kvs_attn ks_ahs bus, not by the sequencer.
  BRANCH_DUP     relay payload b bits whose relay-only provenance is a producer pin bit from an allowed producer set that ALSO
                 reaches >= 1 non-relay reader on another relay branch (fork cargo; the consumer of this branch reads a
                 narrower field of the same held word).
"""
import argparse, collections, hashlib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P

SOURCES = {  # path -> sha256 (GEN7 source epoch 4db097403)
    'rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s.sv': None,
    'rtl/hdc/nearhbm/ot_qkh_subtiles.sv': None,
    'rtl/qwen_sys/static_kv_20261014/qkd_static_ectl_st.sv': None,
    'rtl/qwen_sys/static_kv_20261014/qkd_ectl_c_st.sv': None,
    'rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv': None,
    'rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv': None,
    'rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv': None,
    'rtl/qwen_sys/split_20261014/qkd_astk_strip_st.sv': None,
    'rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv': None,
    'rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv': None,
    'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv': None,
    'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv': None,
    'rtl/lib/face_land/qkd_astk_rly_296_fl.sv': None,
    'rtl/qwen_sys/split_20261014/qkd_astk_phys.sv': None,
}
PINNED = json.loads((Path(__file__).with_name('kv_misc_unused_roles.pins.json')).read_text()) \
    if Path(__file__).with_name('kv_misc_unused_roles.pins.json').is_file() else {}
# exact source facts each class relies on (regex over comment-stripped text, all must match)
FACTS = {
    'KPV_LOCKSTEP': [('rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s.sv', r'\.kpv_in\(kpv_k\[0\]\)'),
                     ('rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s.sv', r'\.kpv_o\(kpv_k\[t\]\)'),
                     ('rtl/hdc/nearhbm/ot_qkh_subtiles.sv', r'kpv\s*<=\s*k3v;')],
    'ECTL_ER_ADDR': [('rtl/qwen_sys/static_kv_20261014/qkd_ectl_c_st.sv', r'\.er_valid\(so\[0\]\),\s*\.er_addr\(so\[12:1\]\)'),
                     ('rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv', r"er_valid_g\s*<=\s*1'b1;\s*er_addr_g\s*<="),
                     ('rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv', r'eso_q<=eso_v'),
                     ('rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv', r'\|\|\s*eso_q\)\s*fault<=1')],
    'ER_TAIL_NEXT': [('rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv', r'next_addr<=da\[0\]'),
                     ('rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv', r'next_v<=dv\[0\]')],
    'ER_TAIL_RESP': [('rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv', r'collide=1'),
                     ('rtl/qwen_sys/split_20261014/qkd_astk_er_owner_st.sv', r'response_addr\[11\*k\+:11\]<=da\[5\]\[11\*k\+:11\]')],
    'ASTK_LT': [('rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv', r'lt\[20:1\]\s*<=\s*aq_q\[20:1\];'),
                ('rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv', r'lt\[0\]\s*<=\s*start;')],
    'EP_ZO_TOK': [('rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv', r'assign zo = \{jd_q\[520:9\], sum, jd_q\[8:0\], zo_tok, sv_\[0\]\};'),
                  ('rtl/qwen_sys/split_20261014/qkd_astk_strip_st.sv', r'assign ro\[8\] = \{zo\[8\]\[650:139\], zo\[8\]\[10:7\], zo\[8\]\[6:3\], zo\[8\]\[2\], zo\[8\]\[0\]\};'),
                  ('rtl/qwen_sys/split_20261014/qkd_astk_strip_st.sv', r'assign zn\[0\] = \{zo\[8\]\[138:11\], zo\[8\]\[10:7\], zo\[8\]\[6:3\], zo\[8\]\[2\], zo\[8\]\[0\]\};')],
    'SEQ_HS': [('rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv', r'hs <= hsd\[2\];')],
    'BRANCH_DUP': [('rtl/qwen_sys/split_20261014/qkd_astk_phys.sv', r'else b <= a;'),
                   ('rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv', r'module qkd_rlys_296')],
}
RELAY = re.compile(r'^(qkd_rlys_\d+|qkd_astk_rly_\d+_fl|qkd_rlysh0?_\d+|qkd_landsh0?_\d+)$')
DUP_PRODUCERS = re.compile(r'^(qkd_kvs_attn:acal_(WS|WN|ES|EN)|qkd_pv16_vport_b:(out_epoch|out_t)|qkd_d2d_static:\w+|'
                           r'qkd_kvs_ctl:dcfg__age_pv)$')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_sources(root, pins):
    got = {}
    for rel in SOURCES:
        p = Path(root) / rel
        if not p.is_file():
            raise ValueError('missing pinned source ' + rel)
        got[rel] = sha(p)
        if pins and pins.get(rel) != got[rel]:
            raise ValueError('pinned source changed; re-prove roles: ' + rel)
    for cls, facts in FACTS.items():
        for rel, rx in facts:
            if not re.search(rx, P.strip_comments((Path(root) / rel).read_text())):
                raise ValueError(f'{cls}: source fact not found in {rel}: {rx}')
    return got


def derive(die_v, record, root, existing, pins=None):
    srcs = check_sources(root, pins if pins is not None else PINNED)
    rec = json.loads(Path(record).read_text())
    die_sha = sha(die_v)
    if rec.get('die_sha256') != die_sha:
        raise ValueError('bind record is for another die')
    mods, cache = {}, {}
    for mst, r in rec['masters'].items():
        if not r.get('rtl'):
            continue
        p = Path(r['rtl']); p = p if p.is_absolute() else Path(root) / p
        if p not in cache:
            cache[p] = P.parse_modules(P.strip_comments(p.read_text(errors='replace')), str(p))
        mods[mst] = next(m for m in cache[p] if m.name == mst)
    doc = json.loads(json.dumps(existing or dict(pads={}, instances={})))
    pads = P.load_pads(doc)
    nets, tin, tout, insts = P.parse_die(str(die_v))
    rd = collections.defaultdict(list)       # (net, bit) -> [(mst, inst, port, pbit)]
    outbit = {}                              # (inst, port, pbit) -> (net, bit)
    drv = {}                                 # (net, bit) -> (mst, inst, port, pbit)
    spare = set(); conn = {}; master_of = {}; consts = {}
    for mst, inst, params, cm in insts:
        m = mods.get(mst)
        if m is None:
            continue
        master_of[inst] = mst; conn[inst] = {}
        env = m.env(params)
        for pn, e in cm.items():
            if pn not in m.ports or not e:
                continue
            bits = P.expr_bits(e, nets) or []
            conn[inst][pn] = bits
            d = m.ports[pn][0]
            w = m.width(pn, env)
            key = (mst, pn, inst) if (mst, pn, inst) in pads else (mst, pn)
            pset = P.pad_bits(pads[key], w if w is not None else len(bits)) if key in pads else set()
            for k, bt in enumerate(bits):
                pbit = len(bits) - 1 - k
                if bt[0] == 'CONST':
                    consts.setdefault((inst, pn), {})[pbit] = bt[1]
                    continue
                if bt[0] in ('Z', 'UNDECL'):
                    continue
                bt = tuple(bt)
                if d == 'output':
                    outbit[(inst, pn, pbit)] = bt; drv[bt] = (mst, inst, pn, pbit)
                    if pbit in pset:
                        spare.add(bt)
                else:
                    rd[bt].append((mst, inst, pn, pbit))
    topout = set()
    for n in tout:
        w, lo = nets[n]; topout.update((n, i) for i in range(lo, lo + w))

    def unread(inst, pn, pbit):
        bt = outbit.get((inst, pn, pbit))
        return bt is not None and not rd.get(bt) and bt not in topout and bt[0] not in tin and bt not in spare

    def port_bits(inst, pn):
        return range(len(conn.get(inst, {}).get(pn) or []))

    def insts_of(mst):
        return [i for i, m in master_of.items() if m == mst]

    adm = collections.defaultdict(lambda: collections.defaultdict(set))   # inst -> port -> bits
    counts = collections.Counter()

    def admit(cls, inst, pn, bits):
        for b in bits:
            if not unread(inst, pn, b):
                raise ValueError(f'{cls}: {inst}.{pn}[{b}] is read/spare/undriven; renewed review required')
        adm[inst][pn].update(bits); counts[cls] += len(bits)

    # KPV_LOCKSTEP: per head, kpv_k[0] read only by an ot_qkh_ktree kpv_in, all other lanes unread.
    heads = collections.defaultdict(dict)
    for inst in insts_of('ot_qkh_head_stk_native'):
        mm = re.fullmatch(r'(.+)__g_t_(\d+)__u_stk', inst)
        if not mm:
            raise ValueError('KPV_LOCKSTEP: unexpected head stack instance ' + inst)
        heads[mm.group(1)][int(mm.group(2))] = inst
    for h, lanes in heads.items():
        if sorted(lanes) != list(range(16)):
            raise ValueError('KPV_LOCKSTEP: head without 16 lanes ' + h)
        r0 = rd.get(outbit.get((lanes[0], 'kpv_o', 0)), [])
        if not r0 or any(not (x[0] == 'ot_qkh_ktree' and x[2] == 'kpv_in') for x in r0):
            raise ValueError('KPV_LOCKSTEP: lane 0 kpv not read by the K-tree in ' + h)
        if not all(rd.get(outbit.get((lanes[t], 'kp_o', b))) for t in range(16) for b in range(32)):
            raise ValueError('KPV_LOCKSTEP: a lane partial kp_o is not consumed in ' + h)
        for t in range(1, 16):
            admit('KPV_LOCKSTEP', lanes[t], 'kpv_o', [0])
    # ECTL_ER_ADDR
    for inst in insts_of('qkd_ectl3_kiss_st'):
        r0 = rd.get(outbit.get((inst, 'so', 0)), [])
        if not r0 or any(not (x[0] == 'qkd_astk_er_owner_st' and x[2] == 'eso_v') for x in r0):
            raise ValueError('ECTL_ER_ADDR: so[0] of %s not consumed only as er_owner eso_v' % inst)
        admit('ECTL_ER_ADDR', inst, 'so', range(1, 13))
    # ER chain: group owners per chain prefix, owner_id straps must be exactly 0..7
    chains = collections.defaultdict(dict)
    for inst in insts_of('qkd_astk_er_owner_st'):
        mm = re.fullmatch(r'(.+)_g_owner_(\d+)__u_owner', inst)
        if not mm:
            raise ValueError('ER: unexpected owner instance ' + inst)
        chains[mm.group(1)][int(mm.group(2))] = inst
    for ch, ow in chains.items():
        ids = sorted(sum(v << k for k, v in consts.get((i, 'owner_id'), {}).items()) for i in ow.values())
        if ids != list(range(8)) or any(len(consts.get((i, 'owner_id'), {})) != 3 for i in ow.values()):
            raise ValueError('ER: owner_id straps are not exactly 0..7 in ' + ch)
        tails = [i for i in ow.values() if all(unread(i, p, b) for p in ('next_addr', 'next_v') for b in port_bits(i, p))]
        if len(tails) != 1:
            raise ValueError('ER: chain %s has %d unread-next tails' % (ch, len(tails)))
        for i in ow.values():
            if i != tails[0] and not all(rd.get(outbit.get((i, p, b))) for p in ('next_addr', 'next_v') for b in port_bits(i, p)):
                raise ValueError('ER: non-tail owner with unread next_* ' + i)
        t = tails[0]
        for p in ('next_addr', 'next_v'):
            admit('ER_TAIL_NEXT', t, p, list(port_bits(t, p)))
        if not all(rd.get(outbit.get((t, 'response_data', b))) for b in port_bits(t, 'response_data')):
            raise ValueError('ER_TAIL_RESP: tail response_data not fully consumed ' + t)
        for p in ('response_addr', 'response_v'):
            bits = [b for b in port_bits(t, p) if unread(t, p, b)]
            if bits:
                if len(bits) != len(port_bits(t, p)):
                    raise ValueError('ER_TAIL_RESP: partial response port read ' + t + '.' + p)
                admit('ER_TAIL_RESP', t, p, bits)
    # ASTK_LT
    for inst in insts_of('qkd_astk_ctl_s'):
        admit('ASTK_LT', inst, 'lt', list(port_bits(inst, 'lt')))
    # EP_ZO_TOK: only bit 1, only for an ep whose zo bit 1 is unread (the strip's last slice)
    eps = [i for i in insts_of('qkd_astk_ep_s') if unread(i, 'zo', 1)]
    for inst in eps:
        if not re.search(r'_g_ep_7__u_ep$', inst):
            raise ValueError('EP_ZO_TOK: unread zo token on a non-terminal slice ' + inst)
        admit('EP_ZO_TOK', inst, 'zo', [1])
    # SEQ_HS: the hub start pin must be driven from the kvs_attn ks_ahs chain
    hubs = insts_of('qkd_ahub_static_dw')
    if len(hubs) != 1:
        raise ValueError('SEQ_HS: expected one qkd_ahub_static_dw')
    hb = (conn[hubs[0]].get('hs_start') or [None])[0]
    seen = 0
    while hb is not None and tuple(hb) in drv and RELAY.match(drv[tuple(hb)][0]) and seen < 10000:
        d = drv[tuple(hb)]; a = conn[d[1]].get('a') or []
        hb = a[len(a) - 1 - d[3]] if d[3] < len(a) else None; seen += 1
    if hb is None or tuple(hb) not in drv or drv[tuple(hb)][:1] != ('qkd_kvs_attn',) or drv[tuple(hb)][2] != 'ahs':
        raise ValueError('SEQ_HS: ahub hs_start is not sourced by qkd_kvs_attn.ahs')
    for inst in insts_of('qkd_seq_core_static_s'):
        admit('SEQ_HS', inst, 'hs', [0])
    # BRANCH_DUP
    def origin(bt):
        n = 0
        while bt in drv and RELAY.match(drv[bt][0]) and drv[bt][2] == 'b':
            d = drv[bt]; a = conn[d[1]].get('a') or []
            if d[3] >= len(a):
                return None
            x = a[len(a) - 1 - d[3]]
            if x[0] in ('CONST', 'Z', 'UNDECL'):
                return None
            bt = tuple(x); n += 1
        return drv.get(bt), bt
    tcache = {}
    def terminals(bt):
        if bt in tcache:
            return tcache[bt]
        out, st, seen_ = set(), [bt], set()
        while st:
            x = st.pop()
            if x in seen_:
                continue
            seen_.add(x)
            for (m, i, p, pb) in rd.get(x, []):
                if RELAY.match(m) and p == 'a':
                    bb = conn[i].get('b') or []
                    if pb < len(bb) and bb[len(bb) - 1 - pb][0] not in ('CONST', 'Z', 'UNDECL'):
                        st.append(tuple(bb[len(bb) - 1 - pb]))
                else:
                    out.add((m, i, p))
        tcache[bt] = out
        return out
    for (inst, pn, pbit), bt in outbit.items():
        mst = master_of[inst]
        if not RELAY.match(mst) or pn != 'b' or not unread(inst, pn, pbit):
            continue
        o = origin(bt)
        if not o or o[0] is None:
            continue
        (pm, pi, pp, ppb), obt = o
        if RELAY.match(pm) or not DUP_PRODUCERS.match(f'{pm}:{pp}'):
            continue
        if not terminals(obt):
            raise ValueError(f'BRANCH_DUP: producer {pi}.{pp}[{ppb}] reaches no consumer at all')
        admit('BRANCH_DUP', inst, pn, [pbit])
    # merge into exact instance entries (union with any existing per-instance declaration)
    entries = doc.setdefault('instances', {})
    for inst, ports in adm.items():
        ent = entries.setdefault(inst, dict(master=master_of[inst], reason='', ports={}))
        if ent.get('master') != master_of[inst]:
            raise ValueError('instance entry master mismatch ' + inst)
        for pn, bits in ports.items():
            old = P.pad_bits(ent['ports'][pn], None) if pn in ent['ports'] else set()
            allb, ranges = sorted(old | bits), []
            for i in allb:
                if ranges and i == ranges[-1][1] + 1:
                    ranges[-1][1] = i
                else:
                    ranges.append([i, i])
            ent['ports'][pn] = ranges
        why = 'KV-FUNC-OPENS misc_unused_contract: source+die proven structurally unused output role (see contract classes)'
        ent['reason'] = (ent['reason'] + ' | ' + why) if ent.get('reason') else why
    doc['misc_unused_contract'] = dict(die_sha256=die_sha, source_sha256=srcs, bits=sum(counts.values()),
                                       classes=dict(counts), bind_record_sha256=sha(record))
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('die_v', type=Path)
    ap.add_argument('--bind-record', type=Path, required=True, help='strict port_bind_v2.json of the same die (master RTL map)')
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--existing', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--write-pins', type=Path, help='record current source SHAs (first derivation only)')
    a = ap.parse_args()
    if a.write_pins:
        a.write_pins.write_text(json.dumps({r: sha(a.root / r) for r in SOURCES}, indent=1) + '\n')
    d = derive(a.die_v, a.bind_record, a.root, json.loads(a.existing.read_text()) if a.existing else None)
    a.out.write_text(json.dumps(d, indent=1) + '\n')
    print(json.dumps(d['misc_unused_contract']))


if __name__ == '__main__':
    main()
