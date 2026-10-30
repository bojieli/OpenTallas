import copy
from types import SimpleNamespace as N
import unittest
from vm_dma_budget import transfer


class BoundaryBandwidth(unittest.TestCase):
    def record(self, op):
        def desc(space, base):
            return N(space=space, base=base, fmt='U32', m=1, n=8, ibcast=False,
                     istride=0, indexed=False, n_sel=0, dyn_mul=0, lstride=0, l1stride=0)
        h, v = desc('HBM', 0x1f00000000), desc('VM', 8)
        return N(unit='DMA', op=op, param=0, wait=65535,
                 desc=dict(A=h if op == 'LOAD' else v, O=v if op == 'LOAD' else h))

    def test_small_sector_and_64byte_store_service(self):
        store = self.record('STORE')
        store.desc['A'].n = store.desc['O'].n = 24
        self.assertEqual(transfer(store, 'store')['optimistic_source_cycles'], 2)
        load = self.record('LOAD')
        self.assertEqual((transfer(load, 'load')['optimistic_source_cycles'],
                          transfer(load, 'load')['stack']), (1, 3))

    def test_wait_removal_and_quadrant_group_are_not_serial_budget(self):
        for field, value in [('wait', 0), ('param', 1)]:
            r = self.record('LOAD')
            setattr(r, field, value)
            with self.assertRaisesRegex(ValueError, 'full-wait'):
                transfer(r, 'load')

    def test_stride_format_and_partial_sector_refused(self):
        for field, value in [('istride', 2), ('fmt', 'BF16'), ('n', 7)]:
            r = self.record('STORE')
            setattr(r.desc['A'], field, value)
            with self.assertRaises(ValueError):
                transfer(r, 'store')
        r = self.record('LOAD')
        r.desc['A'].base += 4
        with self.assertRaisesRegex(ValueError, 'whole-sector'):
            transfer(r, 'load')

    def test_body_records_are_not_added_traffic(self):
        self.assertIsNone(transfer(self.record('LOAD'), 'body'))


if __name__ == '__main__':
    unittest.main()
