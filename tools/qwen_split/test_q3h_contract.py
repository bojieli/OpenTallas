"""Malformed physical contracts must fail before relay planning or case export."""
import copy
import json
from pathlib import Path
import unittest
from qwen_split import q3h_cluster as Q

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'results/arch/qwen_split_compute_1014/dieplan2_1016'

class ContractGate(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((DATA / 'q3h_cluster_contract_cb.json').read_text())
        self.g = json.loads((DATA / 'q3h2_grid.json').read_text())
    def test_actual_contract_and_grid(self):
        self.assertEqual(len(Q.validate_contract_grid(self.c, self.g)), 15)
    def test_stale_bc3_outside_shrunk_outline(self):
        next(p for p in self.c['ports'] if p['port'] == 'bc3')['range_um'] = [2173.76,2345.76]
        with self.assertRaisesRegex(ValueError, 'out-of-outline'):
            Q.validate_contract_grid(self.c, self.g)
    def test_contract_outline_cannot_be_overridden(self):
        self.c['outline_um']['w'] = 2350.08
        with self.assertRaisesRegex(ValueError, 'outline and grid differ'):
            Q.validate_contract_grid(self.c, self.g)
    def test_missing_pin_group(self):
        self.c['ports'].pop()
        with self.assertRaisesRegex(ValueError, 'missing ports'):
            Q.validate_contract_grid(self.c, self.g)
    def test_wrong_port_width(self):
        self.c['ports'][0]['bits'] = 515
        with self.assertRaisesRegex(ValueError, 'wrong-width'):
            Q.validate_contract_grid(self.c, self.g)
    def test_duplicate_group(self):
        self.c['ports'].append(copy.deepcopy(self.c['ports'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            Q.validate_contract_grid(self.c, self.g)
    def test_reversed_bit_order(self):
        self.c['ports'][0]['range_um'].reverse()
        with self.assertRaisesRegex(ValueError, 'unordered'):
            Q.validate_contract_grid(self.c, self.g)
    def test_pin_pitch_collapses(self):
        self.c['ports'][0]['range_um'] = [10,11]
        with self.assertRaisesRegex(ValueError, 'pins overlap'):
            Q.validate_contract_grid(self.c, self.g)
    def test_two_groups_overlap(self):
        # bc0 and bc1 both on S/M5; independently valid widths, mutually invalid homes.
        a = next(p for p in self.c['ports'] if p['port']=='bc0')
        b = next(p for p in self.c['ports'] if p['port']=='bc1')
        b['range_um'] = list(a['range_um'])
        with self.assertRaisesRegex(ValueError, 'overlapping pin groups'):
            Q.validate_contract_grid(self.c, self.g)
    def test_nonfinite_pin(self):
        self.c['ports'][0]['range_um'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'):
            Q.validate_contract_grid(self.c, self.g)
    def test_negative_cluster_gap(self):
        self.g['clusters'][1]['x'] = self.g['clusters'][0]['x']
        self.g['clusters'][1]['y'] = self.g['clusters'][0]['y']
        with self.assertRaisesRegex(ValueError, 'negative gap'):
            Q.validate_contract_grid(self.c, self.g)
    def test_nonfinite_contract_outline(self):
        self.c['outline_um']['w'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite and positive'):
            Q.validate_contract_grid(self.c, self.g)
    def test_missing_cluster_group(self):
        self.g['clusters'].pop()
        with self.assertRaisesRegex(ValueError, '48 unique groups'):
            Q.validate_contract_grid(self.c, self.g)
    def test_instance_master_mismatch(self):
        self.g['clusters'][0]['w'] -= 1
        with self.assertRaisesRegex(ValueError, 'outline differs'):
            Q.validate_contract_grid(self.c, self.g)
    def test_cluster_outside_die(self):
        self.g['clusters'][0]['x'] = -1
        with self.assertRaisesRegex(ValueError, 'outside die'):
            Q.validate_contract_grid(self.c, self.g)


class ClockPinUniqueness(unittest.TestCase):
    def test_late_pin_grant_refuses_closed_view(self):
        import tempfile
        from unittest.mock import patch
        from types import SimpleNamespace
        import qwen_rom_fulldie_b3r2 as G
        closed = object()
        v = SimpleNamespace(masters=lambda *args: {'qfd_cst_s': closed})
        with tempfile.TemporaryDirectory() as tmp:
            grant=Path(tmp)/'grant.json'
            grant.write_text(json.dumps({'late_masters': {'qfd_cst_s': {'ck': {'positions':[1]}}}}))
            with patch.dict('os.environ', {'OT_SPLIT_PIN_GRANT': str(grant)}):
                G._late_pin_grant(v)
                with self.assertRaisesRegex(ValueError, 'closed view.*immutable'):
                    v.masters({})

    def test_repeated_clock_pin_cannot_split_between_roots(self):
        from types import SimpleNamespace as I
        import qwen_rom_fulldie_b3r2 as G
        # Two distant sink fields force the regional median split. A duplicated
        # middle physical pin straddles that median without de-duplication.
        ins=[I(name=n,x=x,y=0,w=10,h=10) for n,x in [('root',0),('a',0),('b',6000),('c',12000)]]
        model=dict(insts=ins,b3r2={},clock_regions=[dict(name='r',kind='test',rect=[0,0,13000,100])],
                   buses=[('clk_r0','clock_trunk',1,[('root','pll_r0'),('a','ck'),('b','ck'),('b','ck'),('c','ck')])])
        G._regions_from_placement(model)
        endpoints=[e for _,_,_,eps in model['buses'] for e in eps if e[0]!='root']
        self.assertEqual(sorted(endpoints),[('a','ck'),('b','ck'),('c','ck')])
        self.assertEqual(model['b3r2']['regions_from_placement']['duplicate_sinks_removed'],1)
        self.assertGreater(model['b3r2']['regions_from_placement']['split'],0)


if __name__ == '__main__':
    unittest.main()
