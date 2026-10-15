"""Exercise the real die writer on face pins fragmented by source joins."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_split.direct_up4 import partition_master


def die_pin_writer():
    source = Path(__file__).resolve().parents[1] / 'qwen_kv_die/tp8b_v5.py'
    tree = ast.parse(source.read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'pin_rects')
    env = dict(base_pr=lambda *args: [], split={}, join_plan={}, VIEWS={},
               v=SimpleNamespace(EMIT_SPLIT=False))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), env)
    return env['pin_rects']


class FragmentPinRectangles(unittest.TestCase):
    def test_all_face_rectangles_survive_reordered_fragment_and_die_emission(self):
        # The E-face case is C21s tt_ctlm/mee[0]; the old centre-only
        # reconstruction produced 777.456..777.552 under full parent OBS.
        source = [('e[0]', 'M4', (777.408, 926.880, 777.600, 926.904)),
                  ('e[1]', 'M4', (777.408, 926.976, 777.600, 927.000)),
                  ('w[0]', 'M4', (0., 100., .192, 100.024)),
                  ('s[0]', 'M5', (58.752, 0., 58.776, .192)),
                  ('n[0]', 'M5', (25., 1814.208, 25.024, 1814.400))]
        q = SimpleNamespace(name='assigned_parent', w=777.6, h=1814.4,
                            obs_top=7, note='', ports={p: ('unused',) for p in ('e','w','s','n')},
                            order=['e','w','s','n'])
        # Real Master supplies a constructor compatible with the die writer.
        from qwen_rom_fulldie import Master
        q = Master(q.name, q.w, q.h, q.obs_top, q.note)
        q.ports = {p: ('unused',) for p in ('e','w','s','n')}
        q.order = list(q.ports)
        partition_master(q, {'er': ('e', [1,0]), 'wr': ('w',[0]),
                             'sr': ('s',[0]), 'nr': ('n',[0])}, source)
        emitted = die_pin_writer()(q, 1, {'er':2,'wr':1,'sr':1,'nr':1})
        expected = [('er[0]', source[1][1], source[1][2]),
                    ('er[1]', source[0][1], source[0][2]),
                    ('wr[0]', source[2][1], source[2][2]),
                    ('sr[0]', source[3][1], source[3][2]),
                    ('nr[0]', source[4][1], source[4][2])]
        self.assertEqual(emitted, expected)
        self.assertEqual(die_pin_writer()(q, 1, {'er':1,'wr':0,'sr':0,'nr':0}), expected[:1])

    def test_genuine_interior_clock_remains_distinct(self):
        from qwen_rom_fulldie import Master
        q = Master('parent', 100.,100.,7,'')
        q.ports = {'ck': ('xy',1,'M5',[(50.,50.)],1)}
        q.order = ['ck']
        self.assertEqual(die_pin_writer()(q,1,{}),
                         [('ck[0]','M5',(49.988,49.952,50.012,50.048))])


if __name__ == '__main__':
    unittest.main()
