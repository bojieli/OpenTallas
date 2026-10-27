#!/usr/bin/env python3
"""Check a KV core's synthesized boundary using the same typed roles as signoff.py.

Exit nonzero on FAIL, missing inputs, or an incomplete check. Run on both the
raw Yosys netlist and the netlist exported from 1_synth.odb before floorplan.

Port gate (PATH-KV-PC2 10-25, GEOM-REVIEW-2 09:43): the set of pin names placed
by the kit io.tcl must equal the set of top-module port bits of the netlist.
A stale io.tcl (pins from another plan revision) otherwise passes face_guard
(which reads pins.json) and only dies at floorplan with PPL-0061.

Island ft gate (KV-CORES-PV2 10-27, 12.2a1): a kit with island_ft.json (die-owned ft arcs
ft_ck_i_<k> -> fixed BUF -> ft_ck_o_<k>) must keep exactly those cells on exactly those port nets.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def io_pins(io_tcl):
    return set(re.findall(r'-pin_name \{([^}]*)\}', Path(io_tcl).read_text()))


def top_port_bits(netlist, module):
    t = Path(netlist).read_text()
    m = re.search(r'^module\s+\\?' + re.escape(module) + r'\s*\(', t, re.M)
    if not m:
        return None
    end = t.find('\nendmodule', m.end())
    body = t[m.end():end]
    bits = set()
    for d in re.finditer(r'^\s*(?:input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s*)?\\?([^\s;,]+)\s*;',
                         body, re.M):
        hi, lo, nm = d.group(1), d.group(2), d.group(3)
        if hi is None:
            bits.add(nm)
        else:
            hi, lo = int(hi), int(lo)
            bits.update(f'{nm}[{k}]' for k in range(min(hi, lo), max(hi, lo) + 1))
    return bits


def port_gate(kit, netlist):
    kit = Path(kit)
    mod = None
    cfg = kit / 'config.mk'
    if cfg.exists():
        mm = re.search(r'^export DESIGN_NAME\s*=\s*(\S+)', cfg.read_text(), re.M)
        mod = mm.group(1) if mm else None
    if not mod or not (kit / 'io.tcl').exists():
        return dict(verdict='FAIL', reason='port gate: config.mk DESIGN_NAME or io.tcl missing')
    io = io_pins(kit / 'io.tcl')
    net = top_port_bits(netlist, mod)
    if net is None:
        return dict(verdict='FAIL', reason=f'port gate: module {mod} not in {netlist}')
    # a scalar port and a [0:0] bus place under the same io.tcl name 'p[0]'
    net = {n if '[' in n or f'{n}[0]' not in io else f'{n}[0]' for n in net}
    io_only, net_only = sorted(io - net), sorted(net - io)
    return dict(verdict='PASS' if not io_only and not net_only else 'FAIL', io_pins=len(io), netlist_ports=len(net),
                io_only=len(io_only), net_only=len(net_only), io_only_first=io_only[:8], net_only_first=net_only[:8])


def island_ft_gate(netlist, module, arcs):
    """structural Verilog (Yosys write_verilog) of the core top: every arc cell exists as a <master> instance whose A is
    the source port and Y the sink port, and no other cell pin is on either port net.  -> dict(verdict, ...)."""
    t = Path(netlist).read_text(errors="replace")
    m = re.search(r"^module\s+\\?" + re.escape(module) + r"\s*\(", t, re.M)
    if not m:
        return dict(verdict="FAIL", reason=f"module {module} not in {netlist}")
    body = t[m.end():t.find("\nendmodule", m.end())]
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)
    ports = {a["source"] for a in arcs} | {a["sink"] for a in arcs}
    uses = {p: [] for p in ports}
    for cm in re.finditer(r"^\s*(\\?\S+)\s+(\\?\S+)\s*\((.*?)\);", body, re.M | re.S):
        master, inst, conns = cm[1], cm[2].lstrip("\\"), cm[3]
        for pm in re.finditer(r"\.(\w+)\s*\(\s*\\?([^\s()]+)\s*\)", conns):
            if pm[2] in ports:
                uses[pm[2]].append((inst, master, pm[1]))
    bad = []
    for a in arcs:
        want_i = sorted((c["name"], a["master"], "A") for c in a["cells"])
        want_o = sorted((c["name"], a["master"], "Y") for c in a["cells"])
        if sorted(uses[a["source"]]) != want_i:
            bad.append([a["source"], sorted(uses[a["source"]])])
        if sorted(uses[a["sink"]]) != want_o:
            bad.append([a["sink"], sorted(uses[a["sink"]])])
    if re.search(r"^\s*assign\s+\\?(" + "|".join(map(re.escape, ports)) + r")\b", body, re.M):
        bad.append(["assign to an ft port"])
    return dict(verdict="FAIL" if bad else "PASS", arcs=len(arcs), cells=sum(len(a["cells"]) for a in arcs), bad=bad[:8])



def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kit', type=Path)
    ap.add_argument('netlist', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(a.kit.resolve()))
    import signoff
    result = signoff.run_face_guard(dict(kit=str(a.kit), synth=str(a.netlist),
                                        pins=str(a.kit / 'pins.json')))
    pg = port_gate(a.kit, a.netlist)
    result['port_gate'] = pg
    if pg['verdict'] != 'PASS':
        result['verdict'] = 'FAIL'
        result.setdefault('fail_counts', {})['port_gate'] = pg.get('io_only', 0) + pg.get('net_only', 0)
    ftj = a.kit / 'island_ft.json'
    if ftj.is_file():
        mod = re.search(r'^export DESIGN_NAME\s*=\s*(\S+)', (a.kit / 'config.mk').read_text(), re.M).group(1)
        fg = island_ft_gate(a.netlist, mod, json.loads(ftj.read_text())['arcs'])
        result['island_ft_gate'] = fg
        if fg['verdict'] != 'PASS':
            result['verdict'] = 'FAIL'
            result.setdefault('fail_counts', {})['island_ft'] = len(fg.get('bad', [])) or 1
    a.out.write_text(json.dumps(result, indent=1) + '\n')
    print('CORE_PREFLIGHT', result['verdict'], a.netlist,
          result.get('fail_counts', {}), result.get('reason', ''),
          'port_gate', pg['verdict'], {k: pg.get(k) for k in ('io_pins', 'netlist_ports', 'io_only', 'net_only')},
          *(['island_ft', result['island_ft_gate']['verdict'], result['island_ft_gate'].get('cells')]
            if 'island_ft_gate' in result else []))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
