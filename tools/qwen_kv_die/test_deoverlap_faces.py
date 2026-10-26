import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qwen_rom_fulldie as F  # noqa: E402
from qwen_kv_die import tp8b_v5 as T  # noqa: E402


def overlaps(m):
    rs = sorted((r, nm.rsplit('[', 1)[0], l) for nm, l, r in F.pin_rects(m, 1, {p: sp[1] for p, sp in m.ports.items()}))
    bad = set()
    for i, ((x0, y0, x1, y1), p, l) in enumerate(rs):
        for (u0, v0, u1, v1), q, l2 in rs[i + 1:]:
            if u0 >= x1:
                break
            if l == l2 and p != q and v0 < y1 and y0 < v1:
                bad.add(tuple(sorted((p, q))))
    return bad


class Deoverlap(unittest.TestCase):
    def vm(self, h=400.0):
        m = F.Master('qfd_sp_vector_memory_par', 300.0, h, 7, 'test')
        m.face('ar', 520, 'E', 'M4', 200.0, 1)              # widened word, placed first
        m.face('write_commit_mask', 624, 'E', 'M4', 215.0, 1)  # packed against the narrow ar -> overlaps
        m.face('q', 524, 'E', 'M4', 290.0, 1)
        return m

    def test_moves_only_the_overlapping_group(self):
        m = self.vm()
        self.assertEqual(overlaps(m), {('ar', 'write_commit_mask')})
        before = {p: sp for p, sp in m.ports.items()}
        moved = T._deoverlap_faces(m, F.pin_rects)
        self.assertEqual(moved, ['ar'])                   # the smaller movable group of the pair moves (to free span)
        self.assertEqual(overlaps(m), set())
        self.assertEqual(m.ports['q'], before['q'])
        self.assertEqual(m.ports['write_commit_mask'], before['write_commit_mask'])

    def test_no_free_span_fails_closed(self):
        m = self.vm(h=62.0)
        with self.assertRaises(ValueError):
            T._deoverlap_faces(m, F.pin_rects)


if __name__ == '__main__':
    unittest.main()
