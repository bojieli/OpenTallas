#!/usr/bin/env python3
"""Prepare an actual native CP/SRAM paging probe using current descriptor bytes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/hbm_next'))
from cw308_pages import write
REF='24de429cd';FIXTURE='79d539a81'
def show(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
desc=[int(x,16)for x in show(FIXTURE,'results/tok_hbm_provider_1030/fixture_desc.mem').decode().splitlines()]
rows=[];at=32
for i in range(140):
 mv=desc[i%len(desc)];n=(mv>>206)//8;issue=at+8;drain=issue+n+20
 rows.append((at,issue|(drain<<32)|(mv<<64)|(7<<292)));at=drain+8
pages=write(rows,out)
src=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_cp_collar.sv','rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
files=[];pins={}
for relative in src:
 raw=show(REF,relative);path=out/Path(relative).name;path.write_bytes(raw);files.append(path);pins[relative]=hashlib.sha256(raw).hexdigest()
(out/'source_pins.json').write_text(json.dumps(dict(source_commit=REF,sha256=pins),indent=1)+'\n')
tb=Path(__file__).with_name('tb_pages.sv').read_text().replace('@@LAST_AT0@@',str(pages[0]['records'][-1]['at'])).replace('@@LAST_AT1@@',str(pages[1]['records'][-1]['at']))
path=out/'tb_pages.sv';path.write_text(tb);files.append(path);(out/'sources.f').write_text('\n'.join(x.name for x in files)+'\n')
print('NATIVE_CP_PAGES140commands128+12; remaining HOSTwire/calendar adoption explicit')
