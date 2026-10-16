#!/usr/bin/env python3
"""Full53-source/3-slot/16384-bit composition: threshold control + standard field4 data AND metadata.
Candidate-only; no timing, physical, compiler or parent adoption. Reuse exact baseline and actual failing mutants.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import area_a2f_split4_equiv_gate as G
G.SOURCES = G.SOURCES[:-1] + ['tools/s81_vm/area_a2f_control_resetlocal.sv', 'tools/s81_vm/area_a2f_split4m_composed.sv']
G.BENCH = G.BENCH.replace('s81_a2f_controlled_split4 dut(', 's81_a2f_controlled_split4m dut(')
# Only DUT metadata ABI changes; reference A2 still has16 quarter roots.
G.BENCH = G.BENCH.replace('.ck_control({4{ck}}),.ck_meta({4{ck}})', '.ck_control({4{ck}}),.ck_meta({28{ck}})')
G.BENCH = G.BENCH.replace('.rst_control_n({4{rst}}),.rst_meta_n({4{rst}})', '.rst_control_n({4{rst}}),.rst_meta_n({28{rst}})')
base_sha = G.sha
G.sha = lambda p: base_sha('tools/s81_vm/area_a2f_split4m_gate.py' if p == 'tools/s81_vm/area_a2f_split4_equiv_gate.py' else p)
G.OUT = G.ROOT / 'results/arch/s81_vm_split4m_2330'
if __name__ == '__main__': G.main()
