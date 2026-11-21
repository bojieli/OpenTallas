#!/usr/bin/env python3
"""portfix178 overlay sources must be mutually consistent: every named parameter override on a module defined in the overlay
set exists on that module (S81-BKSEL-R5 11-20: l20s passed .MLK to a dsdv_idx_txm that had no MLK -> verilator PINNOTFOUND)."""
import re, sys, unittest
from pathlib import Path
D = Path(__file__).resolve().parent / 'source_modules' / 'portfix178'

def strip(t):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', t, flags=re.S))

def balanced(t, i):
    d = 0
    for j in range(i, len(t)):
        d += t[j] == '('
        d -= t[j] == ')'
        if d == 0:
            return j
    raise ValueError('unbalanced')

def params_of(src):
    mods = {}
    for m in re.finditer(r'\bmodule\s+(\w+)\s*#\s*\(', src):
        j = balanced(src, m.end() - 1)
        body, names, d = src[m.end():j], set(), 0
        for part in re.split(r',(?![^\[\(\{]*[\]\)\}])', body):
            mm = re.match(r'\s*(?:parameter\b[^=]*?)?(\w+)\s*=', part)
            if mm:
                names.add(mm.group(1))
        mods[m.group(1)] = names
    for m in re.finditer(r'\bmodule\s+(\w+)\s*(?!#)[(;]', src):
        mods.setdefault(m.group(1), set())
    return mods

class OverlayParams(unittest.TestCase):
    def test_overrides_exist(self):
        srcs = {f.name: strip(f.read_text()) for f in sorted(D.glob('*.sv'))}
        mods = {}
        for s in srcs.values():
            mods.update(params_of(s))
        bad = []
        for n, s in srcs.items():
            for m in re.finditer(r'^\s*(\w+)\s*#\s*\(', s, flags=re.M):
                if m.group(1) not in mods:
                    continue
                j = balanced(s, m.end() - 1)
                for p in re.findall(r'\.(\w+)\s*\(', s[m.end():j]):
                    if p not in mods[m.group(1)]:
                        bad.append((n, m.group(1), p))
        self.assertEqual(bad, [])

    def test_txm_has_mlk(self):
        self.assertIn('MLK', params_of(strip((D / 'dsdv_idx_tree.sv').read_text()))['dsdv_idx_txm'])

if __name__ == '__main__':
    unittest.main()
