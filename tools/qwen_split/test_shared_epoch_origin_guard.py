import copy, unittest
from shared_epoch_origin_guard import evaluate

def fixture():
    return dict(enabled=False,mode='static_existing_events',upstream_clock_reset_correlated=True,origin_receipt_sha256='a'*64,
      period_ps=833.333,global_source_to_consumer_edges=3,source_to_native_input_edges=0,native_output_to_consumer_edges=0,
      cal_start_face_global_edge=100,face_to_cal_start_pin_edges=2,calendar_input_pr_edges=1,calendar_output_pr_edges=1,
      first_event_dt=10,last_cfg_core_global_edge=101,context_pin_global_edge=110,context_to_first_slot_edges=1,
      shared_epoch_global_edge=0,compiled_boot_edges=117,source_stores_ready_global_edge=90,native_kind='flop',
      cases={v:dict(G_raw=0,R0_raw=0,source_origin_global_edge=0,receiver_origin_global_edge=0,phi_pin_ps=0.)for v in ['tt','ff']})

class OriginTests(unittest.TestCase):
    def test_existing_events_all_edges_priced(self):
        r=evaluate(fixture());self.assertEqual(r['status'],'MODEL_CONSISTENT_NOT_NATIVE_SIGNOFF');self.assertFalse(r['qualified'])
        self.assertEqual(r['first_source_global_edge'],114);self.assertEqual(r['first_consumer_global_edge'],117)
    def test_global_price_derives_local_L_not_corner_choices(self):
        c=fixture();c['cases']['ff'].update(source_origin_global_edge=1,G_raw=-1,phi_pin_ps=-833.333)
        r=evaluate(c);self.assertNotIn('NO_COMMON_IMMUTABLE_K',r['blockers']);self.assertEqual(r['cases']['ff']['L_derived'],4)
        self.assertAlmostEqual(r['cases']['tt']['age_ps'],r['cases']['ff']['age_ps'])
    def test_lab_clock_start_is_not_receipt(self):
        c=fixture();c['upstream_clock_reset_correlated']=False;c['origin_receipt_sha256']=None
        r=evaluate(c);self.assertIn('UPSTREAM_CLOCK_RESET_CORRELATION_MISSING',r['blockers'])
    def test_recent_configuration_fails_without_waiting(self):
        c=fixture();c['last_cfg_core_global_edge']=102
        self.assertIn('CFG_RECENT_AT_START',evaluate(c)['blockers'])
    def test_late_context_and_unpriced_boot_reject(self):
        c=fixture();c['context_pin_global_edge']=117;c['compiled_boot_edges']=116
        b=evaluate(c)['blockers'];self.assertIn('CONSUMER_CONTEXT_NOT_INSTALLED_BEFORE_FIRST_USE',b);self.assertIn('BOOT_WARM_FIRST_USE_UNPRICED',b)
    def test_real_lab_corner_K_counterexample_remains_blocked(self):
        c=fixture();c['cases']['tt'].update(G_raw=487,R0_raw=2053);c['cases']['ff'].update(G_raw=492,R0_raw=2059)
        self.assertIn('NO_COMMON_IMMUTABLE_K',evaluate(c)['blockers'])
    def test_missing_production_value_never_defaults(self):
        c=fixture();c['first_event_dt']=None
        self.assertIn('MISSING_NUMERIC:first_event_dt',evaluate(c)['blockers'])
    def test_first_valid_before_native_warm_refused(self):
        c=fixture();c['cases']['tt']['R0_raw']=200
        self.assertIn('FIRST_READ_BEFORE_WARM:tt',evaluate(c)['blockers'])
if __name__=='__main__':unittest.main()
