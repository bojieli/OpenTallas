#!/usr/bin/env python3
"""Price reported capture subtotal; keep model diagnostics separate from physics."""
import argparse, gzip, hashlib, json, re, shutil
from pathlib import Path
from dsrom_noECC_liberty import cell_bodies,block
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(text,cells):
    paths=[];violations={};limits={}
    for master,body in cells.items():
        for m in re.finditer(r'\bpin\s*\(([^)]+)\)',body):
            pin=block(body,m.start());v=re.search(r'\bmax_transition\s*:\s*([\d.]+)',pin)
            if v:limits[master,m[1].strip(' "')]=float(v[1])
    for part in text.split('Startpoint: ')[1:]:
        typ=re.search(r'Path Type: (max|min)',part)
        endpoint=re.search(r'Endpoint: (\S+)',part)
        if not typ or not endpoint:raise ValueError('Unparsed actual timing path')
        arrival=float(re.search(r'([-\d.]+)\s+data arrival time',part)[1])
        slack=float(re.search(r'([-\d.]+)\s+slack',part)[1])
        macro=re.search(r'([\d.]+)\s+([\d.]+)\s+[v^] .*?/rd_out\[\d+\] \(ot_rom_4096x274_m8\)',part)
        if not macro:raise ValueError('Path does not include source macro data')
        constraint=re.search(r'([-\d.]+)\s+[-\d.]+\s+library (setup|hold) time',part)
        if not constraint:raise ValueError('No capture constraint in report')
        setup=-float(constraint[1]) if constraint[2]=='setup' else None
        clkq=float(macro[1])
        paths.append(dict(type=typ[1],endpoint=endpoint[1],arrival_ps=arrival,macro_clkQ_ps=clkq,
            mux_delay_ps=arrival-clkq,setup_ps=setup,hold_ps=float(constraint[1]) if constraint[2]=='hold' else None,
            slack_ps=slack,SS_capture_subtotal_ps=arrival-clkq+setup if setup is not None else None))
        for line in part.splitlines():
            m=re.search(r'([v^])\s+(\S+)/(\S+)\s+\((\w+)\)',line)
            if not m:continue
            nums=re.findall(r'[-+]?\d+(?:\.\d+)?',line[:m.start()])
            if len(nums)<3:continue
            slew=float(nums[-3]);limit=limits.get((m[4],m[3]))
            if limit is not None and slew>limit:
                key=(m[2],m[3]);old=violations.get(key,dict(instance=m[2],pin=m[3],master=m[4],source_limit_ps=limit,max_reported_slew_ps=0))
                old['max_reported_slew_ps']=max(old['max_reported_slew_ps'],slew);violations[key]=old
    if not paths:raise ValueError('No measured paths')
    return paths,list(violations.values())
def archive(work,out=OUT):
    r=json.loads((work/'record.json').read_text())
    if r['status']!='MEASURED_INTRINSIC_CAPTURE_ONLY_CONTEXT_OPEN':raise ValueError('Incomplete campaign')
    dest=out/'terminal_r4'
    if dest.exists():raise ValueError('Immutable terminal already exists')
    dest.mkdir(parents=True);shutil.copyfile(work/'record.json',dest/'record.json')
    summaries=[]
    for item in r['runs']:
        case,corner=item['case'],item['corner'];d=dest/case;d.mkdir(exist_ok=True)
        text=(work/case/(corner+'.log')).read_text()
        paths,v=parse(text,cell_bodies(corner))
        bytype={t:[p for p in paths if p['type']==t] for t in ('max','min')}
        for t,p in bytype.items():
            if len(p)!=1088 or len({x['endpoint'] for x in p})!=1088:raise ValueError('Full capture endpoint coverage missing')
        summary=dict(case=case,corner=corner,endpoint_count_each_max_min=1088,
            report_errors=item['errors'],missing_templates=item['missing_templates'],
            max_setup_path=min(bytype['max'],key=lambda x:x['slack_ps']),
            min_hold_path=min(bytype['min'],key=lambda x:x['slack_ps']),
            source_max_transition_violation_unique_pin_count=len(v),
            worst_slew_violations=sorted(v,key=lambda x:x['max_reported_slew_ps'],reverse=True)[:8],
            all_paths_have_ideal_clock_and_zero_wire_RC=True,clock_tree_slews_not_extracted=True)
        if corner=='ss':
            subtotal=max(p['SS_capture_subtotal_ps'] for p in bytype['max'])
            summary.update(capture_setup_plus_mux_subtotal_max_ps=subtotal,
                conservative_remaining_wire_skew_ps=2*2500/3-60-839.0934-subtotal,
                remaining_is_diagnostic_not_admitted_bound=bool(v))
        summaries.append(summary)
        shutil.copyfile(work/case/(corner+'.tcl'),d/(corner+'.tcl'))
        (d/(corner+'.log.gz')).write_bytes(gzip.compress(text.encode(),mtime=0))
    for p in work.glob('*.lib'):(dest/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    diag=work/'q/ss_dcalc.log';dt=diag.read_text()
    arc=dt.split('Cell: NAND2xp33_ASAP7_75t_R',1)[1].split('A v -> Y ^',1)[1].split('Library:',1)[0]
    observed={key:float(re.search(pattern,arc)[1]) for key,pattern in {
        'input_slew_ps':r'input_net_transition = ([\d.]+)',
        'output_load_fF':r'total_output_net_capacitance = ([\d.]+)',
        'Liberty_delay_ps':r'Delay = ([\d.]+)',
        'report_dcalc_Liberty_slew_ps':r'Slew = ([\d.]+)'}.items()}
    qtext=(work/'q/ss.log').read_text()
    row=re.search(r'([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+\^ _233706_/Y',qtext)
    if not row:raise ValueError('Source-matched diagnostic witness not found')
    observed.update(instance='_233706_',master='NAND2xp33_ASAP7_75t_R',arc='A falling -> Y rising',
        report_checks_propagated_output_slew_ps=float(row[2]),reported_path_delay_ps=float(row[3]),
        interpretation='Delay agrees, slew disagrees. Diagnostic replay reads same complete q netlist/libs/clocks; only reports dcalc, no remap or constraint change. Do not infer physical failure or prescribe resizing from this discrepancy.')
    shutil.copyfile(work/'q/ss_dcalc.tcl',dest/'q/ss_dcalc.tcl')
    (dest/'q/ss_dcalc.log.gz').write_bytes(gzip.compress(diag.read_bytes(),mtime=0))
    result=dict(schema='opentallas.dsrom.capture-priced-terminal.v1',candidate=r['candidate'],
        source_commit=r['source_commit'],terminal_status=r['status'],results=summaries,
        SS_full_available_ps=2*2500/3-60,SS_after_macro_clkQ_ps=r['remaining_after_macro_clkQ_ps'],
        elapsed_s=sum(x['elapsed_s'] for x in r['runs']),child_resources=r['child_resources'],
        physical_admission=False,installed_CTS_not_a_prebuild_requirement=True,
        blocking_source_fact='Raw STA reports capture data slew beyond320ps source model limits. A same-input source-table report_dcalc witness disagrees with propagated slew; this is an unresolved timing-model diagnostic, NOT a proven hardware/physical limitation. Positive slack and extrapolated subtotal are not admitted closure bounds.',
        next_construction='Reconcile source waveform/delay-calculator behavior before inferring capture sizing. Independently construct finite clock/reset branches from actual pin loads and PG cuts; bind parent cfg/stream drivers and return receivers with real mapped cells. No RTL repair or extra edge inferred from tool/preflight failures.',
        original_failures=['failed_r1','failed_r2','failed_r3'],no_arithmetic_source_change=True,no_new_pipeline_edge=True,
        same_loaded_source_table_diagnostic=observed)
    (out/'priced_terminal.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    receipts={str(p.relative_to(out)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}
    (out/'terminal_hashes.json').write_text(json.dumps(receipts,indent=2,sort_keys=True)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,default=OUT);a=p.parse_args()
    print(json.dumps(archive(a.work,a.output),indent=2))
