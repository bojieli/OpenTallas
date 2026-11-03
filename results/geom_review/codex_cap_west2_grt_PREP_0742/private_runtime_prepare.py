#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,difflib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--record',type=Path);p.add_argument('--expected',type=Path);p.add_argument('scripts',type=Path);a=p.parse_args();scripts=a.scripts.resolve()
if scripts!=Path('/OpenROAD-flow-scripts/flow/scripts') or not Path('/work/CAP_SCOPE.json').is_file():raise SystemExit('OWN_CONTAINER_AND_PRD_INPUT_REQUIRED')
inp=Path('/work/run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/INPUT_ROUTED/6_final.odb')
if inp.resolve()!=Path('/work/baseline/6_final.odb') or not inp.is_file():raise SystemExit('OWN_IMMUTABLE_ROUTED_SYMLINK_REQUIRED')
target=scripts/'global_route.tcl';before=target.read_bytes();
if hashlib.sha256(before).hexdigest()!='aeeb5c3aa3bdef64ba569cb650fd119c3389d0f0bf7478a7e440dca3f6b50447':raise SystemExit('EXACT_PINNED_STOCK_POST_MM_BODY_REQUIRED')
anchor=b'load_design 4_cts.odb 4_cts.sdc\n';replacement=b'load_design INPUT_ROUTED/6_final.odb INPUT_ROUTED/6_final.sdc\n'
if before.count(anchor)!=1:raise SystemExit('EXACT_POST_MM_ROUTED_LOADER_ANCHOR_REQUIRED')
s=importlib.util.spec_from_file_location('qualified_wrap','/work/native_pg_birth_wrap_runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
original=m.wrap(scripts,'/work/native_pg_birth_global_route.tcl')
if original.read_bytes()!=before:raise SystemExit('PRESERVED_POST_MM_BODY_DIFFERED')
after=before.replace(anchor,replacement);original.write_bytes(after)
sha=lambda b:hashlib.sha256(b).hexdigest()
r={'schema':'opentallas.owned_cap_west2_routed_pg_runtime.v1','stock_post_mm_sha256':sha(before),'routed_body_sha256':sha(after),'wrapper_sha256':sha(target.read_bytes()),'source_stage':'actual routed6_final, not CTS','actual_input':'/work/baseline/6_final.odb','SDC':'true retained6_final.sdc; no CTS artifact credit','cts_credit':False,'scope':'GRT/resizer only; no DRT/fill/finish admission','input_only_diff':''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='post_mm_global_route',tofile='owned_routed_global_route'))}
if a.expected:
 e=json.loads(a.expected.read_text())
 for k in ['stock_post_mm_sha256','routed_body_sha256','wrapper_sha256','input_only_diff']:
  if r[k]!=e[k]:raise SystemExit('FROZEN_RUNTIME_MISMATCH '+k)
if a.record:a.record.write_text(json.dumps(r,indent=2))
print(json.dumps(r))
