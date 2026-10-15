#!/usr/bin/env python3
"""Audit exact source derivation: clock partitions and top module/ports only."""
import argparse,pathlib,re
p=argparse.ArgumentParser();p.add_argument('original',type=pathlib.Path);p.add_argument('derived',type=pathlib.Path);a=p.parse_args()
s=a.original.read_text().replace('module ot_dsrom_aq12 (','module ot_hbm_sm_aq_static (')
s=re.sub(r'\bclk\b','clk_core',s).replace('input  wire          clk_core,','input  wire          clk_core,\n    input  wire          clk_delay,\n    input  wire          clk_encode,',1)
s=s.replace('.clk_core(','.clk(').replace('u_x (.clk(clk_core)','u_x (.clk(clk_delay)')
i=s.index('    // -- S12:');s=s[:i]+s[i:].replace('posedge clk_core','posedge clk_encode')
s=s.replace('// LATENCY 18 (vs 13):','// Three explicit roots must have identical frequency and functional phase.\n// Cross-root paths require synchronous physical timing constraints; no new stages.\n// LATENCY 18 (vs 13):')
assert a.derived.read_text()==s,'derived AQ differs beyond exact stage clock assignments'
print('AQ12_DERIVATION PASS exact existing arithmetic/stages, three clock roots only')
