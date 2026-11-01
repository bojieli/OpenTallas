#!/usr/bin/env python3
"""Export exact nested core IO-hold evidence from a routed parent and real child views.

parent_core_hold.py --plan PLAN --parent-kit KIT --parent-base RESULTS_BASE
  --receiver u_r0.u_bs0 --receiver-kit CORE_KIT --receiver-base CORE_RESULTS
  --expand u_s0.cfg=CFG7_RESULTS --out OUT [--mem 32]

Every expanded view must contain actual 6_final.v/SPEF. The existing die_sta
stitcher joins their real port RC to the real parent RC; no ideal seam, budget
cell, ETM-only sender or estimated SPEF is introduced. The output die_sta.json
is consumed by io_hold_parent; parent_receipt.json is that consumer's verdict.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta as D
import io_hold_parent as I
import io_hold_qualification as Q
import schema as S
import signoff as SO


def tq(s):
    s = str(s)
    if any(x in s for x in ('{', '}', '\n')):
        raise ValueError('unsupported Tcl identifier/path: ' + s)
    return '{' + s + '}'


def required_bits(base, policy):
    ports = D.port_dirs(Path(base) / '6_final.v')
    result = {}
    for name in policy['input_ports']:
        if name not in ports or ports[name][0] != 'input':
            raise ValueError('option-A input absent from actual receiver: ' + name)
        _, msb, lsb = ports[name]
        result[name] = ([name] if msb is None else
                        [f'{name}[{b}]' for b in range(min(msb, lsb), max(msb, lsb) + 1)])
    return result


def real_view(base):
    v = Q.view_snapshot(base)
    if v['kind'] != 'real' or not v.get('spef_sha256'):
        raise ValueError('actual routed V/SPEF required: ' + str(base))
    return v


def parse_corner(path, bits, receiver, exit_code=0):
    data, pairs, errors = {}, {}, []
    for line in Path(path).read_text().splitlines() if Path(path).is_file() else []:
        f = line.split('\t')
        if f[0] == 'B' and len(f) == 7:
            bit, pin, start, end = f[1:5]
            if pin != receiver + '/' + bit or not end.startswith(receiver + '/'):
                errors.append('wrong receiver witness: ' + bit)
                continue
            try:
                slack, arrival = map(float, f[5:])
                if not all(map(math.isfinite, (slack, arrival))): raise ValueError()
            except ValueError:
                errors.append('nonfinite data witness: ' + bit); continue
            data.setdefault(bit, []).append(dict(receiver_pin=pin, start=start, end=end,
                                                 slack_ps=slack, capture_data_arrival_ps=arrival))
        elif f[0] == 'P' and len(f) == 13:
            bit, launch, capture = f[1:4]
            try:
                setup, sc, hold, hc = map(float, f[4:8])
                if not all(map(math.isfinite, (setup, hold, sc, hc))): raise ValueError()
            except ValueError:
                errors.append('nonfinite pair: ' + bit); continue
            if not math.isfinite(float(f[12])) or not 0 <= float(f[12]) <= SO.PAIR_VERIFY_TOL_PS:
                errors.append('clock/path CPPR verification mismatch: ' + bit); continue
            if not capture.startswith(receiver + '/'):
                errors.append('wrong capture pair: ' + bit); continue
            pairs.setdefault(bit, []).append(dict(launch=launch, capture=capture, setup_ps=setup,
                hold_ps=hold, setup_cppr_ps=sc, hold_cppr_ps=hc, launch_clock=f[8], capture_clock=f[9], launch_clock_pin=f[10], capture_clock_pin=f[11], verify_ps=float(f[12])))
        elif f[0] == 'E':
            errors.append('\t'.join(f[1:]))
    expected = {x for group in bits.values() for x in group}
    for bit in sorted(expected):
        if not data.get(bit): errors.append('missing timed receiver bit ' + bit)
        if not pairs.get(bit): errors.append('missing exact related pair ' + bit)
    if (set(data) | set(pairs)) - expected:
        errors.append('unexpected receiver bits in timing output')
    return dict(exit=exit_code if exit_code else (1 if errors else 0), bit_paths=data,
                bit_pairs=pairs, errors=errors, coverage=dict(expected=len(expected),
                timed=len(expected & set(data)), paired=len(expected & set(pairs))))


# PathEnd objects are copied before clock/arrival queries, which invalidate them
# in the pinned OpenSTA. Data slack retains the actual parent 0/25 policy; clock
# pair measurement zeroes uncertainty afterwards, as pair_skew.tcl requires.
MEASURE = r'''
proc ph_pin {name} {
  set q [get_pins -hierarchical -quiet -regexp "^[regsub -all {[][(){}.*+?^$|\\]} $name {\\&}]$"]
  if {[llength $q] != 1 || [get_full_name [lindex $q 0]] ne $name} {
    error "missing/nonunique exact pin $name"
  }
  return [lindex $q 0]
}
proc ph_paths {pin} {
  if {[catch {set pes [find_timing_paths -through $pin -path_delay min -group_path_count 100000 -endpoint_path_count 1]}]} {
    set pes [find_timing_paths -through $pin -path_delay min -group_count 100000 -endpoint_count 1]
  }
  set rows {}
  foreach pe $pes {
    if {![$pe is_check] || [$pe is_latch_check]} continue
    set end [get_full_name [get_property $pe endpoint]]
    if {![string match "$::ph_receiver/*" $end]} continue
    set start [get_property $pe startpoint]
    set owner [get_cells -quiet -of_objects $start]
    if {[llength $owner] && [get_property [lindex $owner 0] ref_name] in $::ph_opaque} {
      error "unexpanded composed sender has no real minimum path: [get_full_name $start]"
    }
    set points [get_property $pe points]
    if {![llength $points]} continue
    lappend rows [list [get_full_name [get_property $pe startpoint]] $end \
      [get_property $pe slack] [get_property [lindex $points end] arrival]]
  }
  return $rows
}
set ph_cells [get_cells -hierarchical -quiet -regexp "^[regsub -all {[][(){}.*+?^$|\\]} $ph_receiver {\\&}]$"]
if {[llength $ph_cells] != 1 || [get_property [lindex $ph_cells 0] ref_name] ne $ph_master} {
  error "receiver instance/master mismatch: $ph_receiver / $ph_master"
}
sta::worst_slack_cmd max; sta::worst_slack_cmd min
set ph_pair_inputs {}
foreach bit $ph_bits {
  set name "$ph_receiver/$bit"
  if {[catch {set p [ph_pin $name]} why]} {puts $ph_out "E\t$why";continue}
  set rows [ph_paths $p]
  foreach row $rows {puts $ph_out [join [concat [list B $bit $name] $row] \t]}
  # Structural launch/capture enumeration is exact, not a nearest-root or a
  # worst-path-clock proxy. R2 first captures stop the traversal naturally.
  set launches [get_fanin -to $p -flat -startpoints_only]
  set captures [get_fanout -from $p -flat -endpoints_only]
  foreach l $launches {foreach c $captures {
    set cn [get_full_name $c]
    if {[string match "$ph_receiver/*" $cn]} {
      lappend ph_pair_inputs [list $bit [get_full_name $l] $cn]
    }
  }}
}
ot_ps_zero_unc
set ::ot_ps_method tag
sta::worst_slack_cmd max; sta::worst_slack_cmd min
ot_ps_regs
foreach row [lsort -unique $ph_pair_inputs] {
  lassign $row bit ln cn
  set l [ph_pin $ln];set c [ph_pin $cn]
  set launch [ot_ps_clock_role $l clkq]
  set setup [ot_ps_clock_role $c setup];set hold [ot_ps_clock_role $c hold]
  if {[llength $launch] != 2 || [llength $setup] != 2 || [llength $hold] != 2} {
    puts $ph_out "E\tunresolved actual clock role $bit $ln $cn";continue
  }
  set lr [ot_ps_add_clock {*}$launch];set sr [ot_ps_add_clock {*}$setup];set hr [ot_ps_add_clock {*}$hold]
  if {$lr eq "" || $sr eq "" || $hr eq ""} {puts $ph_out "E\tmissing clock arrival $bit";continue}
  set lc [lindex [dict get $::ot_ps_R $lr] 1]
  set sc [lindex [dict get $::ot_ps_R $sr] 1];set hc [lindex [dict get $::ot_ps_R $hr] 1]
  if {$lc ne $sc || $lc ne $hc || abs([get_property [get_clocks $lc] period] - 833.0) > 0.001} {
    puts $ph_out "E\tunrelated/non833 clock pair $bit";continue
  }
  set s [ot_ps_path $lr $cn max];set h [ot_ps_path $lr $cn min]
  if {[llength $s] != 2 || [llength $h] != 2} {puts $ph_out "E\tuntimed exact pair $bit $ln $cn";continue}
  set la [dict get $::ot_ps_R $lr];set sa [dict get $::ot_ps_R $sr];set ha [dict get $::ot_ps_R $hr]
  set verify [expr {max(abs([lindex $s 0] - ([lindex $sa 3]-[lindex $la 2]+[lindex $s 1])), abs([lindex $h 0] - ([lindex $ha 2]-[lindex $la 3]-[lindex $h 1])))}]
  puts $ph_out [join [list P $bit $ln $cn {*}$s {*}$h $lc $sc [lindex $la 0] [lindex $ha 0] $verify] \t]
}
close $ph_out
'''


def make_session(corner, parent, top, expanded, stitch, sdc, receiver, master, bits, out):
    # This reader uses the parent's exact ORFS library selection. Expanded real
    # designs must not also be loaded as opaque ETM Liberty cells.
    prefix = SO.EXACT_TIMING_LIBRARIES_TCL + '\n' + r'''
proc ph_cells_in_lib {file} {
  set f [open $file rb];set text [read $f];close $f
  if {[string match *.gz $file]} {set text [zlib gunzip $text]}
  set cells {};foreach {full name} [regexp -all -inline {\mcell\s*\(\s*"?([^\s")]+)"?\s*\)} $text] {lappend cells $name}
  return $cells
}
set ph_loaded {};set ::ph_opaque {}
foreach file [ot_lib_resolve @CORNER@ /work/config.mk] {
  set names [ph_cells_in_lib $file];set overlap {}
  foreach name $names {if {$name in $ph_expanded} {lappend overlap $name}}
  if {[llength $overlap]} {
    if {[llength $names] != [llength $overlap]} {error "mixed ETM library cannot be safely excluded: $file"}
    continue
  }
  set lf [open $file rb];set lt [read $lf];close $lf
  if {[string match *.gz $file]} {set lt [zlib gunzip $lt]}
  if {[regexp {\m(?:min|max)_clock_tree_path\M} $lt]} {set ::ph_opaque [concat $::ph_opaque $names]}
  read_liberty $file;lappend ph_loaded $file
}
'''.replace('@CORNER@', corner)
    lines = ['set ph_expanded ' + tq(' '.join(sorted(set(x['module'] for x in expanded.values())))), prefix]
    for v in {x['module']: x for x in expanded.values()}.values():
        lines.append('read_verilog ' + tq(Path(v['base']) / '6_final.v'))
    lines += ['read_verilog ' + tq(Path(parent) / '6_final.v'), 'link_design ' + tq(top)]
    for inst, sp in sorted(stitch['core'].items()): lines.append(f'read_spef -path {tq(inst)} {tq(sp)}')
    if stitch['parent']: lines.append('read_spef ' + tq(stitch['parent']))
    if stitch['seams']: lines.append('read_spef ' + tq(stitch['seams']))
    lines += ['read_sdc ' + tq(sdc)]
    if corner == 'FF' and (Path(out) / 'core_taps_ff.sdc').is_file():
        lines.append('read_sdc ' + tq(Path(out) / 'core_taps_ff.sdc'))
    lines += ['set_propagated_clock [all_clocks]', 'set sta_crpr_enabled 1',
              'proc so {args} {puts [join $args { }]}', SO.unc_policy_tcl('nominal'),
              'set ::ot_ps_lib_only 1', 'source ' + tq(Path(out) / 'pair_skew.tcl'),
              'set ph_receiver ' + tq(receiver), 'set ph_master ' + tq(master),
              'set ph_bits ' + tq(' '.join(b for names in bits.values() for b in names)),
              'set ph_out [open ' + tq(Path(out) / (corner + '.tsv')) + ' w]', MEASURE]
    return '\n'.join(lines) + '\n'


def assemble(corners, bits, receiver, expanded, parent_module):
    result = {}
    for corner, raw in corners.items():
        groups = {}
        for bus, names in bits.items():
            for bit in names:
                paths = raw['bit_paths'].get(bit, [])
                pairs = raw['bit_pairs'].get(bit, [])
                if not paths or not pairs: continue
                for path in paths:
                    owners = [i for i in expanded if path['start'].startswith(i + '/')]
                    source = max(owners, key=len) if owners else parent_module
                    group = groups.setdefault(f'{source}->{receiver}/{bus}', dict(paths=[], pairs=[], bits=set()))
                    group['paths'].append(path);group['pairs'] += pairs;group['bits'].add(bit)
        seams, pairskew = {}, {}
        for key, g in groups.items():
            w = min(g['paths'], key=lambda p:p['slack_ps'])
            seams[key] = dict(min=dict(paths=len(g['bits']), worst=w['slack_ps'],
                neg=sum(p['slack_ps'] < 0 for p in g['paths']),
                tns=sum(min(0, p['slack_ps']) for p in g['paths']), start=w['start'], end=w['end'],
                arrival_ps=w['capture_data_arrival_ps'], witness=w), coverage=sorted(g['bits']))
            pairskew[key] = dict(n=len(g['pairs']), max_cppr=max(p['hold_ps'] for p in g['pairs']),
                min_cppr=min(p['setup_ps'] for p in g['pairs']), witnesses=g['pairs'])
        result[corner] = dict(exit=raw['exit'], seams=seams, pairskew=pairskew,
                              coverage=raw['coverage'], errors=raw['errors'])
    return result


def run(a):
    out = Path(a.out).resolve();out.mkdir(parents=True, exist_ok=False)
    parent, kit, receiver_base = map(lambda p:Path(p).resolve(), (a.parent_base,a.parent_kit,a.receiver_base))
    plan_path = Path(a.plan).resolve();P = S.Plan(S.load(plan_path), plan_path)
    policy = Q.kit_policy(dict(kit=a.receiver_kit, sdc_lint_ctx=str(Path(a.receiver_kit)/'sdc_lint.json')))
    if not policy or policy['die'] != P.name or policy['plan_sha256'] != Q.plan_digest(P.raw):
        raise ValueError('receiver option-A contract does not match the actual plan')
    master = D.module_of(receiver_base/'6_final.v')
    if master != policy['receiver_type']: raise ValueError('receiver master differs from its kit contract')
    expanded = {a.receiver: dict(base=str(receiver_base),module=master)}
    for value in a.expand:
        inst, sep, directory = value.partition('=')
        if not sep or inst in expanded: raise ValueError('duplicate/invalid --expand ' + value)
        base = Path(directory).resolve();expanded[inst]=dict(base=str(base),module=D.module_of(base/'6_final.v'))
    evidence = {D.module_of(parent/'6_final.v'): real_view(parent)}
    for v in expanded.values():
        snap = real_view(v['base'])
        if v['module'] in evidence and any(evidence[v['module']][k] != snap[k] for k in ('netlist_sha256','spef_sha256')):
            raise ValueError('different actual views for one hardened module')
        evidence[v['module']] = snap
    top = D.module_of(parent/'6_final.v');nl = D.read_verilog(parent/'6_final.v')[top]
    inst_mod = {inst:cell for cell,inst,_ in nl.insts}
    for inst,v in expanded.items():
        if inst_mod.get(inst) != v['module']:
            raise ValueError('exact structural parent receiver/sender instance mismatch: ' + inst)
    pdirs = {v['module']:D.port_dirs(Path(v['base'])/'6_final.v') for v in expanded.values()}
    ps = {i:str(Path(v['base'])/'6_final.spef') for i,v in expanded.items()}
    bits = required_bits(receiver_base, policy)
    net_of = {(inst,pin): net for net, ends in D.top_conns(nl,pdirs).items() for inst,pin,_ in ends}
    parent_nets = D._die_split(parent/'6_final.spef')
    for bit in [b for group in bits.values() for b in group]:
        if net_of.get((a.receiver,bit)) not in parent_nets:
            raise ValueError('actual parent routed port RC missing: ' + a.receiver + '/' + bit)
    seams, cores, parent_core, stats = D.write_stitch(nl,pdirs,ps,out/'stitch',die_spef=parent/'6_final.spef')
    if not seams or not stats['merged_die_nets']:
        raise ValueError('no actual parent port RC stitched; no ideal seam is permitted')
    shutil.copyfile(HERE/'pair_skew.tcl',out/'pair_skew.tcl')
    sdc = kit/'constraint.sdc'
    SO.copy_core_tap_overlay(sdc,out)
    st = dict(core=cores,parent=parent_core,seams=str(seams))
    mounts = {str(kit):'/work',str(out):str(out),str(parent):str(parent)}
    for v in expanded.values(): mounts[v['base']]=v['base']
    corners = {}
    for corner in ('TT','FF'):
        script = out/(corner+'.tcl')
        script.write_text(make_session(corner,parent,top,expanded,st,'/work/constraint.sdc',a.receiver,master,bits,out))
        command = [*a.docker.split(), 'run','--rm','--memory',str(a.mem)+'g','--memory-swap',str(a.mem)+'g']
        for host,container in mounts.items(): command += ['-v',host+':'+container+('' if host==str(out) else ':ro')]
        command += [a.image,SO.OPENROAD,'-no_init','-exit',str(script)]
        with (out/(corner+'.log')).open('w') as log:
            rc=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
        corners[corner]=parse_corner(out/(corner+'.tsv'),bits,a.receiver,rc)
    sta=dict(mode='flat',period_ps=833.0,unc_setup_ps=0.0,unc_hold_ps=25.0,spine='routed',
        instances={top:top,**{i:v['module'] for i,v in expanded.items()}}, view_evidence=evidence,
        corners=assemble(corners,bits,a.receiver,expanded,top), exporter=dict(schema='opentallas.parent_core_hold.v1',
        receiver=a.receiver,required_bits=bits,source_views=evidence,stitch=stats))
    (out/'die_sta.json').write_text(json.dumps(sta,indent=1)+'\n')
    receipt=I.check(P,sta,core_receiver=a.receiver,core_type=master,core_ports=policy['input_ports'])
    receipt['exporter']=sta['exporter']
    (out/'parent_receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print('PARENT_CORE_HOLD',receipt['verdict'],receipt['counts'])
    return {'PASS':0,'FAIL':1}.get(receipt['verdict'],2)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','parent-kit','parent-base','receiver','receiver-kit','receiver-base','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--expand',action='append',default=[])
    p.add_argument('--mem',type=int,default=32)
    p.add_argument('--docker',default='docker');p.add_argument('--image',default='openroad/orfs:asap7lock')
    a=p.parse_args()
    try:return run(a)
    except (ValueError,OSError) as e:p.exit(2,'PARENT_CORE_HOLD NOT_TIMED: '+str(e)+'\n')

if __name__=='__main__':sys.exit(main())
