#!/usr/bin/env python3
"""Bind actual Verilator consumed inputs to selected-source provenance."""
from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--mdir',default='obj_r6');p.add_argument('--manifest',default='SELECTED_SOURCE_MANIFEST.json');p.add_argument('--cache',default='cache_inventory.json');p.add_argument('--output',default='consumed_source_audit.json');a=p.parse_args()
D=Path.cwd();m=json.loads(Path(a.manifest).read_text());b=json.loads(Path(a.cache).read_text());known=m['files'];tools={r['path']:r['sha256']for r in b['source_files']if r['path'].startswith('/home/ubuntu/.local/opentallas-tools/')}
ledger=[];bench=[];command=None
for line in (Path(a.mdir)/'Vtb__verFiles.dat').read_text().splitlines():
 if line.startswith('C '):command=line
 if not line.startswith('S '):continue
 actual_name=line.rsplit(chr(34),2)[1];name=Path(actual_name).as_posix();f=Path(name);f=f if f.is_absolute() else D/f
 sha=hashlib.file_digest(open(f,'rb'),'sha256').hexdigest()
 if name in known:
  assert sha==known[name]['sha256'],(name,sha,known[name]);role='selected-source';parent=known[name]['parent_source_path']
 elif name in tools:
  assert sha==tools[name],(name,sha,tools[name]);role='same pinned Verilator tool';parent=name
 elif name.startswith('generated_')and name.endswith('/tb.sv'):
  role='generated bounded testbench';parent=m['private_tip'];bench.append(name)
 else:raise AssertionError(('UNEXPECTED_CONSUMED_INPUT',name,sha))
 ledger.append(dict(path=name,sha256=sha,role=role,parent=parent))
assert bench and command and '--timing' in command and '--top-module tb' in command
assert any(r['path']=='rtl/hbm_accel/die_glue/scoped_d4g/pgslice.sv'for r in ledger)
assert any(r['path']=='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore.sv'for r in ledger)
assert not any(r['path']=='hfd_hgi_vm_calendar_f20.sv'for r in ledger)
result=dict(verdict='PASS',private_tip=m['private_tip'],actual_command=command,files=ledger,expected_superset_files=len(known),actual_files=len(ledger),generated_bench=bench)
Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print('ACTUAL_CONSUMED_SOURCE_PASS',len(ledger),'manifest_superset',len(known))
