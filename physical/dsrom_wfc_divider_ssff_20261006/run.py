#!/usr/bin/env python3
"""One pinned divider internal map/SSFF check; no parent/PLL timing fiction."""
import argparse, datetime, gzip, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

IMAGE='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
SOURCE='physical/dsrom_wfc_clock_source_20261006/ot_dsrom_wfc_common_clock_source.sv'
PIN='efde53cd44c63fcef68439283da31ff4a1d5bc795fdf52a81f3c50b3ffd06eb7'
TOP='ot_dsrom_wfc_common_clock_source'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(cmd,out):
    with out.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise RuntimeError(f'{out.name} exit{r.returncode}')
def fit(out,stage):
    def cpu():
        v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(v),v[3]
    x=cpu();time.sleep(1);y=cpu();n=os.cpu_count()
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    row=dict(utc=now(),stage=stage,cpus=n,load1=os.getloadavg()[0],idle_cpus=n*(y[1]-x[1])/(y[0]-x[0]),
        available_bytes=mem['MemAvailable'],nvme_free_bytes=shutil.disk_usage(out).free,
        threads=2,expected_peak_GiB=2,guard='/srv/opentallas-scratch/admit.sh')
    row['fit']=row['load1']+2<=n and row['load1']<128 and row['idle_cpus']>=2 and row['available_bytes']>=102*2**30 and row['nvme_free_bytes']>=2*2**30
    with (out/'headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True);return row['fit']
def inside(root,out,reuse=None):
    p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
    libs={};pins={}
    for corner in ('SS','FF'):
        paths=[]
        for family,date in [('AO','211120'),('INVBUF','220122'),('OA','211120'),('SEQ','220123'),('SIMPLE','211120')]:
            name=f'asap7sc7p5t_{family}_RVT_{corner}_nldm_{date}.lib'
            source=p/name
            if not source.exists():source=Path(str(source)+'.gz')
            dest=out/'libs'/name;dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(gzip.decompress(source.read_bytes()) if source.suffix=='.gz' else source.read_bytes())
            paths.append(dest);pins[str(source)]=sha(source)
        libs[corner]=paths
    (out/'library_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    ss=libs['SS'];seq=next(x for x in ss if '_SEQ_' in x.name)
    script=f'''read_verilog -sv {root/SOURCE}
hierarchy -check -top {TOP} -chparam ENABLE 1
proc
setattr -set keep 1 t:$adff t:$dff t:$adffe t:$dffe
setattr -set keep 1 w:on.f w:on.fn w:on.s w:on.sn w:on.fq w:on.fqn w:on.fh w:on.fhn w:on.sq w:on.sqn w:on.failed w:on.failed_n w:on.bad
synth -top {TOP} -flatten -noabc
dfflibmap -liberty {seq}
abc {' '.join('-liberty '+str(x) for x in ss)} -D 277.777777778
splitnets -ports
opt_clean
tee -o {out/'mapped.stat'} stat {' '.join('-liberty '+str(x) for x in ss)}
write_verilog {out/'mapped.attributes.v'}
write_verilog -noattr {out/'mapped.v'}
write_json {out/'mapped.json'}
'''
    if reuse:
        for name in ('mapped.json','mapped.v','mapped.attributes.v','mapped.stat'):
            shutil.copyfile(reuse/name,out/name)
        (out/'mapped_reuse.json').write_text(json.dumps({name:sha(reuse/name) for name in ('mapped.json','mapped.v')},indent=2)+'\n')
    else:
        (out/'synth.ys').write_text(script)
        run(['yosys','-s',str(out/'synth.ys')],out/'synth.log')
    design=json.loads((out/'mapped.json').read_text())['modules'][TOP]
    ff=[(n,c) for n,c in design['cells'].items() if c['type'].startswith('DFF')]
    unmapped=[(n,c['type']) for n,c in design['cells'].items() if c['type'].startswith('$')]
    (out/'mapped_inventory.json').write_text(json.dumps(dict(FF=len(ff),cells=len(design['cells']),unmapped=unmapped,netnames=design['netnames']),indent=2)+'\n')
    if len(ff)!=16 or unmapped:raise RuntimeError(f'protected source retention/mapping gap FF={len(ff)} unmapped={unmapped}')
    # Find actual Q nets by literal retained source bit and report both
    # primary/shadow paths without relying on generated mapper cell names.
    groups={}
    for group in ['fq','fqn','fh','fhn','sq','sqn','f','fn','s','sn','failed','failed_n']:
        key='on.'+group
        bits=[b for n,row in design['netnames'].items() if n==key or n.startswith(key+'[') for b in row['bits']];q=[];d=[]
        if not bits:raise RuntimeError('missing source state '+key)
        for name,c in ff:
            if any(b in bits for b in c['connections'].get('QN',c['connections'].get('Q',[]))):
                q.append(name+'/QN' if 'QN' in c['connections'] else name+'/Q');d.append(name+'/D')
        groups[group]=dict(Q=q,D=d)
    (out/'path_pins.json').write_text(json.dumps(groups,indent=2)+'\n')
    badbits=design['netnames']['on.bad']['bits'];badpins=[]
    for name,c in design['cells'].items():
        for port,bits in c['connections'].items():
            if c['port_directions'].get(port)=='output' and any(b in badbits for b in bits):badpins.append(name+'/'+port)
    for corner in ('SS','FF'):
        tcl='\n'.join('read_liberty '+str(x) for x in libs[corner])+f'''
read_verilog {out/'mapped.v'}
link_design {TOP}
create_clock -name ref -period 277.777777777778 -waveform {{0 138.888888888889}} [get_ports pll_vco]
set_clock_uncertainty -setup 60 [get_clocks ref]
set_clock_uncertainty -hold 25 [get_clocks ref]
puts "DIVIDER_SCOPE IDEAL_REFERENCE INTERNAL_MAPPED_PIN_LOADS ONLY NO_PLL_OR_PARENT_IO_SIGNOFF"
report_units
report_clock_properties
puts "DIVIDER_WNS"
report_worst_slack -max -digits 6
report_worst_slack -min -digits 6
report_tns -digits 6
puts "DIVIDER_ALL_MAX"
report_checks -path_delay max -group_path_count 20 -format full_clock_expanded -fields {{slew cap input nets fanout}} -digits 6
puts "DIVIDER_ALL_MIN"
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded -fields {{slew cap input nets fanout}} -digits 6
'''
        for name in ('fq','fqn','fh','fhn','f','fn','s','sn','sq','sqn','failed','failed_n'):
            g=groups[name]
            if g['Q']:
                for sense in ('max','min'):
                    tcl+=f'puts "DIVIDER_FROM_{name}_{sense}"\nreport_checks -from [get_pins {{{" ".join(g["Q"])}}}] -path_delay {sense} -group_path_count 20 -format full_clock_expanded -fields {{slew cap input nets fanout}} -digits 6\n'
        for sense in ('max','min'):
            tcl+=f'puts "DIVIDER_BADRAIL_{sense}"\nreport_checks -through [get_pins {{{" ".join(badpins)}}}] -path_delay {sense} -group_path_count 32 -format full_clock_expanded -fields {{slew cap input nets fanout}} -digits 6\n'
        tcl+='''puts "DIVIDER_PULSEWIDTH"
report_check_types -min_period -min_pulse_width -violators -digits 6
puts "DIVIDER_SLEW_CAP"
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6
puts "DIVIDER_END"
'''
        (out/f'{corner}.tcl').write_text(tcl)
        run(['sta','-exit',str(out/f'{corner}.tcl')],out/f'{corner}.log')
        if 'Error' in (out/f'{corner}.log').read_text():raise RuntimeError(f'{corner} STA errors; preserve log')
    run(['yosys','-V'],out/'yosys.version')
    (out/'tools.json').write_text(json.dumps({name:sha(shutil.which(name)) for name in ('yosys','sta')},indent=2)+'\n')

def main():
    a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--reuse-mapped',type=Path);a.add_argument('--admitted',action='store_true');a.add_argument('--inside',action='store_true');args=a.parse_args()
    root=args.source.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    assert sha(root/SOURCE)==PIN
    if args.inside:
        try:inside(root,out,args.reuse_mapped)
        except Exception as e:
            (out/'fatal.json').write_text(json.dumps(dict(utc=now(),error=str(e),physical_qualified=False),indent=2)+'\n');raise
        return 0
    if not fit(out,'post-guard' if args.admitted else 'pre-guard'):return 75
    if not args.admitted:
        extra=['--reuse-mapped',str(args.reuse_mapped)] if args.reuse_mapped else []
        return subprocess.run(['/srv/opentallas-scratch/admit.sh','2','--',sys.executable,str(Path(__file__).resolve()),'--source',str(root),'--output',str(out),'--admitted',*extra]).returncode
    if (out/'command.json').exists():raise RuntimeError('Existing admitted attempt: collect, never overwrite/relaunch')
    extra_mount=['-v',str(args.reuse_mapped.resolve())+':/mapped:ro'] if args.reuse_mapped else []
    extra_arg=' --reuse-mapped /mapped' if args.reuse_mapped else ''
    cmd=['docker','run','--name','descartes-wfc-divider-'+out.name,'--cidfile',str(out/'container.id'),'-e','OMP_NUM_THREADS=2','-v',str(root)+':/src:ro','-v',str(out)+':/out',*extra_mount,IMAGE,'bash','-lc','source /OpenROAD-flow-scripts/env.sh; python3 /src/physical/dsrom_wfc_divider_ssff_20261006/run.py --source /src --output /out --inside'+extra_arg]
    (out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    with (out/'run.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
    (out/'terminal.exit').write_text(str(rc)+'\n');return rc
if __name__=='__main__':sys.exit(main())
