#!/usr/bin/env python3
"""HBM accelerator die v16: the COMPLETE full-die source contract + die top netlist (H-NETLIST 2026-10-15).

    full_die_v16.py --out DIR [--specs tools/hbm_die_v15/v16_specs]

The v15.1 source contract covered only the VM/service/COLL/IDX/SFU/DMA region (83 instances); the SMs, the HBM service
engine, the SU slices, SFU leaves, link endpoints, SerDes, host and HC came from the v14 die without die-name RTL.  v16
composes EVERY die instance from real RTL on main:

  * kept v15 instances and their port-level edges (results/arch/hbm_die_v15/source_contract/contract.json), minus the
    retired v15 service bands / static VM delivery / aw30 PHY (the SM-specific 4-PC service engine replaces them,
    Codex DECISION 14:40, H-DIE 1705);
  * the service engine region (bit-exact from tools/hbm_die_v15/die_case.py): per quadrant the PHY-only abstract
    ot_hbm3e_phy_rc_e8p5 (the one modelled core), 32 real controllers ot_hbm_svc_pc_ctrl_leaf, 8 SM service groups
    ot_hbm_svc_sm_group (issuer + four-PC feed) and 8 SM tiles ot_hbm_accel_smh_attn;
  * region specs written against the owners' RTL (tools/hbm_die_v15/v16_specs/*.json: sm_vm, su_sfu, coll_idx_link,
    host_misc): instances, edges (with the composition RTL / log line that proves each mapping), clock/reset domains,
    straps, and GAPS (owner + missing RTL) for every input no real producer drives.

Nothing is stubbed, tied or aliased: an input without a real producer stays undriven and is listed in a gap with its
owner (owner rule 10-14 08:05).  Outputs: contract.json (opentallas.hbm.full-die-v16-source-contract.v1), die.v (top
hbm_v16_die: instances + wires only), die.v.params.json, straps.json, gaps.md, summary.json.  Then run
tools/die_port_bind.py on die.v (strict v2) and Verilator lint on its elaboration (--elab-out).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as dpb  # noqa: E402

V15 = 'results/arch/hbm_die_v15/source_contract/contract.json'
GRANTS = 'results/arch/hier_contract_1015/hbm_v15.json'
PLAN = 'results/arch/hbm_die_v15/compact660_v5/compact.P.json'
EXPOSED_V15 = 'results/arch/hbm_die_v15/views_v5/exposed_inputs_by_owner_1705.json'
PHY_BB = 'physical/asap7_memory_macros/ot_hbm3e_phy_rc_e8p5/ot_hbm3e_phy_rc_e8p5_bb.v'
Q = ('SW', 'SE', 'NW', 'NE')
QID = dict(SW=0, SE=1, NW=2, NE=3)
TOP = 'hbm_v16_die'
CK = 'hb_ckgen'
DOM = dict(stream=('pll_stream', 'por_stream'), serial=('pll_serial', 'por_serial'), hbm=('pll_hbm', 'por_hbm'),
           link=('pll_link', 'por_link'))
# retired v15 instances (the engine replaces the service bands, the static VM delivery and the K-port PHY model)
RETIRE_V15 = {
    'svc_': 'v15 service band (hfd_svc_v15_*): replaced by the SM-specific 4-PC service engine (ctl_<q>_pNN + svg_<q><k>), '
            'Codex DECISION 14:40, H-DIE 1705 (exposed 816 band inputs retired with it)',
    'delivery_': 'ot_hbm_svc_static_vm_delivery: no v7 slot (grants_v7_1925: VM HBM path open, H-DIE); its band inputs '
                 'retire with the bands; successor = vmks_<q><k> K windows + 8 vmdel_<q><b> lanes + vmfc_<q> '
                 '(v16_specs/vmsm.json, G-VM-HBM-PATH closed)',
    'phy_': 'ot_hbm3e_phy_v41x_aw30_e8p5 carried a modelled controller K interface; v16 uses the PHY-ONLY abstract '
            'ot_hbm3e_phy_rc_e8p5 + 128 real controllers (die_case.py, owner rule 10-14: only the PHY is modelled)',
}
# off-die pins: (master, port regex) -> die top-level port (never an on-die driver)
DIE_PIN = [('ot_pdie_serdes', r'^pma_'), ('ot_pdie_ucie', r'^pma_'), ('hfd_ckgen', r'^(refclk|por_n)$'),
           ('ot_hbm_host_phy_adapt', r'^session_pad$')]   # host link session id: package strap pins (cp2)
ALLOW_MODEL = ['ot_hbm3e_phy_rc_e8p5', 'ot_hbm_pll_bb']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a):
    return subprocess.run(['git', '-C', str(ROOT)] + list(a), capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------------------------------------------ RTL ports
class Rtl:
    """per-master parsed module (die_port_bind's parser: the strict bind evaluates widths the same way)."""

    def __init__(self):
        self.cache = {}

    def mod(self, master, source):
        key = (master, source)
        if key not in self.cache:
            t = dpb.preprocess(dpb.strip_comments((ROOT / source).read_text(errors='replace')), {})
            mods = {m.name: m for m in dpb.parse_modules(t, str(ROOT / source))}
            if master not in mods:
                raise SystemExit(f'full_die_v16: {master} not defined in {source}')
            self.cache[key] = mods[master]
        return self.cache[key]

    def ports(self, master, source, params):
        m = self.mod(master, source)
        env = m.env({k: str(v) for k, v in (params or {}).items()})
        out = {}
        for pn, (d, _) in m.ports.items():
            w = m.width(pn, env)
            if w is None:
                raise SystemExit(f'full_die_v16: width of {master}.{pn} not evaluable with {params}')
            out[pn] = dict(direction=d, bits=w)
        return out


# ------------------------------------------------------------------------------------------------ engine region
def engine_region():
    """PHY rc + controllers + service groups + SM service side, bit-exact as tools/hbm_die_v15/die_case.py, with the
    K ports of each group routed through its VM fill window leaf vmks_<q><k> (H-NETLIST/vmsm 2026-10-15)."""
    inst, edges, clocks = [], [], []
    per = [('row_v', 1, 'c'), ('row_op', 3, 'c'), ('row_bank', 5, 'c'), ('row_row', 19, 'c'), ('col_v', 1, 'c'),
           ('col_we', 1, 'c'), ('col_bank', 5, 'c'), ('col_col', 5, 'c'), ('col_data', 256, 'c'), ('col_strb', 32, 'c'),
           ('dram_rvalid', 1, 'p'), ('dram_rdata', 256, 'p')]
    kw = [('k_v', 1, 'g'), ('k_rdy', 1, 'c'), ('k_we', 1, 'g'), ('k_addr', 30, 'g'), ('k_len', 4, 'g'), ('k_tag', 17, 'g'),
          ('k_wdata', 256, 'g'), ('k_wstrb', 32, 'g'), ('k_wr_done', 1, 'c'), ('kr_v', 1, 'c'), ('kr_rdy', 1, 'g'),
          ('kr_tag', 17, 'c'), ('kr_beat', 4, 'c'), ('kr_data', 256, 'c')]
    rdy = {'k_rdy', 'kr_rdy'}
    basis = 'tools/hbm_die_v15/die_case.py (PHY<->controller per PC, controller p <-> group p//4 lane p%4, group -> SM)'
    KBASIS = ('tools/hbm_die_v15/die_case.py controller p <-> group p//4 lane p%4, through vmks_<q><p//4> '
              '(rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare.sv header: g_* = group packing, '
              'c_* lane l = PC 4k+l)')
    KSHARE = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare.sv'
    for q in Q:
        phy = f'phy_{q}'
        inst.append(dict(name=phy, master='ot_hbm3e_phy_rc_e8p5', source=PHY_BB, params={}, slot=phy, owner='H-DIE',
                         region='engine', note='PHY-only row/column/data abstract: the one allowed modelled core'))
        clocks += [dict(inst=phy, port='clk', domain='hbm', kind='clock'), dict(inst=phy, port='rst_n', domain='hbm', kind='reset')]
        for pc in range(32):
            c = f'ctl_{q}_p{pc:02d}'
            inst.append(dict(name=c, master='ot_hbm_svc_pc_ctrl_leaf',
                             source='rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv',
                             params=dict(P=pc), slot=f'pc_{q}{pc // 4}', owner='H-DIE', region='engine',
                             note='real controller: r14 sequencer + same-row FIFO32 + 128x256 response SRAM'))
            clocks += [dict(inst=c, port='clk', domain='hbm', kind='clock'), dict(inst=c, port='rst_n', domain='hbm', kind='reset')]
            for n, w, d in per:
                if d == 'c':
                    edges.append(dict(src=[c, n, 0, w], dst=[phy, n, pc * w, pc * w + w], clock='hbm', basis=basis))
                else:
                    edges.append(dict(src=[phy, n, pc * w, pc * w + w], dst=[c, n, 0, w], clock='hbm', basis=basis))
        for k in range(8):
            g, s = f'svg_{q}{k}', f'sm_{q}{k}'
            inst.append(dict(name=g, master='ot_hbm_svc_sm_group',
                             source='rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group.sv',
                             params=dict(STACK=QID[q], SM=k, FIXED_GO=1), slot=f'pc_{q}{k}', owner='H-DIE', region='engine',
                             note='SM k service group: issuer (descriptor SRAM) + four-PC feed (LBANKS 4)'))
            # H-NETLIST/attn 2026-10-16 (parent-approved): the ATTENTION SM (owner option B); command[191:83] + kv_desc
            # come from xc_<q><k> (v16_specs/attn_0030.json), command[82:0] from svg_<q><k>.sm_command (below).
            inst.append(dict(name=s, master='ot_hbm_accel_smh_attn', source='rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv',
                             params={}, slot=s, owner='H-SM', region='engine',
                             note='attention-capable static SM (ot_hbm_accel_smh_static + attention front/BE; grant v6 pins + KV_DESC)'))
            for p, dm in (('stream_clk', 'stream'), ('hbm_clk', 'hbm'), ('stream_bank_clk', 'stream'),
                          ('hbm_fifo_clk', 'hbm'), ('hbm_pc_clk', 'hbm')):
                clocks.append(dict(inst=g, port=p, domain=dm, kind='clock'))
            clocks += [dict(inst=g, port='stream_rst_n', domain='stream', kind='reset'),
                       dict(inst=g, port='hbm_rst_n', domain='hbm', kind='reset'),
                       dict(inst=s, port='clk', domain='stream', kind='clock'),
                       dict(inst=s, port='rst_n', domain='stream', kind='reset')]
            # H-NETLIST/vmsm 2026-10-15: the group's four K ports reach the controllers through the VM fill window leaf
            # vmks_<q><k> (compiler-windowed K-port share: G-VM-HBM-PATH; vmsm.json holds the fill calendar, delivery
            # lanes and their edges).  Group side = the group's own packing; controller side = lane slices.
            ks = f'vmks_{q}{k}'
            inst.append(dict(name=ks, master='ot_hbm_svc_vm_kshare', source=KSHARE, params=dict(SM=k, MUT=0),
                             slot=f'pc_{q}{k}', owner='H-DIE', region='engine',
                             note='K-port VM fill window of SM group k: NORM pass-through, compiler window -> 16 x len-4 '
                                  'VM reads per PC, phase-steered beats -> CDC -> delivery fills (pin-registered)'))
            clocks += [dict(inst=ks, port='hbm_clk', domain='hbm', kind='clock'),
                       dict(inst=ks, port='hbm_rst_n', domain='hbm', kind='reset'),
                       dict(inst=ks, port='stream_clk', domain='stream', kind='clock'),
                       dict(inst=ks, port='stream_rst_n', domain='stream', kind='reset')]
            kexc = ('HBM stack / PHY controller boundary (HANDOFF 0az): K-port flow control (vmks is the PC-side K '
                    'window leaf of that boundary)')
            for p, w, d in kw:
                e = (dict(src=[g, p], dst=[ks, 'g_' + p]) if d == 'g' else dict(src=[ks, 'g_' + p], dst=[g, p]))
                e.update(clock='hbm', basis=KBASIS, ready_or_credit=p in rdy, allowed_exception=kexc if p in rdy else None)
                edges.append(e)
            for lane in range(4):
                c = f'ctl_{q}_p{4 * k + lane:02d}'
                for p, w, d in kw:
                    e = (dict(src=[ks, 'c_' + p, lane * w, lane * w + w], dst=[c, p, 0, w]) if d == 'g'
                         else dict(src=[c, p, 0, w], dst=[ks, 'c_' + p, lane * w, lane * w + w]))
                    e.update(clock='hbm', basis=KBASIS, ready_or_credit=p in rdy,
                             allowed_exception=kexc if p in rdy else None)
                    edges.append(e)
            edges.append(dict(src=[g, 'sm_packet'], dst=[s, 'packet'], clock='stream', basis=basis))
            edges.append(dict(src=[g, 'sm_command'], dst=[s, 'command', 0, 83], clock='stream', basis=basis))
    # G-ENG-STACK-FAULT (-> sfault_<q> = ot_hbm_svc_stack_fault) and G-VM-HBM-PATH (-> vmks_<q><k> + vmdel_<q><b> +
    # vmfc_<q>) are closed by tools/hbm_die_v15/v16_specs/vmsm.json (H-NETLIST/vmsm 2026-10-15).
    gaps = []
    return dict(region='engine', instances=inst, edges=edges, clocks=clocks, gaps=gaps, straps=[], retire_v15=[],
                drop_v15_edges=[], notes='coordinator region (die_case.py)')


# ------------------------------------------------------------------------------------------------ build
def rng(ref, ports):
    """[inst, port, lo?, hi?] -> (inst, port, lo, hi) with the whole port when omitted"""
    i, p = ref[0], ref[1]
    if len(ref) >= 4 and ref[2] is not None:
        return i, p, int(ref[2]), int(ref[3])
    return i, p, 0, ports[i][p]['bits']


def apply_relay_splice(specs, edges, ports, problems):
    """H-NETLIST/H-ELEM 2026-10-16 (d4b relay stations, tools/hbm_die_v15/relay_contract_d4b.py): rewire every listed
    bus load bit through its registered station chain. A listed load bit must be driven by the listed driver bit in the
    contract as built so far (else a problem: the station list is stale against this netlist)."""
    buses = [b for s in specs for b in s.get('relay_splice', [])]
    if not buses:
        return edges
    rmap = {}                                    # (di, dport, dbit, sink, sport, sbit) -> (bus, j)
    for b in buses:
        for j, ((p, k), ls) in enumerate(zip(b['driver_bits'], b['loads'])):
            for (si, sp, sb) in ls:
                if b['sink_feed'].get(si) is None and not b.get('pads', {}).get(si):
                    continue                     # depth-0 sink (cfg_no_pad near the driver): stays a direct edge
                rmap[(b['driver'], p, k, si, sp, sb)] = (b['bus'], j)
    drivers = {b['driver'] for b in buses}
    found = set()
    out = []
    for e in edges:
        if e['src'][0] not in drivers:
            out.append(e); continue
        try:
            si, sp, slo, shi = rng(e['src'], ports); di, dp, dlo, dhi = rng(e['dst'], ports)
        except KeyError:
            out.append(e); continue
        keep = [not ((si, sp, slo + k, di, dp, dlo + k) in rmap) for k in range(shi - slo)]
        if all(keep):
            out.append(e); continue
        for k in range(shi - slo):
            if not keep[k]:
                found.add((si, sp, slo + k, di, dp, dlo + k))
        k = 0
        while k < len(keep):                     # keep the unrelayed runs of a partially relayed edge
            if not keep[k]:
                k += 1; continue
            k2 = k
            while k2 + 1 < len(keep) and keep[k2 + 1]:
                k2 += 1
            out.append(dict(e, name=f"{e['name']}__kr{k}", src=[si, sp, slo + k, slo + k2 + 1], dst=[di, dp, dlo + k, dlo + k2 + 1],
                            bits=k2 - k + 1))
            k = k2 + 1
    miss = [x for x in rmap if x not in found]
    if miss:
        problems.append(f'relay splice: {len(miss)} listed load bits not driven by their listed driver bit in this '
                        f'netlist (e.g. {miss[:3]})')
    def runs(seq):
        """[(key, lane)] -> maximal runs of the same key with consecutive values and lanes"""
        res = []
        for key, v, lane in seq:
            if res and res[-1][0] == key and res[-1][2] + 1 == v and res[-1][4] + 1 == lane:
                res[-1][2] = v; res[-1][4] = lane
            else:
                res.append([key, v, v, lane, lane])
        return res
    for b in buses:
        W, T, n, tag, ck = b['width'], b['tiles'], b['bits'], b['bus'], b['domain']
        bas = f"d4b relay station chain {tag} ({b['cls']}, {b['driver']}) -- relay_contract_d4b.py"
        tn = lambda sid, t: f'{tag}_s{sid:03d}_t{t}'
        def from_driver(dst_tile_name):
            for t in range(T):
                seq = [((b['driver_bits'][j][0]), b['driver_bits'][j][1], j - t * W) for j in range(t * W, min(n, (t + 1) * W))]
                for key, v0, v1, l0, l1 in runs(seq):
                    out.append(dict(name=f'{dst_tile_name(t)}__drv{l0}', src=[b['driver'], key, v0, v1 + 1],
                                    dst=[dst_tile_name(t), 'i', l0, l1 + 1], bits=v1 - v0 + 1, clock=ck, basis=bas, region='relays_d4b'))
        def tile_to_tile(a, c):
            for t in range(T):
                out.append(dict(name=f'{c(t)}__i', src=[a(t), 'o'], dst=[c(t), 'i'], bits=W, clock=ck, basis=bas, region='relays_d4b'))
        for s in b['stations']:
            if s['parent'] is None:
                from_driver(lambda t, s=s: tn(s['id'], t))
            else:
                tile_to_tile(lambda t, s=s: tn(s['parent'], t), lambda t, s=s: tn(s['id'], t))
        last_of = {}
        for snk, feed in b['sink_feed'].items():
            pn = b.get('pad_names', {}).get(snk, [])
            prev = (lambda t, f=feed: tn(f, t)) if feed is not None else None
            for k, stage in enumerate(pn):
                cur = (lambda t, st=stage: st[t])
                if prev is None:
                    from_driver(cur)
                else:
                    tile_to_tile(prev, cur)
                prev = cur
            last_of[snk] = prev
        # loads
        seq = collections.defaultdict(list)
        for j, ls in enumerate(b['loads']):
            for (si, sp, sb) in ls:
                if b['sink_feed'].get(si) is None and not b.get('pads', {}).get(si):
                    continue
                seq[si].append((j, sp, sb))
        for si, lst in seq.items():
            src = last_of.get(si)
            if src is None:
                problems.append(f'relay splice {tag}: sink {si} has no station/pad (depth 0) -- direct edge expected'); continue
            lst.sort(key=lambda x: (x[0] // W, x[1], x[2]))
            cur = None
            for j, sp, sb in lst:
                t, L = divmod(j, W)
                if cur and cur[0] == t and cur[1] == sp and cur[3] + 1 == L and cur[5] + 1 == sb:
                    cur[3] = L; cur[5] = sb
                else:
                    if cur:
                        out.append(dict(name=f'{tag}__ld_{si}_{cur[1]}_{cur[4]}', src=[src(cur[0]), 'o', cur[2], cur[3] + 1],
                                        dst=[si, cur[1], cur[4], cur[5] + 1], bits=cur[3] - cur[2] + 1, clock=ck, basis=bas, region='relays_d4b'))
                    cur = [t, sp, L, L, sb, sb]
            if cur:
                out.append(dict(name=f'{tag}__ld_{si}_{cur[1]}_{cur[4]}', src=[src(cur[0]), 'o', cur[2], cur[3] + 1],
                                dst=[si, cur[1], cur[4], cur[5] + 1], bits=cur[3] - cur[2] + 1, clock=ck, basis=bas, region='relays_d4b'))
    return out


STRAP_TARGET_MASTERS = ('ot_static_cmd_target', 'ot_static_program_target')
UNIV_CAL_DIR = 'rtl/hbm_accel/generic/vm/static/'
UNIV_CAL_SRC = UNIV_CAL_DIR + 'hfd_hgi_vm_calendar.sv'
_DBK = 'rtl/hbm_accel/generic/peers/static/'
# H-NETLIST 0600 (H-DIE option A): F20 collars folded into their only consumer master (wrapper = consumer + collar as
# pin-registered soft logic; F20 bus + identity strap tgt on the consumer face; collar status on renamed face ports).
FOLD_RULES = [
    dict(target='ot_static_program_target', detect='program_cfg_we',
         consumers=('hfd_hgi_vm_calendar', 'ot_vms_calendar_static'),
         wrapper='hfd_hgi_vm_calendar_f20', source=UNIV_CAL_DIR + 'hfd_hgi_vm_calendar_f20.sv',
         deps=[UNIV_CAL_DIR + 'ot_vms_calendar_static_xcap.sv', UNIV_CAL_DIR + 'hfd_hgi_vm_calendar.sv',
               UNIV_CAL_DIR + 'ot_static_program_target.sv'],
         status={'configured': 'tgt_configured', 'fault': 'tgt_fault'}, clocks=('clk_tgt',)),
    dict(target='ot_static_cmd_target', detect='cmd', consumers=('ot_hgi_dma_back_static_vp4_banks',),
         wrapper='ot_hgi_dma_back_static_vp4_banks_cp', source=_DBK + 'ot_hgi_dma_back_static_vp4_banks_cp.sv',
         deps=[_DBK + 'ot_hgi_dma_back_static_vp4_banks.sv', 'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'],
         status={'configured': 'cp_configured', 'fault': 'cp_fault', 'active': 'cp_active'},
         clocks=('clk_cp', 'clk_tab')),   # H-HARDEN 1f18141cb: collar CTS root + raw table-SRAM entries
    dict(target='ot_static_cmd_target', detect='a_we', consumers=('ot_hbm_svc_sm_xcal',),
         wrapper='ot_hbm_svc_sm_xcal_t', source='rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_t.sv',
         deps=['rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal.sv', 'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'],
         status={'configured': 'configured', 'fault': 'fault', 'active': 'active'},
         # the xcal_t carries its own descriptor window B (host writes the svg descriptor rows to both targets; both
         # collars fire on the same global launch edge, H-SM tb_hbm_svc_sm_xcal_t): the svg collar no longer feeds it
         drop_dst_ports=('desc_we', 'desc_addr', 'desc_data', 'run_v', 'run_base', 'run_count')),
    dict(target='ot_static_cmd_target', detect='cmd_v', consumers=('ot_hbm_sm_vm_wr_q',),
         wrapper='ot_hbm_sm_vm_wr_q_t', source='rtl/hbm_accel/generic/vm/static/ot_hbm_sm_vm_wr_q_t.sv',
         deps=['rtl/hbm_accel/generic/vm/static/ot_hbm_sm_vm_wr_q.sv', 'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'],
         params={'DEPTH': 4}, param_straps={'QUAD': 'quad'},
         status={'configured': 'configured', 'fault': 'fault', 'active': 'active'}),
]
FOLD_RULES.append(dict(target='ot_static_cmd_target', detect='cmd_v', consumers=('ot_hgi_sm_xload_cl2_ctl',),
     wrapper='ot_hgi_sm_xload_cl2_ctlw', source='rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv',
     deps=['rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'],
     params={'PMAX': 8, 'RD_LAT': 6, 'NR': 32, 'LEAD': 8},   # H-SM xl2 8146db7ac: issuer MODE1 CW108 folded (option A)
     status={'configured': 'configured', 'fault': 'fault', 'active': 'active'},
     clocks=('clk_cal',)))   # r2 8e0535ed5: raw hard entry of the issuer table SRAM
# parameters that became identity strap pins (H-SM DEDUPE 2026-10-16): one hardened master for every value
PARAM_STRAPS = {'ot_hbm_svc_vm_kshare': {'SM': 'sm'}}
# H-NETLIST 1815 (owner: few tile variants; 178 die parameter aliases -> exact view requests): masters whose per-instance
# identity parameters are replaced by strap INPUTS of one generic master (each strap captured by a flop inside it).
# Enabled by --identity-straps.  value(params) gives the strap; 'keep' parameters are carried with their defaults.
_SVC = 'rtl/hbm_accel/loader/service_native/'


def _pc_refresh_reload(p):
    # ot_hbm_svc_pc_ctrl_leaf.sv: RP=(PHASE+P*118/32)%118, RELOAD=118+RP+((RP+118+P)%2) -> the cfg master's refresh_reload
    rp = (int(p.get('PHASE', 0)) + int(p['P']) * 118 // 32) % 118
    return 118 + rp + ((rp + 118 + int(p['P'])) % 2)


IDENTITY_MASTERS = {
    # the parameterised leaf is a pure wrapper: cfg u_cfg(.pc_id(5'(P)),.refresh_reload(8'(RELOAD))) (bench mutants
    # OT_PC_CFG_MUT_PC/PHASE in run_sm_groups_issued.sh); the cfg master registers both straps (pc_id_q/refresh_reload_q)
    'ot_hbm_svc_pc_ctrl_leaf': dict(
        master='ot_hbm_svc_pc_ctrl_leaf_cfg', source=_SVC + 'ot_hbm_svc_pc_ctrl_leaf_cfg.sv', deps=[],
        keep=dict(OREG=1, KREG=1, KRREG=1, RREG=1, WPAY=1),
        straps=[('pc_id', lambda p: int(p['P'])), ('refresh_reload', _pc_refresh_reload)]),
    # tools/hbm_die_v16/gen_svc_sm_group_id.py; bench rtl/hbm_accel/loader/service_native/run_sm_groups_issued_id.sh
    'ot_hbm_svc_sm_group': dict(
        master='ot_hbm_svc_sm_group_id', source=_SVC + 'ot_hbm_svc_sm_group_id.sv',
        deps=[_SVC + 'ot_hbm_svc_sm_feed_programmed_id.sv', _SVC + 'ot_hbm_svc_sm4pc_cdc_id.sv',
              _SVC + 'ot_hbm_svc_prefetch_overlap_owner_id.sv'],
        keep=dict(LBANKS=4, FIXED_GO=0),
        straps=[('id_stack', lambda p: int(p.get('STACK', 0))), ('id_sm', lambda p: int(p.get('SM', 0)))]),
}
IDENTITY_STRAPS = False   # main(): --identity-straps
# --keep-quadrants SW,NW (H-NETLIST 1930, A2P half die): instances of the other quadrants are removed (name tag
# _<Q>/<Q><digit>), then every untagged instance whose edges all go to removed instances (ep/lk of a dropped
# quadrant's links) is removed too (fixpoint).  Multi-target status joins are COMPACTED (a2p_compact): their t_ready /
# t_active slots (NT, TGTS), t_fault (NF) and h_fault (NH) inputs are renumbered over the surviving drivers.  Everything a
# 2-quadrant die cannot drive otherwise must come from a real N_Q RTL parameter (param_override layers).
KEEP_Q = ()
_QTAG = re.compile(r'(?:^|_)(SW|SE|NW|NE)(?=\d|_|$)')
STATUS_JOINS = {   # master -> (slot param, ports, target-id param, slot width, default)
    'ot_hbm_status_join': (('NT', ('t_ready', 't_active'), 'TGTS', 1, None), ('NF', ('t_fault',), None, 1, None),
                           ('NH', ('h_fault',), None, 1, None)),
    'ot_vms_status4_static': (('NQ', ('quadrant_status',), None, 19, 4),)}

# --pc-h8 (with --identity-straps): the PC controller master is the H8 view (H-SU route hdie_pc_ctrl_cfg_h8, one view for
# all 128 PCs); its six registered owner fault classes owner_fault_split[5:0] land in the quadrant stack fault leaf
# (ot_hbm_svc_stack_fault OWN_W=6: the sticky owner bit is their OR) instead of the scalar owner_fault.
PC_H8 = False
PC_H8_MASTER = dict(master='ot_hbm_svc_pc_ctrl_leaf_cfg_h8', source=_SVC + 'ot_hbm_svc_pc_ctrl_leaf_cfg_h8.sv',
                    deps=[_SVC + 'ot_hbm_svc_pc_ctrl_leaf.sv', 'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h7.sv'],
                    keep=dict(OREG=1, KREG=1, KRREG=1, RREG=1, WPAY=1, QREG=1))


# --drop-sm-side SE,NE (H-NETLIST 1940, A2P TP-192 scope: only the SM side halves): the SM-side masters of those
# quadrants (PHY, PC controllers, SM service groups, SMs, x-load + XQL stores, SM write, DMA-back, cmd targets, ...)
# are removed; the core (VM hubs/banks, COLL, SU, SFU, HC, LG) stays.  --drop-instances: explicit extra removals.
DROP_SM_Q = ()
DROP_INST = ()
SM_SIDE = {'ot_hbm3e_phy_rc_e8p5', 'ot_hbm_accel_smh_attn', 'ot_hbm_svc_pc_ctrl_leaf', 'ot_hbm_svc_pc_ctrl_leaf_cfg',
           'ot_hbm_svc_pc_ctrl_leaf_cfg_h8', 'ot_hbm_svc_sm_group', 'ot_hbm_svc_sm_group_id', 'ot_hbm_svc_sm_xcal_t',
           'ot_hbm_svc_stack_fault', 'ot_hbm_svc_vm_kshare', 'ot_hbm_svc_vmdel_lane', 'ot_hbm_svc_wb_kport',
           'ot_hbm_svc_wbw_copy', 'ot_hbm_sm_vm_wr_q_t', 'ot_hgi_sm_xload_cl2_bdring', 'ot_hgi_sm_xload_cl2_bfq',
           'ot_hgi_sm_xload_cl2_ctlw', 'ot_hgi_sm_xload_cl2_ctl', 'ot_hgi_sm_xload_xq_pegress', 'ot_hbm_xp_aq_tree13_fmt',
           'ot_static_cmd_target', 'ot_hgi_dma_back_static_vp4_banks_cp'}


# A2P re-mastering of instances that lose client slots (H-NETLIST 1940): new master + per-port slot maps
# (slot width, kept old slots in new order).  An edge range on such a port is cut per kept slot and moved; parts on
# absent slots must already be gone (their drivers / loads were dropped) else it is a problem.
_VMS = 'rtl/hbm_accel/generic/vm/static/'
A2P_REMASTER = {   # (master, quadrant in DROP_SM_Q) -> rule
    'hfd_hgi_vms_static_SE': dict(master='hfd_hgi_vms_static_SE_core', source=_VMS + 'hfd_hgi_vms_static_core.sv',
                                  deps=[_VMS + 'hfd_hgi_vms_static.sv'],
                                  slots=dict(rq=(136, (0, 3)), rr=(2056, (0, 3)), wq=(2248, (0,)), wq_done=(8, (0,)))),
    'hfd_hgi_vms_static_NE': dict(master='hfd_hgi_vms_static_NE_core', source=_VMS + 'hfd_hgi_vms_static_core.sv',
                                  deps=[_VMS + 'hfd_hgi_vms_static.sv'],
                                  slots=dict(rq=(136, (0, 3)), rr=(2056, (0, 3)), wq=(2248, (0,)), wq_done=(8, (0,)))),
}
# hb_idx: N_Q scorer slots (IDX helper claude/hnl-idxsoft-1815 03aa09d4c); slot = stack SID (SW0 SE1 NW2 NE3)
IDX_SLOTS = dict(key_lines=8792, keep_bitmap=342, score_observe=610)


A2P_RULES = {}   # instance -> {port: (slot width, kept old slots, old slot count)} (filled by a2p_remaster)


def a2p_remaster(insts, problems):
    kept_sid = [k for k, q in enumerate(('SW', 'SE', 'NW', 'NE')) if q not in DROP_SM_Q]
    rules = A2P_RULES
    for n, i in insts.items():
        r = A2P_REMASTER.get(i['master'])
        if r and (m := _QTAG.search(n)) and m.group(1) in DROP_SM_Q:
            i.update(master=r['master'], source=r['source'], rtl_deps=list(r['deps']),
                     note=i.get('note', '') + ' | A2P: SM-side client slots absent (no SM side in this quadrant)')
            rules[n] = {p: (w, k, {'rq': 4, 'rr': 4, 'wq': 2, 'wq_done': 2}[p]) for p, (w, k) in r['slots'].items()}
        if i['master'] in ('ot_hfd_coll_q3_static_host_v4', 'ot_hfd_coll_q2_static_host_v4') and DROP_INST:
            # Explicitly dropped SerDes peers remove whole physical links.  Keep every core quadrant;
            # the surviving endpoints retain their ordered lanes and all on-die operations.
            q = n.rsplit('_', 1)[-1]
            peers = {'SW': ('S0', 'S1', 'S2'), 'SE': ('S3', 'S4'),
                     'NW': ('N0', 'N1'), 'NE': ('N2', 'N3')}[q]
            kept = tuple(k for k, peer in enumerate(peers) if 'ep_' + peer not in DROP_INST)
            i['params'] = dict(i['params'], NLINK=len(kept), TP=192 if DROP_SM_Q else 96)
            i['note'] = i.get('note', '') + f' | A2P: NLINK={len(kept)} physical links, ordered lanes {kept}'
            rules[n] = {p: (w, kept, len(peers)) for p, w in
                        dict(phy_up=1, tx_pin_v=1, tx_pin_flit=612, rx_pin_v=1,
                             rx_pin_flit=612, retry_requested=1, clk_link=5).items()}
        if i['master'] == 'ot_hbm_argmax_static_sw_vm' and DROP_SM_Q:
            i['params'] = dict(i['params'], TP=192 if len(kept_sid)==2 else 96)
        if i['master'] == 'ot_hbm_idx_client_static_sw' and DROP_SM_Q:
            i['params'] = dict(i['params'], N_Q=len(kept_sid), TP=192 if len(kept_sid)==2 else 96)
            i['note'] = i.get('note', '') + f' | A2P: N_Q={len(kept_sid)} scorer slots = stacks {kept_sid}'
            rules[n] = {p: (w, tuple(kept_sid), 4) for p, w in IDX_SLOTS.items()}


PORT_SPLIT = {}   # instance -> {old port: [(new port, lo, hi)]}  (layer key 'remaster', H-NETLIST 2100)


def remaster_layers(insts, specs, problems):
    """Layer key 'remaster' {instance: {master, source, rtl_deps?, params?, port_split?}}: a master swap whose ports
    differ only by bus splits (old bus bits [lo:hi) become new port bits [0:hi-lo)); edges are re-cut in
    port_split_edges().  New clock pins come in the layer's 'clocks'."""
    for s_ in specs:
        for n, r in s_.get('remaster', {}).items():
            if n not in insts:
                problems.append(f'remaster: {n} is not an instance'); continue
            i = insts[n]
            i.update(master=r['master'], source=r['source'],
                     note=i.get('note', '') + f" | {s_['region']}: remastered {i['master']} -> {r['master']}")
            if 'params' in r:
                i['params'] = dict(r['params'])
            if r.get('rtl_deps'):
                i['rtl_deps'] = list(r['rtl_deps'])
            if r.get('port_split'):
                PORT_SPLIT[n] = {p: [tuple(x) for x in v] for p, v in r['port_split'].items()}


def port_split_edges(edges, problems):
    out = []
    for e in edges:
        parts = [e]
        for side, oth in (('dst', 'src'), ('src', 'dst')):
            nxt = []
            for x in parts:
                end = x[side]; segs = PORT_SPLIT.get(end[0], {}).get(end[1])
                if not segs:
                    nxt.append(x); continue
                full = max(h for _, _, h in segs)
                lo, hi = (end[2], end[3]) if len(end) >= 4 else (0, full)
                o = list(x[oth]) if len(x[oth]) >= 4 else list(x[oth][:2]) + [0, hi - lo]
                for np_, slo, shi in segs:
                    a, b = max(lo, slo), min(hi, shi)
                    if a >= b:
                        continue
                    y = dict(x, name=f"{x.get('name', 'e')}__{np_}")
                    y[side] = [end[0], np_, a - slo, b - slo]
                    y[oth] = o[:2] + [o[2] + a - lo, o[2] + b - lo]; y['bits'] = b - a
                    nxt.append(y)
            parts = nxt
        out.extend(parts)
    return out


def a2p_edge_remap(edges, problems):
    rules = A2P_RULES
    out = []
    if True:
        for e in edges:
            if DROP_SM_Q and e['dst'][:2] == ['hb_idx', 'rank']:
                e = dict(e, src=['col_idx', 'prm', 74, 82], bits=8,
                         basis='A2P TP192: same full 8-bit configured die_id as ARGMAX (cp2 operand row0 bits81:74)')
            parts = [e]
            for side, oth in (('dst', 'src'), ('src', 'dst')):
                nxt = []
                for x in parts:
                    end = x[side]
                    sl = rules.get(end[0], {}).get(end[1])
                    if not sl:
                        nxt.append(x); continue
                    w, keep, nold = sl
                    lo, hi = (end[2], end[3]) if len(end) >= 4 else (0, nold * w)
                    o = list(x[oth]) if len(x[oth]) >= 4 else list(x[oth][:2]) + [0, hi - lo]
                    for old in range(lo // w, (hi - 1) // w + 1):
                        a, b = max(lo, old * w), min(hi, (old + 1) * w)
                        if old not in keep:   # sink slot absent: the driver bits stay open; a source slot absent: undriven
                            if side == 'src':
                                problems.append(f'a2p slot remap {end[0]}.{end[1]}[{a}:{b}) is an absent source slot')
                            continue
                        k = keep.index(old)
                        y = dict(x, name=f"{x.get('name', 'e')}__a2p{side[0]}{old}")
                        y[side] = [end[0], end[1], k * w + a - old * w, k * w + b - old * w]
                        y[oth] = o[:2] + [o[2] + a - lo, o[2] + b - lo]; y['bits'] = b - a
                        nxt.append(y)
                parts = nxt
            out.extend(parts)
    return out


def a2p_drop(insts, specs, problems):
    drop = {n for n in insts if (m := _QTAG.search(n)) and KEEP_Q and m.group(1) not in KEEP_Q}
    drop |= {n for n in insts if (m := _QTAG.search(n)) and m.group(1) in DROP_SM_Q and insts[n]['master'] in SM_SIDE}
    for n in DROP_INST:
        if n not in insts:
            problems.append(f'--drop-instances: {n} is not an instance')
        drop.add(n)
    while True:
        nb = collections.defaultdict(set)
        for s_ in specs:
            for e in s_.get('edges', []):
                a, b = e['src'][0], e['dst'][0]
                nb[a].add(b); nb[b].add(a)
        more = {n for n in insts if n not in drop and not _QTAG.search(n) and nb[n]
                and all(x in drop or x == 'hb_ckgen' for x in nb[n]) and insts[n]['master'] not in STATUS_JOINS}
        if not more:
            return drop
        drop |= more


def a2p_compact(insts, specs, problems):
    for n, i in insts.items():
        for npar, pts, tg, w, dflt in STATUS_JOINS.get(i['master'], ()):
            old = int(i['params'].get(npar, dflt))
            def span(d):
                return (d[2], d[3]) if len(d) > 3 else (0, old * w)
            used = set()
            for s_ in specs:
                for e in s_.get('edges', []):
                    if e['dst'][0] == n and e['dst'][1] in pts:
                        lo, hi = span(e['dst']); used |= set(range(lo // w, (hi - 1) // w + 1))
            new = sorted(used); mp = {o: k for k, o in enumerate(new)}
            for s_ in specs:
                for e in s_.get('edges', []):
                    if e['dst'][0] == n and e['dst'][1] in pts:
                        d = e['dst']; lo, hi = span(d)
                        sl = list(range(lo // w, (hi - 1) // w + 1))
                        if [mp[x] for x in sl] != list(range(mp[sl[0]], mp[sl[0]] + len(sl))):
                            problems.append(f'a2p compact {n}.{d[1]}[{lo}:{hi}) not contiguous'); continue
                        nlo = mp[sl[0]] * w + lo % w
                        e['dst'] = [n, d[1], nlo, nlo + hi - lo]
            i['params'][npar] = max(1, len(new))
            if tg:
                v = str(i['params'][tg]); val = int(v.split("'h")[1], 16) if "'h" in v else int(v)
                ids = [(val >> (8 * o)) & 255 for o in new]
                i['params'][tg] = f"{8 * len(new)}'h" + ''.join(f'{x:02x}' for x in reversed(ids))
            i['note'] = i.get('note', '') + f' | A2P: {npar} {old} -> {len(new)}'


# H-NETLIST 0600: logical array wrappers whose RTL is "physically N independently hardened leaves" are FLATTENED in the
# die netlist into their N leaf instances <inst>_b<k> (one hardened leaf master, bit-sliced edges, same clock root bit).
_VMS = 'rtl/hbm_accel/generic/vm/static/'
FLATTEN = {
    'ot_hbm_vm_lg_static_split': dict(leaf='ot_hbm_vm_lg_static_bank', source=_VMS + 'ot_hbm_vm_lg_static_bank.sv', n=8, ret_pin=True,
        ports=dict(clk=1, local_rq=17, far_rq=17, local_wq=281, far_wq=281, local_read=1, local_write=1, near_rq=17,
                   near_wq=281, near_rr=257, near_w_done=1, local_rr=257, far_rr=257, local_w_done=1, far_w_done=1,
                   bank_fault=('fault', 1)), shared=('rst_n',)),
    'ot_hbm_vm_lg_static_split_term': dict(leaf='ot_hbm_vm_lg_static_bank_term', source=_VMS + 'ot_hbm_vm_lg_static_bank_term.sv', n=8,
        ports=dict(clk=1, local_rq=17, local_wq=281, local_read=1, local_write=1, near_rq=17, near_wq=281, near_rr=257,
                   near_w_done=1, local_rr=257, local_w_done=1, bank_fault=('fault', 1)), shared=('rst_n',)),
}


def universal_calendar_fields():
    """(field, lo, bits) of the universal calendar, read from the literal registered slices of its RTL."""
    txt = (ROOT / UNIV_CAL_SRC).read_text()
    f = sorted((int(lo), name, int(b)) for name, lo, b in re.findall(r'assign\s+(\w+)\s*=\s*calendar\[(\d+)\+:(\d+)\]', txt))
    assert [lo for lo, _, _ in f] == [sum(b for _, _, b in f[:k]) for k in range(len(f))], 'universal fields not contiguous'
    return [(name, lo, b) for lo, name, b in f]


def build(specs_dir, out, extra=()):
    v15 = json.loads((ROOT / V15).read_text())
    grants = json.loads((ROOT / GRANTS).read_text())
    plan = json.loads((ROOT / PLAN).read_text())
    rtl = Rtl()
    specs = [engine_region()]
    for f in sorted(Path(specs_dir).glob('*.json')) + [Path(x) for x in extra]:
        s = json.loads(gzip.open(f).read() if str(f).endswith('.gz') else f.read_text())   # --extra-spec: revision layers
        s.setdefault('region', f.stem)
        s['_file'] = str(f.relative_to(ROOT)) if f.is_absolute() and str(f).startswith(str(ROOT)) else str(f)
        specs.append(s)
    problems = []
    # ---------------- instances
    retired = {}
    for n in v15['instances']:
        for pre, why in RETIRE_V15.items():
            if n.startswith(pre):
                retired[n] = why
    for s in specs:
        for r in s.get('retire_v15', []):
            retired[r['instance']] = f"{s['region']}: {r['reason']}"
    insts = {}
    for n, i in v15['instances'].items():
        if n in retired:
            continue
        insts[n] = dict(master=i['master'], source=i['source'], params=i.get('params', {}), slot=None, owner=None,
                        region='v15', note='kept from v15.1 source contract')
    for s in specs:
        for i in s.get('instances', []):
            n = i['name']
            if n in insts and insts[n]['region'] != 'v15':
                same = (insts[n]['master'], insts[n]['params']) == (i['master'], i.get('params') or {})
                if not same:
                    problems.append(f"instance {n} defined differently by {insts[n]['region']} and {s['region']}")
                continue
            prev = insts.get(n)
            insts[n] = dict(master=i['master'], source=i['source'], params=i.get('params') or {}, slot=i.get('slot'),
                            owner=i.get('owner'), region=s['region'], note=i.get('note', ''),
                            replaces_v15=prev['master'] if prev else None)
            if i.get('rtl_deps'):
                insts[n]['rtl_deps'] = list(i['rtl_deps'])
    # H-NETLIST 0600 (H-DIE option A): a programme target whose only consumer is a universal VM calendar is FOLDED into
    # it (hfd_hgi_vm_calendar_f20 = target + calendar; a standalone ~630-pin collar is pin-bound as its own tile).
    folded = {}       # target instance -> consumer instance
    fold_rule = {}    # target instance -> rule
    for s_ in specs:
        for e in s_.get('edges', []):
            a, b = e['src'][0], e['dst'][0]
            if a not in insts or b not in insts:
                continue
            for r in FOLD_RULES:
                if (e['src'][1] == r['detect'] and insts[a]['master'] == r['target']
                        and insts[b]['master'] in r['consumers']):
                    folded[a] = b
                    fold_rule[a] = r
    for t, c in folded.items():
        insts[c]['folded_target'] = dict(instance=t, target=insts[t]['params'].get('TARGET'))
    # H-NETLIST 0600 (owner 19:50 FEWER DISTINCT TILES): programme/command targets take their F20 target id from the
    # identity strap pin tgt (TGT_PIN=1) instead of the TARGET parameter, so one hardened master per shape serves every id
    # (76 cmd + 18+ programme targets -> 5 + 1 masters).  The id is a die constant on the strap, never a runtime value.
    tgt_straps = []
    for n, i in insts.items():
        if i['master'] in STRAP_TARGET_MASTERS and 'TARGET' in i['params']:
            v = str(i['params'].pop('TARGET'))
            tid = int(v.split("'d")[1]) if "'d" in v else (int(v.split("'h")[1], 16) if "'h" in v else int(v))
            i['params']['TGT_PIN'] = 1
            tgt_straps.append(dict(inst=n, port='tgt', value=tid, reason=f'identity: F20 target id {tid} of this target instance'))
    for n, i in insts.items():
        for prm, port in PARAM_STRAPS.get(i['master'], {}).items():
            if prm in i['params']:
                tgt_straps.append(dict(inst=n, port=port, value=int(i['params'].pop(prm)),
                                       reason=f'identity: {prm} of this instance (was a parameter)'))
    if IDENTITY_STRAPS:
        h8 = set()
        for n, i in insts.items():
            r = IDENTITY_MASTERS.get(i['master'])
            if not r:
                continue
            if PC_H8 and i['master'] == 'ot_hbm_svc_pc_ctrl_leaf':
                r = dict(r, **PC_H8_MASTER)
                h8.add(n)
            old = dict(i['params'])
            for port, fn in r['straps']:
                tgt_straps.append(dict(inst=n, port=port, value=fn(old),
                                       reason=f"identity: {port} of this {i['master']} instance (was parameters {old})"))
            i.update(master=r['master'], source=r['source'],
                     params={k: int(old.get(k, v)) for k, v in r['keep'].items()},
                     note=i.get('note', '') + f" | H-NETLIST 1815 identity straps: one generic master (was {i['master']} {old})")
            if r['deps']:
                i['rtl_deps'] = list(r['deps'])
        if h8:
            sf = set()
            for s_ in specs:
                for e in s_.get('edges', []):
                    if e['src'][0] in h8 and e['src'][1] == 'owner_fault':
                        d = list(e['dst']); lo, hi = (d[2], d[3]) if len(d) > 3 else (0, 1)
                        e['src'] = [e['src'][0], 'owner_fault_split', 0, 6]
                        e['dst'] = d[:2] + [6 * lo, 6 * hi]
                        e['bits'] = 6 * (hi - lo)
                        e['basis'] = e.get('basis', '') + ' | H8: six registered owner fault classes (OR in the stack fault leaf)'
                        sf.add(d[0])
            for n in sf:
                if insts[n]['master'] != 'ot_hbm_svc_stack_fault':
                    problems.append(f'H8 owner_fault sink {n} is not ot_hbm_svc_stack_fault')
                insts[n]['params'] = dict(insts[n]['params'], OWN_W=6)
    specs.append(dict(region='target_id_straps', straps=tgt_straps, edges=[], instances=[], clocks=[], gaps=[]))
    # H-NETLIST 0600: fill calendars vmfc_<q> (ot_vms_calendar_static, W<=187) are the CLOSED universal VM calendar
    # master hfd_hgi_vm_calendar (native PASS): same programme ABI, calendar[W-1:0] = its low packed fields cycle for
    # cycle (rtl/hbm_accel/generic/vm/static/fill_universal_0600 gate). Their 'calendar' edges are re-cut per field
    # below and the related clocks clk_cap/clk_mem join the instance clock domain.
    univ_cal = {}
    ucal_fields = universal_calendar_fields()
    for n, i in insts.items():
        if i['master'] == 'ot_vms_calendar_static' and int(i['params'].get('W', 146)) <= sum(b for _, _, b in ucal_fields):
            univ_cal[n] = int(i['params'].get('W', 146))
            i.update(master='hfd_hgi_vm_calendar', source=UNIV_CAL_SRC, params={},
                     rtl_deps=[UNIV_CAL_DIR + 'ot_vms_calendar_static_xcap.sv'],
                     note=i.get('note', '') + f' | H-NETLIST 0600: closed universal calendar master (was ot_vms_calendar_static W{univ_cal[n]})')
    for t, c in folded.items():
        tid = insts[t]['params'].get('TGT_PIN') and next(x['value'] for x in tgt_straps if x['inst'] == t)
        r = fold_rule[t]
        for prm, port in r.get('param_straps', {}).items():
            tgt_straps.append(dict(inst=c, port=port, value=int(insts[c]['params'][prm]),
                                   reason=f'identity: {prm} of this instance (was a parameter)'))
        insts[c].update(master=r['wrapper'], source=r['source'], params=dict(r.get('params', {})), rtl_deps=list(r['deps']))
        insts[c]['note'] = insts[c].get('note', '') + f' | H-NETLIST 0600: F20 target {tid} folded in (was {t})'
        for x in tgt_straps:
            if x['inst'] == t:
                x['inst'] = c
        del insts[t]
    specs.append(dict(region='fill_calendar_universal', edges=[], instances=[], gaps=[], straps=[],
                      clocks=[dict(inst=n, port=p, domain='stream', kind='clock') for n in univ_cal for p in ('clk_cap', 'clk_mem')]
                             + [dict(inst=c, port=p, domain='stream', kind='clock') for t, c in folded.items() for p in fold_rule[t].get('clocks', ())]))
    flat = {}
    for n in list(insts):
        r = FLATTEN.get(insts[n]['master'])
        if not r:
            continue
        i = insts.pop(n)
        flat[n] = r
        for k in range(r['n']):
            insts[f'{n}_b{k}'] = dict(i, master=r['leaf'], source=r['source'], rtl_deps=[], params=dict(i['params']),
                                     note=(i.get('note') or '') + f' | H-NETLIST 0600: leaf {k} of flattened {n} ({i["master"]})')
            if r.get('ret_pin'):
                # one hardened leaf for every tap: return edges on identity straps (RET_PIN=1, depth 18/15)
                pr = insts[f'{n}_b{k}']['params']
                tgt_straps.append(dict(inst=f'{n}_b{k}', port='rret', value=int(pr.pop('READ_RETURN')), reason='identity: tap read return edge'))
                tgt_straps.append(dict(inst=f'{n}_b{k}', port='wret', value=int(pr.pop('WRITE_RETURN')), reason='identity: tap write return edge'))
                pr.update(READ_RETURN=18, WRITE_RETURN=15, RET_PIN=1)
    for s_ in specs:
        for c_ in list(s_.get('clocks', [])):
            if c_['inst'] in flat:
                s_['clocks'].remove(c_)
                s_['clocks'].extend(dict(c_, inst=f"{c_['inst']}_b{k}", port=c_['port']) for k in range(flat[c_['inst']]['n']))
    # H-NETLIST 1815 (d4c revision layers): 'remove_instances' (with every spec edge / clock / strap touching them),
    # 'drop_edges' ([src_inst, src_port] or [src_inst, src_port, dst_inst]) and 'param_override' {inst: {param: value}}.
    remaster_layers(insts, specs, problems)
    rm = {n for s_ in specs for n in s_.get('remove_instances', [])}
    if KEEP_Q or DROP_SM_Q or DROP_INST:
        rm |= a2p_drop(insts, specs, problems)
    drop_e = [d for s_ in specs for d in s_.get('drop_edges', [])]
    for n in sorted(rm):
        if insts.pop(n, None) is None:
            problems.append(f'remove_instances: {n} is not an instance')
    if rm or drop_e:
        def _qdrop(n):   # A2P: also folded / flattened names (not instances any more) of a dropped quadrant
            if folded.get(n) in rm:
                return True
            m_ = KEEP_Q and _QTAG.search(n)
            return bool(m_) and m_.group(1) not in KEEP_Q

        def _dropped(e):
            return e['src'][0] in rm or e['dst'][0] in rm or _qdrop(e['src'][0]) or _qdrop(e['dst'][0]) or any(
                e['src'][0] == d[0] and e['src'][1] == d[1] and (len(d) < 3 or e['dst'][0] == d[2]) for d in drop_e)
        for s_ in specs:
            s_['edges'] = [e for e in s_.get('edges', []) if not _dropped(e)]
            s_['clocks'] = [c_ for c_ in s_.get('clocks', []) if c_['inst'] not in rm]
            s_['straps'] = [x for x in s_.get('straps', []) if x['inst'] not in rm]
    if KEEP_Q or DROP_SM_Q or DROP_INST:
        a2p_compact(insts, specs, problems)
        a2p_remaster(insts, problems)
    for s_ in specs:
        for n, ov in s_.get('param_override', {}).items():
            if n not in insts and n in rm:
                continue
            if n not in insts:
                problems.append(f'param_override: {n} is not an instance')
                continue
            insts[n]['params'].update(ov)
            insts[n]['note'] = insts[n].get('note', '') + f" | {s_['region']}: params {ov}"
    ports = {}
    for n, i in insts.items():
        ports[n] = rtl.ports(i['master'], i['source'], i['params'])
        i['ports'] = ports[n]
    # ---------------- edges
    dropped = {e for s in specs for e in s.get('drop_v15_edges', [])}
    redefined = {n for s in specs for n in (x['name'] for x in s.get('instances', [])) if n in v15['instances']}
    edges = []
    for e in v15['known_actual_edges']:
        a, b = e['source'][0], e['sink'][0]
        if a in retired or b in retired or e['name'] in dropped or a in rm or b in rm:
            continue
        if (a in redefined or b in redefined):
            # a region re-mastered this instance: keep the v15 edge only if the ports still exist with the same width
            try:
                sa, sb = rng(e['source'], ports), rng(e['sink'], ports)
            except KeyError:
                problems.append(f"v15 edge {e['name']} dropped: port gone after re-mastering")
                continue
        edges.append(dict(name=e['name'], src=e['source'], dst=e['sink'], clock=e.get('clock'),
                          ready_or_credit=e.get('ready_or_credit', False), basis='v15.1 source contract', region='v15'))
    for s in specs:
        for k, e in enumerate(s.get('edges', [])):
            e = dict(e)
            e.setdefault('name', f"{s['region']}_{k}")
            e['region'] = s['region']
            edges.append(e)
    if flat:
        fe = []
        def _split(end, lo_hi_other):
            pass
        for e in edges:
            parts = [e]
            for side in ('src', 'dst'):
                nxt = []
                for x in parts:
                    end = x[side]
                    if end[0] not in flat:
                        nxt.append(x); continue
                    r = flat[end[0]]
                    if end[1] in r['shared']:
                        for k in range(r['n']):
                            nxt.append(dict(x, **{side: [f'{end[0]}_b{k}'] + list(end[1:])}, name=f"{x['name']}__b{k}"))
                        continue
                    spec_ = r['ports'][end[1]]
                    lp, w = (spec_ if isinstance(spec_, tuple) else (end[1], spec_))
                    lo = end[2] if len(end) > 2 else 0
                    hi = end[3] if len(end) > 3 else w * r['n']
                    other = 'dst' if side == 'src' else 'src'
                    olo = x[other][2] if len(x[other]) > 2 else 0
                    for k in range(lo // w, (hi - 1) // w + 1):
                        a, b = max(lo, k * w), min(hi, (k + 1) * w)
                        ox = list(x[other])
                        if len(ox) < 4:
                            ox = ox[:2] + [0, 0]
                        ox[2], ox[3] = olo + a - lo, olo + b - lo
                        nxt.append(dict(x, **{side: [f'{end[0]}_b{k}', lp, a - k * w, b - k * w], other: ox},
                                        name=f"{x['name']}__b{k}"))
                parts = nxt
            fe.extend(parts)
        edges = fe
    if folded:
        inv = {}
        consumers_rule = {}
        for t, c in folded.items():
            inv[t] = c
            consumers_rule[c] = fold_rule[t]
        fe = []
        for e in edges:
            a, b = e['src'][0], e['dst'][0]
            if a in inv and b == inv[a]:
                continue                                   # target -> calendar programme pins: now internal
            if b in inv and a == inv[b]:
                continue                                   # calendar active -> target interlock: now internal
            if b in consumers_rule and e['dst'][1] in consumers_rule[b].get('drop_dst_ports', ()):
                continue                                   # superseded feed into a folded consumer (rule note)
            e = dict(e)
            if b in inv:
                e['dst'] = [inv[b]] + list(e['dst'][1:])   # F20 broadcast now lands on the calendar face
            if a in inv:
                port = fold_rule[a]['status'][e['src'][1]]
                e['src'] = [inv[a], port] + list(e['src'][2:])
            fe.append(e)
        edges = fe
    if univ_cal:
        cut = []
        for e in edges:
            src = e['src']
            if src[0] in univ_cal and src[1] == 'calendar':
                lo = src[2] if len(src) > 2 else 0
                hi = src[3] if len(src) > 3 else univ_cal[src[0]]
                dst = e['dst']; dlo = dst[2] if len(dst) > 2 else 0
                for fname, flo, fbits in ucal_fields:
                    a, b = max(lo, flo), min(hi, flo + fbits)
                    if a < b:
                        cut.append(dict(e, name=f"{e['name']}__{fname}", src=[src[0], fname, a - flo, b - flo],
                                        dst=[dst[0], dst[1], dlo + a - lo, dlo + b - lo],
                                        basis=(e.get('basis') or '') + ' | universal calendar field slice (H-NETLIST 0600)'))
            else:
                cut.append(e)
        edges = cut
    if KEEP_Q or DROP_SM_Q or DROP_INST:   # A2P: flattened / folded expansions of removed instances
        edges = [e for e in edges if e['src'][0] in insts and e['dst'][0] in insts]
        edges = a2p_edge_remap(edges, problems)
    if PORT_SPLIT:
        edges = port_split_edges(edges, problems)
    edges = apply_relay_splice(specs, edges, ports, problems)
    # ---------------- bit-level driver map
    drv = {}          # (inst, port, bit) -> (inst, port, bit) | ('PIN', name, bit)
    E = []
    for e in edges:
        try:
            si, sp, slo, shi = rng(e['src'], ports)
            di, dp, dlo, dhi = rng(e['dst'], ports)
        except KeyError as x:
            problems.append(f"edge {e['name']} ({e['region']}): unknown instance/port {x}")
            continue
        if ports[si][sp]['direction'] != 'output' or ports[di][dp]['direction'] != 'input':
            problems.append(f"edge {e['name']}: {si}.{sp} ({ports[si][sp]['direction']}) -> {di}.{dp} "
                            f"({ports[di][dp]['direction']}) is not output->input")
            continue
        if shi - slo != dhi - dlo or shi > ports[si][sp]['bits'] or dhi > ports[di][dp]['bits']:
            problems.append(f"edge {e['name']}: width {si}.{sp}[{slo}:{shi}) vs {di}.{dp}[{dlo}:{dhi}) "
                            f"(ports {ports[si][sp]['bits']}/{ports[di][dp]['bits']})")
            continue
        if all(drv.get((di, dp, dlo + k)) == (si, sp, slo + k) for k in range(shi - slo)):
            continue                                   # a region re-stated an edge already bound (v15 or another region)
        for k in range(shi - slo):
            key = (di, dp, dlo + k)
            if key in drv:
                problems.append(f"edge {e['name']}: {di}.{dp}[{dlo + k}] already driven by {drv[key]}")
                break
            drv[key] = (si, sp, slo + k)
        E.append(dict(name=e['name'], bits=shi - slo, source=[si, sp, slo, shi], sink=[di, dp, dlo, dhi],
                      clock=e.get('clock'), ready_or_credit=bool(e.get('ready_or_credit', False)),
                      allowed_exception=e.get('allowed_exception'), basis=e.get('basis', ''), region=e['region']))
    # ---------------- clocks / resets
    ckdom = {}
    for r in v15['clock_roots']:
        if r['instance'] in flat:
            dm = {v[0]: k for k, v in DOM.items()}[r['source'][1]]
            for k in range(flat[r['instance']]['n']):
                ckdom[(f"{r['instance']}_b{k}", r['port'])] = (dm, 'clock')
            continue
        if r['instance'] in insts and r['instance'] not in redefined:
            dm = {v[0]: k for k, v in DOM.items()}[r['source'][1]]
            ckdom[(r['instance'], r['port'])] = (dm, 'clock')
    for s in specs:
        for c in s.get('clocks', []):
            if c['inst'] in folded:
                continue
            ckdom[(c['inst'], c['port'])] = (c['domain'], c.get('kind', 'clock'))
    # H-NETLIST 1815 reset forest layer: its leaf tiles drive these reset ports by edges (no hb_ckgen por binding)
    rforest = {tuple(x) for s in specs for x in s.get('reset_forest_ports', [])}
    for k in [k for k in ckdom if k in rforest and ckdom[k][1] == 'reset']:
        del ckdom[k]
    clocks = []
    for (i, p), (dm, kind) in sorted(ckdom.items()):
        if (KEEP_Q or DROP_SM_Q or DROP_INST) and i not in insts:
            continue
        if i not in ports or p not in ports[i]:
            problems.append(f'clock {i}.{p}: unknown'); continue
        if i == CK:
            continue
        src = DOM[dm][0 if kind == 'clock' else 1]
        for b in range(ports[i][p]['bits']):
            if (i, p, b) in drv:
                problems.append(f'clock {i}.{p}[{b}] also driven by an edge'); break
            drv[(i, p, b)] = (CK, src, 0)
        clocks.append(dict(instance=i, port=p, bits=ports[i][p]['bits'], domain=dm, kind=kind, source=[CK, src]))
    # v15 reset ports (excluded from v15 exposed counts: 'staged reset tree') -> the domain release of their clock
    for i, pp in ports.items():
        if i == CK:
            continue
        doms = {ckdom[(i, p)][0] for p in pp if (i, p) in ckdom and ckdom[(i, p)][1] == 'clock'}
        for p, d in pp.items():
            if d['direction'] == 'input' and re.fullmatch(r'(rst_n|rst|reset_n)', p) and (i, p) not in ckdom:
                if (i, p, 0) in drv:
                    continue
                dm = 'stream' if 'stream' in doms or not doms else sorted(doms)[0]
                src = DOM[dm][1]
                if p == 'rst':
                    problems.append(f'{i}.rst is active-high: no active-high release on hb_ckgen (left undriven)')
                    continue
                for b in range(d['bits']):
                    drv[(i, p, b)] = (CK, src, 0)
                clocks.append(dict(instance=i, port=p, bits=d['bits'], domain=dm, kind='reset', source=[CK, src],
                                   note='domain of the instance clock (v15 resets were outside the contract)'))
    # ---------------- straps
    straps = []
    for s in specs:
        for st in s.get('straps', []):
            i, p = st['inst'], st['port']
            lo = st.get('lo', 0); hi = st.get('hi', ports[i][p]['bits'])
            for b in range(lo, hi):
                drv[(i, p, b)] = ('CONST', (int(st['value']) >> (b - lo)) & 1, 0)
            straps.append(dict(st, lo=lo, hi=hi, master=insts[i]['master']))
    # ---------------- die pins
    pins = []
    for i, pp in ports.items():
        for p, d in pp.items():
            if any(insts[i]['master'] == m and re.search(rx, p) for m, rx in DIE_PIN):
                pins.append(dict(name=f'{i}__{p}', direction=d['direction'], bits=d['bits'], instance=i, port=p))
                if d['direction'] == 'input':
                    for b in range(d['bits']):
                        drv[(i, p, b)] = ('PIN', f'{i}__{p}', b)
    # ---------------- gaps
    gaps = []
    gap_of = {}
    for s in specs:
        for g in s.get('gaps', []):
            g = dict(g, region=s['region'])
            aff = []
            for a in g.get('affects', []):
                i, p = a[0], a[1]
                if i in flat:
                    continue        # accounting range on a flattened array wrapper (its leaves carry the bits)
                if i in folded.values() and i in ports and p not in ports[i]:
                    continue        # programme pins internal to a folded calendar+target master (H-NETLIST 0600)
                if KEEP_Q and i not in insts and (m_ := _QTAG.search(i)) and m_.group(1) not in KEEP_Q:
                    continue        # A2P: the gap's instance belongs to a dropped quadrant
                if i in rm:
                    continue        # A2P: accounting gaps for explicitly removed SM-side / link instances
                if i not in ports or p not in ports[i]:
                    problems.append(f"gap {g['id']}: unknown {i}.{p}"); continue
                ii, pp_, lo, hi = rng(a, ports)
                aff.append([ii, pp_, lo, hi])
                for b in range(lo, hi):
                    gap_of.setdefault((ii, pp_, b), g['id'])
            g['affects'] = aff
            gaps.append(g)
    # ---------------- exposed inputs (undriven input bits, clocks/resets excluded: they are bound above)
    exp = collections.OrderedDict()
    for i, pp in ports.items():
        for p, d in pp.items():
            if d['direction'] != 'input':
                continue
            und = [b for b in range(d['bits']) if (i, p, b) not in drv]
            if und:
                gids = sorted({gap_of.get((i, p, b), 'UNASSIGNED') for b in und})
                exp[(i, p)] = dict(instance=i, master=insts[i]['master'], port=p, bits=len(und), port_bits=d['bits'],
                                   gaps=gids, owner=insts[i]['owner'])
    unassigned = [v for v in exp.values() if 'UNASSIGNED' in v['gaps']]
    gid = {g['id']: g for g in gaps}
    for g in gaps:
        g['undriven_ports'] = sum(1 for v in exp.values() if g['id'] in v['gaps'])
        g['undriven_bits'] = sum(sum(1 for b in range(lo, hi) if (i, p, b) not in drv) for i, p, lo, hi in g['affects'])
    by_owner = collections.defaultdict(lambda: dict(ports=0, bits=0))
    for v in exp.values():
        ow = sorted({gid[x]['owner'] for x in v['gaps'] if x in gid} or {f"UNASSIGNED ({v['owner'] or 'v15'})"})
        k = ' + '.join(ow)
        by_owner[k]['ports'] += 1; by_owner[k]['bits'] += v['bits']
    v15x = json.loads((ROOT / EXPOSED_V15).read_text())
    # ---------------- unconsumed outputs (informational)
    used = collections.defaultdict(set)
    for (di, dp, b), src in drv.items():
        if src[0] not in ('PIN', 'CONST'):
            used[(src[0], src[1])].add(src[2])
    out_open = []
    for i, pp in ports.items():
        for p, d in pp.items():
            if d['direction'] == 'output' and not used.get((i, p)) and not any(x['instance'] == i and x['port'] == p for x in pins):
                out_open.append([i, p, d['bits']])
    # ---------------- contract
    masters = collections.Counter(i['master'] for i in insts.values())
    summ = dict(instances=len(insts), masters=len(masters), edges=len(E), edge_bits=sum(e['bits'] for e in E),
                clock_reset_ports=len(clocks), straps=len(straps), die_pins=len(pins),
                exposed_input_ports=len(exp), exposed_input_bits=sum(v['bits'] for v in exp.values()),
                exposed_unassigned_ports=len(unassigned), gaps=len(gaps), open_output_ports=len(out_open),
                problems=len(problems),
                before_v15=dict(instances=len(v15['instances']), exposed_input_ports=v15x['total_ports'],
                                exposed_input_bits=v15x['total_bits'], unresolved_source_ports=v15['unbound_count'],
                                source=EXPOSED_V15))
    contract = dict(
        schema='opentallas.hbm.full-die-v16-source-contract.v1', die='hbm_v16', top=TOP, generated_by='tools/hbm_die_v15/full_die_v16.py',
        basis=dict(commit=git('rev-parse', '--short', 'HEAD'), v15_contract=V15, v15_contract_sha256=sha(ROOT / V15),
                   grants=GRANTS, grants_version=grants.get('version'), plan=PLAN, plan_slots=len(plan),
                   specs={s['region']: dict(file=s.get('_file', 'engine (in tool)'), author=s.get('author'),
                                            basis_commit=s.get('basis_commit')) for s in specs}),
        rules=['no stubs / shells / tied ports: an input without a real producer stays undriven and is listed in a gap',
               'on-die edges fixed-slot: ready_or_credit only with allowed_exception at the HBM PHY/controller boundary',
               'clock/reset ports are bound to hb_ckgen domain outputs (die CTS / staged reset tree build the trees)',
               'off-die pins (SerDes/UCIe PMA, refclk, por_n) are die top-level ports'],
        summary=summ, masters=dict(sorted(masters.items())),
        instances={n: {k: v for k, v in i.items()} for n, i in insts.items()},
        retired_v15=[dict(instance=n, master=v15['instances'][n]['master'], reason=r) for n, r in sorted(retired.items())],
        edges=E, clock_resets=clocks, straps=straps, die_pins=pins, gaps=gaps,
        exposed_inputs=dict(ports=len(exp), bits=summ['exposed_input_bits'], by_owner=dict(by_owner),
                            list=list(exp.values())),
        open_outputs=out_open, problems=problems,
        relays_physical=dict(note='registered stations the die relay planner inserts on long edges are physical '
                                  '(latency counted in the compiler stage counts); logical relays that the RTL '
                                  'semantics require (SU RF_RELAY) are instances of their region spec',
                             templates=grants.get('relay_templates'), su_rf=grants.get('su_rf_relays_v7', {}).get('RF_RELAY')),
        notes={s['region']: s.get('notes') for s in specs})
    out.mkdir(parents=True, exist_ok=True)
    (out / 'contract.json').write_text(json.dumps(contract, indent=1) + '\n')
    emit_die(out, insts, ports, drv, pins, straps)
    write_gaps_md(out / 'gaps.md', contract)
    (out / 'summary.json').write_text(json.dumps(dict(summary=summ, by_owner=dict(by_owner), problems=problems[:200],
                                                      gaps=[{k: g[k] for k in ('id', 'owner', 'missing_rtl', 'undriven_ports', 'undriven_bits', 'region')} for g in gaps]),
                                                 indent=1) + '\n')
    return contract


def vparam(v):
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v)


def emit_die(out, insts, ports, drv, pins, straps):
    pinset = {(x['instance'], x['port']): x for x in pins}
    L = [f'// generated by tools/hbm_die_v15/full_die_v16.py -- HBM accelerator die v16 full netlist (instances + wires only)',
         '`default_nettype none']
    hdr = ', '.join(x['name'] for x in pins)
    L.append(f'module {TOP} ({hdr});')
    for x in pins:
        L.append(f"  {x['direction']} wire [{x['bits'] - 1}:0] {x['name']};")
    for i, pp in ports.items():
        for p, d in pp.items():
            if d['direction'] == 'output' and (i, p) not in pinset:
                L.append(f"  wire [{d['bits'] - 1}:0] {i}__{p};")
    partial = []
    body = []
    for i, inst in insts.items():
        conns = []
        for p, d in ports[i].items():
            if d['direction'] == 'output':
                conns.append(f'.{p}({i}__{p})')
                continue
            bits = [drv.get((i, p, b)) for b in range(d['bits'])]
            if all(b is None for b in bits):
                continue                                 # wholly undriven input: INPUT_UNCONNECTED (a listed gap)
            parts = []                                   # MSB first
            b = d['bits'] - 1
            while b >= 0:
                s = bits[b]
                if s is None:
                    e = b
                    while e - 1 >= 0 and bits[e - 1] is None:
                        e -= 1
                    nm = f'nc__{i}__{p}'
                    partial.append((nm, d['bits']))
                    parts.append(f'{nm}[{b}:{e}]'); b = e - 1; continue
                if s[0] == 'CONST':
                    e = b
                    while e - 1 >= 0 and bits[e - 1] is not None and bits[e - 1][0] == 'CONST':
                        e -= 1
                    val = sum(bits[k][1] << (k - e) for k in range(e, b + 1))
                    parts.append(f"{b - e + 1}'d{val}"); b = e - 1; continue
                net = s[1] if s[0] == 'PIN' else f'{s[0]}__{s[1]}'
                e = b
                while (s[0] != CK and e - 1 >= 0 and bits[e - 1] is not None and bits[e - 1][:2] == s[:2]
                       and bits[e - 1][2] == bits[e][2] - 1):
                    e -= 1
                lo, hi = bits[e][2], s[2]
                if s[0] == CK:                               # a domain clock / release: one net, replicated
                    e2 = b
                    while e2 - 1 >= 0 and bits[e2 - 1] == s:
                        e2 -= 1
                    n_ = b - e2 + 1
                    parts.append(f'{{{n_}{{{net}[0]}}}}' if n_ > 1 else f'{net}[0]'); b = e2 - 1; continue
                parts.append(f'{net}[{hi}:{lo}]' if hi != lo else f'{net}[{lo}]'); b = e - 1
            conns.append(f".{p}({parts[0] if len(parts) == 1 else '{' + ', '.join(parts) + '}'})")
        pr = inst['params']
        ps = (' #(' + ', '.join(f'.{k}({vparam(v)})' for k, v in pr.items()) + ')') if pr else ''
        body.append(f"  {inst['master']}{ps} {i} (\n    " + ',\n    '.join(conns) + '\n  );')
    for nm, w in sorted(set(partial)):
        L.append(f'  wire [{w - 1}:0] {nm};   // undriven bits = listed gap bits (never tied)')
    L += body
    L.append('endmodule')
    L.append('`default_nettype wire')
    (out / 'die.v').write_text('\n'.join(L) + '\n')
    ident = [s for s in straps if not str(s.get('reason', '')).startswith('PAD')]
    (out / 'straps.json').write_text(json.dumps(dict(straps=sorted({(s['master'], s['port']) for s in ident})), indent=1) + '\n')
    pads = {}
    for s in straps:
        if str(s.get('reason', '')).startswith('PAD'):
            assert int(s['value']) == 0, s
            e = pads.setdefault(s['master'], dict(reason='DEDUPE standard relay used below its width (results/arch/'
                                                         'tile_dedupe_1015): spare input bits tied low, spare outputs open; '
                                                         'per-instance ranges in contract.json straps', ports={}))
            r = e['ports'].setdefault(s['port'], [])
            if [s['lo'], s['hi'] - 1] not in r:
                r.append([s['lo'], s['hi'] - 1])
    (out / 'die.v.pads.json').write_text(json.dumps(dict(pads=pads), indent=1) + '\n')


def write_gaps_md(path, c):
    S = c['summary']
    L = [f"# HBM die v16 full netlist: gaps ({c['basis']['commit']})", '',
         f"{S['instances']} instances / {S['masters']} masters / {S['edges']} edges ({S['edge_bits']:,} bits). "
         f"Exposed inputs {S['before_v15']['exposed_input_ports']:,} ports / {S['before_v15']['exposed_input_bits']:,} bits "
         f"(v15.1, 83 instances) -> {S['exposed_input_ports']:,} ports / {S['exposed_input_bits']:,} bits (v16 full die).", '',
         '| gap | owner | missing RTL | undriven ports | undriven bits |', '|---|---|---|---:|---:|']
    for g in sorted(c['gaps'], key=lambda g: -g.get('undriven_bits', 0)):
        L.append(f"| {g['id']} | {g['owner']} | {g['missing_rtl']} | {g.get('undriven_ports', 0)} | {g.get('undriven_bits', 0):,} |")
    L += ['', '## Exposed inputs by owner', '', '| owner | ports | bits |', '|---|---:|---:|']
    for k, v in sorted(c['exposed_inputs']['by_owner'].items(), key=lambda kv: -kv[1]['bits']):
        L.append(f"| {k} | {v['ports']} | {v['bits']:,} |")
    if c['problems']:
        L += ['', '## Generator problems', ''] + [f'- {p}' for p in c['problems'][:100]]
    path.write_text('\n'.join(L) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/hbm_die_v16')
    ap.add_argument('--specs', type=Path, default=ROOT / 'tools/hbm_die_v15/v16_specs')
    ap.add_argument('--extra-spec', action='append', default=[],
                    help='revision layer spec (e.g. tools/hbm_die_v15/v16_relays/relays_d4b.json.gz: d4b relay stations)')
    ap.add_argument('--identity-straps', action='store_true',
                    help='IDENTITY_MASTERS: per-instance identity parameters -> strap pins of one generic master')
    ap.add_argument('--drop-sm-side', default='', help='A2P: comma list of quadrants whose SM side is removed')
    ap.add_argument('--drop-instances', default='', help='A2P: comma list of extra instances to remove')
    ap.add_argument('--keep-quadrants', default='', help='A2P: comma list of quadrants to keep (e.g. SW,NW)')
    ap.add_argument('--pc-h8', action='store_true', help='with --identity-straps: PC controller = the H8 view (PC_H8_MASTER)')
    a = ap.parse_args()
    global IDENTITY_STRAPS, PC_H8, KEEP_Q, DROP_SM_Q, DROP_INST
    DROP_SM_Q = tuple(x for x in a.drop_sm_side.split(',') if x)
    DROP_INST = tuple(x for x in a.drop_instances.split(',') if x)
    KEEP_Q = tuple(x for x in a.keep_quadrants.split(',') if x)
    IDENTITY_STRAPS = a.identity_straps
    PC_H8 = a.pc_h8
    c = build(a.specs, a.out, a.extra_spec)
    print(json.dumps(c['summary'], indent=1))
    for p in c['problems'][:40]:
        print('PROBLEM', p)


if __name__ == '__main__':
    main()
