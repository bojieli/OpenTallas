#!/usr/bin/env python3
"""Fail closed on double wrapping, drift and another snapshot's same basename."""
from pathlib import Path
import tempfile
from verify_explicit_boundary_config import verify

receipt=Path('cold/generated/receipt.json');source=Path('cold/generated/parent.sv').resolve()
good='\n'.join(['export OT_PIN_REGS = 0','export OT_RST_LAND = 0','export DESIGN_NAME = qfd_sys_face_control_safe','export VERILOG_FILES = '+str(source)])+'\n'
with tempfile.TemporaryDirectory(prefix='sysface-config-proof-') as d:
 p=Path(d)/'config.mk';p.write_text(good);verify(p,receipt,source)
 bad={
  'double_pin_wrap':good.replace('OT_PIN_REGS = 0','OT_PIN_REGS = 1'),
  'double_reset_wrap':good.replace('OT_RST_LAND = 0','OT_RST_LAND = 1'),
  'foreign_same_basename':good.replace(str(source),'/unrelated/snapshot/parent.sv'),
  'duplicate_source':good.replace(str(source),str(source)+' '+str(source)),
  'wrong_top':good.replace('DESIGN_NAME = qfd_sys_face_control_safe','DESIGN_NAME = qfd_sys_face'),
 }
 for name,text in bad.items():
  p.write_text(text)
  try:verify(p,receipt,source)
  except AssertionError:print('EXPECTED_REFUSAL',name)
  else:raise AssertionError('escaped exact source/config guard '+name)
 p.write_text(good);changed=Path(d)/'parent.sv';changed.write_text(source.read_text()+'\n// drift\n')
 try:verify(p,receipt,changed)
 except AssertionError:print('EXPECTED_REFUSAL source_byte_drift')
 else:raise AssertionError('escaped source drift')
print('EXPLICIT_BOUNDARY_CONFIG_GUARDS_PASS mutants6')
