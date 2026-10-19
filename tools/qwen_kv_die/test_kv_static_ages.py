import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static as K
import kv_static_ages as A
import static_qk_calendar as Q

SRC = json.loads((A.ROOT / A.SOURCE).read_text())


class Ages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ages = A.derive(SRC)

    def test_every_template_parameter_priced(self):
        g, gaps = K.template()
        self.assertTrue(gaps['unpriced_parameters'])
        self.assertEqual(A.apply(g, self.ages), [])
        for i in g['instances']:
            if i['role'] == 'k_issuer':
                a = next(j for j in g['instances'] if j['name'] == i['name'].replace('ki_', 'ectl_a_'))
                self.assertEqual(a['parameters']['ROW_RETURN_LAT'], i['parameters']['RESPONSE_LAT'] + 7)

    def test_issuer_latency_is_landing_plus_relays(self):
        for st in A.STACKS:
            for gr in range(8):
                q = A.stages(SRC, f'krq_{st}_{gr}')[0]
                s = A.stages(SRC, f'krs_{st}_{gr}')[0]
                ki = self.ages['k_issuer'][f'ki_{st}_{gr}']
                self.assertEqual(ki['natural_response_lat'], 8 + q + s)
                # KV-ECTL4: every frame padded (request chain) to the one K round trip of the hardened ECTL children
                self.assertEqual(ki['RESPONSE_LAT'], A.K_RT_BUDGET)
                self.assertEqual(ki['request_pad'], A.K_RT_BUDGET - (8 + q + s))
                self.assertGreaterEqual(ki['request_pad'], 0)

    def test_qk_issue_age_is_minimal_for_the_slowest_group(self):
        age = self.ages['qk']['QK_ISSUE_AGE']
        worst = self.ages['qk']['response_lat_range'][1]
        for T in (1, 1000, 4097, 8192):
            for r in {v['RESPONSE_LAT'] for v in self.ages['k_issuer'].values()}:
                Q.compile_issuer_calendar(T, r, age)
        with self.assertRaises(ValueError):
            Q.compile_issuer_calendar(8192, worst, age - 1)

    def test_vport_rl_matches_plan_pair_age(self):
        # KV-INT 10-17 (KVJ-F measured RT 9, coordinator KVJ-E2 decision): RL = 4 + W 82 + DQ 0 + RT 9 = 95, pair age 96;
        # the kvs13l4 plan source still records the old pair age 95 (OT_KV_PV_AGE=95), so the next die runs OT_KV_PV_AGE=96
        self.assertEqual({v['RL'] for v in self.ages['vport'].values()}, {95})
        self.assertEqual(self.ages['pv']['FIRST_INPUT_AGE'], 96)

    def test_phase_profile_is_legal_for_the_rtl(self):
        p = self.ages['phase_launch']
        self.assertTrue(0 <= p['PH0'] < 768 and 0 < p['SAFE_LOW_U'] <= p['SAFE_HIGH_U'] < 768 and 6 <= p['META_HOLD_CORE'] <= 255)


if __name__ == '__main__':
    unittest.main()
