import unittest
import su_stage_coverage as S

def stages():
    return dict(PHW_required_by_stage=[10]*74+[1]*7,
        rank_dies=[dict(stage=s,rank=r,die_id=4*s+r) for s in range(81) for r in range(4)],
        provider_homes={str(l):2*l for l in range(40)})

class CoverageTests(unittest.TestCase):
    def test_all81_stages_and324_rank_dies_explicit_even_without_source_SU_home(self):
        r=S.export(stages(),[],[dict(node='L0.I1')])
        self.assertEqual(len(r['stage_rank_records']),324)
        self.assertEqual(r['unbound_stage_rank_records'],324)
        self.assertIsNone(r['stage_rank_records'][8]['actual_binding'])
        self.assertFalse(r['historical_59_programs_are_canonical_coverage'])
        with self.assertRaisesRegex(ValueError,'incomplete'):S.require_executable(r)
    def test_allocator89_requires_all356_rank_dies(self):
        st=stages();st['PHW_required_by_stage']=[10]*89
        st['rank_dies']=[dict(stage=s,rank=r,die_id=4*s+r) for s in range(89) for r in range(4)]
        r=S.export(st,[],[])
        self.assertEqual((r['physical_stages'],r['physical_rank_dies']),(89,356))
        self.assertEqual(r['unbound_stage_rank_records'],356)
        st['rank_dies'].pop()
        with self.assertRaisesRegex(ValueError,'complete allocator'):S.export(st,[],[])

    def test_providerhome_is_never_SUhome(self):
        with self.assertRaisesRegex(ValueError,'HE/CROM'):
            S.export(stages(),[],[],[dict(stage=0,rank=0,die_id=0,provider_home=0)])
    def test_fragment_source_stage_and_rank_extent_retained(self):
        f=dict(stage=80,layer='head',rank_slices=[dict(rows=[r*1280,(r+1)*1280]) for r in range(4)])
        r=S.export(stages(),[f],[])['stage_rank_records'][-1]
        self.assertEqual((r['stage'],r['rank'],r['field_rank_scalar_rows']),(80,3,1280))
        self.assertEqual(r['source_layers'],['head'])
    def test_no_fabricated_die_mapping(self):
        with self.assertRaisesRegex(ValueError,'canonical rank die'):
            S.export(stages(),[],[],[dict(stage=80,rank=3,die_id=3)])
    def test_even_populated_descriptors_do_not_qualify_missing_global_source_join(self):
        b=dict(stage=0,rank=0,die_id=0,**{k:'sourcebound' for k in S.REQUIRED})
        b.update(core_epoch=0,duration_edges=100,boundary_activity=[dict(edge=12)],native_kernel_bindings=['QN'])
        r=S.export(stages(),[],[],[b]);self.assertFalse(r['qualified'])
        self.assertFalse(r['source_SU_home_assignment_bound'])
        with self.assertRaises(ValueError):S.require_executable(r)

if __name__=='__main__':unittest.main()
