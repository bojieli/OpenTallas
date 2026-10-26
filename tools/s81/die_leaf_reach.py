#!/usr/bin/env python3
"""die_leaf_reach (S-DIE-NETLIST 2026-10-16): which die-netlist masters instantiate a given module in the die RTL?

A contract master that is absent from the die netlist's TOP level may still be built: it can be a leaf / child of a
present master (e.g. the HC comb leaves under dsfd_sp_hc_c).  This tool answers that from the RTL, the same way
tools/die_port_bind.py reads it: the die RTL manifest's files win, its +define+s apply, every module under rtl/ is
indexed; from each netlist master it follows instantiations (text after preprocessing; generate-if branches are all
followed, so a reached module is a POSSIBLE child, the path is printed for review) and prints, per queried module, the
shortest instance path from a netlist master, or 'NOT REACHED'.

    python3 tools/s81/die_leaf_reach.py --port-bind PORT_BIND.json [-f physical/s81_die_rtl/layer1.f] MODULE ... [--out J]
"""
import argparse, json, re, sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as DPB  # noqa: E402

KW = set('module endmodule input output inout wire reg logic always assign if else for generate endgenerate begin end '
         'case endcase function endfunction task endtask initial localparam parameter genvar integer return posedge '
         'negedge or and not while repeat default typedef struct enum packed signed unsigned int bit'.split())
# master [#(...) | `PARAM_MACRO] instance [range] (   -- a parameter macro left unexpanded, or a multi-line `define the
# preprocessor cut at its first backslash, still matches
INST = re.compile(r'(?m)^\s*([A-Za-z_]\w*)\s*(?:#\s*\((?:[^;]*?)\)|#\s*\([^;]*?\\|`\w+)?\s*\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?\(')


def children(mod):
    body = DPB._lexical_mask(mod.body, strings=True)
    return {(m.group(1), m.group(2)) for m in INST.finditer(body) if m.group(1) not in KW}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('modules', nargs='+')
    ap.add_argument('--port-bind', required=True, type=Path, help='die_port_bind v2 record: its masters{} are the netlist masters')
    ap.add_argument('-f', dest='manifest', default='physical/s81_die_rtl/layer1.f')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    files, defines, libdirs = DPB.load_manifest(ROOT / a.manifest)
    roots = ['rtl'] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'physical').glob('**/rtl') if p.is_dir())   # as die_port_bind
    idx, _ = DPB.rtl_index(roots + libdirs, files, {d: '1' for d in defines}, files)
    masters = sorted(json.loads(a.port_bind.read_text())['masters'])
    # BFS over (module) from every netlist master; remember the first path
    path = {}
    q = deque()
    for m in masters:
        if m in idx and m not in path:
            path[m] = [m]
            q.append(m)
    while q:
        m = q.popleft()
        for c, inst in sorted(children(idx[m])):
            if c in idx and c not in path:
                path[c] = path[m] + [f'{inst}:{c}']
                q.append(c)
    res = {}
    for mod in a.modules:
        if mod in masters:
            res[mod] = dict(state='NETLIST_MASTER')
        elif mod in path:
            res[mod] = dict(state='LEAF_OF_NETLIST_MASTER', top=path[mod][0], path=path[mod])
        else:
            res[mod] = dict(state='NOT_REACHED', rtl=(idx[mod].path if mod in idx else None))
        print(f"{mod:34s} {res[mod]['state']:24s} {' / '.join(res[mod].get('path', [])) or res[mod].get('rtl') or ''}")
    if a.out:
        a.out.write_text(json.dumps(dict(schema='opentallas.die_leaf_reach.v1', port_bind=str(a.port_bind),
                                         manifest=a.manifest, defines=defines, netlist_masters=len(masters),
                                         reach=res), indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
