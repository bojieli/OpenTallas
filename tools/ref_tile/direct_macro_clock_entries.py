"""Explicit raw SRAM clock entries, distinct from routed-child ETM insertion.

The reference is the actual Liberty clock pin. Clock-to-Q and setup/hold remain
in that Liberty; no internal delay is inferred, subtracted or added to them.
Only the propagated source-to-pin wire is balanced by the parent CE policy.
"""
import base64
import hashlib
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import child_lint

CORNERS = ('tt', 'ff', 'ss')


def _groups(text, kind):
    # Ignore comments, but preserve quoted strings and braces within strings.
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    for match in re.finditer(r'\b' + kind + r'\s*\(\s*([^)]*?)\s*\)\s*\{', text):
        start = match.end(); depth = 1; quoted = False; escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if escaped:
                escaped = False; continue
            if char == '\\':
                escaped = True; continue
            if char == '"':
                quoted = not quoted
            if not quoted:
                depth += (char == '{') - (char == '}')
            if depth == 0:
                yield match.group(1).strip('"'), text[start:i]
                break
        else:
            raise ValueError('direct macro: unterminated Liberty group')


def _attr(body, key):
    found = re.findall(r'\b' + re.escape(key) + r'\s*:\s*("[^"]*"|[^;]+)\s*;', body)
    if len(found) != 1:
        raise ValueError(f'direct macro: missing/ambiguous Liberty {key}')
    return found[0].strip().strip('"')


def _liberty(path, master, pin, corner):
    text = path.read_text()
    libs = list(_groups(text, 'library'))
    if len(libs) != 1 or libs[0][0] != f'{master}_{corner}':
        raise ValueError(f'{path}: actual Liberty corner/name mismatch')
    cells = list(_groups(libs[0][1], 'cell'))
    if len(cells) != 1 or cells[0][0] != master:
        raise ValueError(f'{path}: actual Liberty cell mismatch')
    body = cells[0][1]
    # Raw SRAM only: a routed ETM cannot masquerade as this reference kind.
    if re.search(r'timing_type\s*:\s*(?:min|max)_clock_tree_path', body):
        raise ValueError(f'{path}: routed insertion arcs are not raw SRAM pin semantics')
    if len(list(_groups(body, 'memory'))) != 1:
        raise ValueError(f'{path}: raw SRAM memory semantics missing')
    pins = list(_groups(body, 'pin'))
    clocks = [(n, b) for n, b in pins if re.search(r'\bclock\s*:\s*true\s*;', b)]
    if len(clocks) != 1 or clocks[0][0] != pin or _attr(clocks[0][1], 'direction') != 'input':
        raise ValueError(f'{path}: unique actual input clock mismatch')
    kinds = set()
    for _, timing in _groups(body, 'timing'):
        if re.search(r'\brelated_pin\s*:\s*"' + re.escape(pin) + r'"\s*;', timing):
            kinds.add(_attr(timing, 'timing_type'))
    if not {'setup_rising', 'hold_rising', 'rising_edge'} <= kinds:
        raise ValueError(f'{path}: clock pin lacks real setup/hold/clock-to-Q arcs')
    return dict(library=libs[0][0], sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                clock_reference='raw_liberty_clock_pin', arc_types=sorted(kinds))


def _word(value):
    # Tcl braced words used below cannot safely contain these characters.
    if not isinstance(value, str) or not value or any(c in value for c in '{}\\\n\r;'):
        raise ValueError('direct macro: unsafe/empty identity')
    return '{' + value + '}'


def load(spec, root):
    """Return explicit entries, source hashes and an independently callable Tcl hook.

    Opt in per spec.macros item with clock_entry={port,pin,reference}. Runtime
    ownership is proved against the actual linked netlist, never an RTL regex.
    Unannotated macros remain subject to existing CTS ownership checks.
    """
    root = Path(root).resolve(); entries = []; ports = set(); patterns = set()
    for macro in spec.get('macros', []):
        entry = macro.get('clock_entry')
        if entry is None:
            continue
        if spec.get('clock') not in ('entries', 'hybrid_entries'):
            raise ValueError('direct macro: explicit clock entries require entries policy')
        if set(entry) != {'port', 'pin', 'reference'} or entry['reference'] != 'raw_liberty_clock_pin':
            raise ValueError('direct macro: require explicit port/pin/raw_liberty_clock_pin reference')
        if macro.get('count', 1) != 1:
            raise ValueError('direct macro: each binding must own exactly one instance')
        port, pin, pattern = entry['port'], entry['pin'], macro.get('inst')
        for name in (port, pin, pattern):
            _word(name)
        if port not in spec['clock_ports'] or port in spec.get('clock_cts_roots', []):
            raise ValueError('direct macro: source must be declared hard clock port')
        if port in ports or pattern in patterns:
            raise ValueError('direct macro: duplicate source/instance ownership')
        ports.add(port); patterns.add(pattern)
        view = (root / macro['view']).resolve(); master = view.name
        if not view.is_relative_to(root):
            raise ValueError('direct macro: view outside source root')
        lef = view / f'{master}.lef'; physical = child_lint.parse_lef(lef.read_text(), master)
        p = physical['pins'].get(pin, {})
        if physical['name'] != master or p.get('direction') != 'INPUT' or p.get('use') != 'CLOCK' or not p.get('rects'):
            raise ValueError(f'{lef}: actual LEF clock identity/access mismatch')
        if not all(math.isfinite(physical[k]) and physical[k] > 0 for k in ('W', 'H')):
            raise ValueError(f'{lef}: invalid actual macro dimensions')
        corners = {c: _liberty(view/f'{master}_{c}.lib', master, pin, c) for c in CORNERS}
        entries.append(dict(master=master, instance_pattern=pattern, port=port, pin=pin,
                            reference=entry['reference'], corners=corners,
                            lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),
                            dimensions_um=[physical['W'], physical['H']]))
    rows = []
    for e in entries:
        corners = ' '.join(_word(c) + ' {' + _word(e['corners'][c]['library']) + ' ' + _word(e['corners'][c]['sha256']) + '}' for c in CORNERS)
        rows.append('{' + ' '.join(_word(e[k]) for k in ('master', 'instance_pattern', 'port', 'pin')) + ' {' + corners + '}}')
    return dict(entries=entries, bindings_tcl='set ::ot_ce_direct_entries {' + ' '.join(rows) + '}\n' + (scene_accessor_tcl() if entries else '') + BODY)


def scene_accessor_tcl():
    """Embed source so every generated kit uses exactly the reviewed accessor.

    The module is compiled with the running image's headers and dynamically
    resolves that executable's OpenSTA symbols. No prebuilt binary is shipped.
    """
    source = Path(__file__).with_name('sta_scene_binding.cc').read_bytes()
    return ('set ::ot_scene_accessor_source_b64 {' + base64.b64encode(source).decode() + '}\n'
            + 'set ::ot_scene_accessor_source_sha256 {' + hashlib.sha256(source).hexdigest() + '}\n'
            + SCENE_LOADER)


SCENE_LOADER = r'''
proc ot_direct_sha256 {filename} {
  if {![file isfile $filename]} {error "OT_DIRECT_MACRO: missing source file $filename"}
  set result [exec sha256sum -- $filename]
  if {![regexp {^([0-9a-f]{64}) } $result -> digest]} {error "OT_DIRECT_MACRO: invalid source digest $filename"}
  return $digest
}
proc ot_direct_load_scene_accessor {} {
  if {[info exists ::ot_scene_accessor_loaded]} {return}
  # Compile within the exact running image against its installed headers. A
  # missing compiler/header/symbol is an admission failure, never a fallback.
  set channel [file tempfile directory ot_sta_scene_]
  close $channel; file delete $directory; file mkdir $directory
  set source [file join $directory sta_scene_binding.cc]
  set channel [open $source w]; fconfigure $channel -translation binary
  puts -nonewline $channel [binary decode base64 $::ot_scene_accessor_source_b64]; close $channel
  if {[ot_direct_sha256 $source] ne $::ot_scene_accessor_source_sha256} {error "OT_DIRECT_MACRO: accessor source digest mismatch"}
  set executable [file normalize [file readlink /proc/self/exe]]
  set include [file normalize [file join [file dirname $executable] .. include]]
  set flags [list -std=c++20 -shared -fPIC -I$include -I/usr/include/tcl]
  if {![file isfile /usr/include/fmt/core.h] && ![file isfile /usr/local/include/fmt/core.h]} {
    set bundled /usr/local/include/spdlog/fmt/bundled
    if {![file isfile $bundled/core.h]} {error "OT_DIRECT_MACRO: matching image fmt headers missing"}
    file link -symbolic [file join $directory fmt] $bundled
    lappend flags -I$directory
  }
  set module [file join $directory ot_scene_binding.so]
  if {[catch {exec g++ {*}$flags $source -o $module 2>@1} output]} {
    error "OT_DIRECT_MACRO: accessor compile failed ($directory): $output"
  }
  if {[catch {load $module Otscenebinding} output]} {error "OT_DIRECT_MACRO: accessor ABI/load failed: $output"}
  set version [lindex [split [exec g++ --version] \n] 0]
  puts "OT_DIRECT_MACRO ACCESSOR source_sha256=$::ot_scene_accessor_source_sha256 executable_sha256=[ot_direct_sha256 $executable] module_sha256=[ot_direct_sha256 $module] compiler=$version"
  set ::ot_scene_accessor_loaded 1
  file delete -force $directory
}
'''


BODY = r'''
# Return existing CE row shape. Zero internal OFFSET means Liberty-pin reference;
# it is not a measured zero SRAM insertion and does not modify any macro arcs.
proc ot_ce_direct_rows {corner} {
  if {[llength $::ot_ce_direct_entries]} {ot_direct_load_scene_accessor}
  set rows {}; set cells_seen {}
  foreach entry $::ot_ce_direct_entries {
    lassign $entry master pattern name libpin libraries
    set cells [get_cells -quiet -hierarchical $pattern]
    if {[llength $cells] != 1} { error "OT_DIRECT_MACRO: instance ownership is not unique: $pattern" }
    set cell [lindex $cells 0]; set cellname [get_full_name $cell]
    if {[dict exists $cells_seen $cellname] || [get_property $cell ref_name] ne $master} {
      error "OT_DIRECT_MACRO: duplicate/wrong actual macro $cellname"
    }
    dict set cells_seen $cellname 1
    lassign [dict get $libraries $corner] expected_library expected_sha
    set expected "$expected_library/$master"
    if {[catch {ot_sta_scene_binding $cellname $libpin} binding]} {
      error "OT_DIRECT_MACRO: actual scene binding failed: $binding"
    }
    foreach mm {min max} {
      set actual [dict get $binding $mm]
      if {[dict get $actual library] ne $expected_library || [dict get $actual cell] ne $master ||
          [dict get $actual clock_pin] ne $libpin} {
        error "OT_DIRECT_MACRO: actual corner mismatch: scene=[dict get $binding scene] $mm [dict get $actual library]/[dict get $actual cell] expected $expected"
      }
      if {[ot_direct_sha256 [dict get $actual filename]] ne $expected_sha} {
        error "OT_DIRECT_MACRO: actual scene Liberty source digest mismatch $expected"
      }
    }
    set pins {}
    foreach p [get_pins -of_objects $cell] {
      if {[get_property $p lib_pin_name] eq $libpin} { lappend pins $p }
    }
    if {[llength $pins] != 1} { error "OT_DIRECT_MACRO: missing actual clock pin $cellname/$libpin" }
    set pin [lindex $pins 0]
    set net [get_nets -quiet -of_objects $pin]
    set sources [get_ports -quiet -of_objects $net]
    set sinks [get_pins -quiet -of_objects $net]
    if {[llength $sources] != 1 || [get_full_name [lindex $sources 0]] ne $name ||
        [llength $sinks] != 1 || [get_full_name [lindex $sinks 0]] ne [get_full_name $pin]} {
      error "OT_DIRECT_MACRO: actual exclusive direct source/pin ownership mismatch $name -> $cellname/$libpin"
    }
    set i [lsearch -exact $::ot_ce_ports $name]
    if {$i < 0 || $name in $::ot_ce_cts_roots} { error "OT_DIRECT_MACRO: undeclared/nonhard source $name" }
    set clock [get_clocks ot_entry_$i]
    if {[llength $clock] != 1} { error "OT_DIRECT_MACRO: missing source clock $name" }
    set wire [ot_ce_clock_wire $pin $clock]
    if {![ot_ce_finite $wire]} { error "OT_DIRECT_MACRO: nonfinite clock wire $name" }
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $wire <= 0} {
      error "OT_DIRECT_MACRO: actual positive propagated source-to-SRAM wire required $name"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
    if {abs([get_property $vc period]-[get_property $clock period])>0.001} {
      error "OT_DIRECT_MACRO: domain/source period mismatch $name"
    }
    lappend rows [list [lindex $sources 0] $pin $wire 0 0 0 $clock 0 $domain]
    puts "OT_DIRECT_MACRO RAW_LIBERTY_PIN $corner $name -> [get_full_name $pin] wire=$wire library=$expected (internal arcs retained)"
  }
  return $rows
}
'''
