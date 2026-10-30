#!/usr/bin/env python3
"""Attach actual native clock census with no period/phase/spatial credit."""
import json,shutil,sys
from pathlib import Path
src,out,census=map(Path,sys.argv[1:4]);shutil.copytree(src,out)
d=out/'native_domains';d.mkdir()
for k in ('parent','child'):shutil.copyfile(census/(k+'_clock_contract.json'),d/(k+'_clock_contract.json'))
p=out/'source_plan.json';r=json.loads(p.read_text());t=r['partition_types']['hd_serdes'];parent=json.loads((d/'parent_clock_contract.json').read_text());child=json.loads((d/'child_clock_contract.json').read_text())
roots={x['net']:x['port'].removesuffix('[0]') for x in parent['clock_root_ports']}
macros=[dict(inst=x['inst'],module=x['master'],pin=x['pin'],root=roots[x['net']]) for x in parent['macro_clock_pins']]
assert {x['inst'] for x in macros}=={x['inst'] for x in t['hard_cores']}
cc=next(x for x in macros if x['module']=='ot_s81_kp4_dchn')
t['clock']['native_domains']=dict(schema='opentallas.native_clock_domains.v1',census_file='native_domains/parent_clock_contract.json',source_odb_sha256=parent['source_odb_sha256'],core_root='clk',macro_pins=macros,children=[dict(cc,census_file='native_domains/child_clock_contract.json',source_odb_sha256=child['source_odb_sha256'])])
p.write_text(json.dumps(r,indent=1)+'\n')
print('NATIVE_DOMAIN_METADATA_ATTACHED; no periods/planned positions/phase credit')
