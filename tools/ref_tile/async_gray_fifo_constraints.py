"""Bounded CDC admission for one reviewed HBM/PHY SPSC FIFO implementation.

The primitive is source-fingerprinted. Parents are actually elaborated from their
pinned sources; every other crossing, including independent status synchronizers,
is refused. Derived payload endpoints and the actual mapped fanin are both
checked; register naming or a supplied graph receipt cannot grant admission.
No clock groups, false paths or same-domain timing exceptions are generated.

Reset-synchroniser inputs (QF-SFAULT 2026-10-18, Gate-Rule; as gray_fifo_cdc_constraints rule (c)): a reviewed
ot_reset_sync pipe stage (assert asynchronous, release through its own >= 2-stage pipe) is asynchronous to its
async_rst_n by design.  A cross-domain asynchronous control is admitted ONLY into a reset_pipe stage of an
ot_reset_sync instance found in the actual elaborated hierarchy (bound to the fingerprinted rtl/lib/ot_reset_sync.sv,
ASYNC_STAGES >= 2), and receives set_max_delay -ignore_clock_latency <destination period - 60 ps> plus set_min_delay 0
from its actual launch register (or declared input port) to that async pin only, with a finite-path proof.  Every
other cross-domain asynchronous control (for example a register cleared straight from the other domain's reset) is
refused; same-domain recovery/removal stays ordinarily timed.
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
         '3b85c58128cd8f8eeccf6e962c8cbe3672d56d3e10d044343307eb72a4712fe1',
         # QF-SFAULT 10-18: ot_hbm_svc_fault_cdc per-domain ot_reset_sync (FIFO module lines 6-51 byte-identical)
         '08cefc4772d97f3c91718e7f159bd9a6bc4fd2611ddb93517c56bbac57240c3b'),
    'rtl/lib/ot_reset_sync.sv':
        ('489e493c19aa1260853031fee35c14ea3394ae62ff6853cf7ea407cb8fb78bbd',),
}
RESET_SYNC_SOURCE = 'rtl/lib/ot_reset_sync.sv'
# destination period - 60 ps setup uncertainty (gray_fifo_cdc_constraints rule (c) reset bound)
RESET_BOUND_PS = {'core': 773.333, 'hbm': 964.0}
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
                payload_consumer_bits={},reset_syncs=['u_wr_reset','u_rd_reset'],
                reset_aliases=['rd_reset','u_rd_reset.sync_rst_n','u_wr_reset.sync_rst_n','wr_reset'],payload_output_bits={'':{str(i):(['rd_data','rd_data[0]']if params.get('WIDTH',32)==1 else['rd_data['+str(i)+']'])for i in range(params.get('WIDTH',32))}},primitive=True)


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
    syncs,aliases=reset_sync_scopes(document,spec['top'],root)
    result.update(source_sha256=actual_hashes,primitive=False,reset_syncs=syncs,reset_aliases=aliases)
    return result


def reset_sync_scopes(document,top,root):
    # Every actual ot_reset_sync instance in the elaborated hierarchy (including inside reviewed FIFOs), bound to the
    # fingerprinted source by its Yosys src attribute (other sources may not carry src/hdlname: elaborate()).
    src=str((Path(root)/RESET_SYNC_SOURCE).resolve())+':'
    modules=document['modules'];found=[];aliases=set()
    def is_rs(name):
        return (name=='ot_reset_sync' or re.fullmatch(r'\$paramod\$[0-9a-f]{40}\\ot_reset_sync',name)is not None
                or name.startswith('$paramod\\ot_reset_sync\\'))
    def walk(name,scope,depth):
        if depth>64:raise ValueError('async_gray_fifo hierarchy too deep')
        for cname,cell in modules[name].get('cells',{}).items():
            typ=cell['type']
            if typ not in modules:continue
            full=(scope+'.'if scope else'')+cname
            mod=modules[typ];claimed=mod.get('attributes',{}).get('hdlname')=='ot_reset_sync'
            if is_rs(typ) or claimed:
                if not str(mod.get('attributes',{}).get('src','')).startswith(src):
                    raise ValueError('async_gray_fifo ot_reset_sync identity does not bind reviewed source')
                stages=int(mod.get('parameter_default_values',{}).get('ASYNC_STAGES','10'),2)
                if stages<2:raise ValueError('async_gray_fifo ot_reset_sync requires >= 2 stages')
                if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.\[\]]*',full):raise ValueError('async_gray_fifo unsupported reset scope '+full)
                found.append(full)
                # the last stage drives sync_rst_n; synthesis may name that flop after the output or a parent net of it
                out=cell['connections'].get('sync_rst_n',[])
                aliases.add(full+'.sync_rst_n')
                for net,info in modules[name].get('netnames',{}).items():
                    if out and info['bits']==out and not info.get('hide_name'):aliases.add((scope+'.'if scope else'')+net)
            else:walk(typ,full,depth+1)
    walk(top,'',0)
    for a in aliases:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.\[\]]*',a):raise ValueError('async_gray_fifo unsupported reset alias '+a)
    return sorted(found),sorted(aliases)


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
            +'set ::ot_ag_primitive '+str(int(record['primitive']))+'\n'
            +'set ::ot_ag_reset_syncs [list '+' '.join(word(r)for r in record.get('reset_syncs',[]))+']\n'
            +'set ::ot_ag_reset_alias [list '+' '.join(word(r)for r in record.get('reset_aliases',[]))+']\n'
            +'set ::ot_ag_reset_bound [dict create '+' '.join(f'{k} {v}'for k,v in sorted(RESET_BOUND_PS.items()))+']\n')


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
    body=body.replace(async_guard,'    if {[dict exists $async_pins [get_full_name $pin]]} {ot_ag_async_control $pin $cells $inputs; continue}')
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
set ::ot_ag_reset_seen {}
proc ot_ag_public_nets {cell} {
  set result {}
  # The mapped register instance keeps its Yosys register name plus the cell-type suffix ($_DFF_PN0_, $_DFFE_PN0P_, ...)
  # through placement, CTS and repair; its output net names do not (QN-only ASAP7 flops, buffers inserted after CTS:
  # HBMA-SVC 10-17 hdie_svc_stack_fault CTS refused rd_gray[0] -> rd_gray_w1[0] with an empty target role).
  set inst [string map {\\ {}} [get_full_name [get_cells $cell]]]
  if {[regexp {^(.*)\$_[A-Z0-9_]+_$} $inst unused reg]} {lappend result $reg}
  foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
    if {[get_property $p direction] ne "output"} continue
    foreach net [get_nets -quiet -of_objects $p] {
      lappend result [string map {\\ {}} [get_full_name $net]]
      # ASAP7 flops expose only QN (DFFHQNx*, DFFASRHQNx1): synthesis puts the register's public name on the output of
      # the inverter that QN drives, not on QN itself.  Follow exactly that one inverter stage (HBMA-SVC 10-17: the
      # first actual ORFS run of this profile, hdie_svc_stack_fault, refused u_ca.u_status.rd_gray[0] -> rd_gray_w1[0]
      # because both public names sat behind the QN inverter).  No other cell type is traversed.
      if {[lindex [split [get_full_name $p] /] end] ne "QN"} continue
      foreach load [get_pins -quiet -of_objects $net] {
        if {[get_property $load direction] ne "input"} continue
        set lc [get_cells -quiet -of_objects $load]
        if {![regexp {^INVx} [get_property $lc ref_name]]} continue
        foreach q [get_pins -quiet -of_objects $lc] {
          if {[get_property $q direction] ne "output"} continue
          foreach n2 [get_nets -quiet -of_objects $q] {lappend result [string map {\\ {}} [get_full_name $n2]]}
        }
      }
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
proc ot_ag_reset_stage {cell} {
  # QF-SFAULT 10-18 Gate-Rule: a reset_pipe stage of an elaborated, fingerprint-bound ot_reset_sync instance.
  set inst [string map {\\ {}} [get_full_name [get_cells $cell]]]
  set names [ot_ag_public_nets $cell]
  lappend names $inst
  if {[regexp {^(.*)\$_[A-Z0-9_]+_$} $inst unused reg]} {lappend names $reg}
  foreach name $names {
    # the output stage under its output / parent-net name (generator-derived exact aliases, not a pattern)
    if {[regsub {_reg$} $name {} bare] && $bare in $::ot_ag_reset_alias} {return 1}
    if {$name in $::ot_ag_reset_alias} {return 1}
    foreach scope $::ot_ag_reset_syncs {
      set prefix "$scope."
      if {[string first $prefix $name]!=0} continue
      if {[regexp {^reset_pipe(?:_reg)?(?:\[[0-9]+\])?$} [string range $name [string length $prefix] end]]} {return 1}
    }
  }
  return 0
}
proc ot_ag_reset_bound {start pin bound} {
  if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
    set launch [get_ports [get_full_name $start]]
  } else {
    set launch [get_cells -quiet -of_objects $start]
    if {[llength $launch] != 1} {error "OT_ASYNC_GRAY: missing unique reset launch register"}
  }
  set_max_delay -ignore_clock_latency $bound -from $launch -to $pin
  set_min_delay -ignore_clock_latency 0.0 -from $launch -to $pin
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $pin -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} {
      puts "OT_ASYNC_GRAY PATH_DEFERRED reset [get_full_name $start] -> [get_full_name $pin] $kind (strict at sign-off)"
      continue
    }
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_ASYNC_GRAY: missing finite bounded reset $kind path [get_full_name $start] -> [get_full_name $pin]"
    }
  }
}
proc ot_ag_async_control {pin cells inputs} {
  # Reset recovery/removal stays timed within a domain. A FIFO data/pointer publication must
  # never acquire an async-control exception by sharing a legitimate D target.  A cross-domain asynchronous control
  # is admitted only into a reviewed ot_reset_sync pipe stage (QF-SFAULT 10-18 Gate-Rule, gray_fifo_cdc rule (c)).
  set target [get_full_name [get_cells -of_objects $pin]]
  if {![dict exists $cells $target]} {error "OT_ASYNC_GRAY: unowned asynchronous control register $target"}
  set domain [dict get $cells $target]
  foreach start [get_fanin -flat -startpoints_only -to $pin] {
    # A tie-driven async pin (ASAP7 DFFASRHQNx1 SETN/RESETN tied by TIEHI/TIELO) has no driving register: OpenSTA returns
    # the pin itself as its only startpoint (HBMA-SVC 10-17, hdie_svc_stack_fault SETN of u_ca.u_status.rd_bin[2]).
    # Admit exactly that case, and only when every driver of the pin's net is a tie cell.
    if {[get_full_name $start] eq [get_full_name $pin]} {
      set tied 1
      foreach d [get_pins -quiet -of_objects [get_nets -quiet -of_objects $pin]] {
        if {[get_property $d direction] ne "output"} continue
        if {![regexp {^TIE(HI|LO)x} [get_property [get_cells -quiet -of_objects $d] ref_name]]} {set tied 0}
      }
      if {!$tied} {error "OT_ASYNC_GRAY: asynchronous control without a register or tie driver [get_full_name $pin]"}
      continue
    }
    set name [get_full_name $start]
    if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
      if {![dict exists $inputs $name]} {error "OT_ASYNC_GRAY: undeclared input $name drives asynchronous control [get_full_name $pin]"}
      set source_domain [dict get $inputs $name]
    } else {
      set cell [get_cells -quiet -of_objects $start]
      if {[llength $cell]!=1} continue
      if {[llength [ot_ag_role [get_full_name $cell]]]} {
        error "OT_ASYNC_GRAY: FIFO publication drives asynchronous control [get_full_name $pin]"
      }
      set source [get_full_name $cell]
      if {![dict exists $cells $source]} {
        if {[ot_ce_constant_cone $start]} continue
        error "OT_ASYNC_GRAY: unowned asynchronous control $source -> [get_full_name $pin]"
      }
      set source_domain [dict get $cells $source]
    }
    if {$source_domain eq $domain} continue
    if {![ot_ag_reset_stage $target]} {
      error "OT_ASYNC_GRAY: cross-domain asynchronous control $name ($source_domain) -> [get_full_name $pin] ($domain); only an ot_reset_sync pipe may take it"
    }
    ot_ag_reset_bound $start $pin [dict get $::ot_ag_reset_bound $domain]
    dict incr ::ot_ag_reset_seen $domain
    puts "OT_ASYNC_GRAY BOUNDED reset $name -> [get_full_name $pin]"
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
proc ot_ag_online_merged {scope role domains} {
  # HBMA-SVC 10-17 (hdie_svc_stack_fault, first actual ORFS run): FIFOs with the same two clocks and the same reset
  # inputs have bit-identical online flag chains (constant 1 after reset, then the two-flop synchroniser), and synthesis
  # merges them into ONE chain that keeps a single scope's name.  Admit a missing online crossing only when (a) no mapped
  # cell of this scope's online chain is left (it was merged away, not left unaudited) and (b) another FIFO scope with
  # the same writer/reader domains has that online crossing audited.  Gray pointers and payload are never merged here.
  # HBM-KITS-B 10-18 (hdie_svc_vm_kshare gate e1d441878): the reviewed FIFO resets BOTH sides from wr_rst_n&&rd_rst_n, so
  # the writer-side online chain of a core->hbm FIFO (wr_online on core, wr_online_r1/r2 on hbm) is bit-identical to the
  # reader-side chain of an hbm->core FIFO (rd_online on core, rd_online_w1/w2 on hbm); synthesis merged u_cmd wr_online
  # into lane[0].u_fill rd_online.  Admit that as the same launch->capture clock pair with the role swapped, under the
  # same two conditions; the bounded crossing it is admitted against is the actual audited one.
  if {[llength [get_cells -quiet "$scope.${role}*"]]} {return 0}
  set swapped [string map {wr_online rd_online rd_online wr_online} $role]
  set reversed [list [lindex $domains 1] [lindex $domains 0]]
  dict for {other od} $::ot_ag_fifo_domains {
    if {$other eq $scope} continue
    if {$od eq $domains && [dict exists $::ot_ag_seen [list $other $role]]} {
      puts "OT_ASYNC_GRAY MERGED_ONLINE $scope $role -> $other"
      return 1
    }
    if {$od eq $reversed && [dict exists $::ot_ag_seen [list $other $swapped]]} {
      puts "OT_ASYNC_GRAY MERGED_ONLINE $scope $role -> $other $swapped"
      return 1
    }
  }
  return 0
}
proc ot_ag_complete {} {
  dict for {scope domains} $::ot_ag_fifo_domains {
    foreach role {wr_gray rd_gray wr_online rd_online} {
      if {[dict exists $::ot_ag_seen [list $scope $role]]} continue
      if {$role in {wr_online rd_online} && [ot_ag_online_merged $scope $role $domains]} continue
      error "OT_ASYNC_GRAY: missing actual audited crossing $scope $role"
    }
  }
  if {$::ot_ag_primitive && ![dict exists $::ot_ag_seen [list {} payload]]} {error "OT_ASYNC_GRAY: missing primitive payload crossing"}
  puts "OT_ASYNC_GRAY STRUCTURAL_PASS $::ot_ag_seen reset_sync_inputs=$::ot_ag_reset_seen (bounded CDC; no physical closure claim)"
}
'''
