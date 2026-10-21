"""INERT proposal for ROOT review; no production flow imports this module.

Admission only. Adoption still requires independent golden/throughput PASS,
native TT<=220/190 and no combinational boundary, actual FF launch>=25,
FF hold plus neighbour obligations D1-D4, SS/FF/DRC and measured child clocks.
Existing physical hierarchy/PG level is never relabelled.
"""
import copy
import unittest

def qualify(spec):
    if spec.get('kind') != 'cluster' or spec.get('cluster_level',1) != 1:
        return False
    if spec.get('registered_boundary_contract') != 'all-data-pins':
        return False
    pr=spec.get('pin_regs') or {}
    if pr.get('exclude') or not(pr.get('enable') or str(pr.get('reason','')).strip()):
        return False
    if spec.get('inhold') or spec.get('outhold'):
        return False
    if spec.get('child_clock_ref') != 'boundary' or not spec.get('children'):
        return False
    clocks=spec.get('clock_ports') or [spec.get('clock_port')]
    if len(clocks)!=1 or not clocks[0] or spec.get('clock_entry_domains'):
        return False
    return True

class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.good=dict(kind='cluster',cluster_level=1,registered_boundary_contract='all-data-pins',
          pin_regs=dict(enable=False,reason='explicit coherent RTL input/output registers'),
          inhold=False,outhold=False,child_clock_ref='boundary',clock_port='clk',children=[dict(view='actual-closed-view')])
    def changed(self,**kw):
        q=copy.deepcopy(self.good);q.update(kw);return qualify(q)
    def test_explicit_registered_level1_admits_candidate_only(self):self.assertTrue(qualify(self.good))
    def test_wires_only_parent_is_not_admitted(self):self.assertFalse(self.changed(registered_boundary_contract=None))
    def test_pin_exclusion_is_not_admitted(self):self.assertFalse(self.changed(pin_regs=dict(enable=True,exclude='cfg.*',reason='excluded')))
    def test_no_register_basis_is_not_admitted(self):self.assertFalse(self.changed(pin_regs=dict(enable=False)))
    def test_hold_pads_are_not_admitted(self):
        self.assertFalse(self.changed(inhold=True));self.assertFalse(self.changed(outhold=True))
    def test_clock_reference_must_be_boundary(self):self.assertFalse(self.changed(child_clock_ref='pin'))
    def test_multiclock_needs_separate_proof(self):self.assertFalse(self.changed(clock_ports=['a','b']))
    def test_hierarchy_is_not_relabelled(self):self.assertFalse(self.changed(cluster_level=2))

if __name__=='__main__':unittest.main()
