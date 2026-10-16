"""Bounded CDC admission for one reviewed HBM/PHY SPSC FIFO implementation.

The primitive is source-fingerprinted. Parents are actually elaborated from their
pinned sources; every other crossing, including independent status synchronizers,
is refused. Derived payload endpoints and the actual mapped fanin are both
checked; register naming or a supplied graph receipt cannot grant admission.
No clock groups, false paths or same-domain timing exceptions are generated.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
import async_fifo_hierarchy_audit

SOURCES = {
    'rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv':
        ('e83b7120ff9c6b00eb1a7892bdfd0d4a8e9717fdf055f975f96fa879bb6c91b8',
         '3b85c58128cd8f8eeccf6e962c8cbe3672d56d3e10d044343307eb72a4712fe1'),
    'rtl/lib/ot_reset_sync.sv':
        ('489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd',),
}
RELATIONSHIP = dict(kind='hbm_phy_async_gray_fifo', stream_period_ps=833.333,
                    hbm_period_ps=1024.0)


def relationship(spec):
    if any(spec.get(k)for k in ('defines','hard_define','hard_defines','orfs_vars')):
        raise ValueError('async_gray_fifo unsupported build defines/ORFS overrides; source audit uses only SYNTHESIS')
    if (spec.get('clock') != 'multiple_cts_roots' or spec.get('kind') != 'tile'
            or spec.get('clock_relationship') != RELATIONSHIP):
        raise ValueError('async_gray_fifo requires explicit HBM PHY stream833.333/HBM1024 relationship and native leaf roots')
    if any(spec.get(k)for k in ('sdc_extra','boundary_tcl','pre_cts_extra','forwarded_clock')):
        raise ValueError('async_gray_fifo owns all clock/crossing constraints; custom hooks are unsupported')
    if set(spec.get('clock_entry_domains', {})) != {'core', 'hbm'}:
        raise ValueError('async_gray_fifo requires exactly core and hbm domains')
    if float(spec.get('route', {}).get('signoff_period_ps', 833.333)) != 833.333:
        raise ValueError('async_gray_fifo must retain actual stream833.333 primary period')


def load(spec, root):
    relationship(spec)
    if spec.get('children') or spec.get('macros'):
        raise ValueError('async_gray_fifo supports soft native leaves only; no inherited hard children/macros')
    declared = spec.get('sources', [])
    primitive = spec.get('top') == 'ot_hbm_svc_async_fifo'
    if (not set(SOURCES) <= set(declared) or len(set(declared)) != len(declared)
            or primitive and set(declared) != set(SOURCES)):
        raise ValueError('async_gray_fifo sources must include exactly one reviewed FIFO and reset synchronizer')
    actual_hashes = {}
    for path, expected in SOURCES.items():
        actual_hashes[path] = hashlib.sha256((Path(root) / path).read_bytes()).hexdigest()
        if actual_hashes[path] not in expected:
            raise ValueError(f'async_gray_fifo reviewed source changed: {path}')
    if not primitive:
        return parent_load(spec, root, actual_hashes)
    params = spec.get('params', {})
    if set(params) - {'WIDTH', 'DEPTH'} or type(params.get('WIDTH', 32)) is not int or params.get('WIDTH', 32) < 1:
        raise ValueError('async_gray_fifo unsupported primitive parameters')
    if type(params.get('DEPTH', 8)) is not int or params.get('DEPTH', 8) not in (4, 8):
        raise ValueError('async_gray_fifo requires bench-proved DEPTH4 or DEPTH8')
    ds = spec['clock_entry_domains']
    if (spec.get('clock_port') != 'rd_clk' or spec.get('clock_ports') != ['rd_clk', 'wr_clk']
            or ds['core'].get('ports') != ['rd_clk'] or ds['hbm'].get('ports') != ['wr_clk']):
        raise ValueError('async_gray_fifo initial primitive profile requires writer HBM / reader stream actual roots')
    expected = {
        'core': ({'rd_rst_n', 'rd_ready'}, {'rd_valid', 'rd_data', 'rd_underflow'}),
        'hbm': ({'wr_rst_n', 'wr_valid', 'wr_data'}, {'wr_ready', 'wr_overflow'}),
    }
    for name, (inputs, outputs) in expected.items():
        if set(ds[name].get('inputs', [])) != inputs or set(ds[name].get('outputs', [])) != outputs:
            raise ValueError(f'async_gray_fifo wrong actual IO ownership for {name}')
    return dict(source_sha256=actual_hashes, depth=params.get('DEPTH', 8), width=params.get('WIDTH', 32),
                fifo_instances=[dict(path='', writer_domain='hbm', reader_domain='core')],
                payload_consumer_public_nets={}, payload_output_ports={'':['rd_data']},
                payload_consumer_bits={},payload_output_bits={'':{str(i):(['rd_data','rd_data[0]']if params.get('WIDTH',32)==1 else['rd_data['+str(i)+']'])for i in range(params.get('WIDTH',32))}},primitive=True)


@lru_cache(maxsize=16)
def elaborate(root, top, sources, params):
    # The cache key includes every input byte hash. No caller-supplied graph or
    # receipt can grant admission in place of elaborating these actual sources.
    root=Path(root)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',top):
        raise ValueError('async_gray_fifo invalid elaboration top')
    paths=[]
    for path, digest in sources:
        p=(root/path).resolve()
        if not p.is_relative_to(root.resolve()) or not re.fullmatch(r'[A-Za-z0-9_./+-]+',str(p)):
            raise ValueError('async_gray_fifo unsafe source path')
        content=p.read_bytes()
        if hashlib.sha256(content).hexdigest()!=digest:
            raise ValueError('async_gray_fifo source changed during elaboration')
        if path not in SOURCES:
            for attribute in re.findall(rb'\(\*(.*?)\*\)',content,re.S):
                if re.search(rb'\b(?:src|hdlname)\s*=',attribute):
                    raise ValueError('async_gray_fifo reserved source metadata attributes are unsupported')
            if b'$paramod' in content:
                raise ValueError('async_gray_fifo reserved Yosys module identities are unsupported')
        if re.search(rb'`include\b',content):
            raise ValueError('async_gray_fifo includes require explicit source closure; unsupported in this profile')
        paths.append(str(p))
    param_args=''
    for name,value in params:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name) or type(value)is not int:
            raise ValueError('async_gray_fifo requires literal integer elaboration parameters')
        param_args+=f' -chparam {name} {value}'
    modern=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
    yosys=os.environ.get('YOSYS',str(modern)if modern.exists()else shutil.which('yosys'))
    if not yosys:raise ValueError('async_gray_fifo requires actual Yosys source elaboration')
    with tempfile.TemporaryDirectory(prefix='ot-async-gray-source-')as tmp:
        out=Path(tmp)/'hierarchy.json'
        command='read_verilog -sv -DSYNTHESIS '+' '.join(paths)
        command+=f'; hierarchy -check -top {top}'+param_args+f'; proc; opt; dffunmap; techmap; opt_expr; opt_clean; write_json {out}'
        run=subprocess.run([yosys,'-Q','-T','-p',command],capture_output=True,text=True)
        if run.returncode:raise ValueError('async_gray_fifo actual source elaboration failed: '+(run.stdout+run.stderr)[-1800:])
        document=json.loads(out.read_text())
    fifo_src=str((root/next(iter(SOURCES))).resolve())+':6.1-51.10'
    for name,module in document['modules'].items():
        claimed=module.get('attributes',{}).get('hdlname')=='ot_hbm_svc_async_fifo'
        if claimed and not async_fifo_hierarchy_audit.fifo_module_type(name):
            raise ValueError('async_gray_fifo untrusted FIFO source identity alias')
        if async_fifo_hierarchy_audit.fifo_module_type(name):
            if module.get('attributes',{}).get('src')!=fifo_src:
                raise ValueError('async_gray_fifo module identity does not bind reviewed source')
            values=module.get('parameter_default_values',{})
            if int(values.get('DEPTH','0'),2)not in (4,8) or int(values.get('WIDTH','0'),2)<1:
                raise ValueError('async_gray_fifo actual instance exceeds reviewed parameter shape')
    return document


def parent_load(spec,root,actual_hashes):
    actual_hashes.update({f:hashlib.sha256((Path(root)/f).read_bytes()).hexdigest()for f in spec['sources']})
    document=elaborate(str(Path(root).resolve()),spec['top'],tuple((f,actual_hashes[f])for f in spec['sources']),tuple(sorted(spec.get('params',{}).items())))
    roots={p:name for name,d in spec['clock_entry_domains'].items()for p in d['ports']}
    inputs={p:name for name,d in spec['clock_entry_domains'].items()for p in d['inputs']}
    outputs={p:name for name,d in spec['clock_entry_domains'].items()for p in d['outputs']}
    result=async_fifo_hierarchy_audit.audit(document,spec['top'],roots,inputs,outputs,require_bit_graph=True)
    if result['violations']:
        raise ValueError('async_gray_fifo source-domain audit REFUSE: '+json.dumps(result['violations'][:8],sort_keys=True))
    if not result['fifo_instances']:raise ValueError('async_gray_fifo requires actual reviewed FIFO instances')
    result.update(source_sha256=actual_hashes,primitive=False)
    return result


def bindings(record):
    def word(value):
        if value and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.$\[\]/]*',value):
            raise ValueError('async_gray_fifo unsupported mapped public identifier '+repr(value))
        return '{'+value+'}'
    fifo=' '.join(word(f['path'])+' {'+f['writer_domain']+' '+f['reader_domain']+'}'for f in record['fifo_instances'])
    msbs=' '.join(word(f['path'])+' '+str((int(f['parameters']['DEPTH'],2)if 'parameters'in f else record['depth']).bit_length()-1)for f in record['fifo_instances'])
    def exact_rows(key):
        return ' '.join(word(f['path'])+' {'+' '.join('{'+str(i)+'} {'+' '.join(word(v)for v in values)+'}'for i,values in record[key].get(f['path'],{}).items())+'}'for f in record['fifo_instances'])
    targets=exact_rows('payload_consumer_bits');outputs=exact_rows('payload_output_bits')
    return ('set ::ot_ag_fifo_domains [dict create '+fifo+']\n'
            +'set ::ot_ag_pointer_msb [dict create '+msbs+']\n'
            +'set ::ot_ag_targets [dict create '+targets+']\n'
            +'set ::ot_ag_outputs [dict create '+outputs+']\n'
            +'set ::ot_ag_primitive '+str(int(record['primitive']))+'\n')


def extend(body, spec, root):
    record = load(spec, root)
    crossing = '          if {!$::ot_ce_related_data} {error "OT_MULTI_ROOT: cross-domain data path $source -> $cell requires explicit related profile"}'
    if body.count(crossing) != 1:
        raise ValueError('async_gray_fifo actual crossing gate changed; revalidate extension')
    body = body.replace(crossing, '''          ot_ag_crossing $start $pin $source $cell $source_domain $expected
          continue''')
    output = '''      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }'''
    if body.count(output) != 1:
        raise ValueError('async_gray_fifo output gate changed; revalidate extension')
    body = body.replace(output, '''      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        if {[dict exists $cells $source] && [ot_ag_payload $start [get_ports $name] $source $name [dict get $cells $source] $domain]} {continue}
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }''')
    async_guard='    if {[dict exists $async_pins [get_full_name $pin]]} continue'
    if body.count(async_guard)!=1:raise ValueError('async pin classification changed; revalidate CDC guard')
    body=body.replace(async_guard,'    if {[dict exists $async_pins [get_full_name $pin]]} {ot_ag_async_control $pin; continue}')
    marker = '  puts "OT_MULTI_ROOT OWNERSHIP PASS roots='
    if body.count(marker) != 1:
        raise ValueError('async_gray_fifo ownership gate changed; revalidate extension')
    body = body.replace(marker, '  ot_ag_complete\n' + marker)
    body = body.replace('  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}',
                        '  set ::ot_ag_seen {}\n  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}')
    return bindings(record) + TCL + '\n' + body


TCL = r'''
# Source fingerprint is checked by the generator before this audited profile is
# emitted. Fail if mapping loses public register identities; never guess names.
set ::ot_ag_seen {}
proc ot_ag_public_nets {cell} {
  set result {}
  foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
    if {[get_property $p direction] ne "output"} continue
    foreach net [get_nets -quiet -of_objects $p] {
      lappend result [string map {\\ {}} [get_full_name $net]]
    }
  }
  return $result
}
proc ot_ag_role {cell} {
  set roles {}
  foreach name [ot_ag_public_nets $cell] {
    dict for {scope domains} $::ot_ag_fifo_domains {
      if {$scope eq ""} {set local $name} else {
        set prefix "$scope."
        if {[string first $prefix $name]!=0} continue
        set local [string range $name [string length $prefix] end]
      }
      if {[regexp {^(wr_gray|rd_gray|wr_gray_r1|rd_gray_w1|wr_online|rd_online|wr_online_r1|rd_online_w1)(?:\[([0-9]+)\])?$} $local unused role index]} {
        if {$index eq ""} {set index 0}
        dict set roles [list $scope $role $index] 1
      }
      # The reviewed Gray pointer's MSB is exactly the binary pointer MSB.
      # Synthesis may keep only the binary public alias on that shared flop.
      # Lower binary bits are never admitted by this source-derived alias rule.
      if {[regexp {^(wr|rd)_bin\[([0-9]+)\]$} $local unused direction index] && $index == [dict get $::ot_ag_pointer_msb $scope]} {
        dict set roles [list $scope ${direction}_gray $index] 1
      }
      if {[regexp {^mem\[[0-9]+\](?:\[([0-9]+)\])?$} $local unused payload_bit]} {
        if {$payload_bit eq ""} {set payload_bit 0}
        dict set roles [list $scope payload $payload_bit] 1
      }
    }
  }
  if {[dict size $roles] != 1} {return {}}
  return [lindex [dict keys $roles] 0]
}
proc ot_ag_data_pin {pin} {
  return [expr {[lindex [split [get_full_name $pin] /] end] eq "D" && [get_property $pin direction] eq "input"}]
}
proc ot_ag_target {scope source_bit cell pin} {
  if {![ot_ag_data_pin $pin] || ![dict exists $::ot_ag_targets $scope $source_bit]} {return 0}
  set allowed [dict get $::ot_ag_targets $scope $source_bit]
  foreach name [ot_ag_public_nets $cell] {
    if {$name in $allowed} {return 1}
  }
  return 0
}
proc ot_ag_async_control {pin} {
  # Reset recovery/removal stays timed. A FIFO data/pointer publication must
  # never acquire an async-control exception by sharing a legitimate D target.
  foreach start [get_fanin -flat -startpoints_only -to $pin] {
    set cell [get_cells -quiet -of_objects $start]
    if {[llength $cell]!=1} continue
    if {[llength [ot_ag_role [get_full_name $cell]]]} {
      error "OT_ASYNC_GRAY: FIFO publication drives asynchronous control [get_full_name $pin]"
    }
  }
}
proc ot_ag_bound {start target} {
  # OpenSTA graph startpoints are register clock pins; exceptions and path
  # queries must begin at the actual launch register, not a clock input pin.
  set launch [get_cells -quiet -of_objects $start]
  if {[llength $launch] != 1} {error "OT_ASYNC_GRAY: missing unique launch register"}
  # Bound ALL Gray bits within the faster source period minus setup uncertainty;
  # this also bounds inter-bit skew below a source cycle. Payload is held by the
  # verified FIFO protocol, and receives the same conservative datapath budget.
  # No exception applies to any other path or either synchronizer's second stage.
  set_max_delay -ignore_clock_latency 773.333 -from $launch -to $target
  set_min_delay -ignore_clock_latency 0.0 -from $launch -to $target
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} {
      puts "OT_ASYNC_GRAY PATH_DEFERRED [get_full_name $start] -> [get_full_name $target] $kind (strict at sign-off)"
      continue
    }
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_ASYNC_GRAY: missing finite bounded $kind path [get_full_name $start] -> [get_full_name $target]"
    }
  }
}
proc ot_ag_crossing {start pin source target source_domain target_domain} {
  lassign [ot_ag_role $source] scope sr source_bit
  if {![ot_ag_data_pin $pin]} {error "OT_ASYNC_GRAY: cross-domain control pin [get_full_name $pin]"}
  lassign [ot_ag_role $target] target_scope tr target_bit
  if {$sr eq "" || ![dict exists $::ot_ag_fifo_domains $scope]} {
    error "OT_ASYNC_GRAY: unapproved actual crossing $source -> $target"
  }
  lassign [dict get $::ot_ag_fifo_domains $scope] writer reader
  set permitted 0
  if {$scope eq $target_scope && $source_bit eq $target_bit} {
    if {[list $sr $tr] in {{wr_gray wr_gray_r1} {wr_online wr_online_r1}} && $source_domain eq $writer && $target_domain eq $reader} {set permitted 1}
    if {[list $sr $tr] in {{rd_gray rd_gray_w1} {rd_online rd_online_w1}} && $source_domain eq $reader && $target_domain eq $writer} {set permitted 1}
  }
  if {$sr eq "payload" && $source_domain eq $writer && $target_domain eq $reader && [ot_ag_target $scope $source_bit $target $pin]} {set permitted 1}
  if {!$permitted} {error "OT_ASYNC_GRAY: unapproved actual crossing $source -> $target ($scope $sr -> $target_scope $tr)"}
  ot_ag_bound $start $pin
  dict incr ::ot_ag_seen [list $scope $sr]
  puts "OT_ASYNC_GRAY BOUNDED $source -> $target"
}
proc ot_ag_payload {start port source name source_domain target_domain} {
  lassign [ot_ag_role $source] scope role source_bit
  if {$role ne "payload" || ![dict exists $::ot_ag_fifo_domains $scope]} {return 0}
  lassign [dict get $::ot_ag_fifo_domains $scope] writer reader
  if {$source_domain ne $writer || $target_domain ne $reader ||
      ![dict exists $::ot_ag_outputs $scope $source_bit] ||
      $name ni [dict get $::ot_ag_outputs $scope $source_bit]} {return 0}
  ot_ag_bound $start $port
  dict incr ::ot_ag_seen [list $scope payload]
  return 1
}
proc ot_ag_complete {} {
  dict for {scope domains} $::ot_ag_fifo_domains {
    foreach role {wr_gray rd_gray wr_online rd_online} {
      if {![dict exists $::ot_ag_seen [list $scope $role]]} {error "OT_ASYNC_GRAY: missing actual audited crossing $scope $role"}
    }
  }
  if {$::ot_ag_primitive && ![dict exists $::ot_ag_seen [list {} payload]]} {error "OT_ASYNC_GRAY: missing primitive payload crossing"}
  puts "OT_ASYNC_GRAY STRUCTURAL_PASS $::ot_ag_seen (bounded CDC; no physical closure claim)"
}
'''
