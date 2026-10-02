import unittest,numpy as np
from h4_c0_group_operand_tiles import GroupOperandTiles,NATIVE

class GroupTileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=GroupOperandTiles()
    def test_all40_source_bindings_and64_distinct_tiles(self):
        p=self.plan
        for pc in p.parents:
            tiles=[p.tile(pc,0,g,f) for g in range(8) for f in range(0,1024,128)]
            self.assertEqual(len({t['C0_tile_template_id'] for t in tiles}),64)
            self.assertEqual({t['SM'] for t in tiles},set(range(32)))
            self.assertTrue(all(t['native_sha256']==NATIVE for t in tiles))
            self.assertEqual([t['output_flat_word_first'] for t in tiles],list(range(0,8192,128)))
    def test_contributor_rank_and_LOAD_layout_not_reassociated(self):
        pc=next(iter(self.plan.parents));t=self.plan.tile(pc,95,7,896)
        self.assertEqual([s['source_rank'] for s in t['source_spans']],list(range(56,64)))
        self.assertEqual([s['LOAD_flat_word_first'] for s in t['source_spans']],[(j*8+7)*1024+896 for j in range(8)])
        self.assertEqual(t['SM'],31)
    def test_native_tree_and_BF16_round_control_bits(self):
        pc=next(iter(self.plan.parents));rng=np.random.default_rng(14);a=rng.standard_normal((8,128)).astype(np.float32)
        # Adversarial cancellation catches contributor reassociation.
        a[:,0]=[1e20,1,-1e20,1,1,1,1,1]
        expected=((a[0]+a[1])+(a[2]+a[3]))+((a[4]+a[5])+(a[6]+a[7]))
        u=expected.view(np.uint32);expected_bits=(u+np.uint32(32767)+((u>>16)&np.uint32(1)))&np.uint32(0xffff0000)
        observed=self.plan.run_control(pc,0,0,a)
        np.testing.assert_array_equal(observed.view(np.uint32),expected_bits)
    def test_bounded_scratch_and_positive_service_no_latency_claim(self):
        r=self.plan.report();self.assertLess(r['planned_data_scratch_peak_bytes'],65536)
        self.assertEqual(r['planned_shared64_beats_per_call'],64*(64+64+8+8))
        self.assertFalse(r['hardware_admitted']);self.assertIsNone(r['whole_service_latency']);self.assertEqual(r['unknown_calls_retained'],193316)
        self.assertLessEqual(r['ordered_last_use_RF_vectors'],32)
    def test_unbounded_or_old_tile_rejected(self):
        pc=next(iter(self.plan.parents))
        for args in ((pc,0,8,0),(pc,0,0,1),(pc,96,0,0),(-1,0,0,0)):
            with self.assertRaises(ValueError):self.plan.tile(*args)
    def test_all64_tile_bits_match_source_group_flatten(self):
        pc=next(iter(self.plan.parents));a=np.random.default_rng(2).standard_normal((8,8,1024)).astype(np.float32)
        expected=((a[0]+a[1])+(a[2]+a[3]))+((a[4]+a[5])+(a[6]+a[7]))
        u=expected.view(np.uint32);bits=(u+np.uint32(32767)+((u>>16)&np.uint32(1)))&np.uint32(0xffff0000)
        out=np.empty(8192,np.uint32)
        for group in range(8):
            for first in range(0,1024,128):
                value=self.plan.run_control(pc,group,first,a[:,group,first:first+128])
                out[group*1024+first:group*1024+first+128]=value.view(np.uint32)
        np.testing.assert_array_equal(out,bits.reshape(-1))

if __name__=='__main__':unittest.main()
