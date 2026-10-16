"""Exercise the actual allocator release prefix with a lifted-site ownership witness."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from relay_frame_ownership import FrameOwnership

HERE = Path(__file__).resolve().parent

def prefix(source):
    tree = ast.parse(source)
    outer = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_relays'), None)
    body = outer.body if outer else tree.body
    fn = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == 'repair')
    for k, node in enumerate(fn.body):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'D' for t in node.targets):
            fn.body = fn.body[:k] + [ast.Return(value=ast.Constant(value=None))]
            break
    return ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))

class RelayOwnershipTest(unittest.TestCase):
    def witness(self, fixed):
        frame = (10., 20., 8., 8.)
        rect = (10., 20., 18.25, 28.25)
        occupied = {rect: 'A'}
        owner = FrameOwnership(['A', 'B'])
        def unplace(frames):
            for x, y, w, h in frames:
                occupied.pop((x, y, x+w+.25, y+h+.25), None)
        owner.release('A', [frame], unplace)
        # B's successful repair takes A's lifted site before A gets its turn.
        occupied[rect] = 'B'
        owner.mark('B')
        ns = dict(hops_of=lambda pl: [100.], relay_frame=lambda bits, cl: (8., 8.),
                  v=SimpleNamespace(SHAVE=.25), sites=lambda *args: ([], object()),
                  tight_stride=set(), GATE=True, reservations=owner, unplace=unplace,
                  rm_rect=lambda r: occupied.pop(r, None))
        source = ((HERE.parent/'qwen_rom_fulldie_b3r2.py').read_text() if fixed else
                  (HERE/'testdata/repair_release_221a3e09.py').read_text())
        exec(compile(prefix(source), '<actual-repair-prefix>', 'exec'), ns)
        ns['repair']('A', dict(frames=[frame], bits=514, cl='tree', bid='tree_A'))
        return occupied, rect, owner

    def test_frozen_prefix_erases_foreign_reservation(self):
        occupied, rect, _ = self.witness(False)
        self.assertNotIn(rect, occupied)

    def test_corrected_actual_prefix_preserves_foreign_reservation(self):
        occupied, rect, owner = self.witness(True)
        self.assertEqual(occupied[rect], 'B')
        self.assertNotIn('A', owner.live)
        self.assertIn('B', owner.live)

    def test_owned_release_and_retry_are_not_stale(self):
        removed = []
        owner = FrameOwnership(['A'])
        self.assertTrue(owner.release('A', ['old'], removed.extend))
        self.assertFalse(owner.release('A', ['stale'], removed.extend))
        owner.mark('A')
        self.assertTrue(owner.release('A', ['new'], removed.extend))
        self.assertEqual(removed, ['old', 'new'])

    def test_actual_rip_up_settle_tracks_only_surviving_owned_frames(self):
        tree = ast.parse((HERE.parent/'qwen_rom_fulldie_b3r2.py').read_text())
        outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_relays')
        funcs = [n for n in outer.body if isinstance(n, ast.FunctionDef) and n.name in ('_lift', '_settle')]
        frames = [(10., 20., 8., 8.), (30., 20., 8., 8.)]
        def rect(f):
            x, y, w, h = f
            return x, y, x+w+.25, y+h+.25
        occupied = set(map(rect, frames))
        owner = FrameOwnership(['A'])
        plans = dict(A=dict(bid='tree_A', frames=list(frames)))
        def unplace(fs):
            for f in fs:
                occupied.discard(rect(f))
        def free(r):
            return not any(q[0] < r[2] and r[0] < q[2] and q[1] < r[3] and r[1] < q[3] for q in occupied)
        ns = dict(plans=plans, reservations=owner, unplace=unplace, free=free,
                  add_rect=occupied.add, v=SimpleNamespace(SHAVE=.25))
        exec(compile(ast.fix_missing_locations(ast.Module(body=funcs, type_ignores=[])), '<actual-lift-settle>', 'exec'), ns)
        old = ns['_lift']('A')
        self.assertNotIn('A', owner.live)
        occupied.add(rect(frames[0]))  # repaired B now owns the first old site
        self.assertFalse(ns['_settle']('A', old))
        self.assertEqual(plans['A']['frames'], frames[1:])
        self.assertIn('A', owner.live)
        owner.release('A', plans['A']['frames'], unplace)
        self.assertEqual(occupied, {rect(frames[0])})

    def test_actual_rip_up_refuses_unowned_stale_candidates(self):
        tree = ast.parse((HERE.parent/'qwen_rom_fulldie_b3r2.py').read_text())
        outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_relays')
        fn = next(n for n in outer.body if isinstance(n, ast.FunctionDef) and n.name == '_lift')
        removed = []
        ns = dict(plans=dict(A=dict(bid='tree_A', frames=['stale'])),
                  reservations=FrameOwnership(), unplace=removed.extend)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<actual-lift>', 'exec'), ns)
        with self.assertRaisesRegex(ValueError, 'no live reservation'):
            ns['_lift']('A')
        self.assertEqual(removed, [])

    def test_failed_release_callback_does_not_drop_ownership(self):
        owner = FrameOwnership(['A'])
        def fail(frames):
            raise ValueError('removal failed')
        with self.assertRaises(ValueError):
            owner.release('A', ['old'], fail)
        self.assertIn('A', owner.live)

if __name__ == '__main__':
    unittest.main()
