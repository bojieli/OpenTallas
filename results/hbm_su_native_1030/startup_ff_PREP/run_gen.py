#!/usr/bin/env python3
"""Existing generator source-only recipe override API; no generated kit edits."""
import importlib.util,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[3];P=pathlib.Path(__file__).parent
G=R/'physical/die_plan/hbm_arch_cores';sys.path.insert(0,str(G));sys.path.insert(0,str(R/'tools/die_plan'))
spec=importlib.util.spec_from_file_location('gen_core_kit_hbm',G/'gen_core_kit_hbm.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
M.main(recipe_overrides=json.load(open(P/'recipes_PREP.json')))
