#!/usr/bin/env python3
"""Short source/model contract checks. Full arithmetic simulation is parent gated."""
import ast
import json
import subprocess
import unittest
from pathlib import Path
from uarch_full_sm_service import ROOT, model

class ServiceContract(unittest.TestCase):
    def test_default_off(self):
        self.assertFalse(model()['enabled'])
        text=(ROOT/'rtl/gpu/ot_gpu_full_sm_service.sv').read_text()
        self.assertIn('parameter integer ENABLE=0',text)
        self.assertIn('if(ENABLE)',text)
        self.assertIn('for(l=0;l<128;',text)
    def test_pinned_sources_identical(self):
        # Entire original sources, no AST exclusions or byte exceptions.
        paths=('tools/uarch_model.py','rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_sm_v.sv',
               'rtl/gpu/ot_gpu_fadd.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv',
               'results/uarch/full_sm_actual_parent_route_20261002/build_readiness.json',
               'results/uarch/full_sm_actual_parent_route_20261002/priced_full_SM_area_outline.json')
        for path in paths:
            self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','show','5250fe00a:'+path],cwd=ROOT),path)
    def test_capacity_and_negative_admission(self):
        m=model(True)
        for r in m['models'].values():
            self.assertEqual(r['RF_macros'],16*4*2)
            self.assertEqual(r['RF_physical_bytes'],128*128*256//8)
            self.assertEqual(r['scratch_bytes'],2*1024*256//8)
            self.assertEqual(r['ports_bytes_per_cycle']['RF_read_A'],512)
            self.assertFalse(r['shared_channel_screen'])
            self.assertFalse(r['existing_logic_slot_fit'])
            self.assertFalse(r['physical_admissible'])
        self.assertFalse(m['build_GO']);self.assertFalse(m['rate_credit'])
    def test_serial_composition_and_invalid_stalls(self):
        events=[dict(kind='simd',count=3,stall_cycles=4),dict(kind='write',count=2,stall_cycles=0)]
        self.assertEqual(model(True,events)['serialized_service_cycles'],58)
        with self.assertRaises(ValueError):model(True,[dict(kind='simd',count=1,stall_cycles=-1)])
    def test_mirror_and_leases_are_real_providers(self):
        text=(ROOT/'rtl/gpu/ot_gpu_rf_service.sv').read_text()
        self.assertEqual(text.count('.w_ce_in(write_go && wr_addr[8:7]==p)'),2)
        self.assertEqual(text.count('.wd_in(wr_data[b*256+:256])'),2)
        self.assertIn('!read_pending && !rsp_valid && !ack_valid',text)
        self.assertIn('prefer_write<=1',text);self.assertIn('prefer_write<=0',text)
    def test_no_new_hub_or_ROM_routes(self):
        # Provider is local GPU service, not a hub transport layer change.
        for p in ('ot_gpu_rf_service.sv','ot_gpu_scratch_service.sv','ot_gpu_full_sm_service.sv'):
            t=(ROOT/'rtl/gpu'/p).read_text()
            self.assertNotIn('ot_rom_',t)
            self.assertNotIn('ot_hub_',t)
        self.assertFalse(model(True)['models']['DS']['ROM_transfer'])

if __name__=='__main__':unittest.main()
