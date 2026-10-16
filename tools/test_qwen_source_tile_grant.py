"""Clock grants are bound to source ports, including partitioned and legacy roots."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qwen_split import source_pin_plan as plan


class TileGrantTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'rtl/physical').mkdir(parents=True)
        self.addCleanup(patch.stopall)
        patch.object(plan, 'ROOT', self.root).start()
        patch.dict(os.environ, {'OT_SPLIT_TILE_GRANT': 'grant.json'}).start()

    def fixture(self, count):
        clocks = ['ck'] + [f'ck_bank{i}' for i in range(count - 1)]
        top = 'qfd_tile_nk_test'
        (self.root / f'rtl/physical/{top}.sv').write_text(
            f'module {top}(' + ', '.join(f'input wire {c}' for c in clocks)
            + ', input wire rst_n, output wire [3:0] data); endmodule\n')
        return dict(top=top, home_um=[457.92, 950.4], clocks=clocks,
                    pins=[dict(name=c, clock=True) for c in clocks]
                    + [dict(name='rst_n', clock=False)]
                    + [dict(name=f'data[{i}]', clock=False) for i in range(4)])

    def read(self, grant):
        (self.root / 'grant.json').write_text(json.dumps(grant))
        return plan.tile_grant()

    def test_accepts_source_matching_partitioned_and_legacy_roots(self):
        for count in (13, 17, 45):
            with self.subTest(count=count):
                g = self.fixture(count)
                self.assertEqual(self.read(g), g)

    def test_clock_and_pin_mutations_fail_closed(self):
        original = self.fixture(17)
        mutations = (
            lambda g: g['clocks'].pop(),
            lambda g: g['clocks'].append('ck_missing'),
            lambda g: g['clocks'].append(g['clocks'][0]),
            lambda g: g['pins'][0].update(clock=False),
            lambda g: g['pins'].append(dict(name='rst_n', clock=True)),
            lambda g: g['pins'].append(dict(g['pins'][0])),
            lambda g: g['pins'][0].update(name='ck_wrong'),
        )
        for mutate in mutations:
            g = copy.deepcopy(original)
            mutate(g)
            with self.subTest(grant=g), self.assertRaises(ValueError):
                self.read(g)

    def test_missing_or_mismatched_source_fails(self):
        g = self.fixture(17)
        g['top'] = 'missing'
        with self.assertRaises(FileNotFoundError):
            self.read(g)
        g['top'] = '../outside'
        with self.assertRaises(ValueError):
            self.read(g)

    def test_invalid_outline_fails(self):
        for outline in ([0, 950.4], [457.92, -1], [float('nan'), 950.4], [457.92]):
            g = self.fixture(17)
            g['home_um'] = outline
            with self.subTest(outline=outline), self.assertRaises(ValueError):
                self.read(g)

    def test_non_scalar_or_output_clock_fails(self):
        for declaration in ('input wire [1:0] ck', 'output wire ck'):
            g = self.fixture(1)
            (self.root / 'rtl/physical/qfd_tile_nk_test.sv').write_text(
                f'module qfd_tile_nk_test({declaration}, input wire rst_n); endmodule\n')
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                self.read(g)


if __name__ == '__main__':
    unittest.main()
