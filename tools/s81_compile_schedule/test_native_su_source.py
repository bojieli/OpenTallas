"""Exact source-interface transformations; not functional or physical sign-off."""
import copy
from pathlib import Path
import tempfile
import unittest
import native_su_source as N

class NativeSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=N.git_source(N.HIER+N.OLD+'.sv')
        cls.program=N.git_source(N.HIER+N.OLD_PROGRAM+'.sv')
    def test_actual_source_body_is_identical_after_reversing_clock_interface_changes(self):
        output=N.transform(self.source,N.PATCHES);N.verify_identity(self.source,output,N.PATCHES)
        self.assertIn('u_sw576(.ck(sw_ck)',output)
        self.assertIn('u_moe(.ck(moe_ck)',output)
        self.assertNotIn('.ck({152{sk}})',output)
    def test_programmed_source_preserves_real_calendar_and_native_core(self):
        output=N.transform(self.program,N.PROGRAM_PATCHES);N.verify_identity(self.program,output,N.PROGRAM_PATCHES)
        self.assertIn('ot_s81_su_calendar_store',output)
        self.assertIn('.sw_ck(sw_ck),.moe_ck(moe_ck)',output)
    def test_aliasing_sw_clocks_back_to_residual_parent_is_rejected(self):
        output=N.transform(self.source,N.PATCHES).replace('u_sw576(.ck(sw_ck)','u_sw576(.ck({152{sk}})')
        with self.assertRaises(ValueError):N.verify_identity(self.source,output,N.PATCHES)
    def test_unrelated_data_change_cannot_hide_in_clock_refactor(self):
        output=N.transform(self.source,N.PATCHES).replace('sw576_a[14*s+:14]','sw576_a[14*s+:14]^14\'d1',1)
        with self.assertRaisesRegex(ValueError,'outside clock interface'):N.verify_identity(self.source,output,N.PATCHES)
    def test_lost_moe_clock_binding_in_programmed_wrapper_is_rejected(self):
        output=N.transform(self.program,N.PROGRAM_PATCHES).replace('.moe_ck(moe_ck)','')
        with self.assertRaises(ValueError):N.verify_identity(self.program,output,N.PROGRAM_PATCHES)
    def test_group_requirements_do_not_treat_hc_as_su_opcode(self):
        d=dict(nodes=[dict(id='x',kind='instruction',template_word_sha256='sha',instruction=dict(unit=2,_tag='L0.hc_attn',_reads=['SSX'],_writes=['RF']))])
        c=dict(source_operation_homes=[dict(node='x',rank=0,unit=2,stage=5,template_sha256='sha',physical_instance=None)],source_private_SU_colocation_groups=[])
        r=N.requirements(d,c)[0]
        self.assertEqual(r['required_native_SU_kinds'],[])
        self.assertIn('HC/HCP/HCT_SOURCE_LOWERING_REQUIRED',r['other_native_requirements'])
    def test_stale_candidate_cannot_create_native_source_requirements(self):
        d=dict(nodes=[dict(id='x',kind='instruction',template_word_sha256='sha',instruction=dict(unit=2,_reads=[],_writes=[]))])
        c=dict(source_operation_homes=[dict(node='x',rank=0,unit=2,stage=5,template_sha256='stale',physical_instance=None)],source_private_SU_colocation_groups=[])
        with self.assertRaisesRegex(ValueError,'stale'):N.requirements(d,c)
if __name__=='__main__':unittest.main()
