#!/usr/bin/env python3
"""Remove the split_asm alias LOOPS from the actual five-core q3 producer assembly (structural assembly fix).

split_asm.py (ALIASES 10-25) adds 'assign <internal> = <core-port connection bit>' for every parent net that is read but
no longer driven once the remainder instance is replaced.  For a master OUTPUT the flattened parent ALSO still carries
its own 'assign <master port> = {<internal> ...}'.  The core instance output already drives the master port, so that
parent assign closes a zero-delay loop (port <- internal <- port: Verilator 'wire x=x') and double-drives the port.
This tool drops a parent assign statement only when EVERY bit of its LHS is the exact reverse of an alias drive
(LHS bit b <- internal r while the alias block has r <- b) AND the LHS net is connected at a core instance; anything
partial is refused (exit 2).  Nothing else changes.
Usage: q3_asm_alias_loops.py <asm.sv> <out.sv> <report.json>"""
import re, sys, json, hashlib
src, dst, rep = sys.argv[1:4]
raw = open(src).read()
lines = raw.split('\n')
ID = r'(?:\\\S+|[A-Za-z_][\w$]*)'
BIT = re.compile(r'\s*(' + ID + r')\s*(?:\[(\d+)\])?\s*')
decl = {}
for m in re.finditer(r'^\s*(?:input|output|wire)\s+(?:\[(\d+):(\d+)\]\s*)?(' + ID + r')\s*;', raw, re.M):
    if m.group(3) not in decl:
        decl[m.group(3)] = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
def bits(expr):
    e = expr.strip()
    items = [x for x in re.split(r'\s,\s|,\s|\s,', e[1:-1])] if e.startswith('{') and e.endswith('}') else [e]
    out = []
    for it in items:
        it = it.strip()
        m = re.fullmatch(r'(' + ID + r')\s*(?:\[(\d+)\])?', it)
        if not m:
            return None
        n, i = m.group(1), m.group(2)
        if i is not None:
            out.append((n, int(i)))
        else:
            r = decl.get(n)
            if r is None:
                out.append((n, None))
            else:
                hi, lo = r; step = -1 if hi >= lo else 1
                out += [(n, k) for k in range(hi, lo + step, step)]
    return out
# instance spans and alias block
inst_lines = [i for i, l in enumerate(lines) if re.match(r'^  ot_\w+ u_\w+ \($', l)]
ends = []
for s in inst_lines:
    j = s
    while lines[j] != '  );':
        j += 1
    ends.append(j)
conn_text = '\n'.join('\n'.join(lines[s:e + 1]) for s, e in zip(inst_lines, ends))
alias = {}
for i in range(ends[0] + 1, inst_lines[1] if len(inst_lines) > 1 else len(lines)):
    m = re.match(r'^  assign (.+?)\s+=\s+(.+);$', lines[i])
    if m:
        l, r = bits(m.group(1)), bits(m.group(2))
        if l and r and len(l) == len(r) == 1:
            alias[l[0]] = r[0]
drop, partial = [], []
for i in range(ends[-1] + 1, len(lines)):
    m = re.match(r'^  assign (.+?)\s+=\s+(.+);$', lines[i])
    if not m:
        continue
    l, r = bits(m.group(1)), bits(m.group(2))
    if not l or not r or len(l) != len(r):
        continue
    rev = [alias.get(rb) == lb for lb, rb in zip(l, r)]
    if all(rev):
        name = l[0][0]
        if not re.search(r'[\s{(]' + re.escape(name) + r'(\[|\s|\)|,|\})', conn_text):
            partial.append((i + 1, 'lhs not connected at a core instance'))
        else:
            drop.append(i)
    elif any(rev):
        partial.append((i + 1, '%d/%d bits reverse-aliased' % (sum(rev), len(rev))))
if partial:
    print('ALIAS_LOOPS REFUSE', partial[:10]); sys.exit(2)
dropped = [lines[i].strip()[:160] for i in drop]
for i in drop:
    lines[i] = '  // q3_asm_alias_loops: dropped loop ' + lines[i].strip().split('=')[0].replace('assign', '').strip()
out = '\n'.join(lines)
open(dst, 'w').write(out)
json.dump(dict(src=src, src_sha256=hashlib.sha256(raw.encode()).hexdigest(), out_sha256=hashlib.sha256(out.encode()).hexdigest(),
               alias_drives=len(alias), dropped_parent_assigns=len(drop), dropped=dropped), open(rep, 'w'), indent=1)
print('ALIAS_LOOPS PASS alias_drives=%d dropped_parent_assigns=%d' % (len(alias), len(drop)))
