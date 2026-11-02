"""Optional original-state data/forwarded-K observer. No timing constraints or verdict changes."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
HEADER='export data_bit delay status data_ff actual_startpoint actual_endpoint launch_clock_pin launch_clock launch_source_port launch_edge data_arrival_ps native_std_slack_ps native_std_target_clock forwarded_source_port k_rise_early_ps k_rise_late_ps k_fall_early_ps k_fall_late_ps uncredited_relative_bound_ps'.split()

def literal(value):
    if not isinstance(value,str) or not value or any(c in value for c in '{}\n\r\t'):
        raise ValueError('exact Tcl literal required')
    return '{'+value+'}'

def request(sdc,netlist,module):
    text=Path(sdc).read_text();net=Path(netlist).read_text()
    clock=re.findall(r'create_clock -name clk -period (\S+) \[get_ports \{([^}]+)\}\]',text)
    if len(clock)!=1: raise ValueError('one explicit multi-source clk declaration required')
    roots=clock[0][1].split()
    if len(set(roots))!=len(roots): raise ValueError('duplicate actual root')
    body=re.search(r'\bmodule\s+'+re.escape(module)+r'\s*\(.*?\bendmodule\b',net,re.S)
    if not body: raise ValueError('actual top module missing')
    exports=[]
    for name,source in re.findall(r'create_generated_clock -name (fclk_out_\w+) -master_clock clk -source \[get_ports (\w+)\] -divide_by 1 \[get_ports \1\]',text):
        bus=name[len('fclk_out_'):]
        decl=re.findall(r'\boutput\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s+)?'+re.escape(bus)+r'\s*;',body[0])
        if len(decl)!=1 or source not in roots: raise ValueError('missing/ambiguous output or foreign forwarded root')
        hi,lo=(int(x or 0) for x in decl[0]);bits=[f'{bus}[{i}]' for i in range(min(hi,lo),max(hi,lo)+1)]
        exports.append(dict(export=name,source=source,bits=bits))
    if not exports: raise ValueError('no actual forwarded exports')
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return dict(schema='opentallas.forwarded_export_observer.request.v1',master_clock='clk',native_output_clock='vclk',roots=roots,exports=exports,period_ps=float(clock[0][0]),sdc=dict(path=str(sdc),sha256=sha(sdc)),netlist=dict(path=str(netlist),sha256=sha(netlist)),module=module,phase='ORIGINAL_CONSTRAINED_STD_BEFORE_ZERO_UNC',qualification='NOT_ASSERTED')

def emit(req,out_dir,limit=0,enabled=False,helpers=True):
    if not enabled:return '# Forwarded export observer OFF; no timing queries.\n'
    if not isinstance(limit,int) or limit<0:raise ValueError('nonnegative bounded query budget required')
    roots=req['roots'];exports=req['exports']
    if not roots or len(set(roots))!=len(roots):raise ValueError('explicit unique actual roots required')
    seen=set()
    for exp in exports:
        if exp['source'] not in roots or not exp['bits']:raise ValueError('foreign root/empty export')
        for bit in exp['bits']:
            if bit in seen:raise ValueError('duplicate data bit')
            seen.add(bit);literal(bit)
    setup=''
    if helpers:
        setup='set ::ot_ps_lib_only 1\n'+(HERE/'pair_skew.tcl').read_text()+'\nunset ::ot_ps_lib_only\n'
    rows='[list '+' '.join('[list '+literal(e['export'])+' '+literal(e['source'])+' [list '+' '.join(literal(b) for b in e['bits'])+']]' for e in exports)+']'
    return setup+(r'''
# Optional observer only. Caller supplies original loaded SDC/libs/ODB/RC.
# Never call after zero_unc, clock deletion, or forwarded export ETM mutation.
set ::fx_roots [list @ROOTS@]
set ::fx_exports @EXPORTS@
set ::fx_out @OUT@
set ::fx_limit @LIMIT@
set ::fx_clock @CLOCK@
set ::fx_native_target @TARGET@
proc fx_exact {name} {return "^[regsub -all {[][(){}.*+?^$|\\]} $name {\\&}]$"}
proc fx_port {name {vector0 0}} {
  set names [list $name]; if {$vector0} {lappend names "${name}\[0\]"}
  set found {}
  foreach n $names {
    foreach p [get_ports -quiet -regexp [fx_exact $n]] {if {[get_full_name $p] eq $n} {lappend found $p}}
  }
  if {[llength $found]!=1} {error "missing/nonunique exact port $name"}
  return [lindex $found 0]
}
proc fx_root {tag which} {
  # Existing source-by-path resolver validates actual clock/source/edge membership.
  if {[lindex $tag 3] ne $::fx_clock} {error "foreign launch clock"}
  set row [ot_ps_source_from_tag $tag $::fx_clock $which]
  if {[lindex $row 0] ni $::fx_roots} {error "foreign actual path root"}
  return $row
}
proc fx_k {port source edge which} {
  set pin [sta::get_port_pin $port];set observations {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set it [$vertex path_iterator $edge $which]
    while {[$it has_next]} {
      set path [$it next];set tag [$path tag]
      if {[lindex $tag 3] ne $::fx_clock || [lindex $tag 4] ne [expr {$edge eq "rise" ? "^" : "v"}] || [string first "(clock prop)" $tag]<0} continue
      lappend observations [list [expr {[$path arrival]*1e12}] $tag]
    }
    $it finish
  }
  set values {}
  foreach observation $observations {
    lassign $observation value tag
    set root [fx_root $tag $which]
    if {[lindex $root 0] ne $source} {error "forwarded K physical source differs from declared source"}
    if {[lsearch -real $values $value]<0} {lappend values $value}
  }
  if {[llength $values]!=1} {error "missing/nonunique actual K clock path"}
  # Absolute, unwrapped edge arrival. No half-cycle folding or new CPPR credit.
  return [lindex $values 0]
}
proc fx_data {port bit delay} {
  set paths [find_timing_paths -to $port -path_delay $delay -group_path_count 1 -endpoint_path_count 1]
  if {![llength $paths]} {return [list NO_PATH]}
  set pe [lindex $paths 0]
  set start [get_property $pe startpoint];set sp [get_full_name $start]
  set end [get_full_name [get_property $pe endpoint]]
  set points [get_property $pe points]
  if {$end ne $bit || ![llength $points]} {error "actual data endpoint mismatch"}
  set arrival [get_property [lindex $points end] arrival]
  set slack [get_property $pe slack]
  set target [get_full_name [$pe target_clk]]
  set tag [[$pe path] tag]
  set owners [get_cells -quiet -of_objects $start]
  if {[llength $owners]!=1} {error "data path is not launched by a unique actual FF"}
  set ff [get_full_name [lindex $owners 0]]
  if {![dict exists $::fx_ffclocks $ff] || [llength [dict get $::fx_ffclocks $ff]]!=1} {error "missing/nonunique actual launch clock pin"}
  set cp [lindex [dict get $::fx_ffclocks $ff] 0]
  unset paths pe points
  if {$target ne $::fx_native_target} {error "native STD target clock changed"}
  lassign [fx_root $tag $delay] source source_edge source_insertion
  foreach value [list $arrival $slack] {if {![string is double -strict $value] || [regexp -nocase {inf|nan} $value]} {error "nonfinite native data timing"}}
  return [list OK $ff $sp $end $cp $::fx_clock $source $source_edge $arrival $slack $target]
}
proc fx_run {} {
  file mkdir $::fx_out
  write_sdc "$::fx_out/original_state.sdc"
  set clocks [get_clocks -quiet $::fx_clock]
  if {[llength $clocks]!=1} {error "actual master clock missing"}
  set roots [lsort [lmap p [get_property [lindex $clocks 0] sources] {get_full_name $p}]]
  if {$roots ne [lsort $::fx_roots]} {error "actual full root set differs from request"}
  set ::ot_ps_method tag;set ::fx_ffclocks {}
  foreach cp [all_registers -clock_pins] {
    set owner [get_cells -quiet -of_objects $cp]
    if {[llength $owner]==1} {dict lappend ::fx_ffclocks [get_full_name [lindex $owner 0]] [get_full_name $cp]}
  }
  # Complete native timing update before any path-tag/arrival reads.
  sta::worst_slack_cmd max;sta::worst_slack_cmd min
  set fh [open "$::fx_out/data_k.tsv" w]
  puts $fh [join {@HEADER@} \t]
  set queries 0;set errors 0;set missing 0;set limited 0;set total 0
  foreach export $::fx_exports {
    lassign $export name source bits
    set kp [fx_port $name 1]
    set generated [get_clocks -quiet $name]
    if {[llength $generated]!=1 || ![[lindex $generated 0] is_generated]} {error "declared generated export clock missing"}
    set master [lindex $clocks 0];set gc [lindex $generated 0]
    if {abs([$gc period]-[$master period])>1e-6*[$master period] || [$gc waveform] ne [$master waveform]} {error "generated export period/edge changed"}
    set kvals [list [fx_k $kp $source rise min] [fx_k $kp $source rise max] [fx_k $kp $source fall min] [fx_k $kp $source fall max]]
    foreach bit $bits {
      set port [fx_port $bit]
      foreach delay {min max} {
        incr total
        if {$queries >= $::fx_limit} {set row [list LIMIT];incr limited} else {
          incr queries
          if {[catch {set row [fx_data $port $bit $delay]} reason]} {
            set row [list ERROR];incr errors
            puts "OT_FWD_EXPORT_ERROR $name $bit $delay [string map [list \n { } \t { }] $reason]"
          } elseif {[lindex $row 0] ne "OK"} {incr missing}
        }
        if {[lindex $row 0] eq "OK"} {
          set bound [expr {[lindex $row 8]-[lindex $kvals [expr {$delay eq "min" ? 1 : 0}]]}]
        } else {set bound ""}
        while {[llength $row]<11} {lappend row ""}
        puts $fh [join [concat [list $name $bit $delay] $row [list $source] $kvals [list $bound]] \t]
      }
    }
  }
  close $fh
  set fh [open "$::fx_out/counts.tsv" w]
  foreach {key value} [list phase ORIGINAL_CONSTRAINED_STD_BEFORE_ZERO_UNC queries $queries rows $total errors $errors missing $missing limited $limited clock_sources [llength $roots] native_engine_cppr_enabled [sta::crpr_enabled] additional_CPPR_credit NONE bounds UNCORRELATED_CONSERVATIVE_NOT_NATIVE_FWD_STD_SLACK] {puts $fh "$key\t$value"}
  close $fh
  puts "OT_FWD_EXPORT_COMPLETE"
}
set fx_had_method [info exists ::ot_ps_method]
if {$fx_had_method} {set fx_saved_method $::ot_ps_method}
if {[catch {fx_run} fx_failure]} {puts "OT_FWD_EXPORT_FAILED [string map [list \n { } \t { }] $fx_failure]"}
if {$fx_had_method} {set ::ot_ps_method $fx_saved_method} else {unset -nocomplain ::ot_ps_method}
'''.replace('@ROOTS@',' '.join(literal(r) for r in roots)).replace('@EXPORTS@',rows)
       .replace('@OUT@',literal(str(out_dir))).replace('@LIMIT@',str(limit))
       .replace('@CLOCK@',literal(req['master_clock'])).replace('@TARGET@',literal(req['native_output_clock']))
       .replace('@HEADER@',' '.join(HEADER)))

def validate(req,folder,log):
    folder=Path(folder);lines=Path(log).read_text().splitlines()
    if 'OT_FWD_EXPORT_COMPLETE' not in lines:raise ValueError('incomplete actual observer')
    counts=dict(line.split('\t') for line in (folder/'counts.tsv').read_text().splitlines())
    if counts.get('phase')!='ORIGINAL_CONSTRAINED_STD_BEFORE_ZERO_UNC' or any(int(counts[x]) for x in ('errors','missing','limited')):raise ValueError('missing/error/limited actual witness')
    with (folder/'data_k.tsv').open() as f:
        reader=csv.DictReader(f,delimiter='\t')
        if reader.fieldnames!=HEADER:raise ValueError('wrong witness columns')
        rows=list(reader)
    expected={(e['export'],b,d):e['source'] for e in req['exports'] for b in e['bits'] for d in ('min','max')}
    seen=set()
    for r in rows:
        key=(r['export'],r['data_bit'],r['delay'])
        if key not in expected or key in seen or r['status']!='OK':raise ValueError('missing/duplicate/nonexact bit path')
        seen.add(key)
        if r['launch_clock']!=req['master_clock'] or r['launch_source_port'] not in req['roots'] or r['forwarded_source_port']!=expected[key] or r['actual_endpoint']!=r['data_bit'] or r['native_std_target_clock']!=req['native_output_clock'] or r['launch_edge'] not in ('rise','fall'):raise ValueError('foreign root/clock or wrong actual bit identity')
        for name in ('data_arrival_ps','native_std_slack_ps','k_rise_early_ps','k_rise_late_ps','k_fall_early_ps','k_fall_late_ps','uncredited_relative_bound_ps'):
            if not math.isfinite(float(r[name])):raise ValueError('nonfinite witness')
        if not all(r[name] for name in ('data_ff','actual_startpoint','launch_clock_pin')):raise ValueError('missing actual FF identity')
        if float(r['k_rise_early_ps'])>float(r['k_rise_late_ps']) or float(r['k_fall_early_ps'])>float(r['k_fall_late_ps']):raise ValueError('reversed K interval')
        k=float(r['k_rise_late_ps'] if r['delay']=='min' else r['k_rise_early_ps'])
        if abs(float(r['uncredited_relative_bound_ps'])-(float(r['data_arrival_ps'])-k))>1e-6:raise ValueError('invalid uncredited bound')
    if seen!=set(expected):raise ValueError('incomplete all-bit witness')
    state=folder/'original_state.sdc'
    if not state.is_file():raise ValueError('missing original constrained state snapshot')
    return dict(original_state_sha256=hashlib.sha256(state.read_bytes()).hexdigest(),status='COMPLETE_OBSERVATION',qualification='NOT_ASSERTED',parent_or_link_coverage='NOT_ASSERTED',bits=len(rows)//2,rows=len(rows),actual_launch_roots=sorted({r['launch_source_port'] for r in rows}),bounds='UNCORRELATED_CONSERVATIVE_NO_ADDITIONAL_CPPR',native_STD_reference=req['native_output_clock'],native_engine_cppr_enabled=counts['native_engine_cppr_enabled'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sdc',required=True);p.add_argument('--netlist',required=True);p.add_argument('--module',required=True);p.add_argument('--out',required=True);p.add_argument('--out-dir',required=True);p.add_argument('--enable',action='store_true');p.add_argument('--query-limit',type=int,default=0)
    a=p.parse_args();r=request(a.sdc,a.netlist,a.module);Path(a.out).write_text(emit(r,a.out_dir,a.query_limit,a.enable));Path(a.out+'.request.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
