#!/usr/bin/env python3
"""KV-CORES-R4: flatten selected bind_compose head composites back into a bound partition so kv_core_rtl.py can
re-derive the core RTL + core.json from the CURRENT bind (b51).  The b51 bind (recipe compose:) replaced the member
leaves of each head eighth by one composite module (composed_rtl/<sha>.sv, content-addressed); kv_core_rtl.py wants
the member leaves in the bound partition.  This inlines exactly the composite body (leaves, params, nets, constants)
at the instance, renaming member instances m<i> -> u_<plan member> (members order = bind_compose receipt order).
usage: inline_heads.py KITDIR_IN KITDIR_OUT MEMBERS_JSON inst=compfile [...]   (inst = bound instance, e.g. u_head0_e6)"""
import json, re, shutil, sys
from pathlib import Path

kin, kout, memj = Path(sys.argv[1]), Path(sys.argv[2]), json.load(open(sys.argv[3]))
sel = dict(a.split('=', 1) for a in sys.argv[4:])
kout.mkdir(parents=True, exist_ok=True)
kj = json.load(open(kin / 'kit_rtl.json'))
bp = kin / f"{kj['bound_module']}.sv"
text = bp.read_text()
DECL = re.compile(r'^\s*(?:input|output|inout|wire)\s+(?:wire\s+|logic\s+)?(?:\[(\d+):(\d+)\]\s*)?([A-Za-z_]\w*)', re.M)
width = {m.group(3): (int(m.group(1)), int(m.group(2))) if m.group(1) else None for m in DECL.finditer(text)}


def split_top(s, sep=','):
    out, d, cur = [], 0, ''
    for ch in s:
        if ch in '({[': d += 1
        if ch in ')}]': d -= 1
        if ch == sep and d == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur)
    return [x.strip() for x in out]


def bits(e):
    """LSB-first bit expressions of a bound-side connection expression"""
    e = e.strip()
    if e.startswith('{') and e.endswith('}'):
        r = []
        for p in reversed(split_top(e[1:-1])):
            r += bits(p)
        return r
    m = re.fullmatch(r"(\d+)'([bd])([0-9_xzXZ]+)", e)
    if m:
        n = int(m.group(1)); v = m.group(3).replace('_', '')
        v = v if m.group(2) == 'b' else bin(int(v))[2:]
        v = v.rjust(n, '0')[-n:]
        return [f"1'b{c}" for c in reversed(v)]
    m = re.fullmatch(r'([A-Za-z_]\w*)\s*\[(\d+):(\d+)\]', e)
    if m:
        h, l = int(m.group(2)), int(m.group(3))
        return [f'{m.group(1)}[{i}]' for i in range(l, h + 1)]
    m = re.fullmatch(r'([A-Za-z_]\w*)\s*\[(\d+)\]', e)
    if m:
        return [e.replace(' ', '')]
    m = re.fullmatch(r'[A-Za-z_]\w*', e)
    if m:
        w = width.get(e, 'missing')
        if w == 'missing':
            raise SystemExit(f'no declaration for {e}')
        return [e] if w is None else [f'{e}[{i}]' for i in range(w[1], w[0] + 1)]
    raise SystemExit(f'unparsed connection {e!r}')


report = {}
for inst, cf in sel.items():
    ctext = Path(cf).read_text()
    cmod = re.match(r'\s*module\s+(\w+)', ctext).group(1)
    m = re.search(rf'^\s*{cmod}\s+{inst}\s*\((.*?)\n\s*\);\n', text, re.S | re.M)
    if not m:
        raise SystemExit(f'{inst} ({cmod}) not found in {bp}')
    conns = {}
    for c in split_top(m.group(1)):
        cm = re.fullmatch(r'\.(\w+)\s*\((.*)\)', c, re.S)
        conns[cm.group(1)] = bits(cm.group(2)) if cm.group(2).strip() else []
    ports = {pm.group(4): (pm.group(1), int(pm.group(3) or 0)) for pm in re.finditer(
        r'^\s*(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)', ctext, re.M)}   # name -> (dir, lsb)
    head = re.match(r'u_(head\d+)_e\d+$', inst).group(1)
    key = next(k for k, v in memj.items() if k.endswith(f'_{head}_{inst.split("_")[-1]}') and v['module'] == cmod)
    members = memj[key]['members']
    pre = f'r4_{inst}_'
    unconn = []

    def pbit(name, i):
        b = conns.get(name)
        j = i - ports[name][1]
        if b is None or not 0 <= j < len(b):
            return None
        return b[j]

    def sub(s):
        def rp(mm):
            n, i = mm.group(1), int(mm.group(2))
            if n in ports:
                v = pbit(n, i)
                if v is None:
                    if ports[n][0] == 'input':
                        raise SystemExit(f'{inst}: input {n}[{i}] unconnected in the bound partition')
                    return '__UNCONN__'
                return v
            return mm.group(0)
        s = re.sub(r'\b([A-Za-z_]\w*)\[(\d+)\]', rp, s)
        return re.sub(r'\bn(\d+)\b', lambda mm: f'{pre}n{mm.group(1)}', s)

    # resolve the composite's alias assigns (port bit <-> nK, constant -> nK) onto the bound bit itself, so the flat
    # partition has no bit-select assigns (rtlnet keeps whole-net aliases only)
    alias, extra = {}, []
    for ln in ctext.splitlines():
        am = re.fullmatch(r'assign\s+(\S+)\s*=\s*(\S+);', ln.strip())
        if not am:
            continue
        l, r = am.group(1), am.group(2)
        if re.fullmatch(r'n\d+', r) and not re.fullmatch(r'n\d+', l):      # output port bit = nK
            pm_ = re.fullmatch(r'(\w+)\[(\d+)\]', l)
            v = pbit(pm_.group(1), int(pm_.group(2)))
            if v is None:
                continue
            if r in alias:
                extra.append(f'assign {v} = {alias[r]};')
            else:
                alias[r] = v
        elif re.fullmatch(r'n\d+', l):                                       # nK = input port bit / constant
            if re.fullmatch(r"1'b[01xz]", r):
                v = r
            else:
                pm_ = re.fullmatch(r'(\w+)\[(\d+)\]', r)
                v = pbit(pm_.group(1), int(pm_.group(2)))
                if v is None:
                    raise SystemExit(f'{inst}: input {r} unconnected')
            if l in alias:
                raise SystemExit(f'{inst}: {l} aliased twice')
            alias[l] = v
        else:
            raise SystemExit(f'{inst}: unexpected assign {ln.strip()}')
    sub0 = sub

    def sub(s):
        s = re.sub(r'\bn(\d+)\b', lambda mm: alias.get('n' + mm.group(1), 'n' + mm.group(1)), s)
        return sub0(s)
    out = [f'    // KV-CORES-R4 inline_heads.py: composite {cmod} {inst} (b51 composed_rtl {Path(cf).name[:16]}) flattened, '
           f'members {", ".join(members)}']
    nw = na = ni = 0
    for ln in ctext.splitlines():
        s = ln.strip()
        if re.fullmatch(r'wire n\d+;', s):
            if s[5:-1] not in alias:
                out.append('    ' + sub(s)); nw += 1
        elif s.startswith('assign '):
            continue
        elif re.match(r'[A-Za-z_]\w*\s+(#\(.*\)\s+)?m\d+\s*\(', s):
            mi = int(re.match(r'[A-Za-z_]\w*\s+(?:#\(.*\)\s+)?m(\d+)\s*\(', s).group(1))
            mem = members[mi]
            plan_inst = f'{head}__' + mem.split('__', 1)[1]
            bn = 'u_' + plan_inst.replace('__', '_')
            r = sub(s)
            r = re.sub(rf'\)\s+m{mi}\s*\(', f') {bn} (', r, count=1) if '#(' in r else re.sub(rf'^(\w+)\s+m{mi}\s*\(', rf'\1 {bn} (', r)
            if '__UNCONN__' in r:
                raise SystemExit(f'{inst}: unconnected port bit inside instance {bn}')
            out.append('    ' + r); ni += 1
    out += ['    ' + sub0(x) for x in extra]; na = len(extra)
    text = text[:m.start()] + '\n'.join(out) + '\n' + text[m.end():]
    report[inst] = dict(module=cmod, composite=str(cf), members=members, wires=nw, assigns=na, instances=ni,
                        unconnected_output_bits=len(unconn), bound_ports=len(conns))
(kout / bp.name).write_text(text)
fl = [l.strip() for l in open(kin / 'kit_rtl.f') if l.strip()]
drop = {str(Path(c).resolve()) for c in sel.values()}
fl2 = [f for f in fl if str(Path(f).resolve()) not in drop]
(kout / 'kit_rtl.f').write_text('\n'.join(fl2) + '\n')
for f in ('kit_rtl.json', 'kit_rtl_sim.f', f"{kj['bound_module'].replace('_bound', '')}.sv"):
    if (kin / f).exists() and not (kout / f).exists():
        shutil.copyfile(kin / f, kout / f)
(kout / 'inline_heads.json').write_text(json.dumps(dict(source=str(bp), dropped_files=sorted(drop), cores=report), indent=1) + '\n')
print(json.dumps(report, indent=1)[:3000])
