#!/usr/bin/env python3
"""Four-orientation actual OpenROAD pin_access probe of a BE view candidate.

Reuses the established station probe's four-instance geometry and unique pin
nets. Restricts parent signals to M2-M7, with the exact locked ASAP7 image;
records local headroom, image/technology hashes, logs and measured resource use.
No clock/global-route/detailed-route qualification is inferred from pin_access.
"""
import argparse,hashlib,json,os,resource,subprocess,time,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('lef',type=Path);ap.add_argument('work',type=Path);ap.add_argument('--aligned-tracks',action='store_true');ap.add_argument('--m7-pin-shift',type=float,choices=[0,.016,.032],default=0);ap.add_argument('--parent-be-slots',action='store_true');ap.add_argument('--be-x-shift',type=float,choices=[0,-.048],default=0);ap.add_argument('--master',default='dsfd_vm_be_sl');ap.add_argument('--relay-rows',action='store_true');ap.add_argument('--relay-y-offset',type=float,choices=[0,.024],default=0);a=ap.parse_args()
    lef=a.lef.resolve();work=a.work.resolve();work.mkdir(parents=True,exist_ok=True)
    station=ROOT/'physical/hbm_accel_die_views/stations/bench/stn_pa_check.sh'
    prefix=station.read_text().split('docker run --rm',1)[0]
    generator=work/'generate.sh';generator.write_text(prefix)
    subprocess.run(['bash',str(generator),str(lef),a.master,str(work)],check=True,cwd=ROOT)
    tcl=work/'pa.tcl';t=tcl.read_text().replace('set_routing_layers -signal M2-M9','set_thread_count 4\nset_routing_layers -signal M2-M7')
    # Keep legacy placement as a separately reproducible negative. For the
    # actual orientation probe use origins satisfying reflected contact phases:
    # M7 vertical .016/.064 and M4 horizontal .012/.048. This leaf's width is
    # a .064 multiple and height a .048 multiple; reflection flips offsets.
    placements=[('R0',10.368,10.368),('MX',333.12,10.392),('MY',10.4,124.416),('R180',333.152,124.44)]
    if a.m7_pin_shift==.016:
        placements=[('R0',10.416,10.368),('MX',333.168,10.392),('MY',10.416,124.416),('R180',333.168,124.44)]
    if a.m7_pin_shift==.032:
        placements=[('R0',10.4,10.368),('MX',333.152,10.392),('MY',10.368,124.416),('R180',333.12,124.44)]
    if a.parent_be_slots:
        placements=[('R0',.144+64.8+a.be_x_shift+475.2*k,21.6) for k in range(4)]
        t=re.sub(r'initialize_floorplan -die_area \{[^}]+\} -core_area \{[^}]+\}', 'initialize_floorplan -die_area {0 0 1887.384 196.56} -core_area {0 0 1887.384 196.56}',t)
    if a.relay_rows:
        placements=[('R0',.144+21.6+64.8*(k%2),117.72+43.2*(k//2)+a.relay_y_offset) for k in range(4)]
        t=re.sub(r'initialize_floorplan -die_area \{[^}]+\} -core_area \{[^}]+\}', 'initialize_floorplan -die_area {0 0 1887.384 196.56} -core_area {0 0 1887.384 196.56}',t)
    if a.aligned_tracks or a.parent_be_slots or a.relay_rows:
        for k,(o,x,y) in enumerate(placements):
            t=re.sub(r'place_inst -name u'+str(k)+r' -location \{[^}]+\} -orientation \S+ -status FIRM',f'place_inst -name u{k} -location {{{x} {y}}} -orientation {o} -status FIRM',t)
    tcl.write_text(t)
    image='openroad/orfs:asap7lock';image_id=subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip()
    command=['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',f'{work}:/work',image,'bash','-c','cd /work && /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit pa.tcl']
    headroom=Path('/proc/meminfo').read_text();start=time.time()
    with (work/'pa.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    text=(work/'pa.log').read_text();done='OT_PA DONE' in text;failed=text.count('DRT-0073')
    record=dict(schema='opentallas.be_pin_access_probe.v1',lef_sha256=sha(lef),station_generator_sha256=sha(station),tcl_sha256=sha(tcl),image=image,image_id=image_id,
        parent_signal_layers='M2-M7',master=a.master,orientations=[p[0] for p in placements] if a.parent_be_slots or a.relay_rows else ['R0','MX','MY','R180'],track_phase_policy='actual_requested_relay_rows_plus_global_phase_UNALLOCATED' if a.relay_rows else ('actual_requested_BE_slots_plus_VM_global_phase_mod_192_UNALLOCATED' if a.parent_be_slots else ('M7_and_M4_orientation_phases;M5_contact_width_checked_by_actual_AP' if a.aligned_tracks else 'legacy_station_placement')),m7_pin_shift_um=a.m7_pin_shift,relay_y_offset_um=a.relay_y_offset,be_x_shift_um=a.be_x_shift,placements=placements if a.aligned_tracks or a.parent_be_slots or a.relay_rows else None,clock_or_route_qualification=False,
        headroom_meminfo=headroom,threads=4,elapsed_s=time.time()-start,child_peak_rss_kb=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        returncode=r.returncode,DRT0073=failed,OT_PA_DONE=done,pass_=bool(r.returncode==0 and done and failed==0),command=command)
    (work/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['elapsed_s','returncode','DRT0073','OT_PA_DONE','pass_']}))
    return 0 if record['pass_'] else 1
if __name__=='__main__':raise SystemExit(main())
