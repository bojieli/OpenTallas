import copy,importlib.util,unittest
from pathlib import Path
p=Path(__file__).with_name('derive.py');spec=importlib.util.spec_from_file_location('ft_roles',p);D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
class Controls(unittest.TestCase):
    def test_exact_current_fixture(self):
        d=D.derive();self.assertFalse(d['qualified']);self.assertEqual(len(d['interface_additions']),12)
        self.assertFalse(d['models_mutated']);self.assertFalse(d['new_aliases'])
    def bad_load(self,name,edit):
        original=D.load
        def loader(n):
            d=original(n)
            if n==name:edit(d)
            return d
        D.load=loader
        try:
            with self.assertRaises((ValueError,KeyError)):D.derive()
        finally:D.load=original
    def test_reject_wrong_source_net(self):
        self.bad_load('historical_ft_manifest.json',lambda d:d['arcs'][0].update(input_net='clk'))
    def test_reject_wrong_role(self):
        self.bad_load('current_r27_pins.json',lambda d:d['island_ft']['arcs'][0].update(role='tree_node'))
    def test_reject_changed_current_site(self):
        self.bad_load('current_selected_plan.json',lambda d:d['hard_cores'][1]['origin_um'].__setitem__(0,553.0))
    def test_reject_missing_current_base(self):
        self.bad_load('current_selected_plan.json',lambda d:d['hard_cores'].pop(1))
    def test_reject_wrong_output_mesh(self):
        self.bad_load('historical_ft_manifest.json',lambda d:d['arcs'][0].update(output_net='clk_t1'))
if __name__=='__main__':unittest.main()
