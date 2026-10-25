#!/usr/bin/env python3
"""Gate exact native L74 DATA/CTL masks and explicit stage ownership."""
import json
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
layout=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
v='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
for hub,record in layout.items():
    d,c=record['data'],record['ctl'];name=hub.lower()
    stages=d['cycles']-d['boundary']
    args=[f"-GW={d['width']}",f"-GS={c['width']}",f'-GLINK_STAGES={stages}',
          f"-GMASK={d['width']}'h{d['control_mask'][2:]}",f"-GSMASK={c['width']}'h{c['control_mask'][2:]}"]
    with (out/(name+'.build.log')).open('w') as log:
        subprocess.run([v,'--binary','--timing','-j','2','-O1','-Wno-fatal','--top-module','tb',*args,'--Mdir',str(out/('obj_'+name)),
                        'rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv','tools/hbm_layer_vehicle/static_2beat/tb.sv'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (out/(name+'.log')).open('w') as log:
        subprocess.run([str(out/('obj_'+name)/'Vtb')],stdout=log,stderr=subprocess.STDOUT,check=True)
    print((out/(name+'.log')).read_text().splitlines()[0])
with (out/'age.build.log').open('w') as log:
    subprocess.run([v,'--binary','--timing','-j','2','-O1','-Wno-fatal','--top-module','tb_age','--Mdir',str(out/'obj_age'),
                    'rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv','tools/hbm_layer_vehicle/static_2beat/tb_age.sv'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
with (out/'age.log').open('w') as log:
    subprocess.run([str(out/'obj_age'/'Vtb_age')],stdout=log,stderr=subprocess.STDOUT,check=True)
print((out/'age.log').read_text().splitlines()[0]);(out/'done').write_text('LAYOUT_AND_AGE PASS\n')
