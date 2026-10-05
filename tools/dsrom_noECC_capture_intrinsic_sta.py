#!/usr/bin/env python3
"""Full retained maps: macro-to-capture intrinsic SS/FF timing, no synthesis/P&R."""
import argparse, gzip, hashlib, json, re, resource, shutil, subprocess, time
from pathlib import Path
from dsrom_noECC_liberty import library_text

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/uarch/dsrom_noECC_production_context_20261002'
MAP = ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
MAC = ROOT/'results/uarch/dsrom_noECC_physical_transition_20261002/inputs'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def regex_names(names, suffix):
    return '^('+'|'.join(re.escape(n.removeprefix('\\')) for n in names)+')/'+suffix+'$'
def prepare(work):
    if work.exists(): raise ValueError('No overwrite or retry of an existing campaign')
    work.mkdir(parents=True)
    source = json.loads((BASE/'model.json').read_text())
    record = dict(schema='opentallas.dsrom.capture-intrinsic.v1', status='PREPARED',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        candidate=source['candidate'], model_sha256=sha(BASE/'model.json'),
        PG_cut_model_sha256=sha(BASE/'local_cuts.json'), period_ps=2500/3,
        setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        capture_setup_edges=2, capture_hold_edges=1,
        conservative_SS_macro_clkQ_grid_max_ps=839.0934,
        remaining_after_macro_clkQ_ps=2*2500/3-60-839.0934,
        scope='Complete retained q/BF maps, only macro data to source-selected capture D endpoints. Ideal clocks, pin-only load; no wire/skew or parent IO qualification.',
        engine_RTL_changed=False, cold_mapping=False, PnR_admitted=False,
        physical_closure=False, parent_IO_closed=False, added_cycles=0,
        clock_slew_scope='SS 320ps and FF 5ps macro table boundary conditions; NOT extracted clock slews. Stdcell extrapolation must remain disclosed.',
        sta_version=subprocess.check_output(['sta','-version'],text=True).strip(),
        sta_binary_sha256=sha(Path(shutil.which('sta'))), inputs={}, runs=[])
    for corner in ('ss','ff'):
        for family in ('ao','invbuf','oa','simple','seq'):
            original=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002/terminal_r4'/f'{family}_{corner}.lib.gz'
            text=library_text(f'{family}_{corner}.lib')
            p=work/f'{family}_{corner}.lib';p.write_text(text)
            record['inputs'][f'{family}_{corner}_archive']=sha(original)
            record['inputs'][f'{family}_{corner}_prepared']=sha(p)
        (work/f'macro_{corner}.lib').write_text(library_text(f'macro_{corner}.lib'))
        record['inputs'][f'macro_{corner}_lib']=sha(work/f'macro_{corner}.lib')
    for case,c in source['cases'].items():
        d=work/case; d.mkdir()
        original=MAP/case/'retained_mapped.v.gz'
        (d/'mapped.v').write_bytes(gzip.decompress(original.read_bytes()))
        record['inputs'][f'{case}_mapped_archive']=sha(original)
        record['inputs'][f'{case}_mapped_verilog']=sha(d/'mapped.v')
        cap=c['actual_Verilog_captureDFF']; rom=c['actual_Verilog_ROM']; gates=c['actual_Verilog_ICG']
        if (len(cap),len(rom),len(gates))!=(1088,4,8): raise ValueError('Incomplete retained element')
        for corner in ('ss','ff'):
            lines=[f'read_liberty {work}/{family}_{corner}.lib' for family in ('ao','invbuf','oa','simple','seq')]
            lines += [f'read_liberty {work}/macro_{corner}.lib',
                f'read_verilog {d}/mapped.v','link_design ot_v41_rom_elem_w10',
                'create_clock -name root -period 833.333333333333 [get_ports clk]',
                'set allcells [get_cells -hierarchical *]',
                'array set byname {}',
                'foreach c $allcells {set byname([get_full_name $c]) $c}',
                'set data {}']
            for rcell in rom:
                name=rcell['name'].removeprefix('\\')
                lines += [f'set romname {{{name}}}',
                    'if {![info exists byname($romname)]} {error "Missing actual source macro"}',
                    'foreach p [get_pins -of_objects $byname($romname)] {if {[string match */rd_out* [get_full_name $p]]} {lappend data $p}}']
            for i,g in enumerate(gates):
                name=g['name'].removeprefix('\\')
                lines += [f'set gatename {{{name}}}',
                    'if {![info exists byname($gatename)]} {error "Missing actual source ICG"}',
                    'set gp {}',
                    'foreach p [get_pins -of_objects $byname($gatename)] {if {[string match */GCLK [get_full_name $p]]} {lappend gp $p}}',
                    'if {[llength $gp] != 1} {error "Missing unique actual source gated clock"}',
                    f'create_generated_clock -name leaf{i} -source [get_ports clk] -divide_by 1 $gp']
            capnames=' '.join('{'+x['name'].removeprefix('\\')+'}' for x in cap)
            lines += [f'set capnames {{{capnames}}}', 'set caps {}',
                'foreach name $capnames {if {![info exists byname($name)]} {error "Missing actual source capture cell"}; foreach p [get_pins -of_objects $byname($name)] {if {[string match */D [get_full_name $p]]} {lappend caps $p}}}']
            lines += ['set_clock_uncertainty -setup 60 [all_clocks]',
                'set_clock_uncertainty -hold 25 [all_clocks]',
                f'set_clock_transition {320 if corner=="ss" else 5} [all_clocks]',
                'if {[llength $caps] != 1088} {error "Missing capture endpoints"}',
                'if {[llength $data] != 1096} {error "Missing full macro output pins"}',
                'puts "CAPTURE_ENDPOINTS [llength $caps] MACRO_OUTPUTS [llength $data]"',
                'set_multicycle_path -setup 2 -through $data -to $caps',
                'set_multicycle_path -hold 1 -through $data -to $caps',
                'report_units',
                'report_checks -through $data -to $caps -path_delay max -group_count 1088 -endpoint_count 1 -format full_clock_expanded -digits 6 -fields {slew capacitance input_pin net}',
                'report_checks -through $data -to $caps -path_delay min -group_count 1088 -endpoint_count 1 -format full_clock_expanded -digits 6 -fields {slew capacitance input_pin net}',
                'exit']
            tcl=d/f'{corner}.tcl';tcl.write_text('\n'.join(lines)+'\n')
            record['runs'].append(dict(case=case,corner=corner,tcl=str(tcl),tcl_sha256=sha(tcl), status='PREPARED'))
    (work/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    return record
def run(work):
    r=prepare(work)
    for item in r['runs']:
        log=work/item['case']/(item['corner']+'.log');start=time.monotonic()
        with log.open('w') as out:
            p=subprocess.Popen(['sta','-exit',item['tcl']],stdout=out,stderr=subprocess.STDOUT)
            item.update(status='LIVE',pid=p.pid)
            (work/'record.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
            print(json.dumps(item),flush=True); rc=p.wait()
        s=log.read_text()
        item.update(status='TERMINAL',returncode=rc,elapsed_s=time.monotonic()-start,
            log_sha256=sha(log), errors=re.findall(r'^Error:.*',s,re.M),
            warnings=re.findall(r'^Warning:.*',s,re.M),
            missing_templates=bool(re.search(r'table template .* not found',s)),
            arrival_ps=[float(x) for x in re.findall(r'([-\d.]+)\s+data arrival time',s)],
            required_ps=[float(x) for x in re.findall(r'([-\d.]+)\s+data required time',s)],
            slack_ps=[float(x) for x in re.findall(r'([-\d.]+)\s+slack',s)],
            endpoint_counts=re.findall(r'CAPTURE_ENDPOINTS (\d+) MACRO_OUTPUTS (\d+)',s))
        if rc or item['errors'] or item['missing_templates'] or not item['arrival_ps']:
            r['status']='FIRST_FAILURE_PRESERVED';break
    else: r['status']='MEASURED_INTRINSIC_CAPTURE_ONLY_CONTEXT_OPEN'
    u=resource.getrusage(resource.RUSAGE_CHILDREN)
    r['child_resources']=dict(user_s=u.ru_utime,system_s=u.ru_stime,maxrss_KiB=u.ru_maxrss)
    (work/'record.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(r['status'],flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True)
    args=ap.parse_args();run(args.work.resolve())
