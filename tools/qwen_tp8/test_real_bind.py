#!/usr/bin/env python3
"""real_bind.py: a by-name closed view that fits is real (corrected export) / provisional (pre-fix export); an outline
or pin mismatch, an alias view and an open job stay placeholder; the built LEF carries the view macro verbatim."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import real_bind  # noqa: E402


def lef(name, w, h, pins):
    return f'MACRO {name}\n  SIZE {w} BY {h} ;\n' + ''.join(f'  PIN {p}\n  END {p}\n' for p in pins) + f'END {name}\n'


def view(root, sub, name, w, h, pins, job, verdict):
    d = root / 'physical' / sub / name
    d.mkdir(parents=True)
    (d / f'{name}.lef').write_text('VERSION 5.8 ;\n' + lef(name, w, h, pins) + 'END LIBRARY\n')
    for c in ('tt', 'ff', 'ss'):
        (d / f'{name}_{c}.lib').write_text(f'library (x) {{\n  cell ({name}) {{ area : 1; /* {c} */ }}\n}}\n')
    a = {'orfs_dir': f'/s/closure-loop/{job}/routes/r/work/orfs', 'ok': True}
    if verdict:
        a['verdict'] = {'expect_ps': {'tt': 1.0, 'ff': 1.0}}
    (d / 'abstract.json').write_text(json.dumps(a))


class T(unittest.TestCase):
    def test_bind(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo, case, prev = td / 'repo', td / 'case', td / 'prev'
            case.mkdir()
            prev.mkdir()
            P = ['VDD', 'VSS', 'ck', 'a[0]', 'a[1]']
            view(repo, 'ref_tile/k_a/views', 'm_real', 10.0, 20.0, P, 'ja', True)
            view(repo, 'ref_tile/k_b/views', 'm_prov', 10.0, 20.0, P, 'jb', False)
            view(repo, 'ref_tile/k_c/views', 'm_out', 11.0, 20.0, P, 'jc', True)
            view(repo, 'ref_tile/k_d/views', 'm_pin', 10.0, 20.0, P + ['b'], 'jd', True)
            view(repo, 'ref_tile/k_e/views', 'm_open', 10.0, 20.0, P, 'je', True)
            view(repo, 'qwen_die_masters/views', 'm_alias_a', 10.0, 20.0, P, 'jf', True)
            view(repo, 'ref_tile/k_g/views', 'm_new', 5.0, 5.0, ['VDD', 'VSS', 'd[0]', 'q[0]', 'clk'], 'jg', True)
            ms = ['m_real', 'm_prov', 'm_out', 'm_pin', 'm_open', 'm_alias', 'qfd_none']
            (case / 'elements.lef').write_text('VERSION 5.8 ;\n' + ''.join(lef(m, 10.0, 20.0, P) for m in ms) + 'END LIBRARY\n')
            (case / 'die.v').write_text('module die ();\n' + ''.join(f'  {m} u_{m} (.ck(c), .a(x));\n' for m in ms) +
                                        '  m_new u0 (.d(a), .q(b), .clk(c));\n  m_new u1 (.d(a), .q(b), .clk(c));\nendmodule\n')
            (td / 'st').write_text(''.join(f'{j} CLOSED commit\n' for j in ('ja', 'jb', 'jc', 'jd', 'jf', 'jg')) + 'je NEEDS_RTL x\n')
            (prev / 'el_tt.lib').write_text('library (p) {\n  cell (m_real) { area : 9; }\n  cell (qfd_none) { area : 2; }\n}\n')
            out = td / 'out'
            real_bind.main(['--case', str(case), '--repo', str(repo), '--status', str(td / 'st'), '--prev-libs', str(prev),
                            '--bind', str(td / 'b.json'), '--out', str(out)])
            b = json.loads((td / 'b.json').read_text())['masters']
            self.assertEqual({m: b[m]['class'] for m in b},
                             {'m_real': 'real', 'm_prov': 'provisional', 'm_out': 'placeholder', 'm_pin': 'placeholder',
                              'm_open': 'placeholder', 'm_alias': 'placeholder', 'qfd_none': 'placeholder', 'm_new': 'real'})
            self.assertEqual(b['m_prov']['export'], 'pre-fix')
            self.assertIn('outline mismatch (case 10x20 vs view 11x20)', b['m_out']['reason'])
            self.assertIn('pin mismatch', b['m_pin']['reason'])
            self.assertIn('NEEDS_RTL', b['m_open']['reason'])
            self.assertIn('by-role', b['m_alias']['reason'])
            self.assertEqual(b['m_new']['instances'], 2)
            t = (out / 'elements_real.lef').read_text()
            self.assertEqual(t.count('MACRO m_real\n'), 1)
            self.assertEqual(t.count('MACRO m_new\n'), 1)
            self.assertEqual(t.count('END LIBRARY'), 1)
            el = (out / 'el_tt.lib').read_text()                 # the bound cell left the placeholder lib
            self.assertNotIn('cell (m_real)', el)
            self.assertIn('cell (qfd_none)', el)
            self.assertEqual((out / 'real/m_real_tt.lib').read_text(),
                             (repo / 'physical/ref_tile/k_a/views/m_real/m_real_tt.lib').read_text())
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
            import die_real_census as drc
            inst = drc.netlist_instances(case / 'die.v')
            libs = [Path(x) for x in (out / 'libs_tt.txt').read_text().split()]
            r = drc.census_case(inst, [out / 'elements_real.lef'], libs, [repo])['masters']
            self.assertEqual({m for m in r if r[m]['class'] == 'real'}, {'m_real', 'm_prov', 'm_new'})


if __name__ == '__main__':
    unittest.main()
