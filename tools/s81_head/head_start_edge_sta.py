#!/usr/bin/env python3
"""Extract per-role START q-to-D delays from the exact routed prototype RC.

Emit for a cached SPEF by default. Explicit --guides diagnostic mode rebuilds
GRT RC and labels that limitation. The raw single-cycle STA slack is INFO:
count-aligned START must price its measured integer sampling step separately.
"""
import argparse,json,math
from pathlib import Path


def emit(roles,overlay,corner,odb,spef=None,guides=None,out='/audit/edges.tsv'):
    if bool(spef)==bool(guides):raise ValueError('choose cached SPEF or explicit diagnostic guide reconstruction')
    names=overlay['cell_names'];rows=[]
    for i,e in enumerate(roles['edges']):
        l=e['launch'];c=e['capture']
        if l['launch_signal_edge']!='fall' or l['clock_edge']!='rise':raise ValueError('this actual source requires falling QN launched on positive clock')
        src=names[l['cell']]+'/'+l['pin'];sck=names[l['cell']]+'/'+l['clock_pin']
        if 'cell' in c:dst=names[c['cell']]+'/'+c['pin'];ck=names[c['cell']]+'/'+c['clock_pin'];ce=c['clock_edge']
        else:dst=c['port'];ck='NA';ce='NA'
        rows.append((i,src,sck,dst,ck,ce))
    sources=sorted({r[1] for r in rows});dpins=[r[3] for r in rows if r[4]!='NA'];dports=[r[3] for r in rows if r[4]=='NA'];n=len(rows)
    L=[f'foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_{corner}_nldm*.lib*] {{ read_liberty $f }}',f'read_db {{{odb}}}']
    if spef:L += [f'read_spef {{{spef}}}']
    else:L += [f'read_guides {{{guides}}}','source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl','estimate_parasitics -global_routing']
    L += ['create_clock -name dck -period 833 [get_ports root]','set_propagated_clock [get_clocks dck]',
          'set_clock_uncertainty -setup 60 [get_clocks dck]','set_clock_uncertainty -hold 25 [get_clocks dck]',
          'set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]',
          'set_output_delay -clock dck -max 0 [get_ports {'+' '.join(dports)+'}]',
          'set_output_delay -clock dck -min 0 [get_ports {'+' '.join(dports)+'}]',
          'proc ep_crpr {pe} { if {![catch {set c [$pe check_crpr]}]} { return [expr {abs($c)*1e12}] }; return NA }',
          f'set out [open {{{out}}} w]',
          'puts $out {mode\tid\tsource_q\ttarget\tq_arrival_ps\tdata_arrival_ps\tq_to_d_ps\tsource_clock_ps\tclk_to_q_ps\tcapture_clock_insertion_ps\tcrpr_ps\tslack_info_ps}',
          'array set eid {}; array set src {}; array set sck {}; array set cck {}; array set cedge {}']
    for i,s,sc,d,dc,ce in rows:L += [f'set eid({d}) {i}; set src({d}) {s}; set sck({d}) {sc}; set cck({d}) {dc}; set cedge({d}) {ce}']
    L += ['set sources [get_pins {'+' '.join(sources)+'}]',
          'set dests [concat [get_pins {'+' '.join(dpins)+'}] [get_ports {'+' '.join(dports)+'}]]',
          'foreach mode {max min} {',
          f' if {{[catch {{set paths [find_timing_paths -fall_from $sources -rise_to $dests -path_delay $mode -unconstrained -group_path_count {n} -endpoint_path_count 1]}}]}} {{set paths [find_timing_paths -fall_from $sources -rise_to $dests -path_delay $mode -unconstrained -group_count {n} -endpoint_count 1]}}',
          ' array unset seen; array set seen {}',
          ' foreach p $paths {',
          '  set dst [get_full_name [get_property $p endpoint]]; if {![info exists eid($dst)]} {error "unexpected timing endpoint $dst"}',
          '  if {[info exists seen($dst)]} {error "duplicate endpoint $dst"}; set seen($dst) 1',
          '  set first [get_full_name [get_property $p startpoint]]; if {$first ne $src($dst)} {error "unexpected launch $first -> $dst"}',
          '  set qa NA; set da NA; foreach pt [get_property $p points] {set pin [get_full_name [get_property $pt pin]]; if {$pin eq $first} {set qa [get_property $pt arrival]}; if {$pin eq $dst} {set da [get_property $pt arrival]}}',
          '  if {$qa eq "NA" || $da eq "NA"} {error "missing exact path point $dst"}',
          '  set ca [get_property [get_pins $sck($dst)] arrival_${mode}_rise]; if {$ca eq ""} {error "missing source clock arrival"}',
          '  set cap NA; if {$cck($dst) ne "NA"} {set cap [get_property [get_pins $cck($dst)] arrival_${mode}_$cedge($dst)]; if {$cap eq ""} {error "missing capture clock arrival"}; if {$cedge($dst) eq "fall"} {set cap [expr {$cap-416.5}]}}',
          '  puts $out "$mode\\t$eid($dst)\\t$first\\t$dst\\t$qa\\t$da\\t[expr {$da-$qa}]\\t$ca\\t[expr {$qa-$ca}]\\t$cap\\t[ep_crpr $p]\\t[get_property $p slack]"',
          ' }',f' if {{[array size seen]!={n}}} {{error "START endpoint coverage [array size seen] != {n}"}}',
          '}', 'close $out','puts HEAD_START_EDGE_DATA_DONE']
    return '\n'.join(L)+'\n'


def parse(roles,files,source_mode):
    out={};errs=[]
    for corner,path in files.items():
        lines=Path(path).read_text().splitlines();by={}
        for line in lines[1:]:
            z=line.split('\t')
            if len(z)!=12:raise ValueError('malformed data row')
            mode,i,src,dst=z[:4];i=int(i)
            if i>=len(roles['edges']) or mode not in ('min','max'):raise ValueError('unexpected edge/mode')
            v={k:(None if x=='NA' else float(x)) for k,x in zip(['q_arrival_ps','data_arrival_ps','q_to_d_ps','source_clock_ps','clk_to_q_ps','capture_clock_insertion_ps','crpr_ps','slack_info_ps'],z[4:])}
            if any(x is not None and not math.isfinite(x) for x in v.values()):raise ValueError('non-finite actual timing value')
            if (i,mode) in by:raise ValueError('duplicate edge/mode')
            by[i,mode]=dict(source_q=src,target=dst,**v)
        if len(by)!=2*len(roles['edges']):raise ValueError('incomplete routed edge timing')
        rs=[]
        for i,e in enumerate(roles['edges']):
            lo=by[i,'min'];hi=by[i,'max']
            if min(lo['q_to_d_ps'],lo['clk_to_q_ps'])<0 or lo['q_to_d_ps']>hi['q_to_d_ps']+1e-3:errs.append(dict(corner=corner,port=e['port'],error='negative or reversed data delay'))
            rs.append(dict(port=e['port'],src_stage=e['src_stage'],dst_stage=e.get('dst_stage'),dst_part=e.get('dst_part'),kind=e['kind'],capture_edge=e['capture']['clock_edge'],min=lo,max=hi))
        out[corner]=rs
    return dict(schema='ot_head_start_edge_data/1',corners=out,errors=errs,source_mode=source_mode,
        summary=dict(edges=len(roles['edges']),corners=list(out),max_q_to_d_ps={c:max(x['max']['q_to_d_ps'] for x in rs) for c,rs in out.items()},
            max_clock_to_d_ps={c:max(x['max']['data_arrival_ps']-x['max']['source_clock_ps'] for x in rs) for c,rs in out.items()}),
        scope='actual per-role delay receipt; raw single-cycle slack INFO, shared OCV/droop/calibrated START J audit and partition capture views still required')


def main():
    a=argparse.ArgumentParser(description=__doc__);sub=a.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('emit');x.add_argument('--roles',required=True);x.add_argument('--overlay',required=True);x.add_argument('--corner',choices=['TT','FF'],required=True);x.add_argument('--odb',required=True);x.add_argument('--spef');x.add_argument('--guides');x.add_argument('--out',required=True);x.add_argument('--data-out',required=True)
    x=sub.add_parser('parse');x.add_argument('--roles',required=True);x.add_argument('--TT',required=True);x.add_argument('--FF',required=True);x.add_argument('--source-mode',choices=['cached_SPEF','diagnostic_reconstructed_guides'],required=True);x.add_argument('--out',required=True)
    z=a.parse_args();roles=json.load(open(z.roles))
    if z.cmd=='emit':Path(z.out).write_text(emit(roles,json.load(open(z.overlay)),z.corner,z.odb,z.spef,z.guides,z.data_out))
    else:
        d=parse(roles,{'TT':z.TT,'FF':z.FF},z.source_mode);Path(z.out).write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(d['summary']));return bool(d['errors'])
if __name__=='__main__':raise SystemExit(main())
