#!/usr/bin/env python3
"""Opt-in exact bounded-tree TOPK candidate using the shared HBM M5 kit flow."""
import importlib.util,subprocess,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[2]
p=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
spec=importlib.util.spec_from_file_location('topk_tree_kit',p);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
mod='ot_hbm_idx_topk_link_static';top=mod+'_tree'
rec=dict(top=top,files=['rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv','rtl/hbm_accel/index/'+top+'.sv'],params={},defines=[],macros=['ot_sram_1r1w_64x512_m1_r2c2'],source='Opt-in bounded stable-tree compaction, exact same-edge candidate')
profile=dict(source_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),family='TOPK_TREE',diagnostic_inputs=True,clock_ports=['clk','clk_mem'],reset_ports=['rst_n'],qualification='UNROUTED_CANDIDATE')
args=sys.argv[1:]
for k,v in [('--sigmax','M5'),('--clock-taps','density'),('--core-insertion','none'),('--orfs-var','ADDER_MAP_FILE=')]:
 if k not in args:args.extend([k,v])
sys.argv=[str(p),*args];gen.main(recipe_overrides={mod:rec},source_profile=profile)
