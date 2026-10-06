#!/usr/bin/env python3
"""One independent native caller map and SS/FF library analysis on E1.

The child is cut at literal source ports, not compiled, replaced or duplicated.
All external timing remains unbound; mapped STA has no wire RC or CTS credit.
"""
import argparse,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
import hbm_router_pipeline_route_20261006 as B
from hbm_router_successor_map_20261006 import CAPS

ROOT=Path(__file__).resolve().parents[1]
TOP='ot_hbm_item9_ha2_native_boundary_context'
FILES=['rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv',
       'rtl/hbm_accel/ha2_ar/ot_ha2_parent_quiet_prims.sv',
       'physical/hbm_die_abstracts_20261006/integration/ot_hbm_item9_ha2_native_boundary_context.sv']
RAM=256

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def save(p,r):p.write_text(json.dumps(r,indent=2)+'\n')

def capacity(out,phase):
    def s():
        v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]));return sum(v[:8]),v[3]+v[4]
    t,i=s();time.sleep(.5);tt,ii=s();n=os.cpu_count();idle=(ii-i)/(tt-t)*n
    mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    disk=os.statvfs(out).f_bavail*os.statvfs(out).f_frsize
    r=dict(phase=phase,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
           load=os.getloadavg()[0],idle_cpus=idle,CPUs=n,MemAvailable_bytes=mem,disk_free_bytes=disk)
    r['fits']=idle>=16 and r['load']<n and mem>=RAM*1024**3 and disk>=128*1024**3
    with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
    return r

def docker(work,cmd,name=None):
    a=['docker','run','--cpus','16']
    a+=['--name',name] if name else ['--rm']
    return a+['-e','OMP_NUM_THREADS=16','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work',B.IMAGE,'bash','-lc',cmd]

ANALYZE=r'''import json,collections
from pathlib import Path
net=json.loads(Path('/work/mapped.json').read_text())['modules']['ot_hbm_item9_ha2_native_boundary_context']
lib=json.loads(Path('/work/library_input_caps_ff.json').read_text())
cells=net['cells'];seq=collections.Counter(c['type'] for c in cells.values() if c['type'].startswith('DFF'))
ports=net['ports'];owners={}
for name,p in ports.items():
 if p['direction']=='input':
  for idx,b in enumerate(p['bits']):owners.setdefault(b,[]).append((name,idx))
corners={}
for corner,table in lib.items():
 loads={n:[0.]*len(p['bits']) for n,p in ports.items() if p['direction']=='input'}
 receivers={}
 for name,c in cells.items():
  if c['type']=='$scopeinfo':continue
  assert c['type'] in table,(name,c['type'])
  for pin,bits in c['connections'].items():
   if pin not in table[c['type']]:continue
   for bit in bits:
    for port,idx in owners.get(bit,[]):
     loads[port][idx]+=table[c['type']][pin]
     if port.startswith('adapter_'):
      receivers.setdefault(port,[]).append(dict(bit=idx,cell=name,pin=pin,cap_fF=table[c['type']][pin]))
 corners[corner]=dict(input_pin_load_fF=loads,actual_result_receiver_pins=receivers)
Path('/work/caller_pin_caps.json').write_text(json.dumps(dict(top='ot_hbm_item9_ha2_native_boundary_context',sequential_cells=dict(seq),corners=corners,wire_RC_included=False,CTS_included=False,child_included=False,source_clock_qualified=False,physical_closed=False),indent=2)+'\n')
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--admitted',action='store_true');a=p.parse_args()
    if socket.gethostname()!='ot-epyc1tb':p.error('E1 only; no heavy localhost')
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'result.json').exists() or (out/'orfs').exists():p.error('attempt exists; preserve it, no replay')
    if not capacity(out,'post_guard' if a.admitted else 'pre_guard')['fits']:return 75
    if not a.admitted:
        return subprocess.call(['/srv/opentallas-scratch/admit.sh',str(RAM),'--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
    record=dict(phase='RUNNING_NATIVE_CALLER_MAP',top=TOP,parameters=dict(CALLER_ONLY=1,ENABLE=1),
        source_commit=(ROOT/'SOURCE_COMMIT').read_text().strip() if (ROOT/'SOURCE_COMMIT').exists() else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={f:sha(ROOT/f) for f in FILES},NUM_CORES=16,
        memory_guard_GiB=RAM,guard_unchanged=True,
        memory_inventory_basis='Prior active PF384 measured RSS sample Yosys24025044KiB+ABC9538780KiB for267501FF; native caller1468800FF is5.49x. Conservative256GiB envelope includes mapping and analysis reserve; sample scaling is an estimate, not a measured native peak or per-process limit.',
        disk_inventory_basis='Native FF inventory5.49x original map; reserve128GiB free for mapped Verilog/JSON/analysis objects; no file limit.',
        child_ABC_replayed=False,passing_gate_replayed=False,new_RTL_edges=0,
        ideal_clock=True,external_IO_bound=False,wire_RC=False,CTS=False,physical_qualified=False,adopted=False)
    work=out/'orfs';work.mkdir()
    shutil_src=ROOT/'physical/hbm_die_abstracts_20261006/integration/ha2_native_boundary_internal.sdc'
    (work/'constraint.sdc').write_bytes(shutil_src.read_bytes())
    cfg=['export DESIGN_NICKNAME = turing_ha2_native_caller','export DESIGN_NAME = '+TOP,
         'export PLATFORM = asap7','export VERILOG_FILES = '+' '.join('/src/'+f for f in FILES),
         'export VERILOG_TOP_PARAMS = CALLER_ONLY 1 ENABLE 1','export VERILOG_DEFINES = -DSYNTHESIS',
         'export SDC_FILE = /work/constraint.sdc','export SYNTH_REPEATABLE_BUILD = 1',
         'export SYNTH_HIERARCHICAL = 0','export SYNTH_MEMORY_MAX_BITS = 1468800',
         'export ADDER_MAP_FILE =','export LEC_CHECK = 0','export CORNER = WC',
         'export CORNERS = WC BC','export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)',
         'export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)','export ASAP7_USE_VT = RVT']
    # SYNTH_MEMORY_MAX_BITS is a compiler shape allowance for the actual
    # native memory inventory; it is not a RAM/AS/file/time resource limit.
    (work/'config.mk').write_text('\n'.join(cfg)+'\n')
    (work/'preserve_attributes.py').write_text(B.BOOTSTRAP)
    record['config_sha256']=sha(work/'config.mk');record['SDC_sha256']=sha(work/'constraint.sdc')
    command=docker(work,'python3 /work/preserve_attributes.py && cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 synth','turing-ha2-native-caller-'+out.name)
    record['command']=command;save(out/'launch.json',record)
    with (out/'map.log').open('w') as f:rc=subprocess.call(command,stdout=f,stderr=subprocess.STDOUT)
    record['map_exit']=rc
    if rc:
        record['phase']='MAP_FAIL_RETAINED';save(out/'result.json',record);return rc
    mapped=work/'results/asap7/turing_ha2_native_caller/base/1_2_yosys.v'
    record['mapped_sha256']=sha(mapped)
    (work/'analysis.ys').write_text('read_verilog /work/'+str(mapped.relative_to(work))+'\nhierarchy -top '+TOP+'\nwrite_json /work/mapped.json\n')
    (work/'caps.py').write_text(CAPS);(work/'analyze.py').write_text(ANALYZE)
    cmd=docker(work,'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -s /work/analysis.ys && python3 /work/caps.py && python3 /work/analyze.py')
    with (out/'caps.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
    record['analysis_exit']=rc
    if rc:
        record['phase']='CAPS_FAIL_RETAINED';save(out/'result.json',record);return rc
    corners={}
    for c,lib in [('ss','SS'),('ff','FF')]:
        tcl=f'''foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_{lib}_*.lib*] {{read_liberty $f}}
read_verilog /work/{mapped.relative_to(work)}
link_design {TOP}
read_sdc /work/constraint.sdc
puts "OT_EVIDENCE MAPPED_NATIVE_CALLER_IDEAL_CLOCK_NO_RC_NO_CTS_UNBOUND_EXTERNAL_IO"
puts "OT_REGISTERS [llength [all_registers -data_pins]]"
check_setup -verbose
report_checks -path_delay max -group_path_count 20 -format full_clock_expanded
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded
foreach pattern {{caller_h_v* caller_h_d* caller_p_v* caller_p_flit* caller_arm caller_active caller_rank* caller_pf*}} {{
 puts "OT_PRODUCER_CLASS $pattern"
 report_checks -unconstrained -to [get_ports $pattern] -path_delay max -group_path_count 8 -format full_clock_expanded
 report_checks -unconstrained -to [get_ports $pattern] -path_delay min -group_path_count 8 -format full_clock_expanded
}}
report_check_types -max_slew -max_capacitance -max_fanout -violators
exit
'''
        (work/(c+'.tcl')).write_text(tcl)
        cmd=docker(work,'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -threads 16 /work/'+c+'.tcl')
        with (out/(c+'.log')).open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
        corners[c]=dict(exit=rc,tcl_sha256=sha(work/(c+'.tcl')),log_sha256=sha(out/(c+'.log')))
        if rc:break
    record.update(phase='MAPPED_CALLER_ANALYSIS_TERMINAL',corners=corners,caller_caps_sha256=sha(work/'caller_pin_caps.json'),post_capacity=capacity(out,'terminal'))
    save(out/'result.json',record)
    return 0 if len(corners)==2 and all(v['exit']==0 for v in corners.values()) else 1

if __name__=='__main__':sys.exit(main())
