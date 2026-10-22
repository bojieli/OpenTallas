#!/usr/bin/env python3
"""SQC-CTLM 10-22: function-exact check for replica re-deal / kept-copy netlists (extends rr_equiv.py to FLOP copies).

usage: geo_equiv.py <original.sv> <candidate.sv> [--new-prefix u_qkgeo_]

Flop classes: in the ORIGINAL netlist, flops with identical (type, D, C, R) nets are one class (identical inputs give
identical state from the first edge / reset on).  A flop's Q net is a leaf named by its class representative.  Every
combinational net is canonicalised structurally (type + canonical inputs).  The candidate passes when
  1. every non-cell line (ports, macros, hard children, assigns) is byte-identical (wire declarations excepted),
  2. every original cell exists with the same type and every pin net is canonically identical to the original's,
  3. every new cell carries the new prefix and is an identical copy: a flop copy has the canonical D/C/R of an
     original flop (it joins that class), a combinational copy is canonically identical to an original net,
  4. every flop of the candidate has D/C/R canonically identical to its class representative's original D/C/R
     (inductive bisimulation: equal classes stay equal every cycle),
so every port, macro pin and register sees the same value every cycle: no port-visible latency or function change.
"""
import argparse, hashlib, re, sys
sys.setrecursionlimit(1000000)
ap = argparse.ArgumentParser(); ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('--new-prefix', default='u_qkgeo_')
args = ap.parse_args()
cell_re = re.compile(r'^(\(\* [^*]*\*\) )?(qfd_bmath_\w+) #\(\.ID\(0\)\) (\\\S+ |[^\s(]+)\((.*)\);$')
pin_re = re.compile(r'\.(\w+)\(([^()]*)\)')
def outp(t): return 'Q' if t.startswith('qfd_bmath_dff') else 'Y'
def load(f):
    C = {}; D = {}; other = []
    for l in open(f):
        l = l.rstrip('\n'); m = cell_re.match(l)
        if not m:
            if not l.startswith('wire '): other.append(l)
            continue
        t = m.group(2); n = m.group(3).strip(); pins = dict(pin_re.findall(m.group(4))); C[n] = (t, pins)
        o = outp(t)
        if o in pins:
            if pins[o] in D: sys.exit(f'FAIL multiple drivers {pins[o]}')
            D[pins[o]] = n
    return C, D, other
A, DA, OA = load(args.a); B, DB, OB = load(args.b)
if OA != OB: sys.exit('FAIL non-cell lines differ')
cls = {}; rep = {}
for n, (t, p) in sorted(A.items()):
    if t.startswith('qfd_bmath_dff'):
        k = (t, p.get('D'), p.get('C'), p.get('R')); rep[n] = cls.setdefault(k, n)
def canon(C, D, R):
    memo = {}
    def c(net):
        if net in memo: return memo[net]
        stack = [net]; order = []
        while stack:  # iterative post-order (deep cones)
            x = stack.pop()
            if x in memo: continue
            d = D.get(x)
            if d is None or C[d][0].startswith('qfd_bmath_dff'):
                memo[x] = ('FF:' + R(d)) if d is not None else x; continue
            t, p = C[d]; ins = [v for q, v in sorted(p.items()) if q != 'Y']
            pend = [v for v in ins if v not in memo]
            if pend: stack.append(x); stack.extend(pend); continue
            memo[x] = hashlib.sha1((t + '|' + '|'.join(q + '=' + memo[v] for q, v in sorted(p.items()) if q != 'Y')).encode()).hexdigest()
        return memo[net]
    return c
newrep = {}
def RB(f):
    if f in rep: return rep[f]
    return newrep[f]
# merge original classes whose D/C/R are canonically identical under the classes proven so far (fixpoint)
while True:
    ca = canon(A, DA, lambda f: rep[f]); ckey = {}; merged = 0
    for n, (t, p) in sorted(A.items()):
        if not t.startswith('qfd_bmath_dff'): continue
        k = (t,) + tuple(ca(p[q]) if q in p else None for q in ('D', 'C', 'R'))
        r = ckey.setdefault(k, rep[n])
        if r != rep[n]:
            old = rep[n]
            for f in [f for f, x in rep.items() if x == old]: rep[f] = r
            merged += 1
    if not merged: break
bad = 0; pending = []
for n, (t, p) in B.items():
    if n in A: continue
    if not n.lstrip('\\').startswith(args.new_prefix): print('FAIL unexpected new cell', n); bad += 1; continue
    if t.startswith('qfd_bmath_dff'): pending.append(n)
class Unres(Exception): pass
def RB(f):
    if f in rep: return rep[f]
    if f in newrep: return newrep[f]
    raise Unres(f)
# new flop copies join the class of an original flop with canonically identical D/C/R (fixpoint over copies)
while pending:
    cb = canon(B, DB, RB); left = []
    for n in pending:
        t, p = B[n]
        try: k = (t,) + tuple(cb(p[q]) if q in p else None for q in ('D', 'C', 'R'))
        except Unres: left.append(n); continue
        if k in ckey: newrep[n] = ckey[k]
        else: print('FAIL flop copy with no identical original', n); bad += 1
    if len(left) == len(pending): print('FAIL unresolved flop copies', left[:5]); bad += len(left); break
    pending = left
cb = canon(B, DB, RB)
moved = 0
for n, (t, p) in A.items():
    if n not in B: print('FAIL cell missing', n); bad += 1; continue
    t2, p2 = B[n]
    if t2 != t or set(p2) != set(p): print('FAIL cell changed', n); bad += 1; continue
    for q, v in p.items():
        if q == outp(t):
            if p2[q] != v: print('FAIL output renamed', n); bad += 1
            continue
        if p2[q] != v:
            moved += 1
            if ca(v) != cb(p2[q]):
                bad += 1
                if bad < 10: print('FAIL non-identical driver', n, q, v, p2[q])
newc = 0
for n, (t, p) in B.items():
    if n in A: continue
    newc += 1
    # combinational copies: every pin that reads one is checked above against the original driver
# 4. bisimulation obligation on every flop of the candidate
for n, (t, p) in B.items():
    if not t.startswith('qfd_bmath_dff'): continue
    r = RB(n); tr, pr = A[r]
    for q in ('D', 'C', 'R'):
        if q in p and ca(pr[q]) != cb(p[q]):
            bad += 1
            if bad < 20: print('FAIL flop input differs from class', n, q, 'rep', r)
print(f'pins re-pointed {moved}  new cells {newc}  flop classes {len(cls)}  failures {bad}')
print('PASS function-exact' if not bad else 'FAIL')
sys.exit(1 if bad else 0)
