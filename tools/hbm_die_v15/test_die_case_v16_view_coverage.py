import copy
import unittest
from die_case_v16 import validate_view_coverage


def fixture():
    instance = {'master': 'relay', 'ports': {'clk': {'bits': 1, 'direction': 'input'}}, 'params': {'N': 2}}
    instances = {'old': copy.deepcopy(instance), 'rly0000_s000_t0': copy.deepcopy(instance)}
    views = {'relay_n2': {'master': 'relay', 'representative': 'old', 'params': {'N': 2},
                          'instances': list(instances)}}
    return instances, views


class ViewCoverageTest(unittest.TestCase):
    def test_new_relay_instance_requires_current_view_plan(self):
        instances, views = fixture()
        views['relay_n2']['instances'].remove('rly0000_s000_t0')
        with self.assertRaisesRegex(ValueError, 'stale views.json: 1'):
            validate_view_coverage(instances, views)

    def test_missing_synth_receipt_stays_separate_from_membership(self):
        instances, views = fixture()
        # Membership is checked before optional SYNTH files: an unbuilt receipt
        # is separately recorded as an explicit diagnostic exclusion by main().
        validate_view_coverage(instances, views)

    def test_duplicate_membership_refused(self):
        instances, views = fixture()
        views['duplicate'] = copy.deepcopy(views['relay_n2'])
        with self.assertRaisesRegex(ValueError, 'duplicate view membership'):
            validate_view_coverage(instances, views)

    def test_same_width_wrong_direction_refused(self):
        instances, views = fixture()
        instances['rly0000_s000_t0']['ports']['clk']['direction'] = 'output'
        with self.assertRaisesRegex(ValueError, 'view ABI mismatch'):
            validate_view_coverage(instances, views)

    def test_different_master_refused(self):
        instances, views = fixture()
        instances['rly0000_s000_t0']['master'] = 'other_relay'
        with self.assertRaisesRegex(ValueError, 'view ABI mismatch'):
            validate_view_coverage(instances, views)

    def test_same_ports_different_parameters_refused(self):
        instances, views = fixture()
        instances['rly0000_s000_t0']['params']['N'] = 3
        with self.assertRaisesRegex(ValueError, 'view parameter mismatch'):
            validate_view_coverage(instances, views)

    def test_missing_representative_refused(self):
        instances, views = fixture()
        views['relay_n2']['representative'] = 'absent'
        with self.assertRaisesRegex(ValueError, 'view representative absent'):
            validate_view_coverage(instances, views)


if __name__ == '__main__':
    unittest.main()
