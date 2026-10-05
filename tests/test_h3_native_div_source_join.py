from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h3_native_div_source_join as J


def command():
    return {'opcode':'DIV','a':7,'b':6,'dst':6,'src_lane':0,'dst_lane':0,
      'denominator':'45a00000','input_version':'tree.completed','destination_version':'mean.rounded',
      'tree_complete':True,'previous_retired':True}


class Join(unittest.TestCase):
    def test_command_oracle_constant_version_and_aperture(self):
        self.assertTrue(J.validate_command(command()))
        for k,v in [('opcode','RECIP'),('denominator','45800000'),('a',512),('b',7),
          ('src_lane',False),('dst_lane',2),('tree_complete',False),('previous_retired',False),
          ('input_version',''),('dst',True)]:
            c=command();c[k]=v
            with self.subTest(k=k):
                with self.assertRaises(ValueError):J.validate_command(c)
        c=command();c['extra']=0
        with self.assertRaises(ValueError):J.validate_command(c)

    def test_exact_destination_RMW_all127_other_lanes_preserved(self):
        d=[(i*0x01020305)&0xffffffff for i in range(128)]
        q=J.merge_result(d,0x394ccccd)
        self.assertEqual(q[0],0x394ccccd)
        self.assertEqual(q[1:],d[1:])
        self.assertNotEqual(q,d)
        self.assertEqual(d[0],0)
        with self.assertRaises(ValueError):J.merge_result(d[:-1],0)

    def test_success_waits_write_ACK_and_same_version(self):
        l=J.Lease();c=command();l.accept(c)
        with self.assertRaises(ValueError):l.accept(c)
        l.read_consumed();l.result(False)
        with self.assertRaises(ValueError):l.retire('mean.rounded')
        l.write_ack()
        with self.assertRaises(ValueError):l.retire('wrong.version')
        self.assertTrue(l.retire('mean.rounded'))
        self.assertEqual(l.state,'idle')
        with self.assertRaises(ValueError):l.retire('mean.rounded')

    def test_fault_cannot_publish_successful_ACK(self):
        l=J.Lease();l.accept(command());l.read_consumed();l.result(True)
        with self.assertRaises(ValueError):l.write_ack()
        self.assertFalse(l.retire('mean.rounded'))

    def test_reset_flushes_inflight_no_stale_retirement(self):
        for stage in ['read','execute','write','retire']:
            l=J.Lease();l.accept(command())
            if stage!='read':l.read_consumed()
            if stage in ['write','retire']:l.result(False)
            if stage=='retire':l.write_ack()
            l.reset()
            with self.subTest(stage=stage):
                with self.assertRaises(ValueError):l.retire('mean.rounded')
                l.accept(command())
                self.assertEqual(l.state,'read')

    def test_explicit_stalls_add_edges_never_become_zero(self):
        self.assertEqual(J.compose_service(),37)
        self.assertEqual(J.compose_service(3,5,7),52)
        for v in [None,-1,True,0.5]:
            with self.assertRaises(ValueError):J.compose_service(v)

    def test_source_state_and_ports_no_extra_vector_register(self):
        m=J.model()
        self.assertEqual(m['source_join']['new_vector_register_bits'],0)
        self.assertEqual(m['source_join']['existing_result_register_bits_reused'],4096)
        self.assertEqual(m['source_join']['total_incremental_declared_register_bits'],2635)
        self.assertEqual(m['ports']['new_RF_ports'],0)
        self.assertEqual(m['ports']['physical_mirrored_write_B_per_success'],1024)
        self.assertEqual(m['latency']['earliest_reaccept_edge_after_accept'],38)

    def test_priced_delta_and_negative_existing_slot_control(self):
        m=J.model();c=m['cost']
        self.assertAlmostEqual(c['total_incremental_cell_um2'],2954.2616)
        self.assertAlmostEqual(sum(c['incremental_cell_um2_ledger'].values()),c['total_incremental_cell_um2'])
        for b in c['models'].values():
            self.assertFalse(b['existing_expanded_slot_fit'])
            self.assertTrue(b['inside_source_proposed_outline'])
            self.assertGreater(b['added_height_um'],0)
            self.assertFalse(b['physical_admission'])
            self.assertIsNone(b['NS8_current_source_binding'])

    def test_model_explicitly_holds_RTL_clock_and_fullkernel_gate(self):
        m=J.model()
        self.assertFalse(m['RTL_prepared'])
        self.assertEqual(m['RTL_builds'],0)
        self.assertIsNone(m['latency']['whole_kernel_total_ns'])
        self.assertIsNone(m['latency']['finite_service_upper_bound_without_parent_ready_bounds'])
        self.assertFalse(m['clock']['source_depth_is_timing_qualification'])
        self.assertFalse(m['default_enabled'])


if __name__=='__main__':unittest.main()
