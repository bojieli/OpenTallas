#!/usr/bin/env python3
"""Opt-in exact bounded-tree TOPK candidate using the shared HBM M5 kit flow."""
import importlib.util,subprocess,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[2]
p=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
sys.path.insert(0,str(p.parent))
spec=importlib.util.spec_from_file_location('topk_tree_kit',p);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
mod='ot_hbm_idx_topk_link_static';top=mod+'_tree'
rec=dict(top=top,files=['rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv','rtl/hbm_accel/index/'+top+'.sv'],params={},defines=[],macros=['ot_sram_1r1w_64x512_m1_r2c2'],source='Opt-in bounded stable-tree compaction, exact same-edge candidate')
profile=dict(source_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),family='TOPK_TREE',diagnostic_inputs=True,clock_ports=['clk','clk_mem'],reset_ports=['rst_n'],qualification='UNROUTED_CANDIDATE')
args=sys.argv[1:]
# The view names its plan recipe key (e.g. ot_hbm_idx_topk_link_static__650.16x500.04); without an explicit
# --recipe-key gen_core_kit_hbm.py picks that key and silently ignores this override (kits_r1 36b3f0c7a4d0 was the
# serial RTL and OOMed in TECHMAP).  Force the overridden key.
if '--recipe-key' in args and args[args.index('--recipe-key')+1]!=mod:raise SystemExit('topk_tree_kit: --recipe-key must be '+mod)
for k,v in [('--recipe-key',mod),('--sigmax','M5'),('--clock-taps','density'),('--core-insertion','none'),('--orfs-var','ADDER_MAP_FILE=')]:
 if k not in args:args.extend([k,v])
sys.argv=[str(p),*args];gen.main(recipe_overrides={mod:rec},source_profile=profile)
# fail closed: the generated kit must hold the tree RTL, never the serial core
out=Path(args[args.index('--out')+1]);kits=[k for k in out.iterdir() if (k/'freeze.json').is_file()]
import json
for k in kits:
 f=json.load(open(k/'freeze.json'))
 if f.get('recipe_key')==mod and not (k/'rtl'/(top+'.sv')).is_file():raise SystemExit(f'topk_tree_kit: {k} lacks {top}.sv')
if not any(json.load(open(k/'freeze.json')).get('recipe_key')==mod for k in kits):raise SystemExit('topk_tree_kit: no kit built from the tree recipe')
