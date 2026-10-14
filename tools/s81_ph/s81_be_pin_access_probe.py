#!/usr/bin/env python3
"""Four-orientation actual OpenROAD pin_access probe of a BE view candidate.

Reuses the established station probe's four-instance geometry and unique pin
nets. Restricts parent signals to M2-M7, with the exact locked ASAP7 image;
records local headroom, image/technology hashes, logs and measured resource use.
No clock/global-route/detailed-route qualification is inferred from pin_access.
"""
import argparse,hashlib,json,os,resource,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('lef',type=Path);ap.add_argument('work',type=Path);a=ap.parse_args()
    lef=a.lef.resolve();work=a.work.resolve();work.mkdir(parents=True,exist_ok=True)
    station=ROOT/'physical/hbm_accel_die_views/stations/bench/stn_pa_check.sh'
    prefix=station.read_text().split('docker run --rm',1)[0]
    generator=work/'generate.sh';generator.write_text(prefix)
    subprocess.run(['bash',str(generator),str(lef),'dsfd_vm_be_sl',str(work)],check=True,cwd=ROOT)
    tcl=work/'pa.tcl';tcl.write_text(tcl.read_text().replace('set_routing_layers -signal M2-M9','set_thread_count 4\nset_routing_layers -signal M2-M7'))
    image='openroad/orfs:asap7lock';image_id=subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip()
    command=['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',f'{work}:/work',image,'bash','-c','cd /work && /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit pa.tcl']
    headroom=Path('/proc/meminfo').read_text();start=time.time()
    with (work/'pa.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    text=(work/'pa.log').read_text();done='OT_PA DONE' in text;failed=text.count('DRT-0073')
    record=dict(schema='opentallas.be_pin_access_probe.v1',lef_sha256=sha(lef),station_generator_sha256=sha(station),tcl_sha256=sha(tcl),image=image,image_id=image_id,
        parent_signal_layers='M2-M7',orientations=['R0','MX','MY','R180'],clock_or_route_qualification=False,
        headroom_meminfo=headroom,threads=4,elapsed_s=time.time()-start,child_peak_rss_kb=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        returncode=r.returncode,DRT0073=failed,OT_PA_DONE=done,pass_=bool(r.returncode==0 and done and failed==0),command=command)
    (work/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['elapsed_s','returncode','DRT0073','OT_PA_DONE','pass_']}))
    return 0 if record['pass_'] else 1
if __name__=='__main__':raise SystemExit(main())
