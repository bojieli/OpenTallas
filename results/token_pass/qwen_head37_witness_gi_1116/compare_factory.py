#!/usr/bin/env python3
"""Compare the prepared production transform to measured TEST-only nominal RTL.

No production profile is manufactured. Only master/branch names and the explicit
simulation negative-control term differ; comments/whitespace are ignored.
"""
import importlib.util
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
tool=HERE.parents[2]/'tools/qwen_layerbench/prepare_head37_tt_witness_source.py'
if not tool.is_file():tool=HERE.parent/'prepare_head37_tt_witness_source.py'
spec=importlib.util.spec_from_file_location('P',tool)
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
old=(HERE/'original_parts.sv').read_text()
receipt=json.loads((HERE/'test_leaf/receipt.json').read_text())
test=receipt['master'];production_name=test.replace('_test_','_prod_')
expected=P.clear_mission_stage_on_new_image(P.rewrite_parent(old,production_name))
expected=expected.replace(production_name,test).replace('g_wtn_head37','g_wtn_component_TEST_ONLY')
measured=(HERE/'input/qfd_tt_ctlm_dv_lpf_hp13_parts_component_TEST_ONLY.sv').read_text()
mutant=' && !$test$plusargs("NO_STAGE_CLEAR")'
assert measured.count(mutant)==1
measured=measured.replace(mutant,'')
normalize=lambda value:re.sub(r'\s+','',re.sub(r'//[^\n]*|/\*.*?\*/','',value,flags=re.S))
assert normalize(expected)==normalize(measured)
print('FACTORY_EQUALS_MEASURED_NOMINAL_RTL_AFTER_TEST_NAMES_AND_MUTANT_REMOVAL')
