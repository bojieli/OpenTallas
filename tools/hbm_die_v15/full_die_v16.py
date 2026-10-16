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
    ot_hbm_svc_sm_group (issuer + four-PC feed) and 8 SM tiles ot_hbm_accel_smh_static;
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
DIE_PIN = [('ot_pdie_serdes', r'^pma_'), ('ot_pdie_ucie', r'^pma_'), ('hfd_ckgen', r'^(refclk|por_n)$')]
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
                             params=dict(STACK=QID[q], SM=k), slot=f'pc_{q}{k}', owner='H-DIE', region='engine',
                             note='SM k service group: issuer (descriptor SRAM) + four-PC feed (LBANKS 4)'))
            inst.append(dict(name=s, master='ot_hbm_accel_smh_static', source='rtl/hbm_accel/sm/static/ot_hbm_accel_smh_static.sv',
                             params={}, slot=s, owner='H-SM', region='engine', note='static SM tile (grant v6 real pins)'))
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
            edges.append(dict(src=[g, 'sm_command'], dst=[s, 'command'], clock='stream', basis=basis))
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


def build(specs_dir, out):
    v15 = json.loads((ROOT / V15).read_text())
    grants = json.loads((ROOT / GRANTS).read_text())
    plan = json.loads((ROOT / PLAN).read_text())
    rtl = Rtl()
    specs = [engine_region()]
    for f in sorted(Path(specs_dir).glob('*.json')):
        s = json.loads(f.read_text())
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
        if a in retired or b in retired or e['name'] in dropped:
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
        if r['instance'] in insts and r['instance'] not in redefined:
            dm = {v[0]: k for k, v in DOM.items()}[r['source'][1]]
            ckdom[(r['instance'], r['port'])] = (dm, 'clock')
    for s in specs:
        for c in s.get('clocks', []):
            ckdom[(c['inst'], c['port'])] = (c['domain'], c.get('kind', 'clock'))
    clocks = []
    for (i, p), (dm, kind) in sorted(ckdom.items()):
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
    a = ap.parse_args()
    c = build(a.specs, a.out)
    print(json.dumps(c['summary'], indent=1))
    for p in c['problems'][:40]:
        print('PROBLEM', p)


if __name__ == '__main__':
    main()
