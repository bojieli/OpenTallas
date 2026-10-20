#!/usr/bin/env python3
"""L2H-PAD l21 (LEAD2-HBM, 2026-10-19): the GEN2e3 strict-bind residual (878 unread bits / 361 nets / 171 classes after
the admitted re-manifest e08e4c2f) becomes real hardware, no waiver:

- observation exports (fault_cause codes, stat_cycles counters, done / busy / quiet / valid flags, calendar sequence and
  client fields, edge indices, the unread bits of partially read buses) are READ by a host observation readback ring:
  five ot_hbm_obs_leaf instances (obs_SW / obs_SE / obs_NE / obs_NW per quadrant + obs_C for the central blocks) and
  the host ingress becomes ot_hbm_host_static_ingress_obs (read window 0x000-0x3FF, idx = {lid, page, word}; page 0
  live sample, page 1 sticky read-to-clear). Ring: host_cp_ingress -> obs_C -> obs_SW -> obs_SE -> obs_NE -> obs_NW ->
  host_cp_ingress. Every leaf pin is registered; the relay planner (S4, reach 405) adds stations on long hops. Serial-
  domain sources (SU programme slices) take the leaf's synchroniser flop (SYNC_MASK), as the fault leaves do.
- hb_ckgen pll_link / por_link (link clock and its reset release; no link-domain consumer on this die) are truly dead:
  hb_ckgen becomes hfd_ckgen_nolink (link outputs and their release synchroniser removed).

Input: the residual bit map (results/arch/hbm_unread_gen2e3_1019/l21/residual_bits.json, from die_port_bind with the
admitted manifest). Fails closed if any listed bit already has a reader, if a listed port is absent / has another width,
or if a leaf would exceed 512 bits. No cycle of any datapath changes; nothing on the ring gates execution.

    l21_obs_readback.py IN_CONTRACT OUT_CONTRACT --report REPORT [--residual residual_bits.json]
"""
import argparse, copy, gzip, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RESIDUAL = ROOT / 'results/arch/hbm_unread_gen2e3_1019/l21/residual_bits.json'
LEAF = 'ot_hbm_obs_leaf'
LEAF_SRC = 'rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv'
ING_OLD, ING_NEW = 'ot_hbm_host_static_ingress', 'ot_hbm_host_static_ingress_obs'
ING_SRC = 'rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress_obs.sv'
CK_OLD, CK_NEW = 'hfd_ckgen', 'hfd_ckgen_nolink'
CK_SRC = 'rtl/hbm_accel/control/hfd_ckgen_nolink.sv'
CK_DEAD = {'pll_link': 1, 'por_link': 1}
RING = ['obs_C', 'obs_SW', 'obs_SE', 'obs_NE', 'obs_NW']   # LID = position
REGION = 'd4g_l21_obs'
OWNER = 'LEAD2-HBM/L2H-PAD'
QRE = re.compile(r'_(SW|SE|NE|NW)(?=\d|_|$)')


def ranges(bits):
    out, lo = [], None
    for b in sorted(bits):
        if lo is None:
            lo = prev = b
        elif b == prev + 1:
            prev = b
        else:
            out.append((lo, prev + 1)); lo = prev = b
    if lo is not None:
        out.append((lo, prev + 1))
    return out


def domain(c, inst):
    d = {cr['domain'] for cr in c['clock_resets'] if cr['instance'] == inst and cr['kind'] == 'clock'}
    return 'stream' if 'stream' in d or not d else sorted(d)[0]


def apply(original, residual):
    c = copy.deepcopy(original)
    I = c['instances']
    read = {}
    for e in c['edges']:
        s = e['source']
        read.setdefault((s[0], s[1]), set()).update(range(s[2], s[3]))
    # ---- dead clock-generator link outputs: remove ----
    ck = [n for n, v in I.items() if v['master'] == CK_OLD]
    if len(ck) != 1:
        raise ValueError(f'expected one {CK_OLD}, found {ck}')
    ckn = ck[0]
    dead_bits = 0
    for p, w in CK_DEAD.items():
        if I[ckn]['ports'].get(p, {}).get('bits') != w or read.get((ckn, p)):
            raise ValueError(f'{ckn}.{p}: not an unread {w}-bit output')
        if any(cr.get('source') == [ckn, p] for cr in c['clock_resets']):
            raise ValueError(f'{ckn}.{p} clocks / resets something: not dead')
        del I[ckn]['ports'][p]; dead_bits += w
    I[ckn].update(master=CK_NEW, source=CK_SRC, rtl_deps=['rtl/hbm_accel/control/hfd_ckgen.sv'])
    I[ckn]['note'] = I[ckn].get('note', '') + ' | l21: hfd_ckgen_nolink (link domain unused on this die: pll_link/por_link removed)'
    # ---- observation bits -> leaves ----
    per = {n: [] for n in RING}
    obs_bits = 0
    for r in residual:
        i, p = r['inst'], r['port']
        if i == ckn and p in CK_DEAD:
            continue
        v = I.get(i)
        if v is None or v['ports'].get(p, {}).get('direction') != 'output' or v['ports'][p]['bits'] != r['width']:
            raise ValueError(f'{i}.{p}: absent or not a {r["width"]}-bit output')
        taken = read.get((i, p), set()) & set(r['bits'])
        if taken:
            raise ValueError(f'{i}.{p}: bits {sorted(taken)[:4]} already read: not residual')
        m = QRE.search(i)
        leaf = 'obs_' + m.group(1) if m else 'obs_C'
        dom = domain(c, i)
        for lo, hi in ranges(r['bits']):
            per[leaf].append((i, p, lo, hi, dom))
            obs_bits += hi - lo
    edges, sync = [], {}
    for lid, leaf in enumerate(RING):
        k, mask = 0, 0
        for i, p, lo, hi, dom in per[leaf]:
            n = hi - lo
            edges.append(dict(name=f'l21_{leaf}_{i}_{p}_{lo}', bits=n, source=[i, p, lo, hi], sink=[leaf, 'obs', k, k + n],
                              clock=dom, ready_or_credit=False, allowed_exception=None,
                              basis='l21 host observation readback: export lands in an obs leaf pin flop (host read window '
                                    '0x000-0x3FF); no datapath consumer, never gates execution', region=REGION))
            if dom != 'stream':
                mask |= ((1 << n) - 1) << k
            k += n
        if k == 0 or k > 512:
            raise ValueError(f'{leaf}: {k} observation bits (1..512 allowed)')
        sync[leaf] = mask
        I[leaf] = dict(master=LEAF, source=LEAF_SRC, params={'N': k, 'LID': lid, 'SYNC_MASK': f"512'h{mask:x}"},
                       slot=None, owner=OWNER, region=REGION, replaces_v15=None, rtl_deps=['rtl/lib/ot_rst_relay.sv'],
                       note=f'l21 host observation leaf LID {lid}: {k} unread export bits of {len({x[0] for x in per[leaf]})} blocks',
                       ports={'clk': dict(direction='input', bits=1), 'rst_n': dict(direction='input', bits=1),
                              'obs': dict(direction='input', bits=k), 'q_v': dict(direction='input', bits=1),
                              'q_idx': dict(direction='input', bits=8), 'q_d': dict(direction='input', bits=32),
                              'r_v': dict(direction='output', bits=1), 'r_idx': dict(direction='output', bits=8),
                              'r_d': dict(direction='output', bits=32)})
        for port, src in (('clk', 'pll_stream'), ('rst_n', 'por_stream')):
            c['clock_resets'].append(dict(instance=leaf, port=port, bits=1, domain='stream',
                                          kind='clock' if port == 'clk' else 'reset', source=[ckn, src]))
    # ---- ingress master + ring ----
    ing = [n for n, v in I.items() if v['master'] == ING_OLD]
    if len(ing) != 1:
        raise ValueError(f'expected one {ING_OLD}, found {ing}')
    ingn = ing[0]
    I[ingn].update(master=ING_NEW, source=ING_SRC)
    I[ingn]['note'] = I[ingn].get('note', '') + ' | l21: + observation readback window 0x000-0x3FF (obs ring)'
    for p, d, w in (('obs_q_v', 'output', 1), ('obs_q_idx', 'output', 8), ('obs_q_d', 'output', 32),
                    ('obs_r_v', 'input', 1), ('obs_r_idx', 'input', 8), ('obs_r_d', 'input', 32)):
        I[ingn]['ports'][p] = dict(direction=d, bits=w)
    hops = [(ingn, 'obs_q_')] + [(n, 'r_') for n in RING]
    sinks = [(n, 'q_') for n in RING] + [(ingn, 'obs_r_')]
    for (s, sp), (t, tp) in zip(hops, sinks):
        for f, w in (('v', 1), ('idx', 8), ('d', 32)):
            edges.append(dict(name=f'l21_ring_{s}_{t}_{f}', bits=w, source=[s, sp + f, 0, w], sink=[t, tp + f, 0, w],
                              clock='stream', ready_or_credit=False, allowed_exception=None,
                              basis='l21 obs ring hop: registered at both ends; fixed latency per die revision',
                              region=REGION))
    c['edges'] += edges
    # ---- bookkeeping ----
    gone = {(r['inst'], r['port']) for r in residual}
    before = len(c['open_outputs'])
    c['open_outputs'] = [o for o in c['open_outputs'] if (o[0], o[1]) not in gone]
    c['masters'][CK_OLD] = c['masters'].get(CK_OLD, 1) - 1
    c['masters'][CK_NEW] = 1
    c['masters'][ING_OLD] = c['masters'].get(ING_OLD, 1) - 1
    c['masters'][ING_NEW] = 1
    c['masters'][LEAF] = len(RING)
    c['masters'] = {m: k for m, k in c['masters'].items() if k}
    s = c['summary']
    s['instances'] = len(I); s['masters'] = len(c['masters']); s['edges'] = len(c['edges'])
    s['edge_bits'] = sum(e['bits'] for e in c['edges'])
    s['open_output_ports'] = s.get('open_output_ports', before) - (before - len(c['open_outputs']))
    s['clock_reset_ports'] = len(c['clock_resets'])
    shas = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in (LEAF_SRC, ING_SRC, CK_SRC)}
    rep = dict(layer='l21_obs_readback', residual_nets=len(residual), observation_bits=obs_bits, dead_removed_bits=dead_bits,
               leaves={n: dict(lid=i, bits=sum(x[3] - x[2] for x in per[n]), sync_bits=bin(sync[n]).count('1'),
                               blocks=len({x[0] for x in per[n]})) for i, n in enumerate(RING)},
               ring=[ingn] + RING + [ingn], ingress=[ingn, ING_OLD, ING_NEW], ckgen=[ckn, CK_OLD, CK_NEW],
               added_edges=len(edges), open_outputs_dropped=before - len(c['open_outputs']), sources_sha256=shas,
               cycles_changed=0, host_abi='reads 0x000-0x3FF return obs words (were 32hffffffff); idx = araddr[9:2] = '
                                          '{lid[2:0], page, word[3:0]}; page 1 = sticky, read-to-clear',
               qualification='SOURCE_ONLY_NEEDS_SYNTH (3 new masters; no view admitted)')
    return c, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--residual', default=str(RESIDUAL))
    a = ap.parse_args()
    with gzip.open(a.inp, 'rt') if a.inp.endswith('.gz') else open(a.inp) as f:
        c = json.load(f)
    residual = json.loads(Path(a.residual).read_text())['nets']
    c, r = apply(c, residual)
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n')
    Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print(f'L21_OBS_READBACK nets={r["residual_nets"]} obs_bits={r["observation_bits"]} dead_bits={r["dead_removed_bits"]} '
          f'leaves={[(n, v["bits"]) for n, v in r["leaves"].items()]} edges+={r["added_edges"]}')


if __name__ == '__main__':
    main()
