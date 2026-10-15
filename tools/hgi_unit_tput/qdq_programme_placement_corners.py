#!/usr/bin/env python3
"""Source-bound separate-library STA of retained Quant programme CTS ODB; placement RC only."""
import argparse, hashlib, importlib.util, json, re, subprocess
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('run',type=Path); a=ap.parse_args()
r=a.run.resolve(); src=r/'src'; work=r/'routes/gate/work/orfs'
spec=importlib.util.spec_from_file_location('corner_sta',src/'tools/w18/corner_sta.py'); sta=importlib.util.module_from_spec(spec); spec.loader.exec_module(sta)
base=next((work/'results/asap7').glob('*/base')); rel='/work/'+str(base.relative_to(work)); macro='physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2'; sdc='physical/ref_tile/hgi_qdq_program_sw125/signoff.sdc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec={'schema':'opentallas.quant.programme_cts_corners.v1','scope':'retained CTS ODB, placement RC; not routed signoff','run':str(r),'odb_sha256':sha(base/'4_cts.odb'),'saved_sdc_sha256':sha(base/'4_cts.sdc'),'native_sdc_sha256':sha(src/sdc),'corner_helper_sha256':sha(src/'tools/w18/corner_sta.py'),'corners':{}}
for c in ('tt','ff','ss'):
    t=sta.script(c,rel,[macro],[sdc],sdc_name='4_cts.sdc').replace('/6_final.odb','/4_cts.odb').replace(f'read_spef {rel}/6_final.spef',f'source {sta.PLAT}/setRC.tcl\nestimate_parasitics -placement')
    script=work/f'quant_cts_{c}.tcl'; script.write_text(t)
    cmd=['docker','run','--rm','-v',f'{src}:/src:ro','-v',f'{work}:/work','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/work/{script.name}']
    p=subprocess.run(cmd,capture_output=True,text=True); out=p.stdout+'\n'+p.stderr; (work/f'quant_cts_{c}.log').write_text(out)
    m=re.search(r'^OT_WS (\S+)',out,re.M); errors=re.findall(r'(?:\[ERROR[^\n]*|^Error:[^\n]*)',out,re.M)
    entry={'check':'hold' if c=='ff' else 'setup','tool_rc':p.returncode,'errors':errors,'worst_slack_ps':float(m[1])*1e12 if m else None,'script_sha256':sha(script),'log_sha256':sha(work/f'quant_cts_{c}.log'),'std_libs':sta.corner_libs(c),'macro_lib_sha256':sha(src/macro/(Path(macro).name+f'_{c}.lib'))}
    rec['corners'][c]=entry; print(c,json.dumps(entry),flush=True)
rec['timing_pass']=all(rec['corners'][c]['tool_rc']==0 and not rec['corners'][c]['errors'] and rec['corners'][c]['worst_slack_ps'] is not None and rec['corners'][c]['worst_slack_ps']>=0 for c in ('tt','ff'))
(r/'programme_placement_corners.json').write_text(json.dumps(rec,indent=2)+'\n')
