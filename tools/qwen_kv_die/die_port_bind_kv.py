#!/usr/bin/env python3
"""qwen-split/kvsys 2026-10-14 (OWNER 08:05 PT: NO STUBS in any die): port-bind audit of a KV / KV-system die case.

The KV die netlist (kv_die.py case: die.v) instantiates DIE masters (qkd_*) on die-port bundles; a die master is real
only through its kv_die.BINDINGS entry (die port -> concatenation of RTL ports of a named RTL module, LSB first; a
'sliced' die port continues its base port's concatenation).  Per die master this reports:
  class   REAL (BINDINGS module found in the named file) | STUB (no RTL module: a frame / placeholder the die may not ship)
          | HARD_PHY (licensed analog macro: behavioural model allowed; its DIGITAL layer is listed separately)
          | RELAY (die-top relay register: generated stub module today)
  per die port: die net width vs the RTL bit count of its bound ports; die ports with no RTL binding; RTL ports with no
  die port (inputs = a functional input the die leaves unconnected; outputs = unread).
Widths of RTL ports are evaluated with the module's parameter DEFAULTS unless BINDINGS gives 'parameters'.

    python3 tools/qwen_kv_die/die_port_bind_kv.py CASE/die.v --split --out OUT.json
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_die as K  # noqa: E402

HARD_PHY = {'ot_hbm3e_phy': 'HBM3E PHY analog (digital layer = HBM controller qkd_ctrl/qkd_ctrl_pc)',
            'ot_qkvd_ucie_x64_phy': 'UCIe x64 PHY analog (digital layer = D2D adapter: framing/credits ot_qkvd_d2d, CRC/retry/FEC)',
            'ot_qfd_serdes_112g_x12_phy': 'host SerDes PHY analog (digital layer = host link adapter in qkd_host)',
            # v1.2: the clock / reset forwarding bump pair to the compute die is two pad cells (no logic; the compute
            # side's receiver qfd_clkrx / reset synchroniser are its digital layer)
            'qkd_ckbump': 'clock / reset forwarding bump pair to the compute die: pad cells, no logic (by design)',
            'qkd_fwdbump': 'v1.4 forwarded bump to the compute die (epoch strobe / link reset): pad cell, no logic (by design)',
            'qkd_hbm3e_phy_pc': 'HBM3E PHY analog, PHY only (v1.2): per-PC DFI po / pi; digital layer = qkd_ctrl_pc x32 (REAL)'}


HARD_PORT_RTL = {
    'ot_qkvd_ucie_x64_phy': 'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v',
    'ot_qfd_serdes_112g_x12_phy': 'physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v',
}


def header(text, mod):
    m = re.search(r'^\s*module\s+' + mod + r'\b(.*?)\);', text, re.M | re.S)
    if not m:
        return None, None
    h = re.sub(r'//[^\n]*', '', m.group(1))
    h = re.sub(r'/\*.*?\*/', '', h, flags=re.S)
    params, body = {}, h
    pm = re.match(r'\s*#\s*\((.*?)\)\s*\(', h, re.S)
    if pm:
        for d in re.finditer(r'(\w+)\s*=\s*([^,]+?)(?=,\s*(?:parameter\s+)?(?:integer\s+|\[[^\]]*\]\s*)?\w+\s*=|$)', pm.group(1), re.S):
            params[d.group(1)] = d.group(2).strip()
        body = h[pm.end():]
    else:
        body = h[h.find('(') + 1:]
    ports, cur_dir, cur_w = {}, None, '0:0'
    for item in body.split(','):
        item = item.strip()
        mm = re.match(r'(input|output|inout)?\s*(wire|reg|logic)?\s*(signed)?\s*(\[[^\]]+\])?\s*(\w+)\s*$', item)
        if not mm:
            continue
        if mm.group(1):
            cur_dir, cur_w = mm.group(1), (mm.group(4)[1:-1] if mm.group(4) else '0:0')
        elif mm.group(4):
            cur_w = mm.group(4)[1:-1]
        ports[mm.group(5)] = (cur_dir, cur_w)
    return params, ports


def evalw(w, params):
    env = {}
    cl = {'clog2': lambda x: (int(x) - 1).bit_length()}
    for _ in range(4):
        for k, v in params.items():
            try:
                env[k] = int(eval(re.sub(r'\$clog2', 'clog2', re.sub(r"\d+'\(([^)]*)\)", r'(\1)', v).replace('/', '//')), cl, env))
            except Exception:
                pass
    try:
        hi, lo = w.split(':')
        f = lambda e: int(eval(re.sub(r'\$clog2', 'clog2', e.replace('/', '//')), cl, env))  # noqa: E731
        return abs(f(hi) - f(lo)) + 1
    except Exception:
        return None


def parse_die(path):
    wires, insts = {}, []
    for line in open(path):
        if line.startswith('  wire ['):
            m = re.match(r'  wire \[(\d+):0\] (\S+);', line)
            if m:
                wires[m.group(2)] = int(m.group(1)) + 1
        elif line.startswith('  ') and '(' in line and not line.startswith(('  input', '  output', '  wire', '  assign')):
            m = re.match(r'\s*(\S+)\s+(\S+)\s*\((.*)\);\s*$', line.rstrip())
            if m:
                insts.append(m.groups())
    return wires, insts


def die_ports(conns, wires):
    out = {}
    for c in re.finditer(r'\.(\\?\S+?)\((\{[^}]*\}|[^)]*)\)', conns):
        nets = [n.strip() for n in c.group(2).strip('{}').split(',') if n.strip()]
        w = 0
        for n in nets:
            b = re.match(r'(\S+)\[(\d+)(?::(\d+))?\]$', n)
            if b:
                w += (abs(int(b.group(2)) - int(b.group(3))) + 1) if b.group(3) else 1
            elif re.match(r"\d+'[bhd]", n):
                w += int(n.split("'")[0])
            else:
                w += wires.get(n, 1)
        out[c.group(1)] = w
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('die_v')
    ap.add_argument('--out', required=True)
    ap.add_argument('--strict', action='store_true', help='fail when a die master has a stub, relay placeholder, or port mismatch')
    ap.add_argument('--split', action='store_true', help='the split KV/system die bindings (kv_die._set_geometry(True))')
    ap.add_argument('--relay-rtl', help='v1.2: the generated relay RTL (tools/qwen_kv_die/kv_relays.py); its modules bind '
                                        'the qkd_rly_* masters (else they stay class RELAY = stub)')
    ap.add_argument('--expanded', help='v1.3: RUN/expand.json of kv_expand.py; its die-placed leaves bind their own RTL '
                                        'module by name (identity port map: die port = RTL port)')
    a = ap.parse_args(argv)
    K._set_geometry(a.split)
    EXP = json.loads(Path(a.expanded).read_text())['leaves'] if a.expanded else {}
    rtxt = Path(a.relay_rtl).read_text() if a.relay_rtl else None
    wires, insts = parse_die(a.die_v)
    rep = {}
    by_m = defaultdict(list)
    for mst, inst, conns in insts:
        by_m[mst].append((inst, conns))
    for mst, lst in sorted(by_m.items()):
        dp = die_ports(lst[0][1], wires)
        r = dict(n_instances=len(lst), die_ports=len(dp))
        if mst in HARD_PHY:
            r.update(cls='HARD_PHY', note=HARD_PHY[mst])
            if mst in HARD_PORT_RTL:
                f = ROOT / HARD_PORT_RTL[mst]
                params, ports = header(f.read_text(), mst)
                if ports is None:
                    r.update(cls='STUB', file=HARD_PORT_RTL[mst], note='hard macro has no declared native ports')
                else:
                    rw = {p: evalw(w, params or {}) for p, (d, w) in ports.items()}
                    bad = [dict(die_port=p, die=w, rtl=rw.get(p)) for p,w in dp.items() if rw.get(p) != w]
                    unin = sorted(p for p,(d,_) in ports.items() if d == 'input' and p not in dp)
                    unout = sorted(p for p,(d,_) in ports.items() if d == 'output' and p not in dp)
                    r.update(cls='HARD_PHY' if not bad and not unin and not unout else 'MISMATCH',
                             module=mst, file=HARD_PORT_RTL[mst], width_or_missing=bad,
                             die_ports_not_bound=sorted(set(dp)-set(ports)), rtl_inputs_unconnected=unin,
                             rtl_outputs_unread=unout)

        elif mst.startswith('qkd_rly') and rtxt is not None:
            _, ports = header(rtxt, mst)
            if ports is None:
                r.update(cls='RELAY', note=f'no module {mst} in {a.relay_rtl}')
            else:
                bad = [dict(die_port=p_, die=w_, rtl=evalw(ports[p_][1], {}) if p_ in ports else None)
                       for p_, w_ in dp.items() if p_ not in ports or evalw(ports[p_][1], {}) != w_]
                miss = sorted(set(ports) - set(dp))
                r.update(cls='REAL' if not bad and not miss else 'MISMATCH', module=mst, file=a.relay_rtl,
                         note='die relay: generated register RTL, per-bit direction (kv_relays.py)',
                         width_or_missing=bad, die_ports_not_bound=[], rtl_inputs_unconnected=miss, rtl_outputs_unread=[])
        elif mst.startswith('qkd_rly'):
            r.update(cls='RELAY', note='die-top relay register: only a generated lint stub module exists (no RTL relay master)')
        elif mst in EXP:
            f = ROOT / EXP[mst]['rtl']
            params, ports = header(f.read_text(errors='replace'), mst)
            if ports is None:
                r.update(cls='STUB', note=f'die-placed leaf: module {mst} not found in {EXP[mst]["rtl"]}')
            else:
                rw = {p: evalw(w, params or {}) for p, (d, w) in ports.items()}
                bad = [dict(die_port=p_, die=w_, rtl=rw.get(p_)) for p_, w_ in dp.items() if rw.get(p_) != w_]
                unin = sorted(p for p, (d, _) in ports.items() if p not in dp and d == 'input')
                unout = sorted(p for p, (d, _) in ports.items() if p not in dp and d == 'output')
                r.update(cls='REAL' if not bad and not unin else 'MISMATCH', module=mst, file=EXP[mst]['rtl'],
                         note='die-placed CLOSED leaf (kv_expand.py), view ' + EXP[mst]['view'], width_or_missing=bad,
                         die_ports_not_bound=[], rtl_inputs_unconnected=unin, rtl_outputs_unread=unout)
        elif mst not in K.BINDINGS:
            r.update(cls='STUB', note=K.FRAME_ONLY.get(mst) or K.RTL.get(mst) or 'no RTL binding')
        else:
            b = K.BINDINGS[mst]
            f = ROOT / b['file']
            params, ports = header(f.read_text(errors='replace'), b['module']) if f.exists() else (None, None)
            if ports is None:
                r.update(cls='STUB', note=f"BINDINGS module {b['module']} not found in {b['file']}")
            else:
                params = dict(params or {}, **{k: str(v) for k, v in (b.get('parameters') or {}).items()})
                rw = {p: evalw(w, params) for p, (d, w) in ports.items()}
                base_bits = {}
                bad, nobind = [], []
                for d_, rps in b['ports'].items():
                    miss = [p for p in rps if p not in ports]
                    if miss:
                        bad.append(dict(die_port=d_, rtl_missing=miss))
                        continue
                    unknown = [p for p in rps if rw[p] is None]
                    if unknown:
                        bad.append(dict(die_port=d_, unresolved_rtl_widths=unknown))
                        continue
                    base_bits[d_] = sum(rw[p] for p in rps)
                sliced = b.get('sliced') or {}
                groups = defaultdict(int)
                for d_, w in dp.items():
                    base = sliced.get(d_, d_)
                    if base not in b['ports']:
                        nobind.append(d_)
                        continue
                    groups[base] += w
                for base, w in groups.items():
                    if base in base_bits and base_bits[base] != w:
                        bad.append(dict(die_port=base + ('+slices' if any(v == base for v in sliced.values()) else ''), die=w, rtl=base_bits[base]))
                used = {p for d_ in groups for p in b['ports'].get(d_, [])}
                unin = sorted(p for p, (d, _) in ports.items() if p not in used and d == 'input' and p not in b.get('classed', {}))
                unout = sorted(p for p, (d, _) in ports.items() if p not in used and d == 'output' and p not in b.get('classed', {}))
                cls = 'REAL' if not bad and not nobind and not unin else 'MISMATCH'
                r.update(cls=cls, module=b['module'], file=b['file'], width_or_missing=bad, die_ports_not_bound=nobind,
                         rtl_inputs_unconnected=unin, rtl_outputs_unread=unout)
        # Every instance must have the same resolved port layout as the audited
        # representative. A single malformed instance cannot hide behind a master census.
        output_ports = set()
        if mst in K.BINDINGS:
            bm = K.BINDINGS[mst]
            pf = ROOT / bm['file']
            _, pp = header(pf.read_text(), bm['module']) if pf.exists() else (None, None)
            if pp:
                output_ports = {d for d, ps in bm['ports'].items() if all(p in pp and pp[p][0] == 'output' for p in ps)}
        elif mst in EXP and ports is not None:
            output_ports = {p for p,(d,_) in ports.items() if d == 'output'}
        divergent = []
        for i,c in lst:
            di = die_ports(c, wires)
            # A terminal chain's output may be unread. Inputs, unknown ports and
            # every connected width must still match the audited RTL exactly.
            differences = {p for p in set(di) | set(dp) if di.get(p) != dp.get(p)}
            if any(p not in output_ports or p in di for p in differences):
                divergent.append(dict(instance=i, die_ports=di))
        if divergent:
            r['instance_port_mismatches'] = divergent
            r['cls'] = 'MISMATCH'
            r.setdefault('width_or_missing', []).append(dict(instance_layouts=len(divergent)))
            r.setdefault('die_ports_not_bound', [])
            r.setdefault('rtl_inputs_unconnected', [])
            r.setdefault('rtl_outputs_unread', [])
        rep[mst] = r
    summ = defaultdict(lambda: [0, 0])
    for v in rep.values():
        summ[v['cls']][0] += 1
        summ[v['cls']][1] += v['n_instances']
    out = dict(schema='opentallas.qwen_kv_die_port_bind.v1', die_v=a.die_v, summary={k: dict(masters=x[0], instances=x[1]) for k, x in summ.items()},
               masters=rep)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    for k, v in sorted(rep.items(), key=lambda kv: (kv[1]['cls'], kv[0])):
        extra = ''
        if v['cls'] in ('REAL', 'MISMATCH'):
            extra = f" bad={len(v['width_or_missing'])} unbound={len(v['die_ports_not_bound'])} in_unconn={len(v['rtl_inputs_unconnected'])}"
        print(f"{v['cls']:9s} {k:28s} x{v['n_instances']:<5d}{extra}")
    print(json.dumps(out['summary']))
    return int(a.strict and any(v['cls'] not in ('REAL', 'HARD_PHY') for v in rep.values()))


if __name__ == '__main__':
    sys.exit(main())
