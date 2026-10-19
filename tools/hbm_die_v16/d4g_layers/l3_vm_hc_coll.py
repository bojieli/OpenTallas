#!/usr/bin/env python3
"""H-D4G3b 10-18 (owner 0do, plan (b) d4g): GEN1 contract post-layer L3 -- VM per quadrant, HC split, COLL two rings.

    l3_vm_hc_coll.py IN_contract.json[.gz] OUT_contract.json --report R.json [--vm d4g|keep] [--hc split|keep]

Edits the d4g source contract (GEN0 = results/arch/hbm_die_d4g/gen0/contract.json.gz); die.v follows from it
(tools/hbm_die_v16/contract_die_v.py emit).  Every new instance's ports come from its RTL (tools/die_port_bind.py
parser, instance parameters applied); nothing is tied: an input without a producer in THIS layer stays undriven and is
listed in contract['gaps'] (region d4g_gen1_l3) with the layer / lane that owns its producer.

HC (--hc split; HBM-B-RTL2 / 2b, claude/hbm-b-rtl2-1017, split lockstep a143d1f5e, ring form 0015a8769, U decision 0dx)
  hc_eng   ot_hbm_hc_eng_static -> ot_hbm_hc_root_static (programme/table F20 164/165, HCP core TPRE 6 = the partial-sum
           tree root ((q0+q1)+(q2+q3)), mix store, table, tails; XRD = XRU = 0: the relay layer that puts stations on the
           root <-> hub links must set them to its stage counts -- compiler constant RAW0 = 165 + XRD + XRU).
  hc_<q>   ot_hbm_hc_q_static -> ot_hbm_hc_qhub_static (hc_q + quarter centre ot_hbm_hc_qcen_static; x_wave internal);
           port fault -> hcq_fault; eng_fault -> root q_fault[q]; quarter index q = SW 0, SE 1, NW 2, NE 3 (= the GEN0
           x_wave slice order, hidden lanes 64q .. 64q+63).
  hcb_<q><k>  8 bank tiles per quadrant wired exactly as the soft composition ot_hbm_hc_qeng_static (b0 bankq0 W,
           b2 / b6 bankq_ft N / S feeding corners 1, 3 / 5, 7, b4 bankq E; chain 0 -> 7, b7 exit -> b0 s_i -> hub s_i;
           regional resets rstb_* of the hub, corners through their feeding edge tile).
  U placement (0dx): recorded in the report (mouth = the side facing the quadrant's VM hub vmh_<q>); slots are the
  grants' / kit lane's.
VM (--vm d4g; HBM-B-RTL1b, claude/hbm-b-rtl1-vm-1017, results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json)
  hb_vms_SE/NE -> hfd_hgi_vms_static_{SE,NE}b_glue, vmb_SE/NE<b> -> hfd_vms_bank_native_q0_faces (gen_vms_hoist.py
  layer(qb=True) = tools/hbm_die_v15/v16_layers/vm_hoist_qb_d4g.json: masters, clocks, straps, internal edges checked
  equal); smw_<q> x4 = ot_hbm_sm_vm_wr_q_t_lanes4 (lane k: SM -> half 0 / half 1 bank wq1; NW through vmm_NW<b>);
  vmdel_<q><b> x32 = ot_hbm_svc_vmdel_lane_n NPC 2 (view hv18_vmdel_lane2, CLOSED); vmfc_<E> drives the E kshares and
  E lanes; new F20 targets smw_SE 161 / smw_NE 163 (host_status NT/NF/TGTS extended, ingress mask already admits them).
  hsm_smvm_wrq_t4_r1 (lanes4 kit) is NEEDS_RTL in the closure loop: smw_<q> bind as SYNTH of the RTL.
  OPEN after this layer (gaps): SE/NE hub cq (client 0 = quadrant IDX, HBM-B-RTL2 IDX quad lockstep pending) and SE/NE
  bank rq4 (IDX); rq1 (hb_dbk_SE/NE) / rq2 (xl_SE/NE_ctl) come from the host/x-load/stack layer, which must run AFTER
  this layer (it addresses the q0 bank ports); vmdel_<E>b.fault / vmfc_<E>.fault -> sfault_<E> (per-quadrant stack
  fault, same layer).  --vm keep leaves the VM as GEN0.
COLL two rings (HBM-B-RTL3c): NOT bound -- no die master instantiates ot_hgi_coll_ring_ag / _lane (the ring stop is
  u_ring = ot_hgi_coll_ring_v5 inside hb_coll_<q>; ring B needs its command source + a VM publish consumer).  The
  report carries the cut re-check (cut_ring2.py) and the ring-B slot call.
"""
import argparse, collections, copy, gzip, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v16'))
import die_port_bind as DPB  # noqa: E402
import gen_vms_hoist as GVH  # noqa: E402

REGION = 'd4g_gen1_l3'
Q4 = ['SW', 'SE', 'NW', 'NE']                 # HC quarter / x_wave index 0..3
HCD = 'rtl/hbm_accel/generic/peers/static_hc/'
VMD = 'rtl/hbm_accel/generic/vm/static/'
VMAP = ROOT / 'results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json'
STACK = dict(SW='SW', SE='SW', NW='NW', NE='NW')
WR_TGT = dict(SW=160, SE=161, NW=162, NE=163)
CK = ['hb_ckgen', 'pll_stream']; RST = ['hb_ckgen', 'por_stream']
UDRLY = 2                                      # HBM-RTL5 10-18 (0fi): HC hub DRLY / root QDRLY with the U-ring b7->b0 die relay
HC_CHX = 11                                    # HH-9 10-19: bank chain pin registers (CPI/CPO) = +11 chain edges per pass:
                                               # hub CHX / root QCHX 11; RAW0 + 11 (HCRING 10-19 binds them)
URLY_CLASSES = (1136, 624, 304)               # one b7->b0 relay stage: closed hbfd_rly classes side by side (2,064 >= 2,049 b)


def ld(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


class Rtl:
    def __init__(self):
        self.idx, _ = DPB.rtl_index(['rtl'], [], {'OT_SMH_FC_HIER': '1'}, [])

    def ports(self, master, params=None):
        m = self.idx[master]
        env = m.env(params or {})
        out = {}
        for p in m.order:
            w = m.width(p, env)
            if w is None:
                raise SystemExit(f'l3: {master}.{p}: width not evaluable with {params}')
            out[p] = dict(direction=m.ports[p][0], bits=w)
        return out

    def source(self, master):
        return str(Path(self.idx[master].path).resolve().relative_to(ROOT))

    def deps(self, master):
        seen, todo, files = set(), [master], set()
        while todo:
            n = todo.pop()
            if n in seen or n not in self.idx:
                continue
            seen.add(n)
            files.add(self.source(n))
            todo += sorted(DPB.instantiated(self.idx[n].body) - {n})
        return sorted(files - {self.source(master)})


class L3:
    def __init__(self, c, rtl):
        self.c, self.R = c, rtl
        self.I, self.E, self.CR, self.ST = c['instances'], c['edges'], c['clock_resets'], c['straps']
        self.n = 0
        self.log = collections.Counter()
        self.gaps = []

    # ---------------------------------------------------------------- primitives
    def edge(self, src, snk, basis, clock='stream'):
        s0, s1 = src[2], src[3]; d0, d1 = snk[2], snk[3]
        assert s1 - s0 == d1 - d0 and s1 > s0, (src, snk)
        self.n += 1
        self.E.append(dict(name=f'l3_{self.n:05d}', bits=s1 - s0, source=list(src), sink=list(snk), clock=clock,
                           ready_or_credit=False, allowed_exception=None, basis=basis, region=REGION))
        self.log['edges_added'] += 1

    def drop_edges(self, pred):
        k = len(self.E)
        self.E[:] = [e for e in self.E if not pred(e)]
        self.log['edges_dropped'] += k - len(self.E)
        return k - len(self.E)

    def inst(self, name, master, params, slot, note, owner):
        self.I[name] = dict(master=master, source=self.R.source(master), params=dict(params), slot=slot, owner=owner,
                            region=REGION, note=note, replaces_v15=None, rtl_deps=self.R.deps(master),
                            ports=self.R.ports(master, params))
        self.log['instances_added'] += 1

    def remaster(self, name, master, params, note):
        i = self.I[name]
        old = i['master']
        i.update(master=master, source=self.R.source(master), params=dict(params), rtl_deps=self.R.deps(master),
                 ports=self.R.ports(master, params), region=REGION, note=(i.get('note') or '') + f' | {REGION}: {old} -> {master}; {note}')
        for s in self.ST:
            if s['inst'] == name:
                s['master'] = master
        self.log['remastered'] += 1

    def clock(self, name, port, kind='clock', src=None):
        self.CR.append(dict(instance=name, port=port, bits=self.I[name]['ports'][port]['bits'], domain='stream', kind=kind,
                            source=list(src or (CK if kind == 'clock' else RST))))

    def strap(self, name, port, value, reason):
        b = self.I[name]['ports'][port]['bits']
        self.ST.append(dict(inst=name, port=port, value=value, reason=reason, lo=0, hi=b, master=self.I[name]['master']))

    def drop_inst(self, name):
        self.I.pop(name)
        self.drop_edges(lambda e: e['source'][0] == name or e['sink'][0] == name)
        self.CR[:] = [x for x in self.CR if x['instance'] != name]
        self.ST[:] = [s for s in self.ST if s['inst'] != name]
        self.log['instances_dropped'] += 1

    def gap(self, gid, owner, missing, affects, note):
        self.gaps.append(dict(id=gid, owner=owner, missing_rtl=missing, affects=affects, note=note, region=REGION))

    def host_slots(self, items):
        """append F20 status targets [(tid, inst)] to host_status (t_ready/t_active index NT+k, t_fault NF+k)"""
        hs = self.I['host_status']; ing = self.I['host_cp_ingress']
        nt, nf = int(hs['params']['NT']), int(hs['params']['NF'])
        w, h = hs['params']['TGTS'].split("'h")
        for k, (tid, n) in enumerate(items):
            self.edge([n, 'configured', 0, 1], ['host_status', 't_ready', nt + k, nt + k + 1], 'F20 status slot')
            self.edge([n, 'active', 0, 1], ['host_status', 't_active', nt + k, nt + k + 1], 'F20 status slot')
            self.edge([n, 'fault', 0, 1], ['host_status', 't_fault', nf + k, nf + k + 1],
                      'static component sticky fault observation; never reschedules execution')
        add = ''.join(f'{t:02x}' for t, _ in reversed(items))
        hs['params']['TGTS'] = f"{int(w) + 8 * len(items)}'h{add}{h}"
        hs['params']['NT'] = nt + len(items); hs['params']['NF'] = nf + len(items)
        for p in ('t_ready', 't_active'):
            hs['ports'][p]['bits'] = nt + len(items)
        hs['ports']['t_fault']['bits'] = nf + len(items)
        mw, mh = ing['params']['TARGET_MASK'].split("'h")
        v = int(mh, 16)
        for t, _ in items:
            v |= 1 << t
        ing['params']['TARGET_MASK'] = f"{mw}'h{v:0{len(mh)}x}"

    # ---------------------------------------------------------------- HC
    def hc(self, rep):
        I = self.I
        assert I['hc_eng']['master'] == 'ot_hbm_hc_eng_static', I['hc_eng']['master']
        B = 'HBM-B-RTL2b split HC (ot_hbm_hc_qeng_static soft composition lifted to die; lockstep a143d1f5e)'
        # x_wave link is internal to the hub now
        self.drop_edges(lambda e: e['sink'][0] == 'hc_eng' and e['sink'][1].startswith('x_wave'))
        self.remaster('hc_eng', 'ot_hbm_hc_root_static', {'QDRLY': UDRLY, 'QCHX': HC_CHX}, 'centre HC root: programme/table/core TPRE 6/mix/tails; XRD=XRU=0 '
                      '(set to the root<->hub relay stage counts when the relay layer stations those links); QDRLY 2 = '
                      'the U-ring b7->b0 die relay (HBM-RTL5, coordinator 0fi)')
        try:                                               # U mouth per quadrant -> flow of the b7->b0 relay
            P = json.loads((ROOT / 'results/arch/hbm_die_d4g/plan/d4g_phy/compact.P.json').read_text())
        except Exception:
            P = {}
        urly = {}
        for qi, q in enumerate(Q4):
            h = f'hc_{q}'
            assert I[h]['master'] == 'ot_hbm_hc_q_static', I[h]['master']
            self.remaster(h, 'ot_hbm_hc_qhub_static', {'DRLY': UDRLY, 'CHX': HC_CHX}, f'quarter {qi} hub = hc_q + qcen (x_wave internal, 0dx U mouth = '
                          'VM face); DRLY 2: descriptor relay 2 + exit budget 2 = bank 0 register + the b7->b0 die relay')
            for e in self.E:
                if e['source'][:2] == [h, 'fault']:
                    e['source'][1] = 'hcq_fault'
            r = 'hc_eng'
            for rp, hp, w in (('qd_v', 'd_v', 1), ('qd_ss', 'd_ss', 1), ('qd_nv', 'd_nv', 7), ('qd_wa', 'd_wa', 10), ('qd_xa', 'd_xa', 10),
                              ('qi_v', 'i_v', 1), ('qi_kind', 'i_kind', 1), ('qi_slot', 'i_slot', 2), ('qi_lo', 'i_lo', 5),
                              ('qi_w', 'i_w', 5), ('qi_cnt', 'i_cnt', 12), ('qi_word', 'i_word', 10)):
                self.edge([r, rp, qi * w, qi * w + w], [h, hp, 0, w], B + ': root -> quarter descriptor / ingest')
            for hp, rp, w in (('ps_v', 'qps_v', 1), ('ps', 'qps', 32), ('ps_f', 'qps_f', 1), ('eng_fault', 'q_fault', 1)):
                self.edge([h, hp, 0, w], [r, rp, qi * w, qi * w + w], B + ': quarter subtree sum -> root')
            # bank tiles
            M = {0: 'ot_hbm_hc_bankq0_static', 2: 'ot_hbm_hc_bankq_ft_static', 6: 'ot_hbm_hc_bankq_ft_static'}
            bk = {k: f'hcb_{q}{k}' for k in range(8)}
            for k in range(8):
                m = M.get(k, 'ot_hbm_hc_bankq_static')
                # HH-9 chain pin registers: b0 CPO 1, banks 1/3/4/5/7 CPI = CPO = 1, edge banks 2/6 none (their kits' params)
                self.inst(bk[k], m, {'DRLY': 1, 'CPO': 1} if k == 0 else ({} if k in (2, 6) else {'CPI': 1, 'CPO': 1}), f'hcb_{q}{k}',
                          f'HC quarter {qi} ({q}) bank tile {k} (term k of every 8-term chunk; ring form 0015a8769, U 0dx)', 'HBM-B-RTL2/H-D4G')
                self.clock(bk[k], 'clk')
            # chain 0 -> 7
            for k in range(7):
                a, b = bk[k], bk[k + 1]
                for o, d, w in (('o_v', 'd_v', 1), ('o_ss', 'd_ss', 1), ('o_nv', 'd_nv', 7), ('o_wa', 'd_wa', 10), ('o_xa', 'd_xa', 10),
                                ('sum_out', 'sum_in', 2048), ('f_out', 'f_in', 1)):
                    self.edge([a, o, 0, w], [b, d, 0, w], B + f': bank chain {k} -> {k + 1}')
            for o, d, w in (('bd_v', 'd_v', 1), ('bd_ss', 'd_ss', 1), ('bd_nv', 'd_nv', 7), ('bd_wa', 'd_wa', 10), ('bd_xa', 'd_xa', 10)):
                self.edge([h, o, 0, w], [bk[0], d, 0, w], B + ': hub descriptor -> bank 0')
            # b7 -> b0 chain exit: ONE die relay stage (coordinator 0fi: keep the 3x3 U, closed relay, latency accepted),
            # 2,049 b = hbfd_rly_1136 + 624 + 304 side by side (2,064 b, spare 2,049..2,063 tied low), rs = the hub's
            # bank-0 regional reset (rstb_w[0], as bank 0; s_i is unread until the subtree valid, VD = SB + DRLY).
            e_, v_ = P.get(f'hce_{q}'), P.get(f'vmh_{q}')
            mouth = ('E' if v_['x'] + v_['w'] / 2 > e_['x'] + e_['w'] / 2 else 'W') if e_ and v_ else 'W'
            fl = 'WE' if mouth == 'E' else 'EW'            # b7 (U bottom, far side) -> b0 (beside the hub on the mouth)
            src = [[bk[7], 'sum_out', 0, 2048], [bk[7], 'f_out', 0, 1]]
            lo = 0
            for j, wcl in enumerate(URLY_CLASSES):
                rn = f'hcx_{q}_{j}'
                m = f'hbfd_rly_{wcl}_{fl}'
                self.inst(rn, m, {}, f'hcb_{q}0', f'HC quarter {qi} ({q}) U-ring b7->b0 die relay, bits {lo}..{lo + wcl - 1} of the '
                          f'2,049-b chain exit (flow {fl}, mouth {mouth}); one register edge (HBM-RTL5, coordinator 0fi)', 'HBM-RTL5/H-D4G')
                self.clock(rn, 'ck')
                self.edge([h, 'rstb_w', 0, 1], [rn, 'rs', 0, 1], B + ': U relay reset = bank 0 regional reset')
                use = min(wcl, 2049 - lo)
                if lo < 2048:
                    n_ = min(use, 2048 - lo)
                    self.edge([bk[7], 'sum_out', lo, lo + n_], [rn, 'i', 0, n_], B + f': bank 7 chain exit -> U relay {j}')
                    self.edge([rn, 'o', 0, n_], [bk[0], 's_i', lo, lo + n_], B + f': U relay {j} -> bank 0 exit relay')
                    if use > n_:                       # the lane fault bit rides the last class
                        self.edge([bk[7], 'f_out', 0, 1], [rn, 'i', n_, n_ + 1], B + ': bank 7 chain exit fault -> U relay')
                        self.edge([rn, 'o', n_, n_ + 1], [bk[0], 's_i', 2048, 2049], B + ': U relay fault -> bank 0 exit relay')
                if use < wcl:
                    self.ST.append(dict(inst=rn, port='i', lo=use, hi=wcl, value=0, master=m,
                                        reason=f'PAD (DEDUPE standard relay hbfd_rly_{wcl}, logical width {use}, spare bits '
                                               f'{use}..{wcl - 1} tied low; outputs open) -- relay class rule, ot_hbm_rly.sv'))
                lo += wcl
            urly[q] = dict(relays=[f'hcx_{q}_{j}' for j in range(len(URLY_CLASSES))], classes=list(URLY_CLASSES), flow=fl, mouth=mouth)
            self.edge([bk[0], 's_o', 0, 2049], [h, 's_i', 0, 2049], B + ': bank 0 relay -> hub (centre tree)')
            # faces: (bank, xb_v port, xb_beat port, wc port, wfault port+bit, reset port+bit)
            face = {0: ('xb_v', 'xb_beat', 'wc_w', ('wf_w', 0), ('rstb_w', 0)),
                    2: ('xb_v_n', 'xb_beat_n', 'wc_n', ('wf_n', 1), ('rstb_n', 1)),
                    4: ('xb_v_e', 'xb_beat_e', 'wc_e', ('wf_e', 0), ('rstb_e', 0)),
                    6: ('xb_v_s', 'xb_beat_s', 'wc_s', ('wf_s', 1), ('rstb_s', 1))}
            for k, (xv, xbt, wc, (wfp, wfb), (rp, rb)) in face.items():
                t = bk[k]
                self.edge([h, xv, 0, 1], [t, 'xb_v', 0, 1], B + ': beat valid'); self.edge([h, xbt, 0, 2], [t, 'xb_beat', 0, 2], B + ': beat index')
                self.edge([h, f'xb_d{k}', 0, 256], [t, 'xb_d', 0, 256], B + f': x_wave beat slice {k}')
                for p, lo, hi in (('wv', 12, 13), ('xv', 11, 12), ('j', 10, 11), ('wa', 0, 10)):
                    self.edge([h, wc, lo, hi], [t, p, 0, hi - lo], B + f': {wc} write control')
                self.edge([t, 'wfault', 0, 1], [h, wfp, wfb, wfb + 1], B + ': bank residual-check fault')
                self.edge([h, rp, rb, rb + 1], [t, 'rst_n', 0, 1], B + ': regional reset (ot_rst_relay region)')
                if k in (2, 6):                                    # corner feeds a = k-1, b = k+1
                    for side, kc, rbit in (('fa', k - 1, rb - 1), ('fb', k + 1, rb + 1)):
                        c = bk[kc]
                        self.edge([h, xv, 0, 1], [t, f'{side}_xb_v', 0, 1], B + ': corner feed beat valid')
                        self.edge([h, xbt, 0, 2], [t, f'{side}_xb_beat', 0, 2], B + ': corner feed beat index')
                        self.edge([h, f'xb_d{kc}', 0, 256], [t, f'{side}_xb_d', 0, 256], B + f': corner {kc} beat slice')
                        for p, lo, hi in (('wv', 12, 13), ('xv', 11, 12), ('j', 10, 11), ('wa', 0, 10)):
                            self.edge([h, wc, lo, hi], [t, f'{side}_{p}', 0, hi - lo], B + ': corner feed write control')
                        self.edge([h, rp, rbit, rbit + 1], [t, f'{side}_rst_n', 0, 1], B + ': corner reset through the edge tile')
                        for p, w in (('xb_v', 1), ('xb_beat', 2), ('xb_d', 256), ('wv', 1), ('xv', 1), ('j', 1), ('wa', 10)):
                            self.edge([t, f'{side}_{p}_o', 0, w], [c, p, 0, w], B + f': feed register -> corner {kc}')
                        self.edge([t, f'{side}_rst_n_o', 0, 1], [c, 'rst_n', 0, 1], B + f': corner {kc} reset')
                        self.edge([c, 'wfault', 0, 1], [t, f'{side}_wfault', 0, 1], B + f': corner {kc} fault -> edge tile')
                        self.edge([t, f'{side}_wfault_o', 0, 1], [h, wfp, rbit, rbit + 1], B + f': corner {kc} fault registered back')
        rep['hc'] = dict(root='hc_eng = ot_hbm_hc_root_static (XRD 0 / XRU 0, QDRLY 2, QCHX 11)', chain_pin_registers=dict(
                             hub_CHX=HC_CHX, root_QCHX=HC_CHX, banks='b0 CPO 1; b1/b3/b4/b5/b7 CPI=CPO=1; b2/b6 none',
                             compiler='HH-9: HC chain +11 edges -> RAW0 + 11, root SYS_LAT + 11, pops / tail launches / emits + 11'),
                         u_ring_relay=dict(per_quadrant=urly, hub_DRLY=UDRLY, root_QDRLY=UDRLY, bank0_DRLY=1,
                                           edge='bank 7 chain exit (sum_out 2,048 + f_out 1) -> 1 die relay stage -> bank 0 s_i',
                                           compiler='HC exit path +1 edge (die relay) and descriptor relay +1 edge (hub DRLY 2): '
                                                    'chain/subtree/root timing = the DRLY 2 form; RAW0 165 -> 167 + 11 (HH-9 CHX) + XRD + XRU '
                                                    '(pops / tail launches / emits +2); the bench measures it',
                                           bench='results/rtl/hbm_rtl5_hc_uring_1018 (ring lockstep XRLY 1)'), hubs={q: f'hc_{q}' for q in Q4},
                         banks=sum(8 for _ in Q4), quarter_index={q: i for i, q in enumerate(Q4)},
                         compiler='RAW0 165 + 2 (U relay) + 11 (HH-9 chain pin registers) + XRD + XRU (was 137 single block); corner banks 1/3/5/7 wave landing +1 edge (feed register); '
                                  'residual fault +2..+3 edges (sticky only)',
                         u_placement=self.hc_u(rep))

    def hc_u(self, rep):
        try:
            P = json.loads((ROOT / 'results/arch/hbm_die_d4g/plan/d4g_phy/compact.P.json').read_text())
        except Exception as ex:      # placement intent only
            return dict(error=str(ex))
        out = {}
        for q in Q4:
            e, v = P.get(f'hce_{q}'), P.get(f'vmh_{q}')
            if not e or not v:
                continue
            ex, vx = e['x'] + e['w'] / 2, v['x'] + v['w'] / 2
            mouth = 'E' if vx > ex else 'W'
            out[q] = dict(engine_block=f'hce_{q}', vm_hub=f'vmh_{q}', mouth=mouth,
                          rule='8 bank tiles in a U around hc_<q>; the hub VM/LG face (lg_rq/lg_wq/lg_rr 4,448 b) on the open side '
                               f'({mouth}, toward vmh_{q}); x_wave stays inside the hub',
                          hub_cell=f'{mouth}-middle of the U footprint', bank_order='b0 next to the hub (descriptor), chain b0..b7 around '
                          'the U, b7 back to b0 (s_i relay)',
                          note='a 3x3 footprint with the hub on the mouth cell cannot keep b0..b7 + b7->b0 all edge-adjacent '
                               '(bipartite count 5/3): the U needs a 3x4 footprint or the existing DRLY relay on the b7->b0 exit; '
                               'the hub kit (hbm_hcq_hub_1017) has LG on N/E and banks on all 4 faces -> re-pin owed to the kit lane')
        return out

    # ---------------------------------------------------------------- VM
    def vm(self, rep):
        I, E = self.I, self.E
        M = json.loads(VMAP.read_text())['quadrants']
        QB = GVH.layer(qb=True)
        B = 'HBM-B-RTL1b d4g VM per quadrant (vm_quadrant_map.json; VMS_QB_EQUIV / WRQ4 / VMDEL_N benches)'
        # -- 1. E hubs + banks (gen_vms_hoist qb layer)
        for hub, r in QB['remaster'].items():
            assert I[hub]['master'].endswith('_glue') and not I[hub]['master'].endswith('b_glue'), I[hub]['master']
            self.remaster(hub, r['master'], {}, 'E-quadrant hub with the SM client side (NC 1, RG 5, WG 2)')
            q = hub[-2:]
            cal = f'calendar_{q}'
            for e in E:     # calendar -> hub client fields widen to NC 1 (same calendar output, lower bits)
                if e['source'][0] == cal and e['sink'][0] == hub and e['sink'][1] in ('client_seq', 'response_enable', 'response_seq'):
                    w = I[hub]['ports'][e['sink'][1]]['bits']
                    e['source'][3] = e['source'][2] + w; e['sink'][3] = w; e['bits'] = w
                    e['basis'] = (e.get('basis') or '') + f' | {REGION}: NC 1 width'
            self.gap(f'G-D4G-L3-IDXQ-{q}', 'HBM-B-RTL2 (IDX quad client, claude/hbm-b-rtl2-idx-1017, lockstep pending)',
                     f'{hub}.cq[337:0] (hub client 0 = quadrant IDX ctl/query) and vmb_{q}0..7.rq4 (IDX read group 4)',
                     [[hub, 'cq', 0, 338]] + [[f'vmb_{q}{b}', 'rq4', 0, 17] for b in range(8)],
                     'bind the per-quadrant IDX client (ot_hbm_idx_client_static_quad) when its lockstep passes')
            self.gap(f'G-D4G-L3-DBKXL-{q}', 'H-D4G host/x-load/stack layer (xql_quadrant_rebind 101/103, hb_dbk_SE/NE 105/107)',
                     f'vmb_{q}0..7.rq1 (DMA-back) and .rq2 (x-load)',
                     [[f'vmb_{q}{b}', p, 0, 17] for b in range(8) for p in ('rq1', 'rq2')],
                     'that layer must run AFTER l3 (it addresses the q0 bank ports)')
        qb_inst = {x['name']: x for x in QB['instances']}
        for n, x in qb_inst.items():
            assert I[n]['master'] == 'hfd_vms_bank_native_q1_core_pr', (n, I[n]['master'])
            self.remaster(n, x['master'], {}, 'q0 bank shape (SW numbering r0 LG 1 DMA 2 XL 3 COLL 4 IDX, w0 LG 1 SM writer)')
        have = {(x['instance'], x['port']) for x in self.CR}
        for x in QB['clocks']:
            if (x['inst'], x['port']) not in have:
                self.clock(x['inst'], x['port'], x['kind'])
        for s in QB['straps']:
            st = [t for t in self.ST if t['inst'] == s['inst'] and t['port'] == s['port']]
            assert len(st) == 1 and st[0]['value'] == s['value'], (s, st)
        # internal hub <-> bank edges must be exactly the qb layer's
        want = {(tuple(x['src']), tuple(x['dst'])) for x in QB['edges']}
        got = set()
        for e in E:
            s, d = e['source'], e['sink']
            if (s[0] in qb_inst or d[0] in qb_inst) and (s[0] in qb_inst or s[0] in QB['remaster']) and (d[0] in qb_inst or d[0] in QB['remaster']):
                ss = (s[0], s[1], s[2], s[3]) if s[0] in QB['remaster'] else (s[0], s[1])
                dd = (d[0], d[1], d[2], d[3]) if d[0] in QB['remaster'] else (d[0], d[1])
                got.add((ss, dd))
        if want != got:
            raise SystemExit(f'l3: E hub<->bank edges differ from vm_hoist_qb_d4g: missing {sorted(want - got)[:4]} extra {sorted(got - want)[:4]}')
        # -- 2. SM writers: one ot_hbm_sm_vm_wr_q_t_lanes4 per quadrant
        old = {}
        for s in ('SW', 'NW'):
            n = f'smw_{s}'
            assert I[n]['master'] == 'ot_hbm_sm_vm_wr_q_t_lanes', I[n]['master']
            old[s] = [copy.deepcopy(e) for e in E if e['sink'][0] == n or e['source'][0] == n]
            self.drop_inst(n)
        new_slots = []
        for q in Q4:
            n = f'smw_{q}'; wr = M[q]['writer']; S = STACK[q]
            self.inst(n, 'ot_hbm_sm_vm_wr_q_t_lanes4', {'DEPTH': 4}, f'vmh_{q}',
                      f'quadrant SM->VM writer (4 SMs, 2 banks per SM; view kit hsm_smvm_wrq_t4_r1 NEEDS_RTL -> SYNTH)', 'HBM-B-RTL1/H-D4G')
            for p in ('clk', 'clk_cal') + tuple(f'clk_l{k}' for k in range(4)):
                self.clock(n, p)
            self.clock(n, 'rst_n', 'reset')
            self.strap(n, 'tgt', WR_TGT[q], f'identity: F20 target id {WR_TGT[q]} of {n}')
            self.strap(n, 'quad', wr['straps']['quad'], f'identity: quadrant {wr["straps"]["quad"]} of {n}')
            self.strap(n, 'lbase', wr['straps']['lbase'], 'identity: bank base (0 = W: half 0 = banks 0-3; 1 = E: half 0 = banks 4-7)')
            for e in old[S]:        # host config / descriptor / launch: same producer, same bits
                if e['sink'][0] == f'smw_{S}' and e['source'][0] == 'host_cp_ingress':
                    self.edge(e['source'], [n] + e['sink'][1:], e.get('basis') or B)
            if q in ('SW', 'NW'):   # W writers keep their F20 status slots
                for e in old[S]:
                    if e['source'][0] == f'smw_{S}' and e['sink'][0] == 'host_status':
                        self.edge([n] + e['source'][1:], e['sink'], e.get('basis') or B)
            else:
                new_slots.append((WR_TGT[q], n))
            for k, ln in sorted(wr['lanes'].items(), key=lambda t: int(t[0])):
                k = int(k); sm = ln['sm']
                for sp, wp, w in (('rv', 'rv_s', 1), ('rrow', 'rrow_s', 12), ('rdata', 'rdata_s', 256), ('fault', 'smf_s', 1),
                                  ('schedule_fault', 'sms_s', 1)):
                    self.edge([sm, sp, 0, w], [n, f'{wp}{k}', 0, w], B + f': {sm} result lane {k}')
                for half, wp in (('half0_bank', 'wq_s'), ('half1_bank', 'wq_t')):
                    bank = ln[half]
                    tgt = (f'vmm_NW{bank[-1]}', 'wq1') if q == 'NW' else (bank, 'wq1')
                    self.edge([n, f'{wp}{k}', 0, 281], [tgt[0], tgt[1], 0, 281], B + f': writer lane {k} {half} -> {bank}')
        self.host_slots(new_slots)
        # -- 3. delivery lanes: 32 x ot_hbm_svc_vmdel_lane_n NPC 2
        for s in ('SW', 'NW'):
            for b in range(8):
                self.drop_inst(f'vmdel_{s}{b}')
        # begin / start from the quadrant's fill calendar: the GEN0 vmfc_SW -> vmdel_SW0 field map (broadcast to every lane)
        fc_tpl = [(tuple(e['source'][1:]), tuple(e['sink'][1:])) for e in self._fill_tpl]
        assert len(fc_tpl) == 11, len(fc_tpl)
        for q in Q4:
            fc = M[q]['fill_calendar']['inst']
            for b in range(8):
                n = f'vmdel_{q}{b}'; d = M[q]['delivery_lanes'][n]
                self.inst(n, 'ot_hbm_svc_vmdel_lane_n', {'NPC': 2}, f'vmh_{q}',
                          f'{q} delivery lane {b} (NPC 2; view hv18_vmdel_lane2 CLOSED)', 'HBM-B-RTL1/H-D4G')
                self.clock(n, 'clk'); self.clock(n, 'rst_n', 'reset')
                self.strap(n, 'bank_id', d['straps']['bank_id'], 'IDENTITY: VM bank index of this delivery lane')
                for slot, ref in sorted(d['fill_slots'].items()):
                    m = re.match(r'(vmks_\w+)\.fill_\*\[lane (\d)\]', ref); ks, ln = m.group(1), int(m.group(2)); sl = int(slot)
                    for p, w in (('fill_v', 1), ('fill_bank', 1), ('fill_slot', 6), ('fill_epoch', 16), ('fill_data', 256)):
                        self.edge([ks, p, ln * w, ln * w + w], [n, p + '_i', sl * w, sl * w + w], B + f': {ks} lane {ln} -> slot {sl}')
                ring = d['status_ring']
                for k, other in enumerate(ring):
                    for p in ('full0', 'full1', 'pcbad'):
                        self.edge([other, p, 0, 1], [n, p + '_all', k, k + 1], B + ': quadrant status ring (STATUS_LAT 2)')
                bank = d['dq'].split('.')[0]
                self.edge([n, 'dq', 0, 281], [bank, 'dq', 0, 281], B + ': delivery beat -> bank dq')
                sf = f'sfault_{q}' if f'sfault_{q}' in I else (f'sfault_{STACK[q]}' if q == STACK[q] else None)
                if sf and q == STACK[q]:
                    self.edge([n, 'fault', 0, 1], [sf, 'del_fault', b, b + 1], B + ': lane fault -> stack fault')
                elif sf:
                    self.edge([n, 'fault', 0, 1], [sf, 'del_fault', b, b + 1], B + ': lane fault -> quadrant stack fault')
        for q in Q4:
            fc = M[q]['fill_calendar']['inst']
            for b in range(8):
                for (sp, s0, s1), (dp, d0, d1) in fc_tpl:
                    self.edge([fc, sp, s0, s1], [f'vmdel_{q}{b}', dp, d0, d1], B + f': {fc} begin/start fields')
            # the E kshares' vm_* fields move from the W fill calendar to the E one (same field map)
            for ks in M[q]['vm_share']:
                for e in E:
                    if e['sink'][0] == ks and e['sink'][1].startswith('vm_') and e['source'][0].startswith('vmfc_') and e['source'][0] != fc:
                        e['source'][0] = fc; e['basis'] = (e.get('basis') or '') + f' | {REGION}: quadrant fill calendar'
                        self.log['kshare_vm_moved'] += 1
            if f'sfault_{q}' not in I and q != STACK[q]:
                self.gap(f'G-D4G-L3-SFAULT-{q}', 'H-D4G host/x-load/stack layer (sfault_<q> NPC16 ND8, stk_quadrant_services.json)',
                         f'observer of vmdel_{q}0..7.fault and vmfc_{q}.fault (open outputs until sfault_{q} exists)',
                         [[f'vmdel_{q}{b}', 'fault', 0, 1] for b in range(8)], 'outputs only (not a bind failure)')
        rep['vm'] = dict(hubs={h: r['master'] for h, r in QB['remaster'].items()}, banks_remastered=len(qb_inst),
                         writers={q: f'smw_{q} lanes4 tgt {WR_TGT[q]}' for q in Q4}, new_status_targets=[t for t, _ in new_slots],
                         delivery_lanes=32, kshare_vm_moved=self.log['kshare_vm_moved'])

    # ---------------------------------------------------------------- finish
    def finish(self):
        c = self.c
        used = {(e['source'][0], e['source'][1]) for e in self.E} | {tuple(x['source'][:2]) for x in self.CR}
        pins = {(x['instance'], x['port']) for x in c['die_pins']}
        c['open_outputs'] = [[i, p, d['bits']] for i, v in self.I.items() for p, d in v['ports'].items()
                             if d['direction'] == 'output' and (i, p) not in used and (i, p) not in pins]
        drv = collections.defaultdict(set)
        for e in self.E:
            for b in range(e['sink'][2], e['sink'][3]):
                drv[(e['sink'][0], e['sink'][1])].add(b)
        for x in self.CR:
            drv[(x['instance'], x['port'])] |= set(range(x['bits']))
        for s in self.ST:
            drv[(s['inst'], s['port'])] |= set(range(s.get('lo', 0), s.get('hi', self.I[s['inst']]['ports'][s['port']]['bits'])))
        for x in c['die_pins']:
            if x['direction'] == 'input':
                drv[(x['instance'], x['port'])] |= set(range(x['bits']))
        ex = []
        for i, v in self.I.items():
            for p, d in v['ports'].items():
                if d['direction'] == 'input':
                    miss = d['bits'] - len(drv.get((i, p), set()) & set(range(d['bits'])))
                    if miss:
                        ex.append([i, p, miss])
        gp = {(a[0], a[1]) for g in self.gaps for a in g['affects']}
        bad = [x for x in ex if (x[0], x[1]) not in gp]
        c['exposed_inputs'] = dict(ports=len(ex), bits=sum(x[2] for x in ex), by_owner={}, list=ex)
        for g in self.gaps:
            g['undriven_ports'] = sum(1 for a in g['affects'] if [a[0], a[1]] in [x[:2] for x in ex])
            g['undriven_bits'] = sum(x[2] for x in ex if any((x[0], x[1]) == (a[0], a[1]) for a in g['affects']))
        c['gaps'] = [g for g in c['gaps'] if g.get('region') != REGION] + self.gaps
        sm = c['summary']
        sm.update(instances=len(self.I), masters=len({v['master'] for v in self.I.values()}), edges=len(self.E),
                  edge_bits=sum(e['bits'] for e in self.E), clock_reset_ports=len(self.CR), straps=len(self.ST),
                  exposed_input_ports=len(ex), exposed_input_bits=sum(x[2] for x in ex), gaps=len(c['gaps']),
                  open_output_ports=len(c['open_outputs']))
        c.setdefault('notes', {})[REGION] = __doc__.split('\n\n')[0] + ' ' + json.dumps(dict(self.log))
        return ex, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--vm', choices=('d4g', 'keep'), default='d4g'); ap.add_argument('--hc', choices=('split', 'keep'), default='split')
    a = ap.parse_args()
    c = ld(a.inp)
    l3 = L3(c, Rtl())
    # begin/start field template (vmfc_SW -> vmdel_SW0) before any lane is dropped
    l3._fill_tpl = [copy.deepcopy(e) for e in c['edges'] if e['source'][0] == 'vmfc_SW' and e['sink'][0] == 'vmdel_SW0']
    rep = dict(schema='opentallas.hbm.d4g.gen1_l3.v1', region=REGION, inp=str(a.inp), vm=a.vm, hc=a.hc)
    if a.hc == 'split':
        l3.hc(rep)
    if a.vm == 'd4g':
        l3.vm(rep)
    rep['coll'] = dict(bound=False, reason='no die master instantiates ot_hgi_coll_ring_ag / ot_hgi_coll_ring_ag_lane: the ring stop is '
                       'u_ring (ot_hgi_coll_ring_v5) inside hb_coll_<q> (ot_hfd_coll_q2_hard_v5 / q3_hard_v7x); two rings need a '
                       'COLL-quadrant master with u_ring = ot_hgi_coll_ring_ag + a ring-B ot_hgi_coll_ring_ag_lane, the ring-B '
                       'command fields from the COLL calendar and a VM publish consumer for ag_* (2 x 256 b) -> HBM-B-RTL3',
                       view_ready='physical/ref_tile/hcoll_ring_ag_ctl_1017/views/ot_hgi_coll_ring_ag_ctl (CLOSED) binds once that master exists')
    ex, bad = l3.finish()
    rep.update(log=dict(l3.log), exposed_inputs=ex, unlisted_exposed=bad, gaps=l3.gaps, summary=c['summary'])
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L3', json.dumps(dict(l3.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
