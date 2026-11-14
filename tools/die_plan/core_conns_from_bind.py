#!/usr/bin/env python3
"""TYPE-SAFE-2 11-08: core connectivity sidecar (check.py core_conns.json format) from a native BOUND module.

The S81 native bind joins face buses to hard-core ports through wiring only (concatenations / bit selects in
`assign` statements, kept transport chains ot_dp_dly, lane pads u_lpad_*).  None of that is visible to the plan, so
check.py R3-INTERNAL (pin-to-pin reach of bus window -> core port) is blind for those types.  This tool reads the bound
module and writes, per hard core inst (plan name) and port, the face buses and other cores it reaches by WIRING ONLY
(no logic operator in between), plus the existing stages on that wire path (lane pad / kept chain depth), so a plan
event can (1) site existing stages first (0 cycles) and (2) add internal_stations only for the remainder.

usage: core_conns_from_bind.py PLAN.json TYPE BOUND.sv OUT.json
OUT = {"core_conns": {TYPE: {core_inst: {port: ["bus:<bus>", "core:<inst>.<port>", ...]}}},
       "paths": [{core, port, dir, bus|partner, stages_existing, via}]}"""
import json
import re
import sys
from collections import defaultdict

# Bit identities are module-local; None is a constant, never a shared net.
_NAME = r"(?:\\[^\s]+|[A-Za-z_$][A-Za-z0-9_$.]*)"
_DECL = re.compile(r"\b(input|output|inout|wire|reg|logic)\s+((?:(?:wire|reg|logic|signed|unsigned)\s+)*)(?:\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]\s*)?(" + _NAME + r")")


def _split_top(e):
    out, start, depth = [], 0, 0
    for i, ch in enumerate(e):
        if ch in '{[(': depth += 1
        elif ch in '}])': depth -= 1
        elif ch == ',' and depth == 0:
            out.append(e[start:i]); start = i + 1
    return out + [e[start:]]


def _module_sections(text):
    text = strip_comments(text)
    out = {}
    for m in re.finditer(r'\bmodule\s+(' + _NAME + r')(?=\s|\()', text):
        z = re.search(r'\bendmodule\b', text[m.end():])
        if z is None: raise ValueError('unterminated module ' + m[1])
        out[m[1].lstrip('\\')] = text[m.start():m.end()+z.end()]
    return out


def select_module(text, top=None):
    sections = _module_sections(text)
    if not sections: return strip_comments(text)
    if top is not None:
        if top.lstrip('\\') not in sections: raise ValueError('module not found: ' + top)
        return sections[top.lstrip('\\')]
    if len(sections) != 1: raise ValueError('multiple modules require an explicit top')
    return next(iter(sections.values()))


def _decl_entries(body):
    for m in _DECL.finditer(body):
        width = (int(m[3]), int(m[4]), 'signed' in m[2].split()) if m[3] is not None else (None, None, 'signed' in m[2].split())
        yield m[5], width, m[1]
        tail = body[m.end():body.find(';', m.end()) if ';' in body[m.end():] else len(body)]
        for item in _split_top(tail)[1:]:
            item = item.strip()
            # A new ANSI declaration is handled by its own regex match.
            if re.match(r'(input|output|inout|wire|reg|logic)\b', item): break
            n = re.match('(' + _NAME + r')\s*(?:=|$|\))', item)
            if not n: break
            yield n[1], width, m[1]


def declarations(body):
    return {name: width for name, width, _ in _decl_entries(body)}


def module_directions(text):
    return {name: {p.lstrip('\\'): kind.upper() for p, _, kind in _decl_entries(body)
                   if kind in ('input', 'output', 'inout')}
            for name, body in _module_sections(text).items()}


def _enclosed(e, left, right):
    if not (e.startswith(left) and e.endswith(right)): return False
    level = 0
    for i, ch in enumerate(e):
        if ch == left: level += 1
        elif ch == right: level -= 1
        if level == 0 and i != len(e)-1: return False
    return level == 0


def expression_bits(expr, widths):
    """MSB-first bit identities plus signedness; constants retain None positions.

    Unsupported operators/dynamic selectors fail rather than join their inputs.
    """
    e = expr.strip()
    while _enclosed(e, '(', ')'): e = e[1:-1].strip()
    cast = re.fullmatch(r'\$(signed|unsigned)\s*\((.*)\)', e, re.S)
    if cast:
        bits, _ = expression_bits(cast[2], widths)
        return bits, cast[1] == 'signed'
    if _enclosed(e, '{', '}'):
        inner = e[1:-1].strip()
        rep = re.fullmatch(r'(\d+)\s*(\{.*\})', inner, re.S)
        if rep:
            bits, _ = expression_bits(rep[2], widths)
            return bits * int(rep[1]), False
        out = []
        for part in _split_top(inner): out.extend(expression_bits(part, widths)[0])
        return out, False
    const = re.fullmatch(r"(\d*)\s*'([sS]?)([bBoOdDhH])[0-9a-fA-F_xXzZ?]+", e)
    if const: return [None] * (int(const[1]) if const[1] else 32), bool(const[2])
    if re.fullmatch(r"'[01xXzZ]", e): return [None], False
    if re.fullmatch(r'[+-]?\d+', e): return [None]*32, True
    m = re.fullmatch('(' + _NAME + r')(?:\s*\[\s*(-?\d+)\s*(?::\s*(-?\d+)\s*)?\])?', e)
    if not m: raise ValueError('unsupported wiring expression: ' + e)
    name = m[1]
    if m[2] is not None:
        a, z = int(m[2]), int(m[3] or m[2])
        scalar = name in widths and widths[name][0] is None
        return [name if scalar and i == 0 else f'{name}[{i}]' for i in range(a, z + (1 if z >= a else -1), 1 if z >= a else -1)], False
    if name not in widths: raise ValueError('undeclared wire width: ' + name)
    a, z, signed = widths[name]
    if a is None: return [name], signed
    return [f'{name}[{i}]' for i in range(a, z + (1 if z >= a else -1), 1 if z >= a else -1)], signed


def align_bits(lhs, rhs, signed=False):
    if len(rhs) < len(lhs): rhs = [rhs[0] if signed and rhs else None] * (len(lhs)-len(rhs)) + list(rhs)
    elif len(rhs) > len(lhs): rhs = rhs[-len(lhs):] if lhs else []
    return list(zip(lhs, rhs))


def hc_port_directions(hc, repo=None):
    from pathlib import Path
    root = Path(repo) if repo else Path(__file__).resolve().parents[2]
    path = Path(hc.get('lef', ''))
    if not path.is_absolute(): path = root / path
    if not path.is_file(): return {}
    text = strip_comments(path.read_text())
    blocks = []
    for m in re.finditer(r'(?m)^\s*MACRO\s+(\S+)', text):
        end = re.search(r'(?m)^\s*END\s+' + re.escape(m[1]) + r'\s*$', text[m.end():])
        if end: blocks.append((m[1], text[m.end():m.end()+end.start()]))
    chosen = [b for n,b in blocks if n == hc.get('module')]
    if not chosen and len(blocks) == 1: chosen = [blocks[0][1]]
    if len(chosen) != 1: return {}
    result = {}
    for m in re.finditer(r'(?m)^\s*PIN\s+(\S+)', chosen[0]):
        end = re.search(r'(?m)^\s*END\s+' + re.escape(m[1]) + r'\s*$', chosen[0][m.end():])
        if not end: continue
        d = re.search(r'\bDIRECTION\s+(INPUT|OUTPUT|INOUT)\s*;', chosen[0][m.end():m.end()+end.start()])
        if not d: continue
        name = re.sub(r'\[-?\d+\]$', '', m[1]).lstrip('\\')
        if name in result and result[name] != d[1]: result[name] = 'UNKNOWN'
        else: result[name] = d[1]
    return result


def hc_port_bit_indices(hc, repo=None):
    """Logical pin indices from the actual LEF, not from a connected slice width."""
    from pathlib import Path
    root = Path(repo) if repo else Path(__file__).resolve().parents[2]
    path = Path(hc.get('lef', ''))
    if not path.is_absolute(): path = root / path
    if not path.is_file(): return {}
    text = strip_comments(path.read_text())
    blocks=[]
    for m in re.finditer(r'(?m)^\s*MACRO\s+(\S+)',text):
        end=re.search(r'(?m)^\s*END\s+'+re.escape(m[1])+r'\s*$',text[m.end():])
        if end:blocks.append((m[1],text[m.end():m.end()+end.start()]))
    chosen=[b for n,b in blocks if n==hc.get('module')]
    if not chosen and len(blocks)==1:chosen=[blocks[0][1]]
    if len(chosen)!=1:return {}
    pins=defaultdict(set)
    for m in re.finditer(r'(?m)^\s*PIN\s+(\S+)',chosen[0]):
        n=re.fullmatch(r'(.*)\[(-?\d+)\]',m[1])
        if n:pins[n[1].lstrip('\\')].add(int(n[2]))
        else:pins[m[1].lstrip('\\')].add(0)
    return {p:sorted(bits,reverse=True) for p,bits in pins.items()}


def match_hard_cores(hcs, insts):
    """Match only unique scoped identities; never overwrite a shared suffix."""
    def flat(s): return re.sub(r'_+', '_', re.sub(r'\[(\d+)\]', r'_\1', s.replace('.', '_')).lstrip('\\'))
    result, unknown = {}, []
    for mod, inst, *_ in insts:
        full, short = [], []
        compare_inst=flat(inst)
        for hc in hcs:
            if hc.get('module') != mod.lstrip('\\'): continue
            name = flat(hc['inst'])
            if compare_inst == name or compare_inst.endswith('_' + name): full.append(hc['inst'])
            tail = flat(hc['inst'].split('.',1)[-1])
            if compare_inst == tail or compare_inst.endswith('_' + tail): short.append(hc['inst'])
        choices = full or short
        if len(choices) == 1: result[inst] = choices[0]
        elif choices: unknown.append(dict(inst=inst, module=mod, candidates=choices))
    return result, unknown


ID = r"[A-Za-z_][A-Za-z0-9_$]*"
PURE = re.compile(r"^[\s{}\[\]:,0-9A-Za-z_$']*$")     # concatenation / bit select only (no ?:, &, |, ^, ~, +, ==)


def strip_comments(txt):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", txt, flags=re.S))


def idents(expr):
    out = []
    for m in re.finditer(ID, expr):
        s = m.group(0)
        # skip sized-literal pieces like 1'b0 / 595
        if re.match(r"^[0-9]", s) or s in ("b", "d", "h"):
            continue
        out.append(s)
    return out


def parse(txt):
    txt = strip_comments(txt)
    assigns = {}                            # lhs id -> (rhs ids, pure)
    for m in re.finditer(rf"\bassign\s+({ID})\s*(\[[^\]]*\])?\s*=\s*(.*?);", txt, flags=re.S):
        lhs, rhs = m.group(1), m.group(3)
        pure = bool(PURE.match(rhs.replace("'b", "").replace("'d", "").replace("'h", "")))
        prev = assigns.get(lhs)
        ids = idents(rhs)
        if prev:                            # several partial assigns: union, pure only if all pure
            assigns[lhs] = (prev[0] + ids, prev[1] and pure)
        else:
            assigns[lhs] = (ids, pure)
    insts = []                              # (module, inst, {port: expr})
    for m in re.finditer(rf"\n\s*({ID})\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*({ID})\s*\((.*?)\)\s*;", txt, flags=re.S):
        mod, inst, body = m.group(1), m.group(3), m.group(4)
        if mod in ("module", "assign", "wire", "reg", "input", "output", "always", "if", "for"):
            continue
        ports = {}
        for pm in re.finditer(rf"\.({ID})\s*\(", body):
            # balanced parens from pm.end()
            i, depth = pm.end(), 1
            while i < len(body) and depth:
                depth += {"(": 1, ")": -1}.get(body[i], 0)
                i += 1
            ports[pm.group(1)] = body[pm.end():i - 1]
        params = m.group(2) or ""
        dm = re.search(r"\.D\s*\(\s*(\d+)\s*\)", params)
        insts.append((mod, inst, ports, int(dm.group(1)) if dm else None))
    return assigns, insts


def trace(plan, tn, text, repo=None):
    """Trace every actual port bit through wiring/known transport only.

    Physical LEF directions determine hard-core producers and consumers; an
    unknown or ambiguous core stays unresolved rather than acquiring false
    connections from its name or another core's input.
    """
    t = plan['partition_types'][tn]
    sections = _module_sections(text)
    top = next((n for n in (t.get('module'), tn) if n in sections), None)
    body = select_module(text, top) if top else select_module(text)
    widths = declarations(body)
    assigns, insts = parse(body)
    params={m[3]:m[2] for m in re.finditer(r'\n\s*('+ID+r')\s*#\s*\(((?:[^()]|\([^()]*\))*)\)\s*('+ID+r')\s*\(',body,re.S)}
    hcs = t.get('hard_cores', [])
    hc_by_name = {h['inst']: h for h in hcs}
    core_of, ambiguous = match_hard_cores(hcs, insts)
    directions = {i: hc_port_directions(hc_by_name[c], repo) for i,c in core_of.items()}
    pin_indices = {i: hc_port_bit_indices(hc_by_name[c], repo) for i,c in core_of.items()}
    warnings = []
    missing_cores=sorted(set(hc_by_name)-set(core_of.values()))
    def bits(expr, where):
        try: return expression_bits(expr, widths)
        except ValueError as exc:
            warnings.append(dict(where=where, reason=str(exc)))
            return [], False
    # Each bit has one producer. Different partial assignments never join
    # unrelated concat fields; constants terminate a bit without shifting it.
    producers = defaultdict(list)
    def edge(lhs, rhs, stages, via):
        for a,b in align_bits(lhs, rhs):
            if a is not None:
                producers[a].append((b, stages, via))
    for m in re.finditer(r'\bassign\s+(.*?)\s*=\s*(.*?);', body, re.S):
        lhs,_ = bits(m[1], 'assign lhs')
        rhs,signed = bits(m[2], 'assign rhs')
        if lhs and rhs:
            for a,b in align_bits(lhs,rhs,signed):
                if a is not None: producers[a].append((b,0,None))
    bus_roots = {}
    bus_out = defaultdict(list)
    core_inputs = []
    core_outputs = defaultdict(set)
    unknown = []
    for mod, inst, ports, D in insts:
        relay = mod=='ot_s81_rly' or bool(re.fullmatch(r'dsfd_rly_\d+_(SN|SW|WS)',mod))
        seam = mod=='ot_pl_seam_r_plq'
        if mod in ('ot_dp_st','ot_dp_dly') or relay or seam:
            qport,dport=('o','i') if relay else ('o','d') if seam else ('q','d')
            q,_ = bits(ports.get(qport,''), inst+'.'+qport)
            d,sgn = bits(ports.get(dport,''), inst+'.'+dport)
            if mod == 'ot_dp_st' and inst.startswith('u_bin_'):
                bus = inst[len('u_bin_'):]
                if bus in {b['name'] for b in t.get('buses',[]) if b.get('dir')=='in'}:
                    for i,a in enumerate(q):
                        if a is not None: bus_roots[a]=(bus,i)
                else: warnings.append(dict(where=inst,reason='unrecognized input face bus'))
            elif mod == 'ot_dp_st' and inst.startswith('u_bout_'):
                bus = inst[len('u_bout_'):]
                for i,a in enumerate(d):
                    if a is not None: bus_out[a].append((bus,i))
            elif q and d:
                if seam:
                    km=re.search(r'\.K\s*\(\s*(\d+)\s*\)',params.get(inst,''))
                    if '.K' in params.get(inst,'') and km is None:
                        warnings.append(dict(where=inst,reason='nonliteral seam K'));continue
                    stages=max(2,int(km[1]) if km else 2)-1
                elif mod=='ot_dp_dly':
                    if D is None and '.D' in params.get(inst,''):
                        warnings.append(dict(where=inst,reason='nonliteral delay D'));continue
                    stages=D if D is not None else 1
                else: stages=1
                for a,b in align_bits(q,d,sgn):
                    if a is not None: producers[a].append((b,stages,inst))
            continue
        core = core_of.get(inst)
        if core is None: continue
        for port,expr in ports.items():
            bb,sgn = bits(expr,inst+'.'+port)
            direction = directions[inst].get(port.lstrip('\\'))
            if direction not in ('INPUT','OUTPUT'):
                unknown.append(dict(core=core,port=port,reason='unknown/unsupported LEF direction'))
                continue
            indices=pin_indices[inst].get(port.lstrip('\\'),[])
            if not indices:
                unknown.append(dict(core=core,port=port,reason='unknown LEF bit indices'))
                continue
            if direction=='INPUT':
                pairs=align_bits(indices,bb,sgn)
            else:
                n=min(len(indices),len(bb))
                pairs=list(zip(indices[-n:],bb[-n:])) if n else []
            for i,bit in pairs:
                if bit is None: continue
                if direction=='OUTPUT': core_outputs[bit].add((core,port,i))
                else: core_inputs.append((core,port,i,bit))

    roots = {}
    for bit, values in core_outputs.items():
        if len(values)==1: roots[bit]=next(iter(values))
        else: unknown.append(dict(bit=bit,reason='multiple hard-core producers'))
    edges = {}
    for bit,values in producers.items():
        values=set(values)
        if len(values)==1 and bit not in roots and bit not in bus_roots:
            edges[bit]=next(iter(values))
        else:
            roots.pop(bit,None);bus_roots.pop(bit,None)
            unknown.append(dict(bit=bit,reason='multiple/ambiguous wiring producers'))
    def back(bit):
        seen,via,st = set(),[],0
        while bit is not None and bit not in seen:
            seen.add(bit)
            if bit in roots: return ('core',roots[bit],st,tuple(via),bit)
            if bit in bus_roots: return ('bus',bus_roots[bit],st,tuple(via),bit)
            if bit not in edges: return None
            bit,more,node=edges[bit];st+=more
            if node:via.append(node)
        return None
    conns=defaultdict(lambda:defaultdict(set))
    paths={}
    def record(core,port,direction,what,st,via,bit):
        kind,target=what
        key=(core,port,direction,kind,target,st,tuple(via))
        if key not in paths:
            row=dict(core=core,port=port,dir=direction,stages_existing=st,via=list(via),_bits=set())
            row['bus' if kind=='bus' else 'partner']=target
            paths[key]=row
        paths[key]['_bits'].add(bit)
        conns[core][port].add(('bus:' if kind=='bus' else 'core:')+target)
    for core,port,i,bit in core_inputs:
        result=back(bit)
        if result is None:continue
        kind,target,st,via,sourcebit=result
        if kind=='bus':record(core,port,'in',('bus',target[0]),st,via,i)
        elif target[0]!=core:
            record(core,port,'in',('core',target[0]+'.'+target[1]),st,via,i)
            record(target[0],target[1],'out',('core',core+'.'+port),st,tuple(reversed(via)),target[2])
    # Follow each pure output-bus bit backward as well: this avoids vector-wide
    # forward alias unions and naturally handles concatenation slices.
    for bit,users in bus_out.items():
        result=back(bit)
        if result is None or result[0]!='core':continue
        _,target,st,via,_=result
        for bus,i in users:record(target[0],target[1],'out',('bus',bus),st,tuple(reversed(via)),target[2])
    rows=[]
    for _,row in sorted(paths.items(),key=lambda kv:repr(kv[0])):
        bb=sorted(row.pop('_bits'));row['bits_connected']=len(bb);row['bit_sample']=bb[:8]
        ranges=[]
        for bit in bb:
            if ranges and bit==ranges[-1][1]+1:ranges[-1][1]=bit
            else:ranges.append([bit,bit])
        row['bit_ranges']=ranges;rows.append(row)
    return dict(core_conns={tn:{c:{p:sorted(v) for p,v in sorted(ps.items())} for c,ps in sorted(conns.items())}},
                paths=rows,n_insts=len(insts),n_assigns=len(assigns),cores=sorted(hc_by_name),buses=len(t.get('buses',[])),
                unresolved=unknown,ambiguous_cores=ambiguous,wiring_warnings=warnings,
                matched_cores=sorted(set(core_of.values())), unresolved_cores=missing_cores)


def main(argv):
    plan_path, tn, bound, out = argv[1:5]
    res = trace(json.load(open(plan_path)), tn, open(bound).read())
    json.dump(res, open(out, "w"), indent=1)
    conns = res["core_conns"][tn]
    print(f"{tn}: {len(res['paths'])} wiring paths, {sum(len(ps) for ps in conns.values())} core ports connected, "
          f"cores {len(conns)}/{len(res['cores'])}")


if __name__ == "__main__":
    main(sys.argv)
