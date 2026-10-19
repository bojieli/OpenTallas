#!/usr/bin/env python3
"""Enumerate clock ownership and data crossings in elaborated Yosys JSON.

This diagnostic deliberately grants no landing exceptions and is not physical
timing evidence. It expands retained hierarchy using exact elaborated bit maps;
unknown leaves and clock expressions fail closed. Native/mapped pin ownership
must subsequently agree with the timing tool's actual clock objects.
"""
import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import re


def audit(design, top, roots, native=None):
    modules = design['modules']
    native = native or {}
    cells, aliases, issues = {}, defaultdict(list), []
    def key(path, bit, portmap):
        if isinstance(bit, str):
            return ('constant', bit)
        return portmap.get(bit, (path, bit))
    def expand(mod, path, portmap, stack):
        if mod in stack:
            raise ValueError('recursive module hierarchy: ' + mod)
        m = modules[mod]
        for name, net in m.get('netnames', {}).items():
            for i, bit in enumerate(net['bits']):
                aliases[key(path, bit, portmap)].append(f'{path}/{name}[{i}]')
        for inst, cell in m.get('cells', {}).items():
            name = f'{path}/{inst}'
            typ = cell['type']
            con = {p: [key(path, b, portmap) for b in bs]
                   for p, bs in cell['connections'].items()}
            child = modules.get(typ)
            blackbox = child and int(child.get('attributes', {}).get('blackbox', '0'), 2)
            if child and not blackbox and typ not in native:
                mapping = {}
                for p, spec in child['ports'].items():
                    if p not in con or len(spec['bits']) != len(con[p]):
                        raise ValueError(f'{name}.{p}: missing or mismatched port width')
                    for b, outer in zip(spec['bits'], con[p]):
                        if b in mapping and mapping[b] != outer:
                            raise ValueError(f'{name}.{p}: aliased child ports disagree')
                        mapping[b] = outer
                expand(typ, name, mapping, stack + [mod])
            else:
                cells[name] = dict(type=typ, connections=con,
                    parameters=cell.get('parameters',{}),
                    directions=cell.get('port_directions', child.get('ports', {}) if child else {}))
    expand(top, top, {}, [])
    def rootbit(pin):
        match = re.fullmatch(r'(.+?)(?:\[(\d+)\])?', pin)
        port, idx = match[1], int(match[2] or 0)
        spec = modules[top]['ports'].get(port)
        if not spec or spec['direction'] != 'input' or idx >= len(spec['bits']):
            raise ValueError('invalid top root pin: ' + pin)
        return (top, spec['bits'][idx])
    clocks = {}
    for pin, root in roots.items():
        b = rootbit(pin)
        if b in clocks and clocks[b] != (root, 0):
            raise ValueError('conflicting root aliases: ' + pin)
        clocks[b] = (root, 0)
    endpoints, comb, clock_buffers, word_widths = {}, [], [], {}
    for name, c in cells.items():
        typ, con = c['type'], c['connections']
        if typ in native:
            contract = native[typ]
            if set(contract) != {'clock', 'edge', 'outputs', 'reset'} or contract['edge'] not in ('posedge', 'negedge'):
                raise ValueError('native contract requires clock/edge/outputs/reset: ' + typ)
            cp, outs, resets = contract['clock'], contract['outputs'], contract['reset']
            if cp not in con or len(con[cp]) != 1 or any(p not in con for p in outs + resets):
                raise ValueError('native contract pin mismatch: ' + name)
            endpoints[name] = dict(clock=con[cp][0], edge=contract['edge'], outputs=[b for p in outs for b in con[p]],
                inputs={p: bs for p, bs in con.items() if p != cp and p not in outs},
                reset_pins=resets)
        elif typ in ('$dff', '$dffe', '$adff', '$adffe', '$sdff', '$sdffe', '$sdffce', '$dffsr', '$dffsre'):
            if not all(p in con for p in ('CLK','D','Q')) or len(con['CLK'])!=1 or len(con['D'])!=len(con['Q']):
                raise ValueError('word sequential pin mismatch: '+name)
            polarity=c.get('parameters',{}).get('CLK_POLARITY')
            if not isinstance(polarity,str) or not re.fullmatch(r'0*[01]',polarity):
                raise ValueError('word sequential clock polarity missing/unknown: '+name)
            endpoints[name]=dict(clock=con['CLK'][0],edge='posedge' if int(polarity,2) else 'negedge',outputs=con['Q'],
                inputs={p:bs for p,bs in con.items() if p not in ('CLK','Q')},
                reset_pins=[p for p in con if p in ('ARST','SRST','CLR','SET')])
            word_widths[name]=len(con['Q'])
        elif re.fullmatch(r'\$_(?:DFF|DFFE|SDFF|SDFFE|SDFFCE|DFFSR|DFFSRE)_[A-Z0-9]+_', typ):
            if not all(p in con for p in ('C', 'D', 'Q')) or len(con['C']) != 1:
                raise ValueError('sequential pin mismatch: ' + name)
            endpoints[name] = dict(clock=con['C'][0], edge='posedge' if typ.split('_')[2][0] == 'P' else 'negedge', outputs=con['Q'],
                inputs={p: bs for p,bs in con.items() if p not in ('C','Q')},
                reset_pins=[p for p in con if p in ('R','S')])
        elif typ in ('$not','$pos') and len(con.get('A',[]))==1 and len(con.get('Y',[]))==1:
            clock_buffers.append((con['A'][0],con['Y'][0],typ=='$not'))
            comb.append((name,con['A'],con['Y']))
        elif typ in ('$_NOT_', '$_BUF_'):
            clock_buffers.append((con['A'][0], con['Y'][0], typ == '$_NOT_'))
            comb.append((name, con['A'], con['Y']))
        elif typ.startswith('$_') and typ in {
                '$_AND_', '$_NAND_', '$_OR_', '$_NOR_', '$_XOR_', '$_XNOR_',
                '$_ANDNOT_', '$_ORNOT_', '$_MUX_', '$_NMUX_', '$_AOI3_',
                '$_OAI3_', '$_AOI4_', '$_OAI4_'}:
            comb.append((name, [b for p, bs in con.items() if p != 'Y' for b in bs], con['Y']))
        elif typ in {'$not','$pos','$and','$or','$xor','$xnor','$logic_not','$logic_and','$logic_or',
                '$reduce_and','$reduce_or','$reduce_xor','$reduce_xnor','$reduce_bool',
                '$eq','$ne','$eqx','$nex','$lt','$le','$ge','$gt','$add','$sub','$mul','$div','$mod',
                '$divfloor','$modfloor','$pow','$neg','$shl','$shr','$sshl','$sshr','$shift','$shiftx',
                '$mux','$pmux','$bmux','$demux','$bwmux','$concat','$slice','$alu','$macc','$macc_v2','$fa','$lcu'}:
            dirs=c.get('directions',{})
            if set(dirs)!=set(con) or any(v not in ('input','output') for v in dirs.values()):raise ValueError('word combinational directions missing: '+name)
            ins=[b for p,bs in con.items() if dirs[p]=='input' for b in bs]
            outs=[b for p,bs in con.items() if dirs[p]=='output' for b in bs]
            if not outs:raise ValueError('word combinational outputs missing: '+name)
            comb.append((name,ins,outs))
        else:
            issues.append(f'unknown leaf {name}: {typ}; explicit native contract or supported generic primitive required')
    # Only explicit buffers/inverters can derive a clock. Data muxes and gates
    # cannot silently manufacture a root, even if their data provenance agrees.
    changed = True
    while changed:
        changed = False
        for src, dst, invert in clock_buffers:
            if src not in clocks:
                continue
            r, pol = clocks[src]
            value = (r, pol ^ int(invert))
            if dst in clocks and clocks[dst] != value:
                issues.append(f'ambiguous derived clock {aliases[dst][:2]}')
            elif dst not in clocks:
                clocks[dst] = value
                changed = True
    domains = defaultdict(set)
    root_counts = defaultdict(int)
    for name, e in endpoints.items():
        e['owner'] = clocks.get(e['clock'])
        if e['owner'] is None:
            issues.append(f'unowned clock at {name}: {aliases[e["clock"]][:3]}')
            owner = 'UNOWNED:' + name
            phase = None
        else:
            owner = e['owner'][0]
            phase = e['owner'][1] ^ int(e['edge'] == 'negedge')
            root_counts[owner] += 1
        e['phase'] = phase
        for b in e['outputs']:
            domains[b].add((owner, phase))
    # Top data inputs remain explicit boundary origins rather than acquiring a
    # domain from a consumer. Their external timing contract is separate.
    for p, spec in modules[top]['ports'].items():
        if spec['direction'] == 'input':
            for b in spec['bits']:
                k = (top, b)
                if k not in clocks:
                    domains[k].add(('INPUT:' + p, None))
    readers = defaultdict(list)
    for i, (_, ins, _) in enumerate(comb):
        for b in ins:
            readers[b].append(i)
    queue = deque(range(len(comb)))
    pending = set(queue)
    while queue:
        i = queue.popleft(); pending.discard(i)
        _, ins, outs = comb[i]
        value = set().union(*(domains[b] for b in ins))
        for b in outs:
            if not value <= domains[b]:
                domains[b] |= value
                for j in readers[b]:
                    if j not in pending:
                        pending.add(j); queue.append(j)
    crossings = []
    for name, e in endpoints.items():
        owner = (e['owner'][0], e['phase']) if e['owner'] else None
        foreign = defaultdict(list)
        for pin, bits in e['inputs'].items():
            for b in bits:
                for source in domains[b]:
                    if source != owner:
                        foreign[(source, pin)].append(aliases[b][:2])
        for (source, pin), samples in sorted(foreign.items()):
            crossings.append(dict(sink=name, sink_root=owner[0] if owner else None,
                                  sink_pin=pin,
                                  pin_role='reset_set' if pin in e['reset_pins'] else 'data_enable',
                                  sink_active_phase=owner[1] if owner else None,
                                  source_root=source[0], source_active_phase=source[1],
                                  input_bits=len(samples), examples=samples[:3]))
    for root in sorted(set(roots.values()) - set(root_counts)):
        issues.append('declared root has no sequential/native endpoint: ' + root)
    return dict(status='FAIL' if issues else 'ENDPOINTS_ENUMERATED_NOT_TIMING_QUALIFIED',
        **(dict(word_endpoint_widths=word_widths,
                endpoint_count_note='Word FF endpoints each represent the stated vector width; endpoint counts are cell counts, not mapped clock-sink/area claims.') if word_widths else {}),
        scope='Recursive elaborated connectivity only; crossings are enumerated without waivers. Native pin clock owners, phase/age/reset timing and physical reach remain required.',
        top=top, leaf_cells=len(cells), endpoints=len(endpoints),
        endpoints_per_root=dict(sorted(root_counts.items())), issues=sorted(set(issues)),
        endpoint_owners={name: dict(root=e['owner'][0] if e['owner'] else None,
            clock_inverted_from_root=e['owner'][1] if e['owner'] else None,
            cell_active_edge=e['edge'], active_phase_from_root=e['phase'],
            clock_aliases=aliases[e['clock']][:4])
            for name,e in sorted(endpoints.items())}, crossings=crossings)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('netlist'); ap.add_argument('--contract', required=True)
    ap.add_argument('--out', required=True); args=ap.parse_args()
    raw=Path(args.netlist).read_bytes(); contract=json.loads(Path(args.contract).read_text())
    result=audit(json.loads(raw), contract['top'], contract['roots'], contract.get('native'))
    result['netlist_sha256']=hashlib.sha256(raw).hexdigest()
    result['contract_sha256']=hashlib.sha256(Path(args.contract).read_bytes()).hexdigest()
    Path(args.out).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status','leaf_cells','endpoints','endpoints_per_root','issues')}, indent=2))
    return int(bool(result['issues']))


if __name__ == '__main__':
    raise SystemExit(main())
