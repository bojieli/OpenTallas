#!/usr/bin/env python3
"""QC-IMPORT-2: the raw-reset-star preflight check keys on the bound net, not the port name."""
import sys, types, unittest
from pathlib import Path
sys.modules.setdefault('shapely', types.ModuleType('shapely'))
for m in ('shapely.geometry', 'shapely.strtree'):
    mod = sys.modules.setdefault(m, types.ModuleType(m)); mod.box = mod.STRtree = None
sys.path.insert(0, str(Path(__file__).resolve().parent))
from preflight import reset_binding_issue as rb

RS = dict(port='rst_raw_n', part='sl_E0_fw', pin='rst_o_0', net='rstw_sl_E0_fw_rst_o_0')
MAC = ['sl_E0_fw', 'sl_E0_stm']
def q(net='rstw_sl_E0_fw_rst_o_0', role='reset', ep=(('sl_E0_fw', 'rst_o_0'),)):
    return dict(net=net, role=role, native_endpoints=[dict(inst=i, pin=p) for i, p in ep])

class T(unittest.TestCase):
    def test_local_root_passes_despite_port_name(self):
        self.assertIsNone(rb('rst_raw_n', q(), MAC, RS))
    def test_die_raw_reset_net_is_star(self):
        self.assertIn('raw reset', rb('rst_raw_n', q(net='rst_n', ep=()), MAC, RS))
    def test_other_net_rejected(self):
        self.assertIn('not plan reset_source', rb('rst_raw_n', q(net='rstw_sl_W0_fw_rst_o_0', ep=(('sl_W0_fw', 'rst_o_0'),)), MAC, RS))
    def test_wrong_or_extra_endpoint(self):
        self.assertIsNotNone(rb('rst_raw_n', q(ep=(('sl_E0_stm', 'arst_n'),)), MAC, RS))
        self.assertIsNotNone(rb('rst_raw_n', q(ep=(('sl_E0_fw', 'rst_o_0'), ('sl_E0_stm', 'arst_n'))), MAC, RS))
    def test_driver_must_be_partition_macro(self):
        self.assertIn('partition macro', rb('rst_raw_n', q(), ['sl_E0_stm'], RS))
    def test_export_dict_macros(self):
        self.assertIsNone(rb('rst_raw_n', q(), [dict(inst='sl_E0_fw', master='m')], RS))
    def test_no_plan_fails_closed(self):
        self.assertIsNotNone(rb('rst_raw_n', q(), MAC, None))
    def test_role_must_be_reset(self):
        self.assertIsNotNone(rb('rst_raw_n', q(role='clock'), MAC, RS))

if __name__ == '__main__': unittest.main()
