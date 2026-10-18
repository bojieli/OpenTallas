#!/usr/bin/env python3
"""H-D4G3b 2026-10-18, d4g GEN1 contract post-layer L1 (host configuration side, one layer because all three parts
touch the host F20 target map, the ingress TARGET_MASK and host_status):

 (a) XQL  x-load per quadrant (RBH-XQL, results/rtl/rbh_xql_1018/xql_quadrant_rebind.py run on THIS contract):
          xl_<q>_ctl = ot_hgi_sm_xload_cl2_ctlx x4 (tgt SW100 SE101 NW102 NE103), xl_<q>_aq{lo,hi}, W quadrants keep
          xq_<S>_p0/p1, E quadrants take the old xq_<S>_p2/p3 RENAMED xq_<E>_p0/p1; banks read group 2 of the quadrant.
 (b) STK  stack services per quadrant (RBH-STK, results/rtl/rbh_stk_1018/stk_quadrant_services.json):
          hb_dbk_<E> (tgt 105/107, banks vmb_<E>0..7 read group 1), wbk_<q> = ot_hbm_svc_wb_kport_q (quad strap,
          16 K ports: W vmks_<S>0..3, E vmks_<S>4..7), wbc_<S>0/1 -> wbc_<S>/wbc_<E>, sfault_<q> NPC16 NG4 ND8 -> fs_<q>
          (new fs_<E>) -> fr_<q>, refcfg_<q> NPC16 (tgt 128/129; PCs 16Q..16Q+15 refresh rows + PC reset tree).
 (c) HOST per-quadrant host config/status leaves hleaf_<q> = ot_hbm_host_cfg_leaf_{sw,se,nw,ne} (closed views
          hdie_host_cfg_leaf_<q>_r1; map results/arch/hbm_b_rtl1_host_1017/host_cfg_leaf_map_d4g.json): the ingress
          drives the 4 leaves, every target's cfg bundle comes from its leaf copy A (W face) / B (E face), the 69
          ready/active and 107 fault bits return through the leaves to host_status in the join_d4g order (TGTS of the
          map).  The six new E-quadrant targets of (a)/(b) (101, 103, 105, 107, 128, 129) take their cfg bundle from
          their quadrant leaf copy, but their status bits (NT +6, NF +8 incl. wbk_<E>.fault) go STRAIGHT to host_status
          appended after the leaf bits: the closed SE/NE leaves were hardened at NT18/NF26 and NT14/NF23 (exact
          widths, no spare inputs), so they cannot carry them.  host_status NT 69 -> 75, NF 107 -> 115,
          GUARD 8 -> 12 (= 8 + CFG_LAT 2 + ST_LAT 2; the relay layer must add its ingress->leaf + leaf->join lane edges).

Dependencies: the E-quadrant parts read vmb_<E>b.rq1/rr1/rq2/rr2 and vmdel_<E>0..7, which exist only after the VM
layer (SE/NE banks = hfd_vms_bank_native_q0_faces, 32 NPC-2 delivery lanes).  Run this layer AFTER the VM layer.
--gen0-test drops (and lists) the connections whose bank/lane endpoint is missing, so the layer can be bind-checked on
the GEN0 contract alone.

usage: l1_host_xload_stack.py IN_contract.json[.gz] OUT_contract.json --report R.json [--gen0-test]
"""
import argparse, copy, gzip, importlib.util, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGION = 'd4g_gen1_l1'
QS = ('SW', 'SE', 'NW', 'NE')
STK_OF = {'SW': 'SW', 'SE': 'SW', 'NW': 'NW', 'NE': 'NW'}
EAST = {'SW': 'SE', 'NW': 'NE'}
QID = {'SW': 0, 'SE': 1, 'NW': 2, 'NE': 3}
DBK_TGT = {'SE': 105, 'NE': 107}
REF_TGT = {'SE': 128, 'NE': 129}
XL_TGT = {'SE': 101, 'NE': 103}
LEAF_MAP_R1 = ROOT / 'results/arch/hbm_b_rtl1_host_1017/host_cfg_leaf_map_d4g.json'
# HBM-RTL5 10-18 (coordinator 0fi): r2 map = SE / NE leaves re-hardened at NT21/NF30 and NT17/NF27 (hdie_host_cfg_leaf_{se,ne}_r2),
# so the six new E targets + wbk_<E>.fault report THROUGH their leaf; host_status takes leaf outputs only (join_d4g_r2).
LEAF_MAP_R2 = ROOT / 'results/arch/hbm_rtl5_host_1018/host_cfg_leaf_map_d4g_r2.json'
LEAF_MAP = LEAF_MAP_R2
LEAF_SRC_R2 = 'rtl/hbm_accel/host_static_20261015/ot_hbm_host_cfg_leaf_r2.sv'
XQL_PY = ROOT / 'results/rtl/rbh_xql_1018/xql_quadrant_rebind.py'
LEAF_SRC = 'rtl/hbm_accel/host_static_20261015/ot_hbm_host_cfg_leaf.sv'
LEAF_DEPS = ['rtl/lib/ot_rst_relay.sv']
WBKQ_SRC = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kport_q.sv'
CFG_PORTS = ['cfg_v', 'cfg_target', 'cfg_addr', 'cfg_data', 'desc_v', 'desc_base', 'desc_limit', 'desc_loops', 'launch_v']
CFG_W = {'cfg_v': 1, 'cfg_target': 8, 'cfg_addr': 12, 'cfg_data': 256, 'desc_v': 1, 'desc_base': 12, 'desc_limit': 13,
         'desc_loops': 16, 'launch_v': 1}


def ld(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def edge(name, src, snk, basis, clock='stream'):
    b = src[3] - src[2]
    assert b == snk[3] - snk[2], (name, src, snk)
    return dict(name=name, bits=b, source=list(src), sink=list(snk), clock=clock, ready_or_credit=False,
                allowed_exception=None, basis=basis, region=REGION)


class L:
    def __init__(self, c, gen0_test):
        self.c, self.I, self.test = c, c['instances'], gen0_test
        self.rep = dict(deferred=[], added_instances=[], removed_instances=[], renamed={}, notes=[])

    # ---------------------------------------------------------------- generic helpers
    def has_port(self, i, p):
        return i in self.I and p in self.I[i]['ports']

    def ok_ep(self, e):
        """both endpoints exist (else, in --gen0-test, defer)."""
        miss = [x for x in (e['source'], e['sink']) if not self.has_port(x[0], x[1])]
        if not miss:
            return True
        if not self.test:
            raise SystemExit(f'L1: missing endpoint {miss} of {e["name"]} (run the VM layer first)')
        self.rep['deferred'].append(dict(edge=e['name'], missing=[f'{m[0]}.{m[1]}' for m in miss]))
        return False

    def add_edges(self, es):
        for e in es:
            if self.ok_ep(e):
                self.c['edges'].append(e)

    def rename(self, old, new):
        I = self.I
        assert old in I and new not in I, (old, new)
        I[new] = I.pop(old)
        for e in self.c['edges']:
            for end in (e['source'], e['sink']):
                if end[0] == old:
                    end[0] = new
        for x in self.c['clock_resets']:
            if x['instance'] == old:
                x['instance'] = new
            if x['source'][0] == old:
                x['source'][0] = new
        for s in self.c['straps']:
            if s['inst'] == old:
                s['inst'] = new
        self.rep['renamed'][old] = new

    def clone(self, old, new, **upd):
        n = copy.deepcopy(self.I[old])
        n.update(upd)
        n['region'] = REGION
        self.I[new] = n
        self.rep['added_instances'].append(new)
        return n

    def clone_clocks(self, old, new, src_map=None):
        for x in [x for x in self.c['clock_resets'] if x['instance'] == old]:
            y = copy.deepcopy(x)
            y['instance'] = new
            if src_map and tuple(y['source']) in src_map:
                y['source'] = list(src_map[tuple(y['source'])])
            self.c['clock_resets'].append(y)

    def strap(self, inst, port, value, reason, lo=0, hi=None):
        self.c['straps'] = [s for s in self.c['straps'] if not (s['inst'] == inst and s['port'] == port)]
        hi = hi if hi is not None else self.I[inst]['ports'][port]['bits']
        self.c['straps'].append(dict(inst=inst, port=port, value=value, lo=lo, hi=hi, master=self.I[inst]['master'],
                                     reason=reason))

    def drop_edges(self, pred):
        keep, gone = [], []
        for e in self.c['edges']:
            (gone if pred(e) else keep).append(e)
        self.c['edges'] = keep
        return gone

    def setp(self, inst, port, bits, direction=None):
        d = self.I[inst]['ports'].setdefault(port, dict(direction=direction, bits=bits))
        d['bits'] = bits

    # ---------------------------------------------------------------- (a) XQL
    def xql(self):
        spec = importlib.util.spec_from_file_location('xqlr', XQL_PY)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        tmp_in, tmp_out = Path('/tmp') / f'l1_xql_in_{id(self)}.json', Path('/tmp') / f'l1_xql_out_{id(self)}.json'
        json.dump(self.c, open(tmp_in, 'w'))
        m.main(str(tmp_in), str(tmp_out))
        r = json.load(open(tmp_out)); tmp_in.unlink(); tmp_out.unlink()
        I = self.I
        old_cr = {x['instance']: [y for y in self.c['clock_resets'] if y['instance'] == x['instance']] for x in self.c['clock_resets']
                  if re.match(r'^x[lq]_(SW|NW)_', x['instance'])}
        # instances: new / renamed; removed = old pairs 2/3
        for n, v in r['instances'].items():
            base = I.get(n) or I.get(v.get('renamed_from') or '') or {}
            ent = copy.deepcopy(base) if base else {}
            ent.update({k: v[k] for k in ('master', 'source', 'params') if k in v})
            ent['ports'] = v.get('ports') or base.get('ports') or I[v['renamed_from']]['ports']
            ent['note'] = (base.get('note', '') + ' | ' if base else '') + v['note']
            ent.setdefault('slot', None); ent.setdefault('owner', None)
            ent['region'] = REGION
            if n not in I:
                self.rep['added_instances'].append(n)
            I[n] = ent
        for n in r['removed_instances']:
            I.pop(n, None)
            self.rep['removed_instances'].append(n)
        gone = set(r['removed_edges'])
        self.c['edges'] = [e for e in self.c['edges'] if e['name'] not in gone]
        newst = []
        for e in r['edges']:
            e = copy.deepcopy(e); e['region'] = REGION
            if e['sink'][0] == 'host_status' and e['sink'][2] is None:
                newst.append(e)            # E-quadrant status: placed by host() (direct join slots)
                continue
            if self.ok_ep(e):
                self.c['edges'].append(e)
        self.xl_status = newst
        # straps: tgt of the 4 issuers
        for s in r['straps']:
            self.strap(s['inst'], s['port'], s['value'], s['reason'], s['lo'], s['hi'])
        # clocks: E quadrant clones of xl_<S>_*; renamed pairs keep their entries under the new name
        cr = [x for x in self.c['clock_resets'] if not re.match(r'^xq_(SW|NW)_p[23]_', x['instance'])]
        for x in self.c['clock_resets']:
            mm = re.match(r'^xq_(SW|NW)_p([23])_(\w+)$', x['instance'])
            if mm:
                y = copy.deepcopy(x); y['instance'] = f'xq_{EAST[mm.group(1)]}_p{int(mm.group(2)) - 2}_{mm.group(3)}'; cr.append(y)
            mm = re.match(r'^xl_(SW|NW)_(ctl|aqlo|aqhi)$', x['instance'])
            if mm:
                y = copy.deepcopy(x); y['instance'] = f'xl_{EAST[mm.group(1)]}_{mm.group(2)}'; cr.append(y)
        self.c['clock_resets'] = cr
        self.rep['xql'] = r['checks']
        self.new_targets = {f'xl_{q}_ctl': dict(tgt=XL_TGT[q], ready='configured', active='active',
                                                 fault=['fault']) for q in ('SE', 'NE')}

    # ---------------------------------------------------------------- (b) STK
    def stk(self):
        I, E = self.I, self.c['edges']
        # --- wbc_<S>0/1 -> wbc_<S> / wbc_<E>
        for s, e in EAST.items():
            self.rename(f'wbc_{s}0', f'wbc_{s}')
            self.rename(f'wbc_{s}1', f'wbc_{e}')
        # --- wbk_<q>: W remaster, E new
        for s, e in EAST.items():
            w = f'wbk_{s}'
            I[w]['master'] = 'ot_hbm_svc_wb_kport_q'; I[w]['source'] = WBKQ_SRC
            I[w]['note'] = I[w].get('note', '') + ' | d4g L1: ot_hbm_svc_wb_kport_q (quad 0, PCs 0..15, vmks_%s0..3)' % s
            for p in ('w_k_v', 'w_k_rdy', 'w_k_wr_done'):
                self.setp(w, p, 16)
            self.setp(w, 'w_k_addr', 480); self.setp(w, 'w_k_wdata', 4096)
            self.setp(w, 'quad', 1, 'input')
            ports = I[w]['ports']
            I[w]['ports'] = {k: ports[k] for k in ['stream_clk', 'stream_rst_n', 'hbm_clk', 'hbm_rst_n', 'stream_fifo_clk', 'stk', 'quad']
                             if k in ports} | {k: v for k, v in ports.items() if k not in ('stream_clk', 'stream_rst_n', 'hbm_clk', 'hbm_rst_n', 'stream_fifo_clk', 'stk', 'quad')}
            n = self.clone(w, f'wbk_{e}', slot=None, note=f'd4g L1: wbk_{e} = ot_hbm_svc_wb_kport_q quad 1 (PCs 16..31 of stack {s}, vmks_{s}4..7)')
            self.clone_clocks(w, f'wbk_{e}')
            self.strap(w, 'quad', 0, 'identity: quadrant half 0 (W, PCs 0..15) of the write-back K port (RBH-STK)')
            stk_v = next(x['value'] for x in self.c['straps'] if x['inst'] == w and x['port'] == 'stk')
            self.strap(f'wbk_{e}', 'stk', stk_v, 'Registered physical stack identity (same value as hb_dbk_<q>.stk); no runtime selection.')
            self.strap(f'wbk_{e}', 'quad', 1, 'identity: quadrant half 1 (E, PCs 16..31) of the write-back K port (RBH-STK)')
            # K ports: PC index >= 16 move to the E instance
            PW = {'w_k_v': 1, 'w_k_rdy': 1, 'w_k_wr_done': 1, 'w_k_addr': 30, 'w_k_wdata': 256}
            for ed in E:
                for end in ('source', 'sink'):
                    x = ed[end]
                    if x[0] == w and x[1] in PW and x[2] >= 16 * PW[x[1]]:
                        x[0] = f'wbk_{e}'; x[2] -= 16 * PW[x[1]]; x[3] -= 16 * PW[x[1]]
                        ed['region'] = REGION
            # wbw window: wbc_<E> now fed by wbk_<E>
            for ed in E:
                if ed['source'][0] == w and ed['sink'][0] == f'wbc_{e}':
                    ed['source'][0] = f'wbk_{e}'; ed['region'] = REGION
        # --- hb_dbk_<E>: clone of hb_dbk_<S> on the E quadrant's banks and wbk_<E>
        for s, e in EAST.items():
            d, de = f'hb_dbk_{s}', f'hb_dbk_{e}'
            self.clone(d, de, slot=None, note=f'd4g L1: per-quadrant DMA write-back, master unchanged (RBH-STK); banks vmb_{e}0..7 read group 1; F20 target {DBK_TGT[e]}')
            self.clone_clocks(d, de)
            for st in [x for x in self.c['straps'] if x['inst'] == d]:
                v = DBK_TGT[e] if st['port'] == 'tgt' else st['value']
                self.strap(de, st['port'], v, st['reason'] if st['port'] != 'tgt' else f'identity: F20 target id {v} (104 + QID {QID[e]})')
            new = []
            for ed in E:
                so, si = ed['source'], ed['sink']
                if si[0] == d and so[0] == 'host_cp_ingress':
                    new.append(edge(f'{ed["name"]}__{e}', so, [de] + si[1:], f'L1 host F20 broadcast to {de}'))
                elif si[0] == d and re.match(rf'^vmb_{s}\d$', so[0]):
                    new.append(edge(f'{ed["name"]}__{e}', [so[0].replace(s, e)] + so[1:], [de] + si[1:], 'L1 quadrant bank read return rr1'))
                elif so[0] == d and re.match(rf'^vmb_{s}\d$', si[0]):
                    new.append(edge(f'{ed["name"]}__{e}', [de] + so[1:], [si[0].replace(s, e)] + si[1:], 'L1 quadrant bank read request rq1'))
                elif si[0] == d and so[0] == f'wbk_{s}':
                    new.append(edge(f'{ed["name"]}__{e}', [f'wbk_{e}'] + so[1:], [de] + si[1:], 'L1 quadrant write-back'))
                elif so[0] == d and si[0] == f'wbk_{s}':
                    new.append(edge(f'{ed["name"]}__{e}', [de] + so[1:], [f'wbk_{e}'] + si[1:], 'L1 quadrant write-back'))
            self.add_edges(new)
            self.new_targets[de] = dict(tgt=DBK_TGT[e], ready='cp_configured', active='cp_active', fault=['cp_fault'])
            self.fr_add = getattr(self, 'fr_add', {})
            self.fr_add.setdefault(e, []).append([de, 'mv_fault', 0, 1])
            self.new_targets.setdefault(f'wbk_{e}', dict(tgt=None, fault=['fault']))
        # --- refcfg_<q> NPC16
        for s, e in EAST.items():
            r, re_ = f'refcfg_{s}', f'refcfg_{e}'
            I[r]['params'] = dict(I[r].get('params') or {}, NPC=16)
            self.setp(r, 'refresh_reload', 128)
            self.clone(r, re_, slot=None, note=f'd4g L1: refcfg per quadrant NPC16 (RBH-STK): PCs ctl_{s}_p16..p31, F20 target {REF_TGT[e]}')
            self.clone_clocks(r, re_)
            self.strap(re_, 'tgt', REF_TGT[e], f'identity: F20 target id {REF_TGT[e]} (refresh row of quadrant {e})')
            new = []
            for ed in list(E):
                so, si = ed['source'], ed['sink']
                if si[0] == r and so[0] == 'host_cp_ingress':
                    new.append(edge(f'{ed["name"]}__{e}', so, [re_] + si[1:], f'L1 host F20 broadcast to {re_}'))
                if so[0] == r and so[1] == 'refresh_reload':
                    pc = int(re.match(rf'^ctl_{s}_p(\d+)$', si[0]).group(1))
                    if pc >= 16:
                        so[0] = re_; so[2] -= 128; so[3] -= 128; ed['region'] = REGION
            self.add_edges(new)
            for x in self.c['clock_resets']:
                if x['source'] == [r, 'pc_rst_n'] and int(re.match(rf'^ctl_{s}_p(\d+)$', x['instance']).group(1)) >= 16:
                    x['source'] = [re_, 'pc_rst_n']
                    x['note'] = f'PC reset released only after the refresh row is loaded (one balanced reset tree per quadrant, d4g L1)'
            self.new_targets[re_] = dict(tgt=REF_TGT[e], ready='ready', active='active', fault=['fault'])
        # --- sfault_<q> NPC16 NG4 ND8 -> fs_<q> -> fr_<q>
        for s, e in EAST.items():
            f, fe = f'sfault_{s}', f'sfault_{e}'
            I[f]['params'] = dict(I[f].get('params') or {}, NPC=16, NG=4, ND=8)
            for p, b in (('row_v', 16), ('pc_fault', 16), ('owner_fault', 96), ('svg_fault', 4), ('share_fault', 4), ('del_fault', 8)):
                self.setp(f, p, b)
            self.clone(f, fe, slot=None, note=f'd4g L1: stack fault per quadrant NPC16 NG4 ND8 (RBH-STK): ctl_{s}_p16..31, svg/vmks_{s}4..7, vmdel_{e}0..7, vmfc_{e}')
            self.clone_clocks(f, fe)
            PW = {'row_v': 1, 'pc_fault': 1, 'owner_fault': 6, 'svg_fault': 1, 'share_fault': 1}
            new = []
            for ed in self.drop_edges(lambda ed: ed['sink'][0] == f):
                so, si = ed['source'], ed['sink']
                p = si[1]
                if p in ('row_v', 'pc_fault', 'owner_fault'):
                    k = int(re.match(rf'^ctl_{s}_p(\d+)$', so[0]).group(1))
                elif p in ('svg_fault', 'share_fault'):
                    k = int(re.match(rf'^(svg|vmks)_{s}(\d)$', so[0]).group(2)) * 1
                    k = k if k < 4 else 16 + (k - 4)          # encode E with offset 16 below
                elif p == 'del_fault':
                    new.append(ed); continue                  # W keeps vmdel_<S>0..7 (the W quadrant's 8 lanes)
                elif p == 'cal_fault':
                    new.append(ed)
                    new.append(edge(f'{ed["name"]}__{e}', [f'vmfc_{e}'] + so[1:], [fe] + si[1:], 'L1 quadrant fill calendar fault'))
                    continue
                else:
                    raise SystemExit(f'L1 sfault: unexpected input {p}')
                if k < 16:
                    new.append(ed)
                else:
                    sh = 16 * PW[p] if p in ('row_v', 'pc_fault', 'owner_fault') else 4 * PW[p]
                    new.append(edge(f'{ed["name"]}__{e}', so, [fe, p, si[2] - sh, si[3] - sh], 'L1 quadrant stack fault (E half)'))
            for b in range(8):
                new.append(edge(f'l1_{fe}_del_{b}', [f'vmdel_{e}{b}', 'fault', 0, 1], [fe, 'del_fault', b, b + 1],
                                f'L1 quadrant delivery lane fault vmdel_{e}{b}'))
            self.add_edges(new)
            # fs_<E>
            fs, fse = f'fs_{s}', f'fs_{e}'
            self.clone(fs, fse, slot=None, note=f'd4g L1: fault leaf of {fe} (N 8)')
            self.clone_clocks(fs, fse)
            self.add_edges([edge(f'l1_{fe}_fault', [fe, 'fault', 0, 1], [fse, 'in', 0, 1], 'L1 stack fault -> fault leaf'),
                            edge(f'l1_{fe}_status', [fe, 'status', 0, 7], [fse, 'in', 1, 8], 'L1 stack fault status -> fault leaf')])
            self.fr_add.setdefault(e, []).append([fse, 'fault', 0, 1])
        # --- fr_<E>: append the new fault inputs (stream domain: SYNC_MASK unchanged)
        for e, srcs in sorted(self.fr_add.items()):
            fr = f'fr_{e}'
            n0 = I[fr]['ports']['in']['bits']
            self.setp(fr, 'in', n0 + len(srcs))
            I[fr]['params'] = dict(I[fr]['params'], N=n0 + len(srcs))
            self.add_edges([edge(f'l1_{fr}_in{n0 + k}', s_, [fr, 'in', n0 + k, n0 + k + 1], f'L1 quadrant fault root input {s_[0]}.{s_[1]}')
                            for k, s_ in enumerate(srcs)])

    # ---------------------------------------------------------------- (c) HOST leaves + status
    def host(self):
        I, M = self.I, ld(LEAF_MAP)
        hs = I['host_status']
        NT0, NF0 = hs['params']['NT'], hs['params']['NF']
        J = M['join_d4g']
        # GEN0 join = the leaf map (NTm/NF m slots); slots an earlier layer appended (l3: smw_SE/NE 161/163) stay in place
        # as direct targets, and L1's own direct targets follow them.
        NTm, NFm = len(J['t_ready_perm']), len(J['t_fault_perm'])
        assert NTm <= NT0 and NFm <= NF0, (NTm, NFm, NT0, NF0)
        lim = dict(t_ready=NTm, t_active=NTm, t_fault=NFm)
        st_in = {}
        for ed in self.drop_edges(lambda ed: ed['sink'][0] == 'host_status' and ed['sink'][1] in lim and ed['sink'][2] < lim[ed['sink'][1]]):
            assert ed['bits'] == 1, ed
            st_in[(ed['sink'][1], ed['sink'][2])] = ed['source'][:2]
        if (NT0, NF0) != (NTm, NFm):
            self.rep['notes'].append(f'host_status slots kept from an earlier layer: t_ready/t_active {NTm}..{NT0 - 1}, t_fault {NFm}..{NF0 - 1}')
        # leaves
        cfg_sinks = {}
        for ed in self.c['edges']:
            if ed['source'][0] == 'host_cp_ingress' and ed['source'][1] in CFG_PORTS and ed['sink'][0] != 'host_status':
                cfg_sinks.setdefault(ed['sink'][0], []).append(ed)
        face = {}
        status = []          # host_status input k, per port: source endpoint
        via_leaf = set()     # r2: new targets whose status goes through their leaf
        pins = {}
        for q in QS:
            lf = M['leaves'][q]
            li = lf['instance']
            assert li not in I, li
            nt, nf = lf['NT'], lf['NF']
            ports = dict(clk=dict(direction='input', bits=1), rst_n=dict(direction='input', bits=1))
            ports.update({p: dict(direction='input', bits=w) for p, w in CFG_W.items()})
            for cp in ('a', 'b'):
                ports.update({f'{cp}_{p}': dict(direction='output', bits=w) for p, w in CFG_W.items()})
            ports.update(t_ready=dict(direction='input', bits=nt), t_active=dict(direction='input', bits=nt),
                         t_fault=dict(direction='input', bits=nf), s_ready=dict(direction='output', bits=nt),
                         s_active=dict(direction='output', bits=nt), s_fault=dict(direction='output', bits=nf))
            r2 = lf['master'].endswith('2')
            I[li] = dict(master=lf['master'], source=LEAF_SRC_R2 if r2 else LEAF_SRC, params={}, slot=None,
                         owner='host owner (HBM-B-RTL1 host leaf' + (', HBM-RTL5 r2)' if r2 else ')'),
                         region=REGION, rtl_deps=([LEAF_SRC] if r2 else []) + LEAF_DEPS, ports=ports,
                         note=f'd4g L1: host config/status leaf of quadrant {q} ({lf["kit"]}, NT{nt}/NF{nf}, CFG_LAT 2, ST_LAT 2)')
            self.rep['added_instances'].append(li)
            for p in ('clk', 'rst_n'):
                self.c['clock_resets'].append(dict(instance=li, port=p, bits=1, domain='stream', kind='clock' if p == 'clk' else 'reset',
                                                   source=['hb_ckgen', 'pll_stream' if p == 'clk' else 'por_stream']))
            self.c['edges'] += [edge(f'l1_{li}_{p}', ['host_cp_ingress', p, 0, w], [li, p, 0, w], 'L1 ingress -> quadrant host leaf (equal-age lane)')
                                for p, w in CFG_W.items()]
            for t in lf['copy_a_W_face']:
                face[t] = (li, 'a')
            for t in lf['copy_b_E_face']:
                face[t] = (li, 'b')
            pins[li] = {'a': 0, 'b': 0}
            # status: leaf inputs from the targets (checked against the GEN0 host_status driver)
            for port, order, sport in (('t_ready', lf['t_ready_order'], 's_ready'), ('t_active', lf['t_active_order'], 's_active'),
                                       ('t_fault', lf['t_fault_order'], 's_fault')):
                for row in order:
                    k, d4f, pin = row[:3]
                    mm = re.match(r'^(\w+)\.(\w+)\[0\]$', pin)
                    src = [mm.group(1), mm.group(2)]
                    if d4f is None:
                        # r2: a d4g-only source (new E target of (a)/(b)) through its leaf; created by xql()/stk()
                        if not self.has_port(*src):
                            raise SystemExit(f'L1 host r2: leaf {li} {port}[{k}] source {pin} missing (run after xql/stk)')
                        via_leaf.add(src[0])
                        self.c['edges'].append(edge(f'l1_{li}_{port}_{k}', src + [0, 1], [li, port, k, k + 1],
                                                    f'L1 new target status -> leaf {li} (r2 width)'))
                        continue
                    got = st_in.pop((port, d4f), None)
                    if got and got != src and got[0] == src[0]:
                        # same target, port renamed by an earlier layer (l3: hc_<q> qhub fault -> hcq_fault)
                        self.rep['notes'].append(f'{port}[{d4f}]: leaf map {pin} -> {got[0]}.{got[1]} (renamed by an earlier layer)')
                        src = got
                    if got != src:
                        raise SystemExit(f'L1 host: {port}[{d4f}] driver {got} != leaf map {pin}')
                    self.c['edges'].append(edge(f'l1_{li}_{port}_{k}', src + [0, 1], [li, port, k, k + 1], f'L1 target status -> leaf {li}'))
        if st_in:
            raise SystemExit(f'L1 host: host_status inputs not covered by the leaf map: {sorted(st_in)[:8]}')
        # targets' cfg from the leaf copy (new E targets: copy with fewer sink pins)
        for t in sorted(cfg_sinks, key=lambda t: (t not in face, t)):
            if t not in face:
                mq = re.search(r'_(SW|SE|NW|NE)(_|$)', t)
                if not mq:
                    raise SystemExit(f'L1 host: cfg target {t} without a quadrant leaf')
                li = M['leaves'][mq.group(1)]['instance']
                cp = 'a' if pins[li]['a'] <= pins[li]['b'] else 'b'
                face[t] = (li, cp)
                self.rep['notes'].append(f'new cfg target {t} on {li} copy {cp.upper()}')
            li, cp = face[t]
            for ed in cfg_sinks[t]:
                ed['source'] = [li, f'{cp}_{ed["source"][1]}'] + ed['source'][2:]
                ed['basis'] = f'L1: F20 bundle from quadrant leaf {li} copy {cp.upper()} (CFG_LAT 2)'
                ed['region'] = REGION
                pins[li][cp] += 1
        miss = sorted(set(face) - set(cfg_sinks))
        if miss:
            raise SystemExit(f'L1 host: leaf-map targets without an ingress cfg edge: {miss}')
        # host_status: leaf outputs in join_d4g order, then the direct new-target bits
        order = {'t_ready': [], 't_fault': []}
        for q in QS:
            lf = M['leaves'][q]; li = lf['instance']
            order['t_ready'] += [(li, k) for k in range(lf['NT'])]
            order['t_fault'] += [(li, k) for k in range(lf['NF'])]
        for port, sport, key in (('t_ready', 's_ready', 't_ready'), ('t_active', 's_active', 't_ready'), ('t_fault', 's_fault', 't_fault')):
            for j, (li, k) in enumerate(order[key]):
                self.c['edges'].append(edge(f'l1_hs_{port}_{j}', [li, sport, k, k + 1], ['host_status', port, j, j + 1], f'L1 leaf {li} status -> join'))
        J2 = M.get('join_d4g_r2')
        tg_hs = int(hs['params']['TGTS'].split("'h")[1], 16)
        if J2:
            # r2: leaf block = NTl / NFl slots; slots an earlier layer appended (NTm..NT0-1) move up behind the leaf block
            NTl, NFl = len(order['t_ready']), len(order['t_fault'])
            assert (NTl, NFl) == (J2['NT'], J2['NF']), (NTl, NFl, J2['NT'], J2['NF'])
            dT, dF = NTl - NTm, NFl - NFm
            tg = int(J2['TGTS'].split("'h")[1], 16)
            for j in range(NTm, NT0):
                tg |= ((tg_hs >> (8 * j)) & 0xff) << (8 * (j + dT))
            for ed in self.c['edges']:
                if (ed['sink'][0] == 'host_status' and ed['sink'][1] in lim and ed['sink'][2] is not None
                        and not ed['name'].startswith('l1_hs_')):
                    d_ = dF if ed['sink'][1] == 't_fault' else dT
                    ed['sink'] = ['host_status', ed['sink'][1], ed['sink'][2] + d_, ed['sink'][3] + d_]
            nt, nf = NT0 + dT, NF0 + dF
        else:
            tg = int(J['TGTS'].split("'h")[1], 16)
            for j in range(NTm, NT0):
                tg |= ((tg_hs >> (8 * j)) & 0xff) << (8 * j)
            nt, nf = NT0, NF0
        direct = []
        for t, d in sorted(self.new_targets.items(), key=lambda kv: (kv[1]['tgt'] is None, kv[1]['tgt'] or 0, kv[0])):
            if t in via_leaf:
                continue
            if d.get('tgt') is not None:
                if not self.has_port(t, d['ready']):
                    continue
                for port, pin in (('t_ready', d['ready']), ('t_active', d['active'])):
                    self.c['edges'].append(edge(f'l1_hs_{port}_{nt}', [t, pin, 0, 1], ['host_status', port, nt, nt + 1],
                                                f'L1 direct status of new target {t} (tgt {d["tgt"]}): closed leaf widths are exact'))
                tg |= d['tgt'] << (8 * nt)
                direct.append(dict(target=t, tgt=d['tgt'], t_ready=nt))
                nt += 1
            for pin in d['fault']:
                self.c['edges'].append(edge(f'l1_hs_t_fault_{nf}', [t, pin, 0, 1], ['host_status', 't_fault', nf, nf + 1],
                                            f'L1 direct fault of new source {t}: closed leaf widths are exact'))
                direct.append(dict(source=f'{t}.{pin}', t_fault=nf))
                nf += 1
        hs['params'].update(NT=nt, NF=nf, TGTS=f"{nt * 8}'h{tg:0{nt * 2}x}", GUARD=12)
        self.setp('host_status', 't_ready', nt); self.setp('host_status', 't_active', nt); self.setp('host_status', 't_fault', nf)
        hs['note'] = hs.get('note', '') + f' | d4g L1: leaves SW/SE/NW/NE (join_d4g order) + {nt - NT0} direct targets / {nf - NF0} direct faults; GUARD 12 + lane relay edges'
        # ingress TARGET_MASK
        ing = I['host_cp_ingress']
        mask = int(ing['params']['TARGET_MASK'].split("'h")[1], 16)
        add = [d['tgt'] for d in self.new_targets.values() if d.get('tgt') is not None]
        for t_ in add:
            mask |= 1 << t_
        ing['params']['TARGET_MASK'] = f"256'h{mask:x}"
        if J2 and direct:
            raise SystemExit(f'L1 host r2: new targets not carried by a leaf: {direct}')
        self.rep['host'] = dict(NT=[NT0, nt], NF=[NF0, nf], direct=direct, leaf_map=str(LEAF_MAP.relative_to(ROOT)),
                                via_leaf=sorted(via_leaf), mask_added=sorted(add), leaf_copy_sinks=pins,
                                leaf_widths={q: [M['leaves'][q]['NT'], M['leaves'][q]['NF']] for q in QS},
                                leaf_widths_needed_for_R4={'SE': [M['leaves']['SE']['NT'] + 3, M['leaves']['SE']['NF'] + 4],
                                                           'NE': [M['leaves']['NE']['NT'] + 3, M['leaves']['NE']['NF'] + 4]})

    # ---------------------------------------------------------------- bookkeeping
    def finish(self):
        c, I = self.c, self.I
        used = {(e['source'][0], e['source'][1]) for e in c['edges']} | {tuple(x['source'][:2]) for x in c['clock_resets']} \
            | {(p['instance'], p['port']) for p in c['die_pins'] if p['direction'] == 'output'}
        c['open_outputs'] = [[i, p, d['bits']] for i, inst in I.items() for p, d in inst['ports'].items()
                             if d['direction'] == 'output' and (i, p) not in used]
        drv = set()
        for e in c['edges']:
            drv |= {(e['sink'][0], e['sink'][1], b) for b in range(e['sink'][2], e['sink'][3])}
        for x in c['clock_resets']:
            drv |= {(x['instance'], x['port'], b) for b in range(x['bits'])}
        for s in c['straps']:
            drv |= {(s['inst'], s['port'], b) for b in range(s.get('lo', 0), s.get('hi', I[s['inst']]['ports'][s['port']]['bits']))}
        for p in c['die_pins']:
            if p['direction'] == 'input':
                drv |= {(p['instance'], p['port'], b) for b in range(p['bits'])}
        und = {}
        for i, inst in I.items():
            for p, d in inst['ports'].items():
                if d['direction'] == 'input':
                    n = sum(1 for b in range(d['bits']) if (i, p, b) not in drv)
                    if n:
                        und[f'{i}.{p}'] = n
        c['exposed_inputs'] = dict(ports=len(und), bits=sum(und.values()), by_owner={}, list=sorted(und))
        masters = {}
        for v in I.values():
            masters[v['master']] = masters.get(v['master'], 0) + 1
        c['masters'] = dict(sorted(masters.items()))
        c['summary'].update(instances=len(I), masters=len(masters), edges=len(c['edges']),
                            edge_bits=sum(e['bits'] for e in c['edges']), clock_reset_ports=len(c['clock_resets']),
                            straps=len(c['straps']), exposed_input_ports=len(und), exposed_input_bits=sum(und.values()),
                            open_output_ports=len(c['open_outputs']))
        c.setdefault('notes', [])
        note = ('d4g GEN1 L1 (H-D4G3b 10-18, tools/hbm_die_v16/d4g_layers/l1_host_xload_stack.py): x-load per quadrant (RBH-XQL, '
                'tgt 101/103), DMA write-back / wbk_q / wbc / sfault NPC16 / refcfg NPC16 per quadrant (RBH-STK, tgt 105/107, 128/129), '
                '4 host config/status leaves (hleaf_<q>, closed per-quadrant variants); new E targets report straight to host_status '
                '(NT %d, NF %d, GUARD 12 + lane relays)' % (I['host_status']['params']['NT'], I['host_status']['params']['NF']))
        if isinstance(c['notes'], list):
            c['notes'].append(note)
        else:
            c['notes'] = [c['notes'], note]
        # cross-quadrant check of the edges this layer wrote (host leaf <-> ingress / join and fault roots are R3-allowed)
        bad = []
        for e in c['edges']:
            if e.get('region') != REGION:
                continue
            qs = set()
            for x in (e['source'][0], e['sink'][0]):
                if x.startswith(('host_', 'hleaf_')):
                    continue
                m = re.search(r'_(SW|SE|NW|NE)(_|\d|$)', x)
                if m:
                    q = m.group(1)
                    mp = re.match(r'^(ctl|svg|vmks|sm|xc|cp_svg)_(SW|NW)_?p?(\d+)$', x)
                    if mp:
                        k = int(mp.group(3)); q = mp.group(2) if k < (16 if mp.group(1) == 'ctl' else 4) else EAST[mp.group(2)]
                    qs.add(q)
            if len(qs) > 1:
                bad.append(e['name'])
        self.rep['cross_quadrant_edges'] = bad
        self.rep['undriven_inputs'] = und
        return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--gen0-test', action='store_true', help='defer connections whose VM-layer endpoint is missing')
    a = ap.parse_args()
    c = ld(a.inp)
    n0 = (len(c['instances']), len(c['edges']))
    l = L(c, a.gen0_test)
    l.xql(); l.stk(); l.host()
    c = l.finish()
    l.rep.update(instances=[n0[0], len(c['instances'])], edges=[n0[1], len(c['edges'])], gen0_test=a.gen0_test)
    out = a.out
    (gzip.open(out, 'wt') if out.endswith('.gz') else open(out, 'w')).write(json.dumps(c, indent=1))
    json.dump(l.rep, open(a.report, 'w'), indent=1)
    print(json.dumps(dict(instances=l.rep['instances'], edges=l.rep['edges'], host=l.rep['host']['NT'] + l.rep['host']['NF'],
                          deferred=len(l.rep['deferred']), cross_quadrant=len(l.rep['cross_quadrant_edges']),
                          undriven_ports=len(l.rep['undriven_inputs']))))
    if l.rep['cross_quadrant_edges']:
        print('CROSS_QUADRANT', l.rep['cross_quadrant_edges'][:10]); sys.exit(2)


if __name__ == '__main__':
    main()
