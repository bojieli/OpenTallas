#!/usr/bin/env python3
"""Actual multi-family source periods must not fall back to core833 or HBM1024."""
import unittest
import kvsys_clocks as K
from qwen_tp8.die_sta_libs import clock_tcl

class SourceClocks(unittest.TestCase):
    def setUp(self):
        self.domains={K.domain(n):[('i/ck','m','ck')] for n in (
            'n_clk_core_c','n_clk_hbm_WS','n_clk_host_program','n_clk_ingest_map','n_clk_phy_serdes')}
        self.leaves={'m':{c:{'ck':77} for c in ('tt','ff','ss')}}
    def test_actual_source_periods_and_phi_r(self):
        periods=K.periods_for(self.domains)
        self.assertEqual(periods,dict(stream=833.334,hclk_WS=1024.,host=1000.,ingest=1666.668,phy=1043.))
        text=clock_tcl(self.domains,self.leaves,'tt',periods)
        for d,p in periods.items():
            self.assertIn(f'create_clock -name {d} -period {p:.6f}',text)
            self.assertIn(f'set_clock_latency -source -clock [get_clocks {d}] -77.000000',text)
    def test_unknown_source_family_rejected(self):
        with self.assertRaises(ValueError):K.domain('n_clk_unknown_bad')
    def test_missing_period_rejected(self):
        with self.assertRaises(ValueError):clock_tcl(self.domains,self.leaves,'tt',{'stream':833.334})

if __name__=='__main__':unittest.main()
