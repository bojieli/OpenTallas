"""Source-input validation only: synthetic contracts never produce RTL words."""
import unittest
import head_native_contract as H


def fixture(user=0):
    c=H.template(); c.update(rank=0,user=user,test_only=True)
    c['authorities']={k:'SYNTHETIC_INPUT_TEST_ONLY' for k in H.AUTHORITIES}
    c['scalar'].update(k=12,eps_fp32_hex='358637bd')
    for s in c['slices']:
        s.update(x_base=user*4096,rx_base=user*4096+400,gain_base=user*2048,
                 ssq_pidx=user*128,apply_pidx=user*128+1,
                 x_ready_edge=1,gain_committed_edge=1,prog_committed_edge=1,
                 root_config_effective_edge=2,ssq_issue_edge=10,
                 psum_root_arrival_edges=[20+b for b in s['blocks']],
                 rstd_w1_edge=60,rstd_vm_visible_edge=64,
                 apply_issue_edge=65,apply_first_operand_edge=70,
                 protected_vm_ranges=[],protected_crom_ranges=[],protected_prog_indices=[])
    return c


class ContractTest(unittest.TestCase):
    def test_no_missing_contract_becomes_defaults(self):
        errors=H.validate(H.template())
        for name in H.MAPS+H.DATES:
            self.assertIn('slice0.'+name, errors)
        self.assertIn('authorities.native_arithmetic_gate',errors)

    def test_each_user_requires_its_actual_bank(self):
        for user in range(4):
            c=fixture(user); self.assertEqual(H.validate(c),[])
            if user:
                c['slices'][0]['rx_base']=400
                self.assertTrue(any('RX crosses user bank' in e for e in H.validate(c)))

    def test_missing_dates_wrong_ownership_and_live_overwrite_rejected(self):
        mutations=[lambda s:s.update(apply_first_operand_edge=None),
                   lambda s:s.update(blocks=[0,1,2]),
                   lambda s:s.update(protected_crom_ranges=[[0,384]]),
                   lambda s:s.update(protected_prog_indices=[1]),
                   lambda s:s.update(rstd_vm_visible_edge=70)]
        for mutate in mutations:
            c=fixture(); mutate(c['slices'][0]); self.assertTrue(H.validate(c))

    def test_missing_or_duplicate_slices_rejected(self):
        for slices in (None,[],[{}]*12):
            c=fixture(); c['slices']=slices; self.assertTrue(H.validate(c))

if __name__=='__main__': unittest.main()
