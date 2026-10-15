#!/usr/bin/env python3
"""s81-functional-token (2026-10-14): does the generated S81 die netlist (die.v of a die kit) bind each hub / compute
master's REAL RTL ports?  For every non-glue master instance in die.v: the ports the die connects and the width of the
die net(s) on each, against the master's RTL module header (ANSI ports, widths evaluated with the parameter DEFAULTS --
the die instantiates masters without parameter overrides).  Reports per master: RTL found, ports the die connects that
the RTL lacks, RTL ports the die leaves unconnected (inputs = tied by the die: a functional gap; outputs = unread),
width mismatches.  Functional composition item, not a timing check.

    python3 tools/s81_ftok/die_port_bind.py DIE_V --out JSON
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# qwen split compute die (2026-10-14): copied from tools/s81_ftok/die_port_bind.py; die relays / reset repeaters are
# generator glue (their RTL is the generic relay / repeater family), everything else must bind to real RTL by master name.
GLUE = ('qfd_rly', 'qfd_rlyp', 'qfd_rst_rep', 'dsfd_xstg', 'dsfd_lkck', 'dsfd_stn', 'dsfd_hstn', 'dsfd_qbank', 'dsfd_rly', 'dsfd_m2l', 'dsfd_r2l', 'dsfd_l2r',
        'dsfd_sstn', 'dsfd_node', 'dsfd_cfifo', 'dsfd_rstg')


def rtl_index():
    idx = {}
    for p in sorted((ROOT / 'rtl').rglob('*.sv')) + sorted((ROOT / 'rtl').rglob('*.v')):
        if '/test/' in str(p) or '/tb' in p.name:
            continue
        try:
            t = p.read_text(errors='replace')
        except Exception:
            continue
        for m in re.finditer(r'^\s*module\s+(\w+)', t, re.M):
            idx.setdefault(m.group(1), []).append(p)
    return idx


def header(text, mod):
    m = re.search(r'^\s*module\s+' + mod + r'\b(.*?)\);', text, re.M | re.S)
    if not m:
        return None, None
    h = re.sub(r'//[^\n]*', '', m.group(1))
    h = re.sub(r'/\*.*?\*/', '', h, flags=re.S)
    params = {}
    pm = re.match(r'\s*#\s*\((.*?)\)\s*\(', h, re.S)
    body = h
    if pm:
        for d in re.finditer(r'(\w+)\s*=\s*([^,]+?)(?=,\s*(?:parameter\s+)?(?:integer\s+|\[[^\]]*\]\s*)?\w+\s*=|$)', pm.group(1), re.S):
            params[d.group(1)] = d.group(2).strip()
        body = h[pm.end():]
    else:
        body = h[h.find('(') + 1:]
    ports = {}
    cur_dir, cur_w = None, '0'
    for item in body.split(','):
        item = item.strip()
        mm = re.match(r'(input|output|inout)?\s*(wire|reg|logic)?\s*(signed)?\s*(\[[^\]]+\])?\s*(\w+)\s*$', item)
        if not mm:
            continue
        if mm.group(1):
            cur_dir = mm.group(1); cur_w = mm.group(4)[1:-1] if mm.group(4) else '0:0'
        elif mm.group(4):
            cur_w = mm.group(4)[1:-1]
        ports[mm.group(5)] = (cur_dir, cur_w)
    return params, ports


def evalw(w, params):
    env = {}
    for _ in range(4):
        for k, v in params.items():
            try:
                env[k] = int(eval(re.sub(r'\$clog2', 'clog2', v.replace('/', '//')), {'clog2': lambda x: (int(x) - 1).bit_length()}, env))
            except Exception:
                pass
    try:
        hi, lo = w.split(':')
        f = lambda e: int(eval(re.sub(r'\$clog2', 'clog2', e.replace('/', '//')), {'clog2': lambda x: (int(x) - 1).bit_length()}, env))
        return abs(f(hi) - f(lo)) + 1
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('die_v'); ap.add_argument('--out', required=True); a = ap.parse_args()
    wires, insts = {}, []
    for line in open(a.die_v):
        if line.startswith('  wire ['):
            m = re.match(r'  wire \[(\d+):0\] (\S+);', line)
            if m:
                wires[m.group(2)] = int(m.group(1)) + 1
        elif line.startswith('  ') and not line.startswith('  input') and '(' in line:
            mst = line.split()[0]
            if mst.startswith(GLUE) or mst.startswith('ot_rom_') or mst == 'ot_s81_cfg7_seq':
                continue
            insts.append(line)
    idx = rtl_index()
    rep = defaultdict(lambda: dict(instances=[], rtl=None))
    for line in insts:
        m = re.match(r'\s*(\S+)\s+(\S+)\s*\((.*)\);\s*$', line.rstrip())
        if not m:
            continue
        mst, inst, conns = m.groups()
        r = rep[mst]
        r['instances'].append(inst)
        if len(r['instances']) > 1:
            continue
        dport = {}
        for c in re.finditer(r'\.(\\?\S+?)\((\{[^}]*\}|[^)]*)\)', conns):
            nets = [n.strip() for n in c.group(2).strip('{}').split(',') if n.strip()]
            w = 0
            for n in nets:
                b = re.match(r'(\S+)\[(\d+)(?::(\d+))?\]$', n)
                if b:
                    w += (abs(int(b.group(2)) - int(b.group(3))) + 1) if b.group(3) else 1
                elif re.match(r"\d+'[bdhBDH]", n):
                    w += int(n.split("'")[0])
                else:
                    w += wires.get(n, 1)
            dport[c.group(1)] = w
        r['die_ports'] = dport
        files = idx.get(mst)
        if not files:
            r['rtl'] = None
            continue
        params, ports = header(files[0].read_text(errors='replace'), mst)
        r['rtl'] = str(files[0].relative_to(ROOT)); r['rtl_files'] = len(files)
        if ports is None:
            r['rtl_header'] = 'unparsed'; continue
        miss_rtl = sorted(p for p in dport if p not in ports)
        unconn_in = sorted(p for p, (d, _) in ports.items() if p not in dport and d == 'input')
        unconn_out = sorted(p for p, (d, _) in ports.items() if p not in dport and d == 'output')
        wmis = []
        for p, dw in dport.items():
            if p in ports:
                rw = evalw(ports[p][1], params)
                if rw is not None and rw != dw:
                    wmis.append(dict(port=p, die=dw, rtl=rw))
        r.update(die_ports_not_in_rtl=miss_rtl, rtl_inputs_unconnected=unconn_in, rtl_outputs_unconnected=unconn_out,
                 width_mismatch=wmis, n_rtl_ports=len(ports), n_die_ports=len(dport))
    out = dict(schema='opentallas.s81_ftok.die_port_bind.v1', die_v=a.die_v, masters={k: dict(v, n_instances=len(v['instances']),
               instances=v['instances'][:4]) for k, v in sorted(rep.items())})
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    for k, v in sorted(rep.items()):
        print(f"{k:28s} x{len(v['instances']):<5d} rtl={'NONE' if not v['rtl'] else 'yes'} "
              f"die_not_rtl={len(v.get('die_ports_not_in_rtl', []))} in_unconn={len(v.get('rtl_inputs_unconnected', []))} "
              f"out_unconn={len(v.get('rtl_outputs_unconnected', []))} wmis={len(v.get('width_mismatch', []))}")


if __name__ == '__main__':
    sys.exit(main())
