import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import compute_spine as S
import qwen_rom_fulldie_b3r2 as B


class SplitSuVmSeam(unittest.TestCase):
    def test_trimmed_and_previous_vm_envelopes_meet_the_existing_seam_contract(self):
        original = S.VM_WH
        try:
            for outline in [(4708.8, 2203.2), (4838.4, 2546.64)]:
                S.VM_WH = outline
                slots = {}
                def put(name, x, y, wh):
                    i = SimpleNamespace(name=name, x=math.floor(x / 2.16) * 2.16,
                        y=math.floor(y / 2.16) * 2.16, w=wh[0] - .024, h=wh[1] - .024,
                        orient='R0', domain='serial_0p9')
                    slots[name] = i
                    return i
                su, vm = S._place_su_vm(put, 16137.36, 20856.96)
                m = dict(insts=[su, vm], buses=[])
                v = SimpleNamespace(SU_VM_NORTH=True, masters=lambda *args: {})
                B._su_vm_bus(v, m, B.SU_VM_A_BITS_BV, B.SU_VM_Q_BITS)
                self.assertEqual(m['r21v_su_vm']['rtl_latency_added'], 0)
                self.assertEqual(m['r21v_su_vm']['stations'], 0)
                self.assertAlmostEqual(m['r21v_su_vm']['gap_um'], .024)
                self.assertGreater(m['r21v_su_vm']['vm_face_offset_um'], 0)
        finally:
            S.VM_WH = original

    def test_recorded_c2_channel_gap_is_still_refused(self):
        su = SimpleNamespace(name='sp_su64_sfu',x=13696.992,y=20856.960,w=3239.976,h=3671.976,
                             orient='R0',domain='serial_0p9')
        vm = SimpleNamespace(name='sp_vector_memory',x=13782.960,y=18567.360,w=4708.776,h=2203.176,
                             orient='R0',domain='serial_0p9')
        v = SimpleNamespace(SU_VM_NORTH=True)
        with self.assertRaisesRegex(ValueError, 'do not abut'):
            B._su_vm_bus(v, dict(insts=[su,vm],buses=[]), B.SU_VM_A_BITS_BV, B.SU_VM_Q_BITS)


if __name__ == '__main__':
    unittest.main()
