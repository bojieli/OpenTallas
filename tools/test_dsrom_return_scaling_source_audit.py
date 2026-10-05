import hashlib
import json
import subprocess
import unittest
import dsrom_return_scaling_source_audit as M


class ScalingAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=M.generate()

    def test_full_declaration_exact(self):
        t=M.declaration(8192)
        self.assertEqual((t['return_nodes'],t['declared_lower_bits']),(16256,138469120))
        self.assertEqual(t['node_queue_bits']+t['node_RST_bits']+t['fixed_root_bits'],t['declared_lower_bits'])
        self.assertAlmostEqual(t['conservative_FF_50pct_mm2'],104.9817480192)

    def test_scaling_is_affine_not_fixed_workload_or_pure_ratio(self):
        a,b=M.declaration(8192),M.declaration(4096)
        self.assertEqual(b['declared_lower_bits'],69771008)
        self.assertEqual(a['declared_lower_bits']-b['declared_lower_bits'],2*(8192-4096)*8386)
        self.assertNotEqual(b['declared_lower_bits'],a['declared_lower_bits']//2)
        self.assertEqual(a['fixed_root_bits'],b['fixed_root_bits'])

    def test_active_mask_does_not_resize_forest(self):
        x=self.m['active_pair_mask']
        self.assertEqual((x['compiled_NP'],x['active_workload_pairs'],x['declared_lower_bits']),(8192,6899,138469120))
        self.assertEqual(x['current_BF_site_image_hardware_mismatch'],781)

    def test_illegal_unpadded_compiled_shapes_refused(self):
        for n in (2966,4773,512,0):
            with self.assertRaises(ValueError):M.declaration(n)
        with self.assertRaises(ValueError):M.declaration(8192,r=0)
        with self.assertRaises(ValueError):M.declaration(8192,rd=63)

    def test_ports_and_root_contexts_not_discarded(self):
        for c in self.m['preexisting_partition_parameter_cases_not_new_sweep']:
            self.assertEqual((c['R'],c['NBF'],c['root_public_port_count'],c['root_public_bits_per_cycle']),(128,1024,128,8832))
            self.assertEqual(c['fixed_root_bits'],2146304)
            self.assertFalse(c['source_array_discount_admitted'])
            self.assertFalse(c['physical_or_calendar_qualified'])

    def test_lifetime_and_port_credits_remain_zero(self):
        x=self.m['lifetimes_and_ports']
        self.assertEqual((x['port_credit'],x['occupancy_area_credit'],x['embedded_slot_area_credit']),(0,0,0))
        self.assertIsNone(x['actual_current_L0_L20_peak_live_bytes'])
        self.assertEqual(x['VM_edge_contract']['edges_from_root_publish'],dict(spine_write_register=1,VM_write_NBA=2,earliest_synchronous_reader_sees_new=3))

    def test_all_inputs_bound_to_committed_source(self):
        for key,h in self.m['source_pins'].items():
            commit,path=key.split(':',1)
            raw=subprocess.check_output(['git','show',commit+':'+path],cwd=M.ROOT)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),h)

    def test_exact_regeneration_and_no_execution_admission(self):
        encoded=json.dumps(self.m,indent=2,sort_keys=True)+'\n'
        self.assertEqual((M.OUT/'model.json').read_text(),encoded)
        d=self.m['decision']
        self.assertEqual(d['current_reservation_bits'],138469120)
        self.assertFalse(d['compiled_NP_resize_admitted']);self.assertFalse(d['reticle_fit']);self.assertFalse(d['fulltoken'])
        self.assertTrue(d['no_new_RTL']);self.assertTrue(d['no_PNR']);self.assertTrue(d['no_jobs'])


if __name__=='__main__':unittest.main()
