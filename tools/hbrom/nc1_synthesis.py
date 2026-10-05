#!/usr/bin/env python3
"""Pinned full NC1 baseline mapping and intrinsic SS/FF screen; never physical closure."""
import argparse, collections, hashlib, json, os, pathlib, re, resource, shutil, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from dsrom_noECC_liberty import library_text

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p, obj): p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=pathlib.Path, required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--run', action='store_true')
    a=ap.parse_args(); w=a.work.resolve()
    if w.exists(): raise SystemExit('Refusing to overwrite any campaign directory')
    w.mkdir(parents=True)
    manifest=ROOT/'results/uarch/hbrom_cluster_20261005/nc1_calibration_inventory.json'
    inv=json.loads(manifest.read_text())
    for p,h in inv['source_pins'].items():
        if sha(ROOT/p)!=h: raise ValueError('Source pin mismatch '+p)
    libs={}
    for corner in ('ss','ff'):
        libs[corner]=[]
        for family in ('ao','invbuf','oa','simple','seq'):
            p=w/f'{family}_{corner}.lib';p.write_text(library_text(p.name));libs[corner].append(p)
    top=inv['top']
    ys=[f'read_verilog -lib -sv {ROOT/m["source"]}' for m in inv['macro_sources']]
    ys += [f'read_verilog -sv {ROOT/p}' for p in inv['rtl_sources']]
    ys += [f'hierarchy -check -top {top}',f'synth -top {top} -flatten',
           f'dfflibmap -liberty {w}/seq_ss.lib',
           'abc '+ ' '.join('-liberty '+str(p) for p in libs['ss'])+' -D 833.333333333333',
           *[f'read_liberty -lib {p}' for p in libs['ss']],
           f'write_rtlil {w}/mapped.precheck.il',
           'check -assert', 'splitnets -ports', 'opt_clean',
           f'tee -o {w}/stat.json stat -json '+ ' '.join('-liberty '+str(p) for p in libs['ss']),
           f'write_json {w}/mapped.json', f'write_verilog -noattr -noexpr {w}/mapped.v']
    (w/'synth.ys').write_text('\n'.join(ys)+'\n')
    for corner in ('ss','ff'):
        tc=[f'read_liberty {p}' for p in libs[corner]]
        tc += [f'read_liberty {ROOT/m[corner+"_lib"]}' for m in inv['macro_sources']]
        tc += [f'read_verilog {w}/mapped.v',f'link_design {top}',
               'create_clock -name root -period 833.333333333333 [get_ports clk]',
               'set_clock_uncertainty -setup 60 [all_clocks]', 'set_clock_uncertainty -hold 25 [all_clocks]',
               'set_clock_transition 50 [all_clocks]',
               'set_input_delay -max 166.666666666667 -clock root [get_ports {start op_* d_valid d_base* d_lines* req_ready rsp_* xw_* release_in}]',
               'set_input_delay -min 0 -clock root [get_ports {start op_* d_valid d_base* d_lines* req_ready rsp_* xw_* release_in}]',
               'set_output_delay -max 166.666666666667 -clock root [all_outputs]',
               'set_output_delay -min 0 -clock root [all_outputs]',
               'set_load 3.898 [all_outputs]',
               'set_false_path -from [get_ports rst_n]',
               'report_units','check_setup -verbose',
               'report_checks -path_delay max -group_count 20 -format full_clock_expanded -digits 6',
               'report_checks -path_delay min -group_count 20 -format full_clock_expanded -digits 6',
               'report_worst_slack -max','report_worst_slack -min', 'report_tns', 'exit']
        (w/f'{corner}.tcl').write_text('\n'.join(tc)+'\n')
    record=dict(schema='hbrom.nc1.synthesis.v1',source_commit=a.source_commit,
        status='PREPARED',scope=inv['scope'],physical_closure=False,
        timing_scope='Intrinsic pin-only ideal-clock SS/FF screen; assumed 50ps clock slew, 20% IO budget,3.898fF output load; no wires/CTS. Async reset excluded; needs physical recovery/removal.',
        period_ps=833.333333333333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        source_manifest_sha256=sha(manifest),source_pins=inv['source_pins'],
        scripts={p.name:sha(p) for p in w.glob('*.tcl')},library_pins={p.name:sha(p) for p in w.glob('*.lib')}, runs=[])
    record['scripts']['synth.ys']=sha(w/'synth.ys');write(w/'record.json',record)
    if not a.run: print(json.dumps(record));return
    yosys=pathlib.Path(os.environ.get('OT_YOSYS',str(pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys')))
    sta=shutil.which('sta')
    if not sta: raise ValueError('OpenSTA executable missing')
    record['tool_pins']={str(p):sha(p) for p in (yosys,yosys.with_name('yosys-abc'),pathlib.Path(sta))}
    commands=[('synth',[str(yosys),'-t','-s',str(w/'synth.ys')]),('ss',[sta,'-exit',str(w/'ss.tcl')]),('ff',[sta,'-exit',str(w/'ff.tcl')])]
    for name,cmd in commands:
        if name=='ss':
            net=json.loads((w/'mapped.json').read_text());mods=net['modules'];counts=collections.Counter()
            def visit(module):
                for c in mods[module].get('cells',{}).values():
                    typ=c['type']; counts[typ]+=1
                    if typ in mods and not int(mods[typ].get('attributes',{}).get('blackbox','0'),2):visit(typ)
            visit(top)
            record['macro_inventory']={m['module']:counts[m['module']] for m in inv['macro_sources']}
            if any(counts[m['module']]!=m['count'] for m in inv['macro_sources']):
                record['status']='FAILED_MACRO_INVENTORY';write(w/'record.json',record);raise SystemExit(1)
            write(w/'cell_inventory.json',dict(counts))
        item=dict(stage=name,command=cmd,status='RUNNING');record['runs'].append(item);write(w/'record.json',record)
        start=time.monotonic()
        with (w/f'{name}.log').open('w') as out:
            p=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,cwd=ROOT);item['pid']=p.pid;write(w/'record.json',record);rc=p.wait()
        log=(w/f'{name}.log').read_text(errors='replace')
        item.update(returncode=rc,elapsed_s=time.monotonic()-start,log_sha256=sha(w/f'{name}.log'),status='TERMINAL')
        item['errors']=re.findall(r'^(?:\[[^]]+\] )?(?:ERROR|Error:).*',log,re.M)
        item['warnings']=re.findall(r'^Warning:.*',log,re.M)
        item['worst_slack_ps']=re.findall(r'worst slack\s+([-+0-9.eE]+)',log)
        record['child_maxrss_KiB']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        if rc or item['errors']:
            record['status']='FAILED_PRESERVED';write(w/'record.json',record);raise SystemExit(1)
        write(w/'record.json',record)
    record['status']='MEASURED_INTRINSIC_SCREEN_ONLY'
    record['mapped_netlist_sha256']=sha(w/'mapped.v');write(w/'record.json',record)
    print(json.dumps(record))
if __name__=='__main__':main()
