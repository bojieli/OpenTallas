"""Tiny real SM model captures must leave downstream STREAM input intact."""
import unittest

import numpy as np

from hbm_layer_vehicle.qwen_sm_mv_kv import capture_sm
from hgi_sim import lib, machine as MC
from hgi_sim.records import MDesc, Rec


class CaptureTest(unittest.TestCase):
    def _run(self, space):
        weights = np.tile(np.array([-2, 1, 3, -1], np.int8), (2, 128))
        weights[1] *= -1
        activation = np.full(512, 0.5, np.float32)
        hbm = MC.Hbm()
        hbm.add(32, weights)
        die = MC.Die(5, hbm)
        die.vm[:512] = activation.view(np.uint32)
        output = MDesc(space=space, fmt='FP32', base=0 if space == 'STREAM' else 2048, n=2)
        record = Rec('SM', 'MATVEC', param=3, tag='head', desc={
            'A': MDesc(space='VM', fmt='FP32', base=0, n=512),
            'B': MDesc(space='HBM', fmt='INT8', base=32, n=512, m=2, stride=512), 'O': output})
        machine = MC.Machine([die])
        machine.cur = record
        prefix = np.array([7.0], np.float32)
        if space == 'STREAM':
            die.streams[0] = prefix.copy()
        arrays, rows = {}, []
        capture_sm(MC.u_sm_matvec, {5}, arrays, rows)(machine, record, 0)
        expected = np.asarray(lib.sm_int8(weights, activation), np.float32)
        self.assertTrue(np.any(expected != 0))
        captured = arrays['d5.L0.head.O']
        np.testing.assert_array_equal(captured.view(np.uint32), expected.view(np.uint32))
        self.assertEqual(rows[0]['rank'], 5)
        if space == 'STREAM':
            # Capture observes only the new producer vector, never consumes any
            # previously queued or newly produced consumer input.
            np.testing.assert_array_equal(die.streams[0], np.concatenate([prefix, expected]))
            self.assertFalse(np.shares_memory(captured, die.stream_seen[0]))
            machine.cur = Rec('SU', 'VOP')
            np.testing.assert_array_equal(machine.stream_pop(output, die, 3), np.concatenate([prefix, expected]))
            self.assertEqual(die.streams[0].size, 0)
        else:
            np.testing.assert_array_equal(machine.read(output, die, 0), expected)

    def test_head_stream_capture_preserves_consumer_fifo(self):
        self._run('STREAM')

    def test_layer_vm_capture_keeps_existing_contract(self):
        self._run('VM')


if __name__ == '__main__':
    unittest.main()
