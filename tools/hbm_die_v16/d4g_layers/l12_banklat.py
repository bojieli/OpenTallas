#!/usr/bin/env python3
"""TW5-BANKLATDIE 10-19: d4g contract post-layer L12 -- VM bank-client LATENCY budgets + die lane pads.

    l12_banklat.py IN_contract.json[.gz] OUT_contract.json --report R.json [--max-iter 8]

Every fixed-latency VM bank client of the d4g die (faces banks: input pin flop +1) gets its round-trip parameter set to
the HARDENED budget its sub-lane derived (BUDGETS below; sources: results/arch/hbm_banklat_1019/{su_sfu_hc_budget_gen2c,
xl_budget, coll_budget, idx_budget}.json, DMA RR_RT 80 = d4g_bank_latency.DMA_RR_RT_BUDGET), and the die pads the SHORT
lanes UP to the budget, so the LAT class of d4g_functional_bind.py (d4g_bank_latency.check) passes STRICT:
  (1) params: scalar or per-bank list (x-load ctlx RD_LAT, element b = bank vmb_<q>b), set by master or by instance;
  (2) pads:   N fixed register stages (hbfd_pad #(W, N) = rtl/hbm_accel/die_glue/hbfd_pad.sv, ot_hdc_delay RESET 1; static,
              no valid/ready, no credit) on the NARROW direction only: the 17-b request lane of a read (never the 257-b rr
              data lane), the 1-b done lane of a write, the client->share request face of a share client, the narrower
              return lane of an IDX hub / selector control loop (SEGMENTS).  A request pad sits at the CLIENT end when the
              client bits reach only that bank lane (else at the bank end); a return pad at the client input.  Pad clock /
              reset = the endpoint's regional clock + reset of the lane's domain (copied from the contract).
  pad_b = budget round trip - actual round trip (derived E: the landing latency the K straps in the netlist give);
  pad_b < 0 -> the lane is LONGER than the budget -> FAIL (re-harden that client at a larger budget).
  Dependencies are padded in order (a share before its clients, a downstream LG tap before the tap in front of it), so
  the layer iterates check -> pad until the LAT class passes or nothing is left to pad.
Re-runnable: pads this layer inserted earlier (region d4g_l12_banklat) are removed first (lanes reconnected), then
re-derived -- re-run it after die STA sets the landing E (K straps are NO_E placeholders today) or on a new floorplan.
NO_E: every path through a NO_E landing is also evaluated at the sub-lanes' worst case E = 8; the report lists the lanes
whose pad would go negative at E = 8 (budget too small if die STA lands at E 8: re-check there).
Exit != 0 if a budget instance is missing, a lane is over budget, or the LAT class still fails.
--budget-overlay JSON (HBM-SUPROF 10-20): a documented, priced budget raise for one die geometry, {"master": {M: {P: v}},
"inst": {I: {P: v}}, "deltas": [...], "price": {...}} merged over BUDGET_MASTER / BUDGET_INST (an inst entry keeps its
master pattern).  Every raised value is listed in the report (overlay + params old/new); it is a static fixed-latency
budget handed to the compiler schedule and priced (TOK.HDS.PRICE), never a waiver: LAT must still PASS exactly.
"""
import argparse, collections, gzip, json, math, re, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent))
import d4g_bank_latency as L  # noqa: E402

REGION = 'd4g_l12_banklat'
PAD = 'hbfd_pad'
PAD_SRC = 'rtl/hbm_accel/die_glue/hbfd_pad.sv'
PAD_DEPS = ['rtl/hdc/ot_hdc_delay.sv']
OWN = 'TW5-BANKLATDIE l12 bank-client latency pad'
Q4 = ('SW', 'SE', 'NW', 'NE')

# ---------------------------------------------------------------------------------------------------------------- budgets
# by master (every instance of the master on the die) -> params
BUDGET_MASTER = {
    # HBM-BANKLAT-SU (su_sfu_hc_budget_gen2c.json): LG tap chain, one hard view per master
    'ot_hbm_su_static_pgslice_lg': {'READ_RETURN': 18, 'WRITE_RETURN': 15},
    'ot_hgi_sfu_lg_pair_tap_leaf': {'READ_RETURN': 24, 'WRITE_RETURN': 21},
    'ot_hgi_sfu_lg_pair_tap_leaf_term': {'READ_RETURN': 32, 'WRITE_RETURN': 29},
    'ot_hgi_sfu_core_split3': {'TAP_RR': 24, 'TAP_WR': 21},           # sfucore bridge expects the bound SFU tap 24/21
    'ot_hbm_hc_qhub_static': {'RD_CAPTURE': 37, 'GATHER_PHASE': 37, 'DONE_LAT': 33},   # +14 for the HC tap 32/29
    # HBM-BANKLAT-XL (xl_budget.json): ONE view (hgi_sm_xl2_ctlx_bl) for the 4 quadrants, per-bank vector
    'ot_hgi_sm_xload_cl2_ctlx': {'RD_LAT': [37, 39, 27, 29, 53, 55, 43, 45]},
    # HBM-BANKLAT-DMA: controller view hv16_dbk_vp4_ctl_rt80
    'ot_hgi_dma_back_static_vp4_banks_cp': {'RR_RT': L.DMA_RR_RT_BUDGET},
    # HBM-BANKLAT-COLL (coll_budget.json): COLL v8 parents (ctl_v5r leaves #(VM_RT 74)) + gather issuer
    'ot_hfd_coll_q2_hard_v8g': {'VM_RT': 74},
    'ot_hfd_coll_q3_hard_v8x': {'VM_RT': 74},   # COORD 0kj: SW ARGMAX -> deeper q3 programme (256 rows), VM_RT stays 74
    'ot_hgi_coll_gq_issue': {'VM_RT': 74},
}
# by instance -> (expected master or None, params)
BUDGET_INST = {f'hcollrs_{q}': ('ot_hbm_idx_vm_share2_static|ot_hbm_idx_vm_share2_static_r', {'BANK_RT': 72}) for q in Q4}
BUDGET_INST.update({
    'hb_idx__nwsh': ('ot_hbm_idx_vm_share2_static|ot_hbm_idx_vm_share2_static_r', {'BANK_RT': 40}),
    'hb_quant_NW': ('ot_hgi_qdq_host_split|ot_hgi_qdq_host_split_r2', {'RL': 45}),
    # HBM-BANKLAT-IDX (idx_budget.json budget_worst_E8)
    'hb_idx__ctl': ('ot_hbm_idx_rootctl_static_am', {'VM_RT': 65, 'CR_RT': 36, 'SEL_LAT': 30}),
    'hb_argmax': ('ot_hbm_argmax_static_sw_vm_r2', {'VMX': 77, 'ACK': 52}),
})
BUDGET_INST.update({f'hb_idx__op_{q}': ('ot_hbm_idx_vm_query_static_n12', {'VM_RT_EXTRA': 171}) for q in Q4})
# IDX hub / selector control loops (not bank clients; idx_budget.json rule): (name, a, a request port, b, b return port,
# a return port, target lane sum = f(params of a)).  The return lane (into a) is padded at a's input.
SEGMENTS = [
    ('ctl_cq_cr', 'hb_idx__ctl', 'cq', 'hb_vms_SW', 'cr', 'cr', lambda p: int(p['CR_RT']) - 1,
     'CR_RT = faces pin 1 + lanes(cq) + lanes(cr) (TOPK ACK 13 + CR_RT)'),
    ('argmax_cq_cr', 'hb_argmax', 'cq', 'hb_vms_SW', 'cr', 'cr', lambda p: int(p['ACK']) - 14,
     'ACK = 13 + faces pin 1 + lanes(cq) + lanes(cr)'),
    ('ctl_sel', 'hb_idx__ctl', 'sel_op', 'hb_idx__selector', 'selected_v', 'selected_v', lambda p: int(p['SEL_LAT']) - 4,
     'SEL_LAT = 4 + lanes(sel_op) + lanes(selected_v) (exact)'),
]


def load(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def bank_index(bk):
    return int(re.sub(r'\D', '', bk[-1]) or 0)


def worst_extra(notes):
    """edges a path gains if every NO_E landing on it lands at E = 8 instead of the K-derived E."""
    return sum(8 - int(m.group(1)) for n in notes for m in [re.search(r'NO_E placeholder \(E (\d+) derived', n)] if m)


# ---------------------------------------------------------------------------------------------------------------- netlist
class Net:
    def __init__(self, c):
        self.c, self.I, self.E, self.CR, self.ST = c, c['instances'], c['edges'], c['clock_resets'], c['straps']
        self.n = 0
        self.log = collections.Counter()
        self.src_map = collections.defaultdict(dict)   # (inst, port) -> {bit: (pad, 'o', k)}   re-source
        self.snk_map = collections.defaultdict(dict)   # (inst, port) -> {bit: (pad, 'i', k)}   re-sink
        self.new_edges = []
        self.pads = []
        self._dom = None

    def ename(self):
        self.n += 1
        return f'l12_{self.n:05d}'

    @staticmethod
    def runs(e, end, fn):
        """split edge e by fn(bit at `end`) -> new (inst, port, bit) or None; yields (new endpoint or None, j0, j1)."""
        i, p, lo, hi = e[end]
        cur, j0 = None, 0
        out = []
        for j in range(hi - lo):
            t = fn(i, p, lo + j)
            if j == 0:
                cur, j0 = t, 0; continue
            contig = (t is None and cur is None) or (t is not None and cur is not None and t[0] == cur[0] and t[1] == cur[1]
                                                     and t[2] == cur[2] + (j - j0))
            if not contig:
                out.append((cur, j0, j)); cur, j0 = t, j
        out.append((cur, j0, hi - lo))
        return out

    def rewrite(self, end, mp):
        """apply a bit map {(inst, port): {bit: (i2, p2, b2)}} to every edge's `end` (source or sink)."""
        if not mp:
            return
        other = 'sink' if end == 'source' else 'source'
        out = []
        for e in self.E:
            k = tuple(e[end][:2])
            if k not in mp or not any(b in mp[k] for b in range(e[end][2], e[end][3])):
                out.append(e); continue
            m = mp[k]
            parts = self.runs(e, end, lambda i, p, b: m.get(b))
            for n_, (t, j0, j1) in enumerate(parts):
                x = dict(e)
                if n_:
                    x['name'] = f'{e.get("name", "e")}_l12s{n_}'
                o = e[other]
                x[other] = [o[0], o[1], o[2] + j0, o[2] + j1]
                x[end] = [e[end][0], e[end][1], e[end][2] + j0, e[end][2] + j1] if t is None else [t[0], t[1], t[2], t[2] + j1 - j0]
                x['bits'] = j1 - j0
                if t is not None:
                    x['basis'] = (e.get('basis') or '') + f' | {REGION}: through lane pad {t[0]}'
                out.append(x)
        self.E[:] = out

    def edge(self, src, snk, basis, clock):
        assert src[3] - src[2] == snk[3] - snk[2] > 0, (src, snk)
        self.new_edges.append(dict(name=self.ename(), bits=src[3] - src[2], source=list(src), sink=list(snk), clock=clock,
                                   ready_or_credit=False, allowed_exception=None, basis=basis, region=REGION))

    def edge_runs(self, a_inst, a_port, a_bits, b_inst, b_port, b_bits, basis, clock):
        """edges a[a_bits[k]] -> b[b_bits[k]], merged into contiguous runs."""
        k0 = 0
        for k in range(1, len(a_bits) + 1):
            if k == len(a_bits) or a_bits[k] != a_bits[k - 1] + 1 or b_bits[k] != b_bits[k - 1] + 1:
                self.edge([a_inst, a_port, a_bits[k0], a_bits[k - 1] + 1], [b_inst, b_port, b_bits[k0], b_bits[k - 1] + 1],
                          basis, clock)
                k0 = k

    def domain_of(self, inst, port, end):
        if self._dom is None:
            self._dom = {}
            for e in self.E:
                for en in ('source', 'sink'):
                    self._dom.setdefault((e[en][0], e[en][1], en), e.get('clock') or 'stream')
        return self._dom.get((inst, port, end), 'stream')

    def clock_reset_src(self, ref, dom):
        crs = [x for x in self.CR if x['instance'] == ref]
        ck = [x for x in crs if x['kind'] == 'clock' and x['domain'] == dom]
        ck.sort(key=lambda x: (x['port'] not in ('clk', 'ck'), x['port']))
        rs = [x for x in crs if x['kind'] == 'reset' and x['domain'] == dom]
        rs.sort(key=lambda x: (x['port'] not in ('rst_n', 'rs'), x['port']))
        cks = ck[0]['source'] if ck else ['hb_ckgen', f'pll_{dom}']
        if rs:
            return cks, ('cr', rs[0]['source'])
        # reset delivered by an edge (reset forest leaf, GEN2d): drive the pad's rs from the same producer bit
        for e in self.E:
            if e['sink'][0] == ref and re.match(r'^(rst_n|rs|rst)$', e['sink'][1]):
                return cks, ('edge', e['source'][:2] + [e['source'][2], e['source'][2] + 1])
        return cks, ('cr', ['hb_ckgen', f'por_{dom}'])

    def add_pad(self, name, w, n, ref, dom, note):
        assert name not in self.I, name
        self.I[name] = dict(master=PAD, source=PAD_SRC, params={'W': w, 'N': n}, slot=None, owner=OWN, region=REGION,
                            note=note, replaces_v15=None, rtl_deps=list(PAD_DEPS),
                            ports={'ck': dict(direction='input', bits=1), 'rs': dict(direction='input', bits=1),
                                   'i': dict(direction='input', bits=w), 'o': dict(direction='output', bits=w)})
        cks, (rk, rsrc) = self.clock_reset_src(ref, dom)
        self.CR.append(dict(instance=name, port='ck', bits=1, domain=dom, kind='clock', source=list(cks)))
        if rk == 'cr':
            self.CR.append(dict(instance=name, port='rs', bits=1, domain=dom, kind='reset', source=list(rsrc)))
        else:
            self.edge(rsrc, [name, 'rs', 0, 1], f'{OWN}: reset = {ref} reset producer', dom)
        self.log['pads'] += 1; self.log['pad_flops'] += w * n

    def pad_src(self, name, inst, port, bits, n, ref, note):
        """pad on an OUTPUT port's bits: every consumer edge re-sourced to the pad."""
        bits = sorted(bits); dom = self.domain_of(inst, port, 'source')
        self.add_pad(name, len(bits), n, ref, dom, note)
        for k, b in enumerate(bits):
            assert b not in self.src_map[(inst, port)], (inst, port, b)
            self.src_map[(inst, port)][b] = (name, 'o', k)
        self.edge_runs(inst, port, bits, name, 'i', list(range(len(bits))), f'{OWN}: {inst}.{port} -> pad', dom)
        self.pads.append(dict(pad=name, at=f'{inst}.{port}', end='source', bits=len(bits), N=n, note=note))

    def pad_snk(self, name, inst, port, bits, n, ref, note):
        """pad on an INPUT port's bits: the driving edges re-sunk to the pad, pad -> port."""
        bits = sorted(bits); dom = self.domain_of(inst, port, 'sink')
        self.add_pad(name, len(bits), n, ref, dom, note)
        for k, b in enumerate(bits):
            assert b not in self.snk_map[(inst, port)], (inst, port, b)
            self.snk_map[(inst, port)][b] = (name, 'i', k)
        self.edge_runs(name, 'o', list(range(len(bits))), inst, port, bits, f'{OWN}: pad -> {inst}.{port}', dom)
        self.pads.append(dict(pad=name, at=f'{inst}.{port}', end='sink', bits=len(bits), N=n, note=note))

    def commit(self):
        self.rewrite('source', self.src_map)
        self.rewrite('sink', self.snk_map)
        self.E.extend(self.new_edges)
        self.src_map.clear(); self.snk_map.clear(); self.new_edges = []; self._dom = None

    def strip(self):
        """remove pads of an earlier run of this layer, reconnecting each lane (pad.i driver -> pad.o consumers)."""
        old = [k for k, v in self.I.items() if v['master'] == PAD and v.get('region') == REGION]
        if not old:
            return 0
        olds = set(old)
        drv = {}
        for e in self.E:
            if e['sink'][0] in olds and e['sink'][1] == 'i':
                for j in range(e['bits']):
                    drv[(e['sink'][0], e['sink'][2] + j)] = (e['source'][0], e['source'][1], e['source'][2] + j)
        self.E[:] = [e for e in self.E if e['sink'][0] not in olds]
        while True:   # chained pads: resolve to the first non-pad producer
            changed = False
            for k, v in drv.items():
                if v[0] in olds and v[1] == 'o':
                    drv[k] = drv[(v[0], v[2])]; changed = True
            if not changed:
                break
        mp = collections.defaultdict(dict)
        for (p, b), v in drv.items():
            mp[(p, 'o')][b] = v
        self.rewrite('source', mp)
        self.E[:] = [e for e in self.E if e['source'][0] not in olds]
        self.CR[:] = [x for x in self.CR if x['instance'] not in olds]
        self.ST[:] = [s for s in self.ST if s['inst'] not in olds]
        for k in old:
            self.I.pop(k)
        self.log['stripped_pads'] += len(old)
        return len(old)


# ---------------------------------------------------------------------------------------------------------------- params
def set_params(c, rep, bm=None, bi=None):
    bm = BUDGET_MASTER if bm is None else bm; bi = BUDGET_INST if bi is None else bi
    I = c['instances']; prob = []; done = []
    for n, x in sorted(I.items()):
        b = bm.get(x['master'])
        if b:
            old = {k: x.get('params', {}).get(k) for k in b}
            x.setdefault('params', {}).update(b); done.append([n, x['master'], old, dict(b)])
    for m in bm:
        if not any(x['master'] == m for x in I.values()):
            prob.append(f'no instance of budget master {m}')
    for n, (mre, b) in bi.items():
        x = I.get(n)
        if x is None or not re.fullmatch(mre, x['master']):
            prob.append(f'{n}: expected {mre}, got {None if x is None else x["master"]}'); continue
        old = {k: x.get('params', {}).get(k) for k in b}
        x.setdefault('params', {}).update(b); done.append([n, x['master'], old, dict(b)])
    for n, m, old, new in done:
        I[n]['note'] = (I[n].get('note') or '').split(f' | {REGION}:')[0] + f' | {REGION}: latency budget {new} (was {old})'
    rep['params'] = done
    return prob


# ---------------------------------------------------------------------------------------------------------------- pads
def safe(s):
    return re.sub(r'[^A-Za-z0-9_]', '_', s)


def request_pad(N, G, row, p, n, why, rep):
    """pad n stages on the request lane of path p (row = its LAT row)."""
    si, sp, lo, hi = p['sink']
    ci, cp = row['client'], row['port']
    cbits = {}
    for b in range(lo, hi):
        d, _ = G.back(si, sp, b)
        if d is not None and d[0] == ci and d[1] == cp:
            cbits[b] = d[2]
    if not cbits:
        rep['problems'].append(f'{ci}.{cp} -> {si}.{sp}: request lane not traced'); return
    # client end only if every client bit reaches nothing but this lane's sink range
    excl = all(all(s[0] == si and s[1] == sp and lo <= s[2] < hi for s, _ in G.fwd(ci, cp, cb)) for cb in cbits.values())
    name = safe(f'l12p_{ci}_{cp}_{si}_{sp}_{lo}')
    note = f'{OWN}: {n} stages on the request lane {ci}.{cp} -> {si}.{sp}[{lo}:{hi}] ({why})'
    if excl:
        N.pad_src(name, ci, cp, sorted(cbits.values()), n, ci, note)
    else:
        N.pad_snk(name, si, sp, sorted(cbits), n, si, note)


def return_pad(N, G, row, p, n, why, rep):
    """pad n stages on the return (done) lane of path p, at the client's input."""
    ri, rp, lo, hi = p['rsrc']
    ci = row['client']
    cb = collections.defaultdict(list)
    for b in range(lo, hi):
        for s, _ in G.fwd(ri, rp, b):
            if s[0] == ci:
                cb[s[1]].append(s[2])
    if len(cb) != 1:
        rep['problems'].append(f'{ri}.{rp}[{lo}:{hi}] -> {ci}: return lane not traced to one port {dict(cb)}'); return
    port, bits = next(iter(cb.items()))
    name = safe(f'l12p_{ci}_{port}_{ri}_{rp}_{lo}')
    N.pad_snk(name, ci, port, bits, n, ci, f'{OWN}: {n} stages on the return lane {ri}.{rp}[{lo}:{hi}] -> {ci}.{port} ({why})')


def plan_row(N, G, I, row, rows_by, rep):
    """insert the pads row needs; returns number of pads planned (0 = nothing to do or blocked)."""
    k = 0
    if row['kind'] in ('rd', 'wr'):
        ps = row['paths']
        if any('via' in p for p in ps):                       # LG tap chain: the downstream tap must pass first
            for p in ps:
                dr = rows_by.get((p['via'], row['kind']))
                if dr is None or dr['status'] != 'PASS':
                    return 0
        have = I[row['client']].get('params', {}).get(row['param'])
        ref, ref_rt = row['ref'], row['ref_rt']
        if ref is None or have is None:
            rep['problems'].append(f'{row["client"]}.{row["param"]}: no budget / reference'); return 0
        for p in ps:
            t = int(have[bank_index(p['bank'])]) if isinstance(have, list) else int(have)
            pad = ref_rt + t - ref - p['rt']
            wx = worst_extra(p['notes'])
            if wx and pad - wx < 0:
                rep['e8_recheck'].append(dict(client=row['client'], port=row['port'], bank=p['bank'], pad=pad, e8_extra=wx,
                                              note='budget below the E=8 round trip: re-check at die STA E'))
            elif wx:
                rep['e8_lanes'].append(dict(client=row['client'], port=row['port'], bank=p['bank'], pad=pad, e8_extra=wx))
            if pad < 0:
                rep['over_budget'].append(dict(client=row['client'], port=row['port'], bank=p['bank'], rt=p['rt'],
                                               budget_rt=ref_rt + t - ref, param=row['param'], have=have))
                continue
            if pad == 0:
                continue
            why = f'{row["param"]} {have} -> round trip {ref_rt + t - ref}, lanes give {p["rt"]}'
            wq = p['sink'][3] - p['sink'][2]; wr = (p['rsrc'][3] - p['rsrc'][2]) if p['rsrc'] else 1 << 30
            if wq <= wr:
                request_pad(N, G, row, p, pad, why, rep)
            else:
                return_pad(N, G, row, p, pad, why, rep)
            k += 1
    elif row['kind'] == 'rd_via_share':
        sr = rows_by.get((row['share'], 'rd'))
        if sr is None or sr['status'] != 'PASS':
            return 0
        have = I[row['client']].get('params', {}).get(row['param'])
        if have is None:   # qdq r3 LG children carry RL as latency_budget (as d4g_bank_latency reads it)
            have = I[row['client']].get('latency_budget', {}).get(row['param'])
        if have is None:
            rep['problems'].append(f'{row["client"]}.{row["param"]}: no budget (rd_via_share via {row["share"]})'); return 0
        have = int(have)
        tgt = have - row['ref'] - row['share_excess'] - row['share_extra'] + row['ref_lanes']
        for pe in row['pair_ends']:
            pad = tgt - pe['lanes']
            wx = worst_extra(pe['notes'])
            if wx and pad - wx < 0:
                rep['e8_recheck'].append(dict(client=row['client'], share=row['share'], pair=pe['pair'], pad=pad, e8_extra=wx))
            if pad < 0:
                rep['over_budget'].append(dict(client=row['client'], share=row['share'], pair=pe['pair'], lanes=pe['lanes'],
                                               budget_lanes=tgt, param=row['param'], have=have))
                continue
            if pad == 0:
                continue
            si, sp, lo, hi = pe['sink']
            bits = [b for b in range(lo, hi) if G.back(si, sp, b)[0] is not None]
            N.pad_snk(safe(f'l12p_{row["client"]}_{si}_{sp}_{lo}'), si, sp, bits, pad, si,
                      f'{OWN}: {pad} stages on the share request face {row["client"]} -> {si}.{sp}[{lo}:{hi}] '
                      f'({row["param"]} {have}: client<->share lanes {pe["lanes"]} -> {tgt})')
            k += 1
    return k


def segments(N, G, I, rep, segs=None):
    out = []
    for name, a, ap, b, bp, arp, fn, why in (SEGMENTS if segs is None else segs):
        if a not in I or b not in I:
            rep['problems'].append(f'segment {name}: {a} or {b} missing'); continue
        tgt = fn(I[a].get('params', {}))
        fw = []
        for bit in range(I[a]['ports'][ap]['bits']):
            for s, hops in G.fwd(a, ap, bit):
                if s[0] == b:
                    lat, notes = G.lane_latency(hops); fw.append((lat, worst_extra(notes)))
        bk = collections.defaultdict(list)
        for bit in range(I[b]['ports'][bp]['bits']):
            for s, hops in G.fwd(b, bp, bit):
                if s[0] == a and s[1] == arp:
                    lat, notes = G.lane_latency(hops); bk[(lat, worst_extra(notes))].append(s[2])
        if not fw or not bk:
            rep['problems'].append(f'segment {name}: no {a}.{ap} -> {b} or {b}.{bp} -> {a}.{arp} lane'); continue
        lf = max(x[0] for x in fw); wf = max(x[1] for x in fw)
        seg = dict(name=name, target=tgt, fwd=lf, fwd_e8_extra=wf, back={str(k): len(v) for k, v in bk.items()}, why=why, pads=[])
        if len({x[0] for x in fw}) > 1:
            seg['fwd_unequal'] = sorted({x[0] for x in fw})
        for (lb, wb), bits in sorted(bk.items()):
            pad = tgt - lf - lb
            if wf + wb and pad - wf - wb < 0:
                rep['e8_recheck'].append(dict(segment=name, pad=pad, e8_extra=wf + wb))
            if pad < 0:
                rep['over_budget'].append(dict(segment=name, lanes=lf + lb, target=tgt)); continue
            if pad:
                N.pad_snk(safe(f'l12p_{name}_{a}_{arp}_{min(bits)}'), a, arp, bits, pad, a,
                          f'{OWN}: {pad} stages on the {name} return lane {b}.{bp} -> {a}.{arp} ({why}: target {tgt}, '
                          f'lanes {lf}+{lb})')
                seg['pads'].append(dict(bits=len(bits), N=pad))
        out.append(seg)
    rep['segments'] = out


def run(c, rep, max_iter=8, check=L.check, bm=None, bi=None, segs=None):
    N = Net(c); I = c['instances']
    rep.update(problems=[], over_budget=[], e8_recheck=[], e8_lanes=[], iterations=[])
    rep['stripped'] = N.strip()
    rep['problems'] += set_params(c, rep, bm, bi)
    if rep['problems']:
        return N, None
    seg_done = False
    for it in range(max_iter):
        t0 = time.time()
        G = L.Graph(c)
        rows, summ = check(c, G)
        rows_by = {}
        for r in rows:
            rows_by[(r['client'], r['kind'])] = r
        planned = 0
        if summ['fail']:
            for r in rows:
                if r['status'] == 'FAIL':
                    planned += plan_row(N, G, I, r, rows_by, rep)
        if not seg_done:
            segments(N, G, I, rep, segs); seg_done = True
            planned += sum(len(s['pads']) for s in rep['segments'])
        N.commit()
        rep['iterations'].append(dict(it=it, lat=summ, pads_planned=planned, s=round(time.time() - t0, 1)))
        print(f'L12 iter {it}: LAT fail {summ["fail"]}/{summ["checked"]} pads planned {planned}', flush=True)
        if planned == 0 or rep['over_budget']:
            break
    rows, summ = check(c)
    rep['final_lat'] = summ
    rep['final_fail'] = [dict(client=r['client'], port=r['port'], kind=r['kind'], bad=r['bad'][:3]) for r in rows
                         if r['status'] == 'FAIL']
    rep['pads'] = N.pads; rep['log'] = dict(N.log)
    sm = c.get('summary')
    if isinstance(sm, dict):
        sm.update(instances=len(I), edges=len(c['edges']), edge_bits=sum(e['bits'] for e in c['edges']),
                  clock_reset_ports=len(c['clock_resets']))
    note = (f'L12 (TW5-BANKLATDIE 10-19): bank-client latency budgets bound, {N.log["pads"]} lane pads hbfd_pad '
            f'({N.log["pad_flops"]} flops); LAT {summ["fail"]} fail of {summ["checked"]}')
    if isinstance(c.get('notes'), list):
        c['notes'].append(note)
    elif isinstance(c.get('notes'), dict):
        c['notes'][REGION] = note
    return N, summ


SEG_PARAM = {'ctl_cq_cr': ('hb_idx__ctl', 'CR_RT'), 'argmax_cq_cr': ('hb_argmax', 'ACK'), 'ctl_sel': ('hb_idx__ctl', 'SEL_LAT')}


NEED_RE = re.compile(r'^(\S+)\.(\w+) = (\d+), .*?need (\d+)')
# HC qhub phases track the HC LG tap term (overlay h15.8: tap + 5 / + 5 / + 4; functional coupling the LAT class does not check)
QHUB = ('ot_hbm_hc_qhub_static', 'ot_hgi_sfu_lg_pair_tap_leaf_term')


def need_rows(rep):
    """over-budget rows + LAT FAIL rows that state a scalar need ('X.P = have, ... need N')."""
    rows = list(rep.get('over_budget') or [])
    for f in rep.get('final_fail') or []:
        for b in f.get('bad') or []:
            m = NEED_RE.match(str(b))
            if m and int(m.group(4)) > int(m.group(3)):
                rows.append(dict(client=m.group(1), param=m.group(2), have=int(m.group(3)), rt=int(m.group(4)),
                                 budget_rt=int(m.group(3)), from_lat_fail=True))
    return rows


def apply_qdq_rl(c, rl):
    """qdq r3: RL is a runtime strap (ctl rl_cfg = RL+4+2*XR), never a netlist parameter -> raise without re-synthesis."""
    q = c.get('qdq_split') or {}
    if not q or rl is None:
        return
    rli = rl + 4 + 2 * int(q['XR'])
    if rli > 126:
        raise SystemExit(f'L12_FAIL qdq RL {rl}: RLI {rli} beyond ctl_r4 126')
    q['RL'] = rl
    for n in q['lgs']:
        c['instances'][n].setdefault('latency_budget', {})['RL'] = rl
    for st in c['straps']:
        if st['inst'] == q['ctl'] and st['port'] == 'rl_cfg':
            st['value'] = rli; st['reason'] = f'HBMb/R18 l12 reprice: qdq RL {rl} -> RLI = RL+4+2*XR = {rli}'


def reprice(over, I, bm, bi, qdq=None):
    """HBMb/R18 10-21: measured need for every over-budget row (budget raised by exactly the lane shortfall; per-bank
    vectors element-wise, master budgets = max over its instances).  Mutates bm/bi, returns the delta list."""
    need = {}
    for x in over:
        if 'segment' in x:
            sp = SEG_PARAM.get(x['segment'])
            if not sp:
                continue
            inst, prm = sp; d = x['lanes'] - x['target']; idx = None
        else:
            inst, prm = x['client'], x['param']
            if 'rt' in x:
                d = x['rt'] - x['budget_rt']
            elif 'budget_lanes' in x:
                d = x['lanes'] - x['budget_lanes']
            else:
                continue
            idx = bank_index(x['bank']) if isinstance(x.get('have'), list) and x.get('bank') else None
        if d <= 0 or inst not in I:
            continue
        if qdq is not None and prm == 'RL' and inst in (qdq.get('lgs') or []):
            qdq['_need'] = max(qdq.get('_need', 0), int(x['have']) + d); continue
        if inst in bi and prm in bi[inst][1]:
            key = ('inst', inst)
        else:
            key = ('master', I[inst]['master'])
        need.setdefault((key, prm), {}); k2 = idx if idx is not None else -1
        need[(key, prm)][k2] = max(need[(key, prm)].get(k2, 0), d)
    out = []
    for ((scope, key), prm), dd in sorted(need.items(), key=str):
        if scope == 'inst':
            cur = bi[key][1].get(prm)
        else:
            cur = (bm.get(key) or {}).get(prm)
            if cur is None:
                cur = next((x.get('params', {}).get(prm) for x in I.values() if x['master'] == key), None)
        if cur is None:
            continue
        if isinstance(cur, list):
            new = [int(v) + dd.get(i, dd.get(-1, 0)) for i, v in enumerate(cur)]
        else:
            new = int(cur) + max(dd.values())
        if scope == 'inst':
            bi[key] = (bi[key][0], {**bi[key][1], prm: new})
        else:
            bm[key] = {**bm.get(key, {}), prm: new}
        out.append(dict(scope=scope, key=key, param=prm, **{'from': cur, 'to': new}))
    tap = bm.get(QHUB[1]) or {}
    if any(x['key'] == QHUB[1] for x in out) and 'READ_RETURN' in tap and 'WRITE_RETURN' in tap:
        qh = dict(RD_CAPTURE=int(tap['READ_RETURN']) + 5, GATHER_PHASE=int(tap['READ_RETURN']) + 5, DONE_LAT=int(tap['WRITE_RETURN']) + 4)
        cur = {k: (bm.get(QHUB[0]) or {}).get(k) for k in qh}
        bm[QHUB[0]] = {**bm.get(QHUB[0], {}), **qh}
        out.append(dict(scope='master', key=QHUB[0], param='RD_CAPTURE/GATHER_PHASE/DONE_LAT (tap coupling)', **{'from': cur, 'to': qh}))
    if qdq is not None and qdq.get('_need', 0) > int(qdq.get('RL') or 0):
        out.append(dict(scope='qdq', key=qdq.get('parent'), param='RL (strap rl_cfg)', **{'from': qdq.get('RL'), 'to': qdq['_need']}))
        qdq['RL'] = qdq.pop('_need')
    qdq is not None and qdq.pop('_need', None)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--max-iter', type=int, default=8)
    ap.add_argument('--budget-overlay', default=None, help='documented, priced budget raise JSON (see module doc)')
    ap.add_argument('--reprice-out', default=None, help='HBMb/R18: raise over-budget params to the measured need, record deltas here')
    ap.add_argument('--reprice-rounds', type=int, default=4)
    a = ap.parse_args()
    c = load(a.inp)
    bm, bi, ov = dict(BUDGET_MASTER), dict(BUDGET_INST), None
    if a.budget_overlay:
        ov = json.load(open(a.budget_overlay))
        for m, b in ov.get('master', {}).items():
            bm[m] = {**bm.get(m, {}), **b}
        for n, b in ov.get('inst', {}).items():
            if n not in bi:
                sys.exit(f'L12_FAIL overlay inst {n} has no BUDGET_INST entry (master pattern unknown)')
            bi[n] = (bi[n][0], {**bi[n][1], **b})
        print(f'L12 budget overlay {a.budget_overlay}: master {sorted(ov.get("master", {}))} inst {sorted(ov.get("inst", {}))}')
    qs = c.get('qdq_split') or {}
    if qs.get('parent') and qs['parent'] not in c['instances']:
        # HBMb/R18 10-21: l32q split hb_quant_NW into the CLOSED r3 leaves; the RL budget now lives on the 4 LG children
        # (latency_budget RL, read by d4g_bank_latency via DOWN_PARAM ot_hgi_qdq_lg_port_group_r2) at the netmap RL.
        b = bi.pop(qs['parent'], None)
        print(f'L12 qdq split: {qs["parent"]} budget {None if b is None else b[1]} -> LG children {qs.get("lgs")} RL {qs.get("RL")}')
    rep = dict(schema='opentallas.hbm.d4g.l12_banklat.v1', region=REGION, inp=str(a.inp),
               budgets=dict(master=bm, inst={k: v[1] for k, v in bi.items()}),
               overlay=None if ov is None else dict(path=a.budget_overlay, master=ov.get('master'), inst=ov.get('inst'),
                                                     deltas=ov.get('deltas'), price=ov.get('price')))
    N, summ = run(c, rep, a.max_iter, bm=bm, bi=bi)
    reprices = []
    qrl = dict(parent=qs.get('parent'), lgs=qs.get('lgs'), RL=qs.get('RL')) if qs else None
    for attempt in range(a.reprice_rounds if a.reprice_out else 0):
        if summ is None or rep['problems'] or not (rep['over_budget'] or summ['fail']):
            break
        d = reprice(need_rows(rep), c['instances'], bm, bi, qrl)
        if not d:
            break
        reprices.append(dict(round=attempt + 1, deltas=d))
        print(f'L12_REPRICE round {attempt + 1}: ' + '; '.join(f'{x["scope"]} {x["key"]} {x["param"]} {x["from"]} -> {x["to"]}' for x in d))
        c = load(a.inp)
        if qs.get('parent') and qs['parent'] not in c['instances']:
            bi.pop(qs['parent'], None)
        if qrl:
            apply_qdq_rl(c, qrl['RL'])
        N, summ = run(c, rep, a.max_iter, bm=bm, bi=bi)
    if a.reprice_out:
        rep['reprice'] = reprices
        Path(a.reprice_out).write_text(json.dumps(dict(
            schema='opentallas.hbm.d4g.l12_reprice.v1', inp=str(a.inp), overlay=a.budget_overlay,
            rule='HBMb/R18 10-21: over-budget lanes on the actual geometry raise the budget to the measured need '
                 '(explicit, recorded, priced via lanes/STEWARD-TOK.md; never an undersized bind, never silent)',
            rounds=reprices, final_budgets=dict(master=bm, inst={k: v[1] for k, v in bi.items()})), indent=1, default=str))
    ok = summ is not None and summ['fail'] == 0 and not rep['problems'] and not rep['over_budget']
    rep['verdict'] = 'PASS' if ok else 'FAIL'
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    if ok:
        op = gzip.open(a.out, 'wt') if a.out.endswith('.gz') else open(a.out, 'w')
        with op as f:
            json.dump(c, f)
    print(f'L12_{"OK" if ok else "FAIL"} pads={N.log["pads"]} pad_flops={N.log["pad_flops"]} stripped={rep["stripped"]} '
          f'lat_fail={None if summ is None else summ["fail"]} over_budget={len(rep["over_budget"])} '
          f'e8_recheck={len(rep["e8_recheck"])} problems={len(rep["problems"])}')
    for x in (rep['problems'] + rep['over_budget'] + rep.get('final_fail', []))[:30]:
        print('  ', x)
    sys.exit(0 if ok else 2)


if __name__ == '__main__':
    main()
