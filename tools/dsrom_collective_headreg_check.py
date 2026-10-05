"""New W15 parity-head integration check only; no model inference/old gate replay."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

FILES = ['rtl/test/tb_dsrom_collective_headreg.sv',
         'rtl/rom/ot_w15_rom_oneshot_px.sv',
         'rtl/rom/ot_w15_rom_oneshot_px_headreg.sv',
         'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv',
         'rtl/proto/ot_fp32_add_rne_pipe.sv']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verilator',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    a.output.mkdir(parents=True,exist_ok=False)
    pins={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in FILES}
    record={'scope':'New W15 parity/relay/GW4 head integration; no whole-system gain or SSFF qualification',
            'source_sha256':pins,'runs':[]}
    for name,extra in [('parity_relay_gw4',[]),('badtag',['-GBAD_TAG=1']),
                       ('linear_gw1',['-GRELAY=0','-GGW=1','-GPAIRWISE=0'])]:
        obj=a.output/('obj_'+name)
        cmd=[a.verilator,'--binary','--timing','--build','-j',str(a.jobs),'-Wno-fatal',
             '--top-module','tb_dsrom_collective_headreg','--Mdir',str(obj),
             *extra,*[str(root/f) for f in FILES]]
        with (a.output/(name+'.build.log')).open('w') as log:
            rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
        r={'name':name,'parameters':extra,'compile_returncode':rc}
        if rc==0:
            with (a.output/(name+'.run.log')).open('w') as log:
                r['run_returncode']=subprocess.run([str(obj/'Vtb_dsrom_collective_headreg')],stdout=log,stderr=subprocess.STDOUT).returncode
            r['pass']=r['run_returncode']==0 and 'DS_HEADREG PASS' in (a.output/(name+'.run.log')).read_text()
        else: r['pass']=False
        record['runs'].append(r)
        (a.output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        if not r['pass']: break
    record['sources_unchanged']=pins=={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in FILES}
    record['pass']=len(record['runs'])==3 and all(r['pass'] for r in record['runs']) and record['sources_unchanged']
    (a.output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    return int(not record['pass'])

if __name__=='__main__':raise SystemExit(main())
