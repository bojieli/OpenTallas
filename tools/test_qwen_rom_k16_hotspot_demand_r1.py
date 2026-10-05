"""Measured-grid refusal mutants and prospective cost/scope checks; no P&R."""
import json
from pathlib import Path
import tempfile
import unittest
import qwen_rom_k16_hotspot_demand_r1 as H

class HotspotTests(unittest.TestCase):
    def parse(self, text, regions=None):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'grid';p.write_text(text)
            return H.hotspot_usage(p, regions or {'r':[0,0,5,5]},1000)

    def grid(self):
        return ('GRIDX 0,1000,2000,3000,4000\nGRIDY 0,1000,2000,3000,4000\n'
                'L M8 0 10/8 1/0\nL M8 4 1/0 1/0\n'
                'L M9 0 10/13 1/0\nL M9 4 1/0 1/0\n')

    def test_units_peak_and_overcapacity(self):
        r=self.parse(self.grid())['r']
        self.assertEqual(r['M9']['demand'],13)
        self.assertEqual(r['M9']['capacity'],13)
        self.assertEqual(r['M9']['peak_fraction'],1.3)
        self.assertEqual(r['M9']['over_capacity_windows'],1)
        self.assertEqual(r['M9']['peak_window_rect_um'],[0,0,4,4])

    def test_duplicate_and_missing_rows_refused(self):
        for s in [self.grid()+'L M9 0 10/13 1/0\n',self.grid().replace('L M9 4 1/0 1/0\n','')]:
            with self.subTest(s=s),self.assertRaises(ValueError):self.parse(s)

    def test_truncated_negative_and_nonfinite_refused(self):
        for s in ['10/13','10/-1 1/0','10/nan 1/0']:
            with self.subTest(s=s),self.assertRaises(ValueError):self.parse(self.grid().replace('10/13 1/0',s))

    def test_invalid_outside_selected_region_still_refused(self):
        with self.assertRaises(ValueError):
            self.parse(self.grid().replace('10/13','10/nan'),{'far':[20,20,30,30]})

    def test_nonmonotonic_grid_refused(self):
        with self.assertRaises(ValueError):self.parse(self.grid().replace('0,1000,2000','0,1000,1000'))

    def test_unknown_overflow_source_retained(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'rpt';p.write_text('violation type: Vertical\nbbox = ( 0, 0) - ( 1, 1)\ncapacity:1 usage:2\nnet:alien[0]\ncomment: end\n')
            r=H.overflow_sources(p,{'r':[0,0,2,2]},{'buses':[]})
            self.assertEqual(r['r']['source_mentions_by_class'],{'UNKNOWN':1})

    def test_actual_station_state_and_latency_priced_without_adoption(self):
        root=Path(__file__).resolve().parents[1]
        f=json.loads((root/'results/rtl/qwen_rom_fulldie_20261003/k16_demand_r1/inputs/SS_cell_prices.json').read_text())
        r=H.prospective(H.F.build(tree_mode='banded'),f)
        self.assertEqual(r['instruction']['stations'],1536)
        self.assertEqual(r['instruction']['protected_added_bits'],1437696)
        self.assertEqual(r['narrow_links']['serialized_extra_edges_per_36layer_token'],4032)
        self.assertEqual(r['narrow_links']['serialized_extra_us_at_1p2GHz'],3.36)
        self.assertFalse(r['implementation_admitted'])
        self.assertIsNone(r['GALS']['source_matched_cut_count'])

    def test_k32_tech_refused_before_other_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tech';p.write_text('DATABASE MICRONS 1000 ; # k = 32')
            with self.assertRaisesRegex(ValueError,'wrong physical k16'):
                H.build_record(None,'banded',None,p,None)

if __name__=='__main__':unittest.main()
