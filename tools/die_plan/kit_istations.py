#!/usr/bin/env python3
"""KV-G3 10-24: realise a plan type's FIRM internal_stations[] (R3-INTERNAL) and FIRM plan-cell sites in a BOUND G3 kit.

The bind (bind.py) lands a lane's fixed_cycles as pad stages at the partition face (u_bin_<bus>_pad<j>) or not at all
(a bind older than the plan), and GPL places plan cells (contents[] without a hard view, e.g. qkd_hp_or2 fault ORs)
anywhere.  The plan however FIXES where those stages sit (internal_stations[].regs_um) and where plan cells sit
(contents[].origin_um).  This tool, run on a kit-rtl directory (after kit_rsync.py, before gen.py phys --kit-rtl):
  1. for every internal_stations entry with conn 'bus:<name>' it makes sure the bound module has exactly
     len(regs_um) stages on that bus between the face register and the leaf:
       * in bus : stations u_ist_<bus>_<j> (ot_dp_st, data + epoch) after u_bin_<bus>; the leaf readers of
                  <bus>_q / <bus>_eq read the last station.  Existing u_bin_<bus>_pad<j> stages (bind-landed
                  fixed_cycles) are COUNTED first and only renamed in the placement table, never duplicated;
       * out bus: stations before u_bout_<bus> (its .d / .ea come from the last station).
     A bound module that already carries more stages than regs_um is an error (the plan and the bind disagree).
  2. writes istations.tcl (sourced from face_flops.tcl before reset_taps.tcl, PRE_GLOBAL_PLACE): every station's
     flops FIRM at its regs_um site, every plan cell with origin_um (contents[], no lef) FIRM at its site, all
     appended to ot_face_flops.txt so face_flops_release.tcl hands them to DPL like the face flops.
Cycle effect: +len(regs_um) - (existing pads) register stages on that bus = the plan lane's fixed_cycles; the plan's
latency table (gen.py latency) carries it.  Report the bind delta when the bound RTL had none (kit RTL then differs
from the bind by exactly these stages: re-bind on the plan to make it authoritative).
S81-PLAN R3 (10-25): core<->core entries (conn 'core:<launch pin>|core:<capture>') are no longer skipped.  Each is
mapped to a link class of the leaf RTL's station chains (CORE_CLASSES: ot_s81sl_leaf CS_* depths, see
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv).  Fail closed when an entry matches no class, when the entries of one class
(per lane for the h trees) carry unequal stage counts, when a class has no RTL stations (vn_a -> vn_b c_s: vn_b's
fixed chain timeline), or when the RTL depth of the class (the CS_* override on the bound module's leaf instance, 0 when
absent) differs from the plan's count.  --apply writes the plan's depths onto the leaf instance first (h trees:
--h-tree G,GS_IN,GS_OUT, default 4,0,0).  Stage j of a chain is FIRM at the bits-weighted centroid of its entries'
regs_um[j] (ordered from the RTL launch side; regs_um is reversed where the plan's launch pin is the RTL's capture side).
usage: kit_istations.py PLAN.json TYPE KIT_RTL_DIR [--apply] [--h-tree G,GSI,GSO]
       ->  KIT_RTL_DIR/istations.tcl + edited bound module"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import kit_bus_bitgroups as BG  # noqa: E402


def bound_bus_width(tn, bus, txt, manifest):
    """Size stations to the real face register; narrow inputs need the bind proof, narrow outputs the spare-out tie."""
    name, planned = bus['name'], bus['width']
    widths = re.findall(rf'\bot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+'
                        rf'u_b(?:in|out)_{re.escape(gen_rtl.sv_id(name))}\s*\(', txt)
    if len(widths) != 1:
        raise SystemExit(f'kit_istations: {tn} {name}: expected one actual face register, got {len(widths)}')
    actual = int(widths[0])
    if actual == planned:
        return actual
    narrow = dict(port=name, plan=planned, bound=actual)
    if bus['dir'] == 'out':
        # DIE-HBM-90-TSTRAP 11-07: a narrow OUTPUT is the bind's declared spare-out form (DIE-S81-46, COORD 10-30
        # 14:0x (2)(b)): the kit-rtl wrapper ties plan bits [plan-1:bound] to 0 (kit_rtl.json spare_out_bits, the
        # same bits gen_phys.kit_spare_out_bits hands face_guard), so stations carry the real face register only.
        # Exact: the narrow mapping AND a spare_out_bits row of exactly plan-bound bits, else fail as before.
        spare = [e for e in manifest.get('spare_out_bits', []) if e.get('port') == name]
        if (0 < actual < planned and narrow in manifest.get('narrow_buses', [])
                and len(spare) == 1 and int(spare[0].get('bits', -1)) == planned - actual):
            return actual
        raise SystemExit(f'kit_istations: {tn} {name}: plan width {planned} != face width {actual}; '
                         'matching narrow-output mapping and spare_out_bits (tied plan bits) required')
    dead = manifest.get('dead_inputs', {})
    omitted = {f'{name}[{bit}]' for bit in range(actual, planned)}
    if (bus['dir'] != 'in' or not 0 < actual < planned
            or narrow not in manifest.get('narrow_buses', [])
            or dead.get('proof', {}).get('verdict') != 'PASS'
            or not omitted.issubset(set(dead.get('bits', [])))):
        raise SystemExit(f'kit_istations: {tn} {name}: plan width {planned} != face width {actual}; '
                         'matching narrow-input mapping and complete dead-input proof required')
    return actual


def packed_input_delay(tn,bus,txt,width,stages):
    """Recognize the canonical already-priced packed receiver delay, including epoch."""
    name=gen_rtl.sv_id(bus['name']);inst='u_lpad_'+name
    if inst not in txt:return None
    from kit_assembly import _masked_rtl
    code=_masked_rtl(txt)
    if not re.search(r'\b'+re.escape(inst)+r'\s*\(',code):return None
    if bus['dir']!='in':raise ValueError(f'{tn}.{name}: packed receiver delay on non-input bus')
    hits=list(re.finditer(r'\bot_dp_dly\s*#\(\s*\.W\((\d+)\)\s*,\s*\.D\((\d+)\)\s*\)\s+'
                         +re.escape(inst)+r'\s*\(([^;]*)\);',code,re.S))
    if len(hits)!=1:raise ValueError(f'{tn}.{name}: unsupported or duplicate packed receiver delay')
    w,d=map(int,hits[0].group(1,2))
    # D above the planned site count is fine: the die latency table priced D cycles, the plan pins the first `stages`
    # registers and the placer keeps the rest (KW-FIX-27: QC v4 nb_i00 D9/7, nb_i22 D3/2).
    # DIE-HBM-91-KCLS 11-08 (class l, COORD default (A)): D BELOW the planned count is the bound, priced latency too
    # (HBM q_hub_ne/nw L12s_i D12 vs 34/32 planned, L96_i D6 vs 8): the D registers go to evenly spaced planned
    # sites of the bus path (packed_sites); the cycle count is unchanged and the longer hops are judged at sign-off.
    if w!=width+1 or d<=0:raise ValueError(f'{tn}.{name}: packed delay W{w}/D{d} != payload+epoch {width+1}/planned {stages}')
    if re.search(r'\b(?:u_ist_'+re.escape(name)+r'_\d+|u_b(?:in|out)_'+re.escape(name)+r'_pad\d+)\s*\(',code):
        raise ValueError(f'{tn}.{name}: mixed packed/individual station forms; regenerate native source')
    pins=dict(re.findall(r'\.(clk|d|q)\s*\(([^()]*)\)',hits[0].group(3)))
    pins={k:re.sub(r'\s+','',v) for k,v in pins.items()}
    face=re.search(r'\bot_dp_ste?\s*#\(\.W\('+str(width)+r'\)\)\s+u_bin_'+re.escape(name)+r'\s*\(([^;]*)\);',code,re.S)
    facepins=dict(re.findall(r'\.(q|eq)\s*\(([^()]*)\)',face.group(1))) if face else {}
    expected={'clk':'clk','d':'{'+facepins.get('eq','?')+','+facepins.get('q','?')+'}',
              'q':'{'+name+'_eq,'+name+'_q}'}
    if pins!=expected:raise ValueError(f'{tn}.{name}: packed delay does not preserve exact face epoch/data connection: {pins}')
    return dict(instance=inst,master='ot_dp_dly',width=w,depth=d,pins=pins,
                stage_registers=[f'{inst}.r[{j}]' for j in range(d)])


def packed_sites(regs, depth):
    """[(register j, planned site index)] of a packed receiver delay of `depth` registers on a bus with planned
    station sites regs (face -> leaf order).  depth >= len(regs): registers 0..len-1 on the sites in order, the rest
    float (KW-FIX-27).  depth < len(regs) (DIE-HBM-91-KCLS 11-08): register j on site round((j+1)(n+1)/(D+1)) - 1, so
    the D registers split the planned n+1 hops into D+1 near-equal groups, strictly increasing along the path."""
    n = len(regs)
    if depth >= n:
        return [(j, j) for j in range(n)]
    return [(j, round((j + 1) * (n + 1) / (depth + 1)) - 1) for j in range(depth)]


def exact_banks(entry, width):
    """Validate explicit geometry without changing the existing station RTL/depth."""
    from ft_bit_sites import validate_slot
    if 'bit_sites_um' not in entry and 'face_bit_sites_um' not in entry:
        return None
    if entry.get('bit_route'):
        raise ValueError('exact internal bank sites cannot also request bit_route')
    cell = entry.get('bit_site_cell_um')
    banks = entry.get('bit_sites_um')
    if banks is None:
        raise ValueError('exact face bank requires exact internal bit_sites_um')
    validate_slot(dict(width=width, stations=len(entry['regs_um'])+1,
                       bit_sites_um=banks, bit_site_cell_um=cell))
    face = entry.get('face_bit_sites_um')
    if face is not None:
        validate_slot(dict(width=width, stations=2,
                           bit_sites_um=[face], bit_site_cell_um=cell))
    return banks, cell, face

RELAY_TCL = """# DIE-KV-59 10-31 plan relay_sites (opt-in partition_types[].relay_sites): FIRM sites for EXISTING RTL stage
# flops (0 added cycles).  Keys are the Yosys flop names below the bound instance, cell suffix dropped
# (u_kvs_hroot.u_rly.fan[13]); a plan key that matches no flop is reported as missing.
proc rs_place_all {sites} {
  global ff_blk ff_dbu is_fh is_miss
  set n 0; set hit [dict create]
  foreach i [$ff_blk getInsts] {
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    set nm [string map {\\\\ {}} [$i getName]]
    regsub {\\$_[A-Za-z0-9_]*$} $nm {} k
    if {![dict exists $sites $k]} { regsub {^[^./]*[./]} $k {} k }
    if {![dict exists $sites $k]} continue
    lassign [dict get $sites $k] x y
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend is_miss $nm; continue }
    # raw (escaped) inst name: face_flops_release.tcl findInst releases it to PLACED before DPL
    puts $is_fh "[$i getName]\\trelay\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
    dict set hit $k 1; incr n
  }
  set miss [expr {[dict size $sites] - [dict size $hit]}]
  if {$miss} { lappend is_miss "relay_sites:$miss" }
  puts "OT_RELAY_SITES placed $n flops FIRM (plan keys unmatched: $miss of [dict size $sites])"
}
"""


TCL_HEAD = """# GENERATED by tools/die_plan/kit_istations.py: FIRM plan internal stations + plan-cell sites (R3-INTERNAL).
# Sourced inside face_flops.tcl (PRE_GLOBAL_PLACE) before reset_taps.tcl; uses its ff_put_near / ff_blk / ff_dbu.
set is_n 0; set is_miss {}
set is_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc is_place {pat x y tag} {
  global ff_blk ff_dbu is_n is_miss is_fh
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match $pat [string map {\\\\ {}} $nm]]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend is_miss $nm; continue }
    puts $is_fh "$nm\\t$tag\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
    incr is_n; incr hit
  }
  if {!$hit} { lappend is_miss $pat }
}
# HEAD-SPINE2 10-25 per-bit station sites (plan internal_stations[].bit_route = "per_bit"): bit b of station k sits on
# ITS OWN L route between the planned leaf point (leaf_um) and its face pin <bus>[b] (epoch flop eq -> pin [W]); the
# segment next to the pin runs perpendicular to the face at the pin row / column, so a station is a column (E/W) or
# row (N/S) parallel to the pin window and every hop of bit b is L_b / (n+1) (the ft_bit_sites rule for ft slots).
# Common bank legs: every payload/epoch bit uses the same stage-to-leg mapping.
# Unlike per-bit arclength fractions, a stage remains one straight column/row.
# order "along" (plan leg_order along_first, SUL0-PINFACE-1 11-11): the leg at the pin runs along the face, the corner
# is (px, ly) for an E/W face / (lx, py) for N/S, so a route can pass a macro column in a free strip; default unchanged.
proc is_knee_site {px py lx ly face edge edges dir geometry {order normal}} {
  lassign $geometry xmin ymin xmax ymax
  if {$face in {E W}} {
    set normal [expr {max(abs($xmin-$lx),abs($xmax-$lx))}]
    set along [expr {max(abs($ymin-$ly),abs($ymax-$ly))}]
    set cx $lx; set cy $py
  } else {
    set normal [expr {max(abs($ymin-$ly),abs($ymax-$ly))}]
    set along [expr {max(abs($xmin-$lx),abs($xmax-$lx))}]
    set cx $px; set cy $ly
  }
  set n1 $normal; set a1 $along
  if {$order eq "along"} {
    if {$face in {E W}} { set cx $px; set cy $ly } else { set cx $lx; set cy $py }
    set n1 $along; set a1 $normal
  } elseif {$order ne "normal"} { error "internal station knee order $order" }
  if {$dir eq "in"} {
    set first $n1; set second $a1
    set ax $px; set ay $py; set bx $lx; set by $ly
  } else {
    set first $a1; set second $n1
    set ax $lx; set ay $ly; set bx $px; set by $py
  }
  if {$first < 1e-8} { set split 0; set worst [expr {$second/double($edges)}]
  } elseif {$second < 1e-8} { set split $edges; set worst [expr {$first/double($edges)}]
  } else {
    set split -1; set worst 1e99
    for {set j 1} {$j < $edges} {incr j} {
      set w [expr {max($first/double($j),$second/double($edges-$j))}]
      if {$w < $worst} { set worst $w; set split $j }
    }
    if {$split < 0} { error "internal station chain has no stage for its Manhattan knee" }
  }
  if {$worst > 403.0} { error "internal station knee needs a plan depth change: worst ideal hop $worst >403um" }
  if {$edge <= $split} {
    set f [expr {$edge/double($split)}]
    return [list [expr {$ax+$f*($cx-$ax)}] [expr {$ay+$f*($cy-$ay)}]]
  }
  set f [expr {($edge-$split)/double($edges-$split)}]
  return [list [expr {$cx+$f*($bx-$cx)}] [expr {$cy+$f*($by-$cy)}]]
}

# SUL0-PINFACE-1 11-11: starts = {bit x y ...} (plan internal_stations[].start_core/start_port, e.g. the q pins of the
# clock-landing macro a landed bus really launches from) replaces the face BTerm as bit b's L-route start; empty =
# the BTerm (every other chain unchanged).
proc is_bits {inst bus face W lx ly k n dir tag {offset 0} {starts {}} {order normal}} {
  global ff_blk ff_dbu is_n is_miss is_fh
  set hit 0
  set xmin 1e99; set ymin 1e99; set xmax -1e99; set ymax -1e99
  set is_st [dict create]
  foreach {sb sx sy} $starts { dict set is_st $sb [list $sx $sy] }
  for {set bit 0} {$bit <= $W} {incr bit} {
    if {[llength $starts]} {
      if {![dict exists $is_st $bit]} { error "internal station start missing: ${bus} bit $bit" }
      lassign [dict get $is_st $bit] x y
    } else {
      set pin [$ff_blk findBTerm "${bus}\\[$bit\\]"]
      if {$pin eq "NULL"} { error "internal station pin missing: ${bus} bit $bit" }
      set box [$pin getBBox]
      set x [expr {([$box xMin]+[$box xMax])/2.0/$ff_dbu}]
      set y [expr {([$box yMin]+[$box yMax])/2.0/$ff_dbu}]
    }
    set xmin [expr {min($xmin,$x)}]; set xmax [expr {max($xmax,$x)}]
    set ymin [expr {min($ymin,$y)}]; set ymax [expr {max($ymax,$y)}]
  }
  set geometry [list $xmin $ymin $xmax $ymax]
  # Separate opposite-face bank corridors inside the declared leaf box.
  if {$face eq "W"} {set lx [expr {$lx-$offset}]}
  if {$face eq "E"} {set lx [expr {$lx+$offset}]}
  if {$face eq "S"} {set ly [expr {$ly-$offset}]}
  if {$face eq "N"} {set ly [expr {$ly+$offset}]}
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match "*${inst}/*" $nm]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    if {[regexp {/q\\\\?\\[([0-9]+)\\\\?\\]} $nm -> b]} {
    } elseif {[regexp {/eq\\$} $nm]} { set b $W } else { lappend is_miss $nm; continue }
    if {[llength $starts]} {
      if {![dict exists $is_st $b]} { lappend is_miss "$nm:nostart"; continue }
      lassign [dict get $is_st $b] px py
    } else {
      set bt [$ff_blk findBTerm "${bus}\\[$b\\]"]
      if {$bt eq "NULL"} { lappend is_miss "$nm:nopin"; continue }
      set bb [$bt getBBox]
      set px [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $ff_dbu}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $ff_dbu}]
    }
    lassign [is_knee_site $px $py $lx $ly $face [expr {$k+1}] [expr {$n+1}] $dir $geometry $order] x y
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend is_miss $nm; continue }
    puts $is_fh "$nm\t$tag\t[expr {[lindex $got 0] / double($ff_dbu)}]\t[expr {[lindex $got 1] / double($ff_dbu)}]\t-"
    incr is_n; incr hit
  }
  if {!$hit} { lappend is_miss $inst }
}
# D-QC-FE-REACH 10-26 (plan internal_stations[].bit_route = "chain"): bit b of an in bus with n stations follows ITS
# OWN L route (normal to the in face first, then along) from its in pin to the face pin register it lands on, traced
# through the netlist: a zero-logic forwarder, or a leaf interface register (name glob core_glob) that then sits FIRM
# at its own hop point.  edges = n + 1 (+1 with the register); station k at arclength L (k+1)/edges, the register at
# L (n+1)/edges, so every planned hop is L / edges (<= the plan reach by the generator's n rule).
set is_core_done {}
set is_chain_worst 0.0
proc is_fwd_ffs {inst} {
  set out {}; set seen {}; set todo [list $inst]; set cnt 0
  while {[llength $todo] && $cnt < 400} {
    set i [lindex $todo 0]; set todo [lrange $todo 1 end]; incr cnt
    foreach o [ff_sig_iterms $i out] {
      set n [$o getNet]
      if {$n eq "NULL" || $n eq ""} continue
      foreach it [$n getITerms] {
        if {[[$it getMTerm] getIoType] ne "INPUT"} continue
        set j [$it getInst]; set jn [$j getName]
        if {[dict exists $seen $jn]} continue
        dict set seen $jn 1
        if {[ff_is_ff $j]} { lappend out $j } else { lappend todo $j }
      }
    }
  }
  return $out
}
proc is_chain {bus W names face core_glob tag} {
  # names: the bus's station instances in chain order (bind pads u_bin_<bus>_pad<j> first, then u_ist_<bus>_<j>)
  global ff_blk ff_dbu is_n is_miss is_fh is_core_done is_chain_worst
  set n [llength $names]
  set alt [join $names |]
  set st {}
  foreach i [$ff_blk getInsts] {
    set nm [string map {\\\\ {}} [$i getName]]
    # data flop q[b] (q for W == 1, yosys "q$_DFF_P_"), epoch flop eq (absent when synthesis merged it)
    if {![regexp "(^|\\[./\\])($alt)\\[./\\](q\\\\\\[(\\[0-9\\]+)\\\\\\]|q\\\\\\$|q\\$|eq\\\\\\$|eq\\$)" $nm -> _ sn f b]} continue
    if {![ff_is_ff $i]} continue
    if {[string match eq* $f]} { set b $W } elseif {$b eq ""} { set b 0 }
    dict set st "[lsearch -exact $names $sn],$b" $i
  }
  set lastE ""; set placed 0
  for {set b 0} {$b <= $W} {incr b} {
    if {![dict exists $st "[expr {$n-1}],$b"]} { continue }
    set pin [$ff_blk findBTerm "${bus}\\[$b\\]"]
    if {$pin eq "NULL"} { lappend is_miss "${bus}\\[$b\\]:nopin"; continue }
    set bb [$pin getBBox]
    set px [expr {([$bb xMin] + [$bb xMax]) / 2.0}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
    set core ""; set ends {}
    foreach f [is_fwd_ffs [dict get $st "[expr {$n-1}],$b"]] {
      set fn [string map {\\\\ {}} [$f getName]]
      if {[string match "*u_bout_*" $fn]} { lappend ends $f } elseif {[string match "*${core_glob}*" $fn] && $core eq ""} { set core $f }
    }
    if {$core ne ""} {
      foreach f [is_fwd_ffs $core] { if {[string match "*u_bout_*" [string map {\\\\ {}} [$f getName]]]} { lappend ends $f } }
    }
    if {[llength $ends]} {
      set ex 0.0; set ey 0.0
      foreach f $ends { lassign [$f getLocation] fx fy; set ex [expr {$ex + $fx}]; set ey [expr {$ey + $fy}] }
      set E [list [expr {$ex / [llength $ends]}] [expr {$ey / [llength $ends]}]]
      set lastE [list $E [expr {$core ne ""}]]
    } elseif {$lastE ne ""} {
      lassign $lastE E hc
      if {$hc && $core eq ""} { set core "-" }
    } else { lappend is_miss "${bus}\\[$b\\]:noend"; continue }
    lassign $E ex ey
    if {$face in {E W}} { set pts [list $px $py $ex $py $ex $ey] } else { set pts [list $px $py $px $ey $ex $ey] }
    set L [expr {abs($px - $ex) + abs($py - $ey)}]
    set edges [expr {$n + 1 + ($core ne "" ? 1 : 0)}]
    set h [expr {$L / $edges / $ff_dbu}]
    if {$h > $is_chain_worst} { set is_chain_worst $h }
    for {set k 0} {$k < $n} {incr k} {
      if {![dict exists $st "$k,$b"]} { lappend is_miss "${bus}_${k}\\[$b\\]"; continue }
      set f [dict get $st "$k,$b"]
      lassign [ff_point_at $pts [expr {$L * ($k + 1) / $edges}]] x y
      set got [ff_put_near $f $x $y]
      if {$got eq ""} { lappend is_miss [$f getName]; continue }
      puts $is_fh "[$f getName]\\t$tag\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
      incr is_n; incr placed
    }
    if {$core ne "" && $core ne "-" && ![dict exists $is_core_done [$core getName]]} {
      dict set is_core_done [$core getName] 1
      lassign [ff_point_at $pts [expr {$L * ($n + 1) / $edges}]] x y
      set got [ff_put_near $core $x $y]
      if {$got ne ""} {
        puts $is_fh "[$core getName]\\t${tag}:core\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
        incr is_n
      } else { lappend is_miss [$core getName] }
    }
  }
  puts "OT_ISTATIONS chain $bus: $placed station flops FIRM, worst planned hop so far [format %.1f $is_chain_worst] um"
}
"""

EXACT_BANK_TCL = r'''
# Generic exact internal/face FF banks: no spiral or post-measurement placement.
proc is_exact_bank {inst W sites fw fh tag {epoch_unobserved 0}} {
  global ff_blk ff_dbu ff_orient ff_sw ff_x0 ff_y0 ff_x1 ff_y1 is_n is_fh
  set seen {}
  foreach i [$ff_blk getInsts] {
    set nm [string map {\\ {}} [$i getName]]
    if {![string match "*${inst}\[./\]*" $nm]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    if {[regexp {[/.]q\[([0-9]+)\]} $nm -> bit]} {
    } elseif {[regexp {[/.]eq(\$|$)} $nm]} { set bit $W
    } elseif {$W == 1 && [regexp {[/.]q\$} $nm]} { set bit 0
    } else { error "unmapped flop in exact internal bank: $nm" }
    if {$bit < 0 || $bit > $W || [dict exists $seen $bit]} {
      error "duplicate/out-of-range exact internal bank bit: $nm"
    }
    lassign [lindex $sites $bit] x y
    set cx [expr {round($x*$ff_dbu)}]; set cy [expr {round($y*$ff_dbu)}]
    if {![dict exists $ff_orient $cy] || ($cx-$ff_x0)%$ff_sw != 0} {
      error "exact internal bank site is not on row/site: $nm $x $y"
    }
    set m [$i getMaster]
    if {[$m getWidth] > $fw*$ff_dbu+1 || [$m getHeight] > $fh*$ff_dbu+1} {
      error "exact internal bank flop exceeds its footprint: $nm"
    }
    if {$cx < $ff_x0 || $cy < $ff_y0 || $cx+[$m getWidth] > $ff_x1 || $cy+[$m getHeight] > $ff_y1} {
      error "exact internal bank site outside core: $nm"
    }
    $i setPlacementStatus PLACED
    $i setOrient [dict get $ff_orient $cy]
    $i setLocation $cx $cy
    $i setPlacementStatus FIRM
    dict set seen $bit 1
    puts $is_fh "$nm\t$tag\t$x\t$y\t-"
    incr is_n
  }
  for {set bit 0} {$bit < $W} {incr bit} {
    if {![dict exists $seen $bit]} { error "exact internal bank $inst missing payload bit $bit" }
  }
  if {![dict exists $seen $W]} {
    if {!$epoch_unobserved} { error "exact internal bank $inst missing observed/unproved epoch" }
    puts "OT_ISTATIONS exact bank $inst: all $W payload flops; unobserved epoch absent, site reserved"
  }
}
'''


# (class, RTL launch side, regex on 'launch|capture' of the plan entry (inst paths relative to the leaf u_lf), plan
#  launch is the RTL launch side?) -- first match wins.  Classes: CS_<CLASS>_D on ot_s81sl_leaf.
_P = r"core:u_lf\."
CORE_CLASSES = [
    ("cs", rf"^{_P}u_vn\.u_a\.c_s\|u_lf\.u_vn\.u_b", True),
    ("hi", rf"^{_P}u_vn\.u_[ab]\.(hq_|hr_)\w+\|u_lf\.u_vp\.g_ln\[\d+\]\.u_l$", True),    # glue -> lane
    ("ho", rf"^{_P}u_vn\.u_[ab]\.hw_\w+\|u_lf\.u_vp\.g_ln\[\d+\]\.u_l$", False),          # lane -> glue -> vn
    ("vni", rf"^{_P}u_vn\.u_[ab]\.(n_go|n_pre|wl_\w+|hw_\w+|hr_\w+)\|u_lf\.u_vp\.u_b[01]$", False),
    ("vno", rf"^{_P}u_vn\.u_[ab]\.hq_\w+\|u_lf\.u_vp\.u_b[01]$", True),
    ("y", rf"^{_P}u_vn\.u_[ab]\.y\w*\|u_lf\.u_vq\.", True),
    ("y", rf"^{_P}u_vq\.y\w*\|u_lf\.u_vn\.", False),
    ("u", rf"^{_P}u_vq\.(u|um)\w*\|u_lf\.u_vs\.", False),
    ("u", rf"^{_P}u_vs\.(u|um)\w*\|u_lf\.u_vq\.", True),
    ("sw", rf"^{_P}u_vs\.sw_\w+\|u_lf\.u_vsw\.i_", True),
    ("swr", rf"^{_P}u_vs\.sw_\w+\|u_lf\.u_vsw\.o_", False),
    ("sw", rf"^{_P}u_vsw\.i_\w+\|u_lf\.u_vs\.", False),
    ("swr", rf"^{_P}u_vsw\.o_\w+\|u_lf\.u_vs\.", True),
    ("ra", rf"^{_P}u_vs\.ra_\w+\|u_lf\.u_rxsf\.", True),
    ("rar", rf"^{_P}u_vs\.ra_\w+\|u_lf\.u_rxsb\.", False),
    ("rar", rf"^{_P}u_rxsb\.o_\w+\|u_lf\.u_vs\.", True),
    ("ve", rf"^{_P}u_vs\.ve_(r|a)\w*\|u_lf\.u_ve\.", True),
    ("ver", rf"^{_P}u_vs\.ve_\w+\|u_lf\.u_ve\.", False),        # ve_p* / ve_o* / fault: ve -> vs
    ("ve", rf"^{_P}u_ve\.u_[ms]\.(r|a)_\w+\|u_lf\.u_vs\.", False),
    ("ver", rf"^{_P}u_ve\.u_[ms]\.\w+\|u_lf\.u_vs\.", True),
    ("pvs", rf"^{_P}u_vs\.x_q\w+\|u_lf\.u_vp\.u_b[01]$", False),
    ("vsp", rf"^{_P}u_vs\.x_\w+\|u_lf\.u_vp\.u_b[01]$", True),
]
CLASS_PARAM = {c: f"CS_{c.upper()}_D" for c, _, _ in CORE_CLASSES if c != "cs"}
H_CLASSES = ("hi", "ho")
LEAF_INST = "u_lf"


def core_class(e):
    key = f"{e.get('launch', e['conn'].split('|')[0])}|{e.get('capture', e['conn'].split('|')[-1].replace('core:', ''))}"
    for c, rx, fwd in CORE_CLASSES:
        if re.match(rx, key):
            lane = re.search(r"g_ln\[(\d+)\]", key)
            return c, fwd, int(lane.group(1)) if lane and c in H_CLASSES else None
    return None, None, None


def _glob(path):
    """inst path -> Tcl glob: '.' or '/' separators, literal brackets (is_place strips name escapes)."""
    return "*" + path.replace(".", "?").replace("[", "\\[").replace("]", "\\]") + "[./]*"


# DIE-S81-70 11-06 (spec s81_istations_native_spec_1106, form A1): the S81 native binds are FLAT (ot_s81sl_leaf /
# ot_s81sl_vp / ot_s81sl_cst dissolved): the leaf's station chains are bound at the depths the slice instance sets
# (LF_CS_*), as registers named after the flattened path (u_lf.u_vp.g_ln[9].u_cst_hi.gd.s[0].u -> ..u_vp_g_ln_9_u_cst_hi_
# gd_s_0_u..).  Native mode: no re-parameterisation (the depths are bound), the bound depth per class is COUNTED from
# the stage registers and must equal the plan's (fail closed), and the sites use flat-name globs.
NATIVE_MARK = re.compile(r"\bw_(?:u_lf\d*_)?u_vp_g_ln_\d+_u_cst_h[io]_")  # KW-FIX-27: u_lf<k>_ of the image-flat leaf binds


def _flat(path):
    """leaf-relative inst path -> the bind's flattened name stem (u_lf. prefix dropped, [n] -> _n, . -> _)."""
    path = path[len(LEAF_INST) + 1:] if path.startswith(LEAF_INST + ".") else path
    return re.sub(r"\[(\d+)\]", r"_\1", path).replace(".", "_")


LF_PFX = r"(?:u_lf\d*_)?"   # S81-LEAF-FLOOR-2 11-12: image-flat leaf binds name their stage registers g_u_lf<k>_u_... (KW-FIX-27)


def native_params(txt):
    """bound CS_* of a flat native leaf bind, counted from the stage registers (d stages = s_0..s_{d-1}).
    S81-LEAF-FLOOR-2 11-12: the image-flat u_lf<k>_ prefix is allowed in the register names too (it was only allowed in
    NATIVE_MARK, so every lf-prefixed ordinary leaf bind counted 0 on every class: 61 of the 75 r12ng leaf types)."""
    def stages(rx):
        return len({int(j) for j in re.findall(rx + r"_gd_s_(\d+)_u_", txt)})
    have = {}
    for c in {c for c, _, _ in CORE_CLASSES if c != "cs"}:
        if c in H_CLASSES:
            shared = stages(rf"\bg_{LF_PFX}u_vp_g_{c[0]}{c[1]}g_\d+_u_cst")
            lane = max((stages(rf"\bg_{LF_PFX}u_vp_g_ln_{l}_u_cst_{c}") for l in range(16)), default=0)
            have[CLASS_PARAM[c]] = shared + lane
            have[f"CS_{c.upper()}_GS"] = shared
        else:
            have[CLASS_PARAM[c]] = stages(rf"\bg_{LF_PFX}u_cst_{c}")
    groups = {int(g) for g in re.findall(rf"\bg_{LF_PFX}u_vp_g_h[io]g_(\d+)_u_cst_gd_s_", txt)}
    have["CS_H_G"] = 16 // len(groups) if groups else 4
    return have


def leaf_params(txt):
    m = re.search(rf"\bot_s81sl_leaf\b\s*(#\((?P<p>(?:[^()]|\([^()]*\))*)\))?\s*{LEAF_INST}\s*\(", txt)
    if not m:
        raise SystemExit(f"kit_istations: core<->core stations planned but the bound module has no ot_s81sl_leaf {LEAF_INST}")
    return m, {k: int(v) for k, v in re.findall(r"\.(CS_\w+)\s*\(\s*(\d+)\s*\)", m.group("p") or "")}


# DIE-S81-71 11-06 (spec s81_istations_native_spec_1106 "col st -> t0", COORD 17:0x option A1): the col_h9/h10 r0 status
# hop u_r<i>.u_s<k>.st -> u_r<i>.u_t<k'> (core<->core, 657-856 um) is realised IN the col plan_kit RTL as a reset register
# chain cst_st_s0..s<D-1> in front of u_t0.c0 (rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h*_l4_lp_plan_kit.sv).  The bound
# depth is COUNTED from the bound text and must equal the plan's (fail closed); stage j is FIRM at regs_um[j].
COL_ST = re.compile(r"^u_r\d+\.u_s\d+\.st\|u_r\d+\.u_t\d+(\.c[01])?$")


def _col_key(e):
    a, c = e["conn"].split("|")[0], e["conn"].split("|")[-1]
    return f"{e.get('launch', a.replace('core:', ''))}|{e.get('capture', c.replace('core:', ''))}"


def _col_chain(txt, launch, capture):
    """reg names of the station chain launch(st) -> capture.c0 in a bound text, launch side first; None = no instance"""
    # the bind may dissolve the leading hierarchy (r0_nx types: u_u_t0 / w_u_s0_st, no u_r0_): match the longest suffix
    cp, lp = capture.split("."), launch.split(".")
    for d in range(min(len(cp), len(lp))):
        ci = "_".join(cp[d:])
        m = re.search(r"\b\w*" + re.escape(ci) + r"\s*\((.*?)\n\s*\);", txt, re.S)
        if m:
            launch = ".".join(lp[d:])
            break
    else:
        return None
    c0 = re.search(r"\.c0\(\s*([\w$]+)", m.group(1))
    if not c0:
        return None
    net, regs, lw = c0.group(1), [], launch.replace(".", "_")
    for _ in range(16):
        if lw in net:
            return regs[::-1]
        am = re.search(r"\bassign\s+" + re.escape(net) + r"\s*=\s*(\w+)\s*;", txt)
        q = am.group(1) if am else net
        dm = re.search(r"\belse\s+" + re.escape(q) + r"\s*<=\s*([\w$]+)", txt)
        if not dm:
            return []
        regs.append(q)
        net = dm.group(1)
    return []


def col_st_stations(t, txt, tcl, rep):
    """col st -> t0 entries of this type (realised by the col RTL); returns them so core_stations skips them."""
    es = [e for e in t.get("internal_stations", []) if not e.get("conn", "").startswith("bus:") and COL_ST.match(_col_key(e))]
    if not es:
        return []
    ns = sorted({len(e["regs_um"]) for e in es})
    regs = sorted({tuple(tuple(r) for r in e["regs_um"]) for e in es})
    if len(ns) != 1 or len(regs) != 1:
        raise SystemExit(f"kit_istations: col st stations: entries disagree (depths {ns}, {len(regs)} site lists; fail closed)")
    k = _col_key(es[0]).split("|")
    chain = _col_chain(txt, k[0].rsplit(".", 1)[0] + "_st" if k[0].endswith(".st") else k[0], k[1].split(".c")[0])
    if chain is None:
        have = sorted({int(j) for j in re.findall(r"cst_st_s(\d+)(?!\d)", txt)})
        chain = [f"cst_st_s{j}" for j in have] if have == list(range(len(have))) else []
    for q, (x, y) in zip(chain, regs[0]):
        tcl.append(f"is_place {{*{q}*}} {x} {y} cst:st")
    # KW-FIX-27 (OWNER 11-03 only sign-off blocks): an older bind without the chain builds as bound; sign-off judges the hop
    rep.append(dict(col_st=dict(stages=ns[0], entries=len(es), regs=chain, sites=[list(r) for r in regs[0]],
                                **({"bound_stages": len(chain)} if len(chain) != ns[0] else {}))))
    return es


def core_stations(t, txt, apply, htree, tcl, rep):
    """Map core<->core entries onto the leaf's station chains; returns the (maybe re-parameterised) bound text.
    KW-FIX-27 (OWNER 11-03 only sign-off blocks): plan stations here are sites, the bound RTL holds the stages.  One
    interface is one chain, so its depth is the deepest entry, sited from its deepest entries.  What the bound text
    does not show (no class, a depth a flat bind cannot count) is reported in the receipt, and GPL places those flops."""
    groups = {}
    unmapped = []
    col = col_st_stations(t, txt, tcl, rep)
    for e in t.get("internal_stations", []):
        if e.get("conn", "").startswith("bus:") or any(e is c for c in col):
            continue
        c, fwd, lane = core_class(e)
        if c is None:
            unmapped.append(e["conn"])
            continue
        regs = [list(r) for r in e["regs_um"]]
        if not fwd:
            regs.reverse()
        groups.setdefault((c, lane), []).append((regs, int(e.get("bits", 1)), e["conn"]))
    if unmapped:
        rep.append(dict(core_unmapped=sorted(set(unmapped))))
    if not groups:
        return txt
    native = not re.search(rf"\bot_s81sl_leaf\b[^;]*?\b{LEAF_INST}\s*\(", txt) and bool(NATIVE_MARK.search(txt))
    depth = {}
    merged = {}
    for key, es in list(groups.items()):
        c, lane = key
        deep = max(len(r) for r, _, _ in es)
        if len({len(r) for r, _, _ in es}) > 1:
            merged[f"{c}{'' if lane is None else lane}"] = sorted({len(r) for r, _, _ in es})
            groups[key] = es = [x for x in es if len(x[0]) == deep]
        if c == "cs" and deep and native:
            rep.append(dict(cs_stations_unrealized=deep))   # the flat bind's RTL holds no such stage; sign-off judges the hop
            continue
        if c == "cs" and deep:
            raise SystemExit("kit_istations: vn_a -> vn_b c_s stations planned, but vn_b's chain adders read c_s on a "
                             "fixed edge (hard cores): no RTL realises them; re-plan vn_a / vn_b within reach")
        depth[c] = max(depth.get(c, 0), deep)
    h_lanes = {}
    if "hi" in depth or "ho" in depth:
        # DIE-S81-69 11-06: the leaf RTL applies CS_HI_D / CS_HO_D to all 16 lanes (one depth per class: the static
        # schedule holds whatever lanes the plan sited).  The planner sites a lane's stations only where that lane's
        # hop exceeds reach, so hi and ho may be sited on different lanes (kv_leaf t1/t3/t4/t5).  A lane without a
        # sited entry for a class gets its stage(s) placed by GPL, exactly like the lanes sited in neither class;
        # the unequal-depth checks above still fail closed.  Reported (h_lanes), not failed.
        lanes = {lane for (c, lane) in groups if c in H_CLASSES}
        for c in H_CLASSES:
            if c in depth:
                sited = sorted(l for (cc, l) in groups if cc == c)
                h_lanes[c] = dict(sited=sited, unsited_of_planned=sorted(lanes - set(sited)))
    if native:
        m, have = None, native_params(txt)
    else:
        m, have = leaf_params(txt)
    want = {CLASS_PARAM[c]: d for c, d in depth.items() if c != "cs"}
    G, GSI, GSO = htree
    if apply and not native:
        want.update(CS_H_G=G, CS_HI_GS=min(GSI, want.get("CS_HI_D", 0)), CS_HO_GS=min(GSO, want.get("CS_HO_D", 0)))
        merged = dict(have)
        merged.update(want)
        ps = ", ".join(f".{k}({v})" for k, v in sorted(merged.items()))
        rest = [p.strip() for p in re.split(r",(?![^()]*\))", m.group("p") or "") if p.strip() and not p.strip().startswith(".CS_")]
        newp = ", ".join(rest + [ps])
        txt = txt[:m.start()] + f"ot_s81sl_leaf #({newp}) {LEAF_INST} (" + txt[m.end():]
        m, have = leaf_params(txt)
    counted = {}
    for k, v in sorted(want.items()):
        if k.endswith("_D") and have.get(k, 0) != v:
            if not native:
                raise SystemExit(f"kit_istations: leaf RTL {k} = {have.get(k, 0)} but the plan stations {v} stage(s) "
                                 "(--apply sets the plan's depths)")
            counted[k] = dict(plan=v, counted=have.get(k, 0))
    if native:
        counted.update({k: dict(plan=0, counted=v) for k, v in have.items() if k.endswith("_D") and v and k not in want})
    G, GSI, GSO = have.get("CS_H_G", 4), have.get("CS_HI_GS", 0), have.get("CS_HO_GS", 0)

    def centroid(es, j):
        es = [x for x in es if len(x[0]) > j]
        w = sum(b for _, b, _ in es)
        return (round(sum(r[j][0] * b for r, b, _ in es) / w, 3), round(sum(r[j][1] * b for r, b, _ in es) / w, 3))

    sites = []
    for c, d in sorted(depth.items()):
        if c in H_CLASSES:
            gs = GSI if c == "hi" else GSO
            for j in range(d):
                shared = j < gs if c == "hi" else j >= d - gs
                if shared:
                    for g in range(16 // G):
                        es = [x for l in range(G * g, G * g + G) for x in groups.get((c, l), []) if len(x[0]) > j]
                        if not es:
                            continue                # no sited lane in this group: GPL places the shared stage
                        jj = j if c == "hi" else j - (d - gs)
                        sites.append((f"{LEAF_INST}.u_vp.g_{c}g[{g}].u_cst.gd.s[{jj}].u", centroid(es, j), c))
                else:
                    jj = j - gs if c == "hi" else j
                    for l in sorted(l for (cc, l) in groups if cc == c):
                        if any(len(x[0]) > j for x in groups[(c, l)]):      # a shallower lane: GPL places this stage
                            sites.append((f"{LEAF_INST}.u_vp.g_ln[{l}].u_cst_{c}.gd.s[{jj}].u", centroid(groups[(c, l)], j), c))
        else:
            for j in range(d):
                sites.append((f"{LEAF_INST}.u_cst_{c}.gd.s[{j}].u", centroid(groups[(c, None)], j), c))
    for nm, (x, y), c in sites:
        tcl.append(f"is_place {{{'*' + _flat(nm) + '_*' if native else _glob(nm)}}} {x} {y} cst:{c}")
    rep.append(dict(core_classes={c: dict(param=CLASS_PARAM.get(c), stages=d,
                                          entries=sum(len(v) for (cc, _), v in groups.items() if cc == c))
                                  for c, d in sorted(depth.items())},
                    h_tree=dict(G=G, GS_IN=GSI, GS_OUT=GSO), h_lanes=h_lanes, placed_stages=len(sites),
                    **({"merged_depths": merged} if merged else {}), **({"native_depth_differs": counted} if counted else {}),
                    bind="native_flat" if native else "leaf_instance"))
    return txt


# CODEX-PICKUP-KV 11-01 (KV HHP joint event): a relay key below a clock-landing ring instance (u_cland_*) names an
# EXISTING ring flop that landing_placement.tcl packs into its ring band; that hook runs AFTER istations.tcl
# (face_flops.tcl tail), so such a key is placed by relay_sites_post_tcl(), sourced after the landing hook.
RING_KEY = re.compile(r"(^|[./])u_cland_")


def _relay_dict(rs):
    return "rs_place_all [dict create " + " ".join(f"{{{k}}} {{{v[0]:g} {v[1]:g}}}" for k, v in sorted(rs.items())) + "]"


MACRO_CROSS_TCL = r"""# DIE-HEAD-79 11-07 plan macro_cross (opt-in partition_types[].macro_cross): a registered hop that must cross a hard core.
# Repair buffers cannot sit over the core, so legalisation dropped them in the channels beside it: the net detoured on low
# metal (hd_tile R 9.8 kohm, slew up to 645 ps) where the straight M6/M7 crossing measured R 3.6 kohm, C 28 fF.  One strong
# driver at the launch side, then the net stays untouched by every repair step.  A buffer only: function and cycles unchanged.
proc mc_drive_all {sink_glob sink_pin cell} {
  global ff_blk ff_dbu is_fh is_miss
  set m [[ord::get_db] findMaster $cell]
  if {$m eq "NULL"} { error "OT_MACRO_CROSS: no master $cell" }
  set n 0
  foreach i [$ff_blk getInsts] {
    set nm [string map {\\ {}} [$i getName]]
    if {![string match $sink_glob $nm]} continue
    set d [$i findITerm $sink_pin]
    set src [$d getNet]
    if {$src eq "NULL"} { lappend is_miss "macro_cross:$nm"; continue }
    set drv ""
    foreach t [$src getITerms] { if {[$t isOutputSignal]} { set drv [$t getInst] } }
    if {$drv eq ""} { lappend is_miss "macro_cross:$nm:nodrv"; continue }
    # the logic cell behind a Q inverter is not placed yet: the launch site is the flop that feeds it
    set at $drv
    if {![string match "*DFF*" [[$at getMaster] getName]]} {
      foreach t [$at getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} {
        foreach u [[$t getNet] getITerms] { if {[$u isOutputSignal] && [string match "*DFF*" [[[$u getInst] getMaster] getName]]} { set at [$u getInst] } } } }
    }
    set b [odb::dbInst_create $ff_blk $m "ot_mc_drv_$n"]
    set w [odb::dbNet_create $ff_blk "ot_mc_x_$n"]
    $w setSigType SIGNAL
    $d disconnect; $d connect $w
    foreach t [$b getITerms] {
      if {[$t isInputSignal]} { $t connect $src } elseif {[$t isOutputSignal]} { $t connect $w }
    }
    lassign [$at getLocation] ax ay
    set got [ff_put_near $b $ax $ay]
    if {$got eq ""} { lappend is_miss "macro_cross:$nm:noplace"; continue }
    puts $is_fh "[$b getName]\trelay\t[expr {[lindex $got 0] / double($ff_dbu)}]\t[expr {[lindex $got 1] / double($ff_dbu)}]\t-"
    $w setDoNotTouch 1; $b setDoNotTouch 1
    incr n
  }
  puts "OT_MACRO_CROSS $sink_glob: $n drivers $cell, nets dont_touch"
  if {!$n} { error "OT_MACRO_CROSS: no sink matched $sink_glob" }
}
"""


def macro_cross_lines(tn, t):
    """plan macro_cross -> istations.tcl lines; [] when absent.  Entries: {sink_glob, sink_pin, cell}"""
    mc = t.get("macro_cross") or []
    for e in mc:
        if set(e) != {"sink_glob", "sink_pin", "cell"}:
            raise SystemExit(f"kit_istations: {tn}: macro_cross entry {e}")
    if not mc:
        return []
    return [MACRO_CROSS_TCL] + ["mc_drive_all {%s} %s %s" % (e["sink_glob"], e["sink_pin"], e["cell"]) for e in mc]


def relay_sites_lines(tn, t):
    """plan relay_sites -> istations.tcl lines (RELAY_TCL + rs_place_all of the non-ring keys); [] when absent"""
    rs = t.get("relay_sites") or {}
    if not rs:
        return []
    for k, v in rs.items():
        if not (isinstance(v, list) and len(v) == 2 and all(isinstance(a, (int, float)) for a in v)):
            raise SystemExit(f"kit_istations: {tn}: relay_sites[{k}] must be [x_um, y_um]")
    pre = {k: v for k, v in rs.items() if not RING_KEY.search(k)}
    return [RELAY_TCL] + ([_relay_dict(pre)] if pre else [])


def relay_sites_post_tcl(tn, t):
    """ring-flop relay keys (RING_KEY) -> face_flops.tcl tail lines run after the landing placement hook (the ring
    band packing would otherwise move them back); None when there is none.  Needs rs_place_all from istations.tcl."""
    relay_sites_lines(tn, t)                                            # same validation
    post = {k: v for k, v in (t.get("relay_sites") or {}).items() if RING_KEY.search(k)}
    if not post:
        return None
    return ("uplevel #0 {\nset is_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]\n" + _relay_dict(post)
            + "\nclose $is_fh\n}")


def relay_sites_only_tcl(tn, t):
    """DIE-KV-60 11-01: a bound kit with plan relay_sites but no native station sidecar (e.g. the KV hard PHY
    wrappers) still gets its FIRM relay sites: the same istations.tcl form, relay part only; None when absent."""
    rs = relay_sites_lines(tn, t)
    if not rs:
        return None
    return "\n".join([TCL_HEAD] + rs + macro_cross_lines(tn, t) + ["close $is_fh\nputs \"OT_ISTATIONS placed $is_n flops FIRM (missing: [llength $is_miss] $is_miss)\""]) + "\n"


def soft_plan_cells(tn, t):
    """Sited logical cells that remain soft after authoritative hard-view resolution.

    A contents entry need not repeat a LEF carried by hard_cores. Use the same
    physical identity/view resolver as gen_phys before emitting DFF guides.
    Partial physical_parts retain their existing soft-container treatment.
    """
    hard = set()
    if any(c.get('lef') for c in t.get('hard_cores', [])):
        import gen_phys
        from types import SimpleNamespace
        placed = {(row[0], row[1]) for row in gen_phys.type_macros(SimpleNamespace(types={tn: t}), tn)}
        for c in t.get('hard_cores', []):
            if not c.get('lef'):
                continue
            identity = (gen_phys.content_physical_identity(c)
                        if 'physical_inst' in c or 'physical_master' in c
                        else (c['inst'], c.get('module', c['inst'])))
            if identity in placed:
                hard.add(c['inst'])
    return [c for c in t.get('contents', [])
            if 'origin_um' in c and not c.get('lef') and c['inst'] not in hard]


def core_pin_stations(tn, t, txt, man, tcl, rep, plan_dir=None, pins=None):
    """SUL0-PINFACE-1 (DIE-QC-97 11-10, COORD geom-1235-1110): per-hard-core pin-face station chains.
    A bus whose face register serves several hard cores at different distances (QC su_lN: u_bin_x_su_c_i -> four
    lane macros, lane3 1.27 mm away) cannot be fixed by one bus chain: its stations sit at one place.  Entries with
    'core' (a hard_cores inst) and 'core_bits' (the bus bits that core reads / drives through this chain) get their
    OWN chain u_ist_<bus>__<core>_<g>_<j> (ot_dp_st, full bus width; bits outside core_bits have no load / a 0 input
    and synthesis drops them):
      * in bus : face register (after bind pads) -> chain -> ONLY the core's instance reads <bus>_q[b], b in core_bits;
      * out bus: core outputs -> chain -> u_bout_<bus>.d bit b (every d bit must belong to exactly one chain).
    Every chain of one bus carries the SAME number of stations (len(regs_um)) so the bus keeps one latency (fail closed
    otherwise); placement is the per_bit is_bits form (each bit on its own L from its face pin to leaf_um, the kit knee
    rule, <= 403 um) with leaf_um at the core pin-face centroid of the chain's bits.
    'core' may be a LIST of hard cores (DIE-QC-97 11-10, l1 east cws0_o strip): ONE chain serves them all (in bus: every
    listed core reads its bits of core_bits from the chain's last station, so a bit two cores share crosses the strip
    once), chain u_ist_<bus>__<core1>_<core2>.._<g>_<j>.  After insertion every core read of a chain is checked to be
    the LAST station of a chain listing that core (check_core_delay: one bus = one latency per consumer).  Returns the
    edited text."""
    es = [e for e in t.get("internal_stations", []) if e.get("core")]
    if not es:
        return txt
    cores = {c["inst"] for c in t.get("hard_cores", [])}
    by = {}
    for e in es:
        if e.get("bit_route") != "per_bit" or "leaf_um" not in e or not e.get("conn", "").startswith("bus:"):
            raise SystemExit(f"kit_istations: {tn}: core station {e.get('conn')} {e.get('core')}: needs bus conn, "
                             "bit_route per_bit and leaf_um")
        cl = core_list(e)
        if len(set(cl)) != len(cl) or any(c not in cores for c in cl):
            raise SystemExit(f"kit_istations: {tn}: core station on unknown / repeated hard core {e['core']}")
        by.setdefault(e["conn"][4:], []).append(e)
    for bus, bes in by.items():
        b = next((x for x in t["buses"] if x["name"] == bus), None)
        if b is None or "face" not in b:
            raise SystemExit(f"kit_istations: {tn}: core station on unknown / faceless bus {bus}")
        ns = {len(e["regs_um"]) for e in bes}
        if len(ns) != 1 or 0 in ns:
            raise SystemExit(f"kit_istations: {tn} {bus}: core chains carry unequal / zero depths {sorted(ns)} "
                             "(one bus = one latency)")
        k = ns.pop()
        n = gen_rtl.sv_id(bus)
        W = bound_bus_width(tn, b, txt, man)
        if re.search(rf"\bu_ist_{re.escape(n)}_(\d+)\b", txt) or re.search(rf"\bu_ist_{re.escape(n)}__", txt):
            raise SystemExit(f"kit_istations: {tn} {bus}: stations already inserted (run on a fresh kit-rtl copy)")
        owner = {}
        for gi, e in enumerate(bes):
            for bit in e["core_bits"]:
                if not 0 <= int(bit) < W:
                    raise SystemExit(f"kit_istations: {tn} {bus}: core_bits {bit} outside bound width {W}")
                if b["dir"] == "out" and int(bit) in owner:
                    raise SystemExit(f"kit_istations: {tn} {bus}: out bit {bit} in two core chains")
                owner.setdefault(int(bit), []).append(gi)
        pads = sorted(int(m) for m in re.findall(rf"\bu_b(?:in|out)_{re.escape(n)}_pad(\d+)\b", txt))
        decl, body, names_all = [], [], []
        chains = []
        tags = [f"{n}__" + "_".join(gen_rtl.sv_id(c) for c in core_list(e)) + f"_{gi}" for gi, e in enumerate(bes)]
        for gi, e in enumerate(bes):
            chains.append([f"u_ist_{tags[gi]}_{j}" for j in range(k)])
        if b["dir"] == "in":
            q, eq = (f"{n}_p{pads[-1]}_q", f"{n}_p{pads[-1]}_eq") if pads else (f"{n}_q", f"{n}_eq")
            lines = txt.split("\n")
            for gi, e in enumerate(bes):
                tag = tags[gi]
                cq, ceq = q, eq
                for j in range(k):
                    decl.append(f"    wire [{W - 1}:0] {tag}_s{j}_q;\n    wire {tag}_s{j}_eq;  // kit_istations core chain")
                    body.append(f"    ot_dp_st #(.W({W})) u_ist_{tag}_{j} (.clk(clk), .rst_n(rst_n), .d({cq}), .ea({ceq}), "
                                f".q({tag}_s{j}_q), .eq({tag}_s{j}_eq));  // kit_istations: FIRM core pin-face station")
                    cq, ceq = f"{tag}_s{j}_q", f"{tag}_s{j}_eq"
                want = {int(x) for x in e["core_bits"]}
                seen = set()
                for core in core_list(e):
                    hit = core_line(lines, core)
                    if len(hit) != 1:
                        raise SystemExit(f"kit_istations: {tn} {bus}: {len(hit)} instance lines of core {core}")
                    got = set()

                    def sub(m, cq=cq, want=want, got=got, core=core):
                        if m.group(1) is None:          # bare read: only a 1-bit bus ([0:0]) reads its bit 0 this way
                            if W != 1:
                                raise SystemExit(f"kit_istations: {tn} {bus}: bare whole-bus read of {q} by {core}")
                            bit = 0
                        else:
                            bit = int(m.group(1))
                        if bit in want:
                            got.add(bit)
                            return f"{cq}[{bit}]"
                        return m.group(0)
                    lines[hit[0]] = re.sub(rf"\b{re.escape(q)}(?:\[(\d+)\]|(?![\w$\[]))", sub, lines[hit[0]])
                    if not got:
                        raise SystemExit(f"kit_istations: {tn} {bus}: core {core} of shared chain {tag} reads none of "
                                         "its core_bits")
                    seen |= got
                if seen != want:
                    raise SystemExit(f"kit_istations: {tn} {bus}: core {e['core']} does not read bits "
                                     f"{sorted(want - seen)[:8]} of core_bits")
            txt = "\n".join(lines)
            for ln in txt.split("\n"):      # every reader must now be a core chain
                if (re.search(rf"\b{re.escape(q)}(?:\[\d+\]|(?![\w$\[]))", ln)
                        and not re.search(rf"\bu_ist_{re.escape(n)}__|\bu_bin_{re.escape(n)}(_pad\d+)?\s*\(", ln)
                        and not re.match(r"^\s*(wire|reg|logic)\b", ln)):
                    raise SystemExit(f"kit_istations: {tn} {bus}: {q} still read outside the core chains: {ln.strip()[:120]}")
        else:
            m = re.search(rf"^(\s*ot_dp_ste?\s+#\(\.W\({W}\)\)\s+u_bout_{re.escape(n)}\s*\(.*?\.d\()(\{{[^}}]*\}}|[^)]*)"
                          rf"(\),\s*\.ea\()([^)]*)(\).*)$", txt, re.M)
            if not m:
                raise SystemExit(f"kit_istations: {tn}: no u_bout_{n} face register line to feed")
            d0, ea0 = m.group(2).strip(), m.group(4)
            els = [x.strip() for x in (d0[1:-1] if d0.startswith("{") else d0).split(",")]
            bits = []                          # MSB-first element per bit (expand part selects)
            for el in els:
                ps = re.fullmatch(r"([\w$]+)\s*\[(\d+):(\d+)\]", el)
                if ps:
                    bits += [f"{ps.group(1)}[{x}]" for x in range(int(ps.group(2)), int(ps.group(3)) - 1, -1)]
                else:
                    bits.append(el)
            if len(bits) != W:
                raise SystemExit(f"kit_istations: {tn} {bus}: u_bout d has {len(bits)} bits != {W} (whole-wire "
                                 "references are not expanded; fail closed)")
            miss = [W - 1 - i for i in range(W) if (W - 1 - i) not in owner]
            if miss:
                raise SystemExit(f"kit_istations: {tn} {bus}: u_bout d bits {miss[:8]} belong to no core chain")
            fin = []
            for gi, e in enumerate(bes):
                tag = tags[gi]
                cd = "{" + ", ".join(bits[i] if owner[W - 1 - i] == [gi] else "1'b0" for i in range(W)) + "}"
                cq, ceq = cd, ea0
                for j in range(k):
                    decl.append(f"    wire [{W - 1}:0] {tag}_s{j}_q;\n    wire {tag}_s{j}_eq;  // kit_istations core chain")
                    body.append(f"    ot_dp_st #(.W({W})) u_ist_{tag}_{j} (.clk(clk), .rst_n(rst_n), .d({cq}), .ea({ceq}), "
                                f".q({tag}_s{j}_q), .eq({tag}_s{j}_eq));  // kit_istations: FIRM core pin-face station")
                    cq, ceq = f"{tag}_s{j}_q", f"{tag}_s{j}_eq"
                fin.append((cq, ceq))
            dfin = "{" + ", ".join(f"{fin[owner[W - 1 - i][0]][0]}[{W - 1 - i}]" for i in range(W)) + "}"
            line = m.group(1) + dfin + m.group(3) + fin[0][1] + m.group(5)
            line = re.sub(r"^(\s*)ot_dp_ste\b", r"\1ot_dp_st", line)
            txt = txt[:m.start()] + line + txt[m.end():]
        txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
        if b["dir"] == "in":
            check_core_delay(tn, bus, txt, [(tags[gi], core_list(e)) for gi, e in enumerate(bes)], k, q)
        for gi, e in enumerate(bes):
            lx, ly = e["leaf_um"]
            st = ""
            if e.get("start_core"):
                check_start_source(tn, bus, t, e, txt, W)
                sp = chain_starts(tn, t, e, b, W, plan_dir, None)
                st = " {" + " ".join(f"{bit} {x:.4f} {y:.4f}" for bit, (x, y) in sorted(sp.items())) + "}"
            if e.get("leg_order", "normal_first") == "along_first":
                st = (st or " {}") + " along"
            chan = None
            if e.get("leg_order") == "channel":                 # KIT-CHAN-1
                import istation_channel as _IC
                chan = _IC.entry_channel(e)
                if TCL_CHAN not in tcl:
                    tcl.insert(1, TCL_CHAN)
            for j, nm in enumerate(chains[gi]):
                # out chains run core -> face: is_bits stage j counts from the leaf for out, from the pin for in
                if chan:
                    tcl.append(f"is_chan_bits {nm} {n} {b['face']} {W} {lx} {ly} {j} {k} {b['dir']} "
                               f"ist:{bus}:{'+'.join(core_list(e))} {chan[0]:.4f} {chan[1]:.4f} 0{st}")
                    continue
                tcl.append(f"is_bits {nm} {n} {b['face']} {W} {lx} {ly} {j} {k} {b['dir']} "
                           f"ist:{bus}:{'+'.join(core_list(e))} 0{st}")
            rep.append(dict(conn=e["conn"], core=e["core"], planned=k, bound_pads=len(pads), inserted=k,
                            stations=chains[gi], core_bits=len(e["core_bits"]), plan_width=b["width"], bound_width=W))
    return txt


# KIT-CHAN-1 (DIE-QC-97 11-11): plan leg_order "channel" (istation_channel.py).  Bit b of the bound bus (W payload bits
# + epoch) routes pin -> (col_b, py) -> (col_b, ly) -> leaf for an E/W face (transpose for N/S), col_b = lo + (hi - lo) *
# (b + 0.5) / (W + 1); station edge e of edges sits at arclength L_b e / edges (per bit), fails closed above 403 um.
# Emitted only into kits with a channel chain, so every other kit's istations.tcl is unchanged.
TCL_CHAN_SITE = """proc is_chan_site {px py lx ly face edge edges dir lo hi b W} {
  set col [expr {$lo + ($hi - $lo) * ($b + 0.5) / double($W + 1)}]
  if {$face in {E W}} { set pts [list $px $py $col $py $col $ly $lx $ly] } else { set pts [list $px $py $px $col $lx $col $lx $ly] }
  if {$dir ne "in"} { set r {}; foreach {x y} $pts { set r [linsert $r 0 $x $y] }; set pts $r }
  set L 0.0
  foreach {ax ay} [lrange $pts 0 end-2] {cx cy} [lrange $pts 2 end] { set L [expr {$L + abs($ax - $cx) + abs($ay - $cy)}] }
  if {$L / double($edges) > 403.0} {
    error "internal station channel needs a plan depth change: bit $b hop [expr {$L / double($edges)}] >403um"
  }
  set t [expr {$L * $edge / double($edges)}]
  foreach {ax ay} [lrange $pts 0 end-2] {cx cy} [lrange $pts 2 end] {
    set d [expr {abs($ax - $cx) + abs($ay - $cy)}]
    if {$t <= $d} {
      if {$d == 0} { set f 0.0 } else { set f [expr {$t / $d}] }
      return [list [expr {$ax + $f * ($cx - $ax)}] [expr {$ay + $f * ($cy - $ay)}]]
    }
    set t [expr {$t - $d}]
  }
  return [lrange $pts end-1 end]
}
"""


def _tcl_chan():
    """is_chan_bits = is_bits verbatim (pin / start lookup, flop matching, ff_put_near, report) with the site from
    is_chan_site; built from TCL_HEAD so the two cannot drift"""
    a = TCL_HEAD.index("proc is_bits ")
    body = TCL_HEAD[a:TCL_HEAD.index("\n}\n", a) + 3]
    for old, new in (
            ("proc is_bits {inst bus face W lx ly k n dir tag {offset 0} {starts {}} {order normal}} {",
             "proc is_chan_bits {inst bus face W lx ly k n dir tag lo hi {offset 0} {starts {}}} {"),
            ("lassign [is_knee_site $px $py $lx $ly $face [expr {$k+1}] [expr {$n+1}] $dir $geometry $order] x y",
             "lassign [is_chan_site $px $py $lx $ly $face [expr {$k+1}] [expr {$n+1}] $dir $lo $hi $b $W] x y")):
        assert body.count(old) == 1, old
        body = body.replace(old, new)
    return "# KIT-CHAN-1 leg_order channel (istation_channel.py)\n" + TCL_CHAN_SITE + body


TCL_CHAN = _tcl_chan()


MACRO_TOL_UM = 0.5     # a station site / L-route leg may touch a hard-macro box, not enter it by more than this


def _core_pins(tn, t, inst, plan_dir):
    hc = next((c for c in t.get("hard_cores", []) if c["inst"] == inst), None)
    if hc is None:
        raise SystemExit(f"kit_istations: {tn}: start_core {inst} is not a hard core of the type")
    if hc.get("orient", "R0") != "R0":
        raise SystemExit(f"kit_istations: {tn}: start_core {inst} orient {hc['orient']} not handled (fail closed)")
    pf = Path(hc["pins_file"])
    pf = pf if pf.is_absolute() else Path(plan_dir or ".") / pf
    if not pf.exists():
        raise SystemExit(f"kit_istations: {tn}: start_core {inst} pins file {pf} missing")
    ox, oy = hc["origin_um"]
    return hc, {p["name"]: (ox + float(p["x"]), oy + float(p["y"])) for p in json.loads(pf.read_text())["pins"]}


def chain_starts(tn, t, e, b, W, plan_dir, pins):
    """{bit: (x, y)} L-route start of every bit of a core chain: the face pin (pins: {bit: (x, y)}, gen_phys.type_pins;
    core_bits + epoch W) or, with start_core, the plan's start_um (one site per bound bit 0..W, the epoch last): each
    must sit on the start core's outline edge (<= MACRO_TOL_UM; a landed bus launches at its landing macro's q edge).
    With plan_dir (kit --apply) the sites must also equal start_core's <start_port>[bit] pins (pins file)."""
    if not e.get("start_core"):
        bits = sorted({int(x) for x in e["core_bits"]} | {W})
        if pins is None:
            return None
        miss = [x for x in bits if x not in pins]
        if miss:
            raise SystemExit(f"kit_istations: {tn} {b['name']}: face pins missing for bits {miss[:8]}")
        return {x: pins[x] for x in bits}
    hc = next((c for c in t.get("hard_cores", []) if c["inst"] == e["start_core"]), None)
    if hc is None:
        raise SystemExit(f"kit_istations: {tn}: start_core {e['start_core']} is not a hard core of the type")
    su = e.get("start_um")
    if not isinstance(su, list) or not su:
        raise SystemExit(f"kit_istations: {tn} {b['name']}: start_core {e['start_core']} without start_um")
    if W is not None and len(su) != W + 1:
        raise SystemExit(f"kit_istations: {tn} {b['name']}: start_um has {len(su)} sites != bound width + epoch {W + 1}")
    if max(int(x) for x in e["core_bits"]) >= len(su) - 1:
        raise SystemExit(f"kit_istations: {tn} {b['name']}: core_bits beyond start_um")
    (x0, y0), (w, h) = hc["origin_um"], hc["outline_um"]
    out = {}
    for x, p in enumerate(su):
        p = (float(p[0]), float(p[1]))
        d = min(abs(p[0] - x0), abs(p[0] - x0 - w), abs(p[1] - y0), abs(p[1] - y0 - h))
        inside = x0 - MACRO_TOL_UM <= p[0] <= x0 + w + MACRO_TOL_UM and y0 - MACRO_TOL_UM <= p[1] <= y0 + h + MACRO_TOL_UM
        if d > MACRO_TOL_UM or not inside:
            raise SystemExit(f"kit_istations: {tn} {b['name']}: start site of bit {x} {p} is not on the edge of "
                             f"start_core {e['start_core']} ({d:.3f} um off)")
        out[x] = p
    if plan_dir is not None:
        _, cp = _core_pins(tn, t, e["start_core"], plan_dir)
        port = e.get("start_port", "q")
        for x, p in out.items():
            q = cp.get(f"{port}[{x}]")
            if q is None or abs(q[0] - p[0]) + abs(q[1] - p[1]) > 0.01:
                raise SystemExit(f"kit_istations: {tn} {b['name']}: start site of bit {x} {p} is not start_core "
                                 f"{e['start_core']} pin {port}[{x}] {q}")
    return out


def check_start_source(tn, bus, t, e, txt, W):
    """fail closed unless the bound RTL really launches bus from start_core: u_bin_<bus> .d(<w>[W-1:0]) .ea(<w>[W]) and
    the start core's (unique) instance drives .<start_port>(<w>)"""
    n = gen_rtl.sv_id(bus)
    hc = next((c for c in t.get("hard_cores", []) if c["inst"] == e["start_core"]), None)
    if hc is None:
        raise SystemExit(f"kit_istations: {tn}: start_core {e['start_core']} is not a hard core of the type")
    m = re.search(rf"\bu_bin_{re.escape(n)}\s*\(.*?\.d\(([\w$]+)\[{W - 1}:0\]\),\s*\.ea\(([\w$]+)\[{W}\]\)", txt)
    if not m or m.group(1) != m.group(2):
        raise SystemExit(f"kit_istations: {tn} {bus}: u_bin_{n} does not take one landed wire [{W}:0] (start_core "
                         f"{e['start_core']})")
    w = m.group(1)
    im = re.findall(rf"^\s*{re.escape(hc['module'])}\s+[\w$]+\s*\((.*?)\);\s*$", txt, re.M | re.S)
    if len(im) != 1 or not re.search(rf"\.{re.escape(e.get('start_port', 'q'))}\(\s*{re.escape(w)}\s*\)", im[0]):
        raise SystemExit(f"kit_istations: {tn} {bus}: start_core {e['start_core']} ({hc['module']}) does not drive "
                         f".{e.get('start_port', 'q')}({w})")


def _seg_in_box(a, c, box, tol):
    x0, x1, y0, y1 = min(a[0], c[0]), max(a[0], c[0]), min(a[1], c[1]), max(a[1], c[1])
    bx0, by0, bx1, by1 = box[0] + tol, box[1] + tol, box[2] - tol, box[3] - tol
    return bx0 < bx1 and by0 < by1 and x0 < bx1 and x1 > bx0 and y0 < by1 and y1 > by0


def chain_macro_hits(t, e, b, starts, nbits=None):
    """[(bit, hard core)] whose box (shrunk by MACRO_TOL_UM) a bit's planned L route start -> corner -> leaf_um enters
    (every station site lies on that route, so this covers the sites too).  leg_order channel (KIT-CHAN-1): the bit's
    Z route through its channel column; nbits = bound width + 1 (default max(starts) + 1)."""
    lx, ly = e["leaf_um"]
    if e.get("leg_order") == "channel":
        import istation_channel as _IC
        lo, hi = _IC.entry_channel(e)
        nb = nbits if nbits is not None else max(starts) + 1
        boxes = {c["inst"]: (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                             c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", [])}
        out = []
        for bit, (px, py) in sorted(starts.items()):
            for nm, box in boxes.items():
                if any(_seg_in_box(a, c, box, MACRO_TOL_UM)
                       for a, c in _IC.legs(px, py, lx, ly, b["face"], lo, hi, bit, nb)):
                    out.append((bit, nm))
        return out
    along = e.get("leg_order", "normal_first") == "along_first"
    boxes = {c["inst"]: (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                         c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", [])}
    out = []
    for bit, (px, py) in sorted(starts.items()):
        c = (lx, py) if (b["face"] in "EW") != along else (px, ly)
        for nm, box in boxes.items():
            if _seg_in_box((px, py), c, box, MACRO_TOL_UM) or _seg_in_box(c, (lx, ly), box, MACRO_TOL_UM):
                out.append((bit, nm))
    return out


def core_chain_geometry_errors(P, tn, plan_dir=None):
    """validate / --apply gate (COORD 11-11, SUL0-PINFACE-1): every core pin-face chain's planned per-bit L routes stay
    off every hard macro (incl. landing macros) by MACRO_TOL_UM; start_core starts sit on the core edge.  Returns error
    strings (one per chain, with its bit count)."""
    import gen_phys
    t = P.types[tn]
    es = [e for e in t.get("internal_stations", []) if e.get("core")]
    if not es:
        return []
    pins = {}
    for name, bit, _ln, x, y, _f in gen_phys.type_pins(P, tn):
        pins.setdefault(name, {})[int(bit)] = (float(x), float(y))
    buses = {b["name"]: b for b in t.get("buses", [])}
    errs = []
    for e in es:
        bus = e["conn"][4:]
        b = buses.get(bus)
        if b is None:
            errs.append(f"type {tn}: core chain on unknown bus {bus}")
            continue
        W = len(pins.get(bus, {})) - 1
        try:
            st = chain_starts(tn, t, e, b, None if e.get("start_core") else W, plan_dir, pins.get(bus, {}))
        except SystemExit as ex:
            errs.append(f"type {tn}: {ex}")
            continue
        keep = {int(x) for x in e["core_bits"]} | {max(st)}     # bits synthesis keeps (+ epoch; start_um lists all)
        if e.get("leg_order") == "channel":                     # KIT-CHAN-1: channel_um present and well formed
            import istation_channel as _IC
            try:
                _IC.entry_channel(e)
            except SystemExit as ex:
                errs.append(f"type {tn}: {ex}")
                continue
        hits = chain_macro_hits(t, e, b, {k: v for k, v in st.items() if k in keep}, nbits=max(st) + 1)
        if hits:
            errs.append(f"type {tn}: core chain {bus} {e['core']}: {len({h[0] for h in hits})} bit L routes enter hard "
                        f"macros {sorted({h[1] for h in hits})} by > {MACRO_TOL_UM} um (station sites would be moved off "
                        "the planned hop)")
    return errs


def core_list(e):
    """hard cores one core pin-face chain serves ('core': inst or [inst, ...])"""
    return [e["core"]] if isinstance(e["core"], str) else list(e["core"])


def core_line(lines, core):
    rx = re.compile(rf"^\s*\w+\s+{re.escape(core)}\s*\(")
    return [i for i, ln in enumerate(lines) if rx.match(ln)]


def check_core_delay(tn, bus, txt, chains, k, q):
    """fail closed unless every read of a core chain (outside the chain itself) is the LAST station (k-1) on the
    instance line of a core that chain lists, and no listed core reads the face register q directly: a consumer at
    any other stage would see the bus at a different latency"""
    n = gen_rtl.sv_id(bus)
    tags = {tag: set(cs) for tag, cs in chains}
    lines = txt.split("\n")
    for core in sorted({c for _, cs in chains for c in cs}):
        hit = core_line(lines, core)
        if len(hit) != 1:
            raise SystemExit(f"kit_istations: {tn} {bus}: {len(hit)} instance lines of core {core}")
        d = re.search(rf"\b{re.escape(q)}(?:\[\d+\]|(?![\w$\[]))", lines[hit[0]])
        if d:
            raise SystemExit(f"kit_istations: {tn} {bus}: core {core} reads {d.group(0)} off the face register "
                             f"(stage 0 of {k}): wrong delay")
    for ln in lines:
        if re.match(r"^\s*(wire|reg|logic)\b", ln) or re.search(rf"\bu_ist_{re.escape(n)}__", ln):
            continue
        refs = [(m.group(0), m.group(1), int(m.group(2))) for m in re.finditer(rf"\b({re.escape(n)}__\w+?)_s(\d+)_q\b", ln)
                if m.group(1) in tags]
        if not refs:
            continue
        mi = re.match(r"^\s*\w+\s+([\w$]+)\s*\(", ln)
        inst = mi.group(1) if mi else None
        for ref, tag, j in refs:
            if inst not in tags[tag] or j != k - 1:
                raise SystemExit(f"kit_istations: {tn} {bus}: {inst or ln.strip()[:40]} reads {ref} (stage {j + 1} of {k}"
                                 f"{'' if inst in tags[tag] else ', not a core of that chain'}): wrong delay")


def chain_floats(t, conn):
    """WIDE-FLOAT-1 11-12: True when every internal_stations entry of this bus chain says sites="float".  The chain keeps
    its stage count (the lane's cycles) but its stages get no FIRM site: GPL places them toward the bus's real data
    consumers.  For wide face-bus chains whose planned sites trace a narrow relay path (col_* frame buses: 1167-1264 b
    pinned along the outline toward a 1-bit u_bn*.rs capture while the data feeds soft u_lpl_* seams)."""
    es = [e for e in t.get("internal_stations", []) if e.get("conn") == conn]
    return bool(es) and all(e.get("sites") == "float" for e in es)


def bus_entries(t):
    """Station entries of a type's buses, one per bus.  The planner lists one entry per capture group, but a bus has one
    chain (bind face register -> leaf): its depth is the deepest entry, stage j at the bits-weighted centroid of the
    deepest entries (KW-FIX-27: depths 1,1,2 restarted the out chain at j=0).  bit_route / exact-site entries stay as
    written."""
    by = {}
    for e in t.get("internal_stations", []):
        if e.get("conn", "").startswith("bus:"):
            by.setdefault(e["conn"], []).append(e)
    out = []
    for conn, es in by.items():
        if len(es) == 1 or any(e.get("bit_route") or "bit_sites_um" in e or "face_bit_sites_um" in e for e in es):
            out.extend(es)
            continue
        n = max(len(e["regs_um"]) for e in es)
        deep = [e for e in es if len(e["regs_um"]) == n]
        w = sum(int(e.get("bits", 1)) for e in deep)
        regs = [[round(sum(e["regs_um"][j][k] * int(e.get("bits", 1)) for e in deep) / w, 3) for k in (0, 1)] for j in range(n)]
        out.append(dict(deep[0], regs_um=regs, bits=sum(int(e.get("bits", 1)) for e in es), merged_entries=len(es), per_core_rows=es))
    return out


def main(argv):
    apply = "--apply" in argv
    # KIT-ISTATIONS 11-11: per-bit-group station sites of a multi-core bus (kit_bus_bitgroups); auto = only when the merged
    # chain leaves a core group farther than the planning reach; --bit-groups forces, --no-bit-groups disables
    bit_groups = "off" if "--no-bit-groups" in argv else ("force" if "--bit-groups" in argv else "auto")
    argv = [a for a in argv if a not in ("--apply", "--bit-groups", "--no-bit-groups")]
    htree = (4, 0, 0)
    if "--h-tree" in argv:
        i = argv.index("--h-tree")
        htree = tuple(int(x) for x in argv[i + 1].split(","))
        del argv[i:i + 2]
    if len(argv) != 3:
        raise SystemExit(__doc__)
    plan, tn, kd = argv[0], argv[1], Path(argv[2]).resolve()
    raw = json.load(open(plan))
    t = raw["partition_types"][tn]
    man = json.loads((kd / "kit_rtl.json").read_text())
    bfile = next(Path(f) for f in man["files"] if Path(f).stem == man["bound_module"])
    if bfile.resolve().parent != kd:      # kd is resolved; a moved kit dir leaves a symlink in the recorded path (DIE-HBM-94 11-08, q_spt0)
        raise SystemExit(f"kit_istations: bound module {bfile} is not a kit-local copy (run kit_rsync.py first)")
    txt = bfile.read_text()
    tcl = [TCL_HEAD]
    rep = []
    bad = [e.get("conn") for e in t.get("internal_stations", []) if e.get("leg_order") == "channel" and not e.get("core")]
    if bad:   # KIT-CHAN-1: the channel order is a core pin-face chain form only (bus chains have no leg order)
        raise SystemExit(f"kit_istations: {tn}: leg_order channel on non-core chain(s) {bad[:4]}")
    if any(e.get("core") for e in t.get("internal_stations", [])) and any(
            p.get("type") == tn for p in raw.get("partitions", [])):   # SUL0-PINFACE-1 geometry gate (fail closed)
        import schema as _S
        gerr = core_chain_geometry_errors(_S.Plan(json.loads(json.dumps(raw)), path=plan), tn, Path(plan).resolve().parent)
        if gerr:
            raise SystemExit("kit_istations: " + "; ".join(gerr[:6]) + (f" (+{len(gerr) - 6} more)" if len(gerr) > 6 else ""))
    txt = core_pin_stations(tn, t, txt, man, tcl, rep, Path(plan).resolve().parent)      # SUL0-PINFACE-1 per-core chains
    for e in bus_entries(dict(t, internal_stations=[x for x in t.get('internal_stations', []) if not x.get('core')])):           # core<->core: core_stations() below
        conn = e["conn"]
        bus = conn[4:]
        n = gen_rtl.sv_id(bus)
        regs = e["regs_um"]
        b = next((x for x in t["buses"] if x["name"] == bus), None)
        if b is None:
            raise SystemExit(f"kit_istations: {tn}: internal station on unknown bus {bus}")
        W = bound_bus_width(tn, b, txt, man)
        exact = exact_banks(e, W)
        floating = chain_floats(t, conn)
        if floating and (exact is not None or e.get("bit_route") or "bit_sites_um" in e or "face_bit_sites_um" in e):
            raise SystemExit(f"kit_istations: {tn} {bus}: sites=float is a whole-chain form only "
                             "(no exact bank / bit_route / bit sites)")
        packed=packed_input_delay(tn,b,txt,W,len(regs))
        if packed:
            if exact is not None:
                raise ValueError(f'{tn}.{bus}: packed data+epoch delay requires complete packed bit sites; unsupported exact bank')
            sites=packed_sites(regs,packed['depth'])
            for j,k in sites:
                if floating:
                    break
                x,y=regs[k]
                pattern='*'+packed['instance']+f'[./]r\\[{j}\\]\\[*'
                tcl.append(f'is_place {{{pattern}}} {x} {y} ist:{bus}')
            row=dict(conn=conn,planned=len(regs),bound_pads=packed['depth'],inserted=0,
                     stations=packed['stage_registers'],packed_delay=packed,
                     plan_width=b['width'],bound_width=W)
            if floating:
                row.update(sites="float")
                print(f"kit_istations: {tn} {bus}: sites=float, {packed['depth']} packed stages left to placement")
            if packed['depth']<len(regs):
                pts=[p for p in [e.get('from_um')]+[regs[k] for _,k in sites]+[e.get('to_um')] if p]
                row.update(respread_sites=[k for _,k in sites],
                           respread_max_hop_um=round(max(abs(a[0]-c[0])+abs(a[1]-c[1]) for a,c in zip(pts,pts[1:])),3))
                print(f"kit_istations: {tn} {bus}: packed D{packed['depth']} < {len(regs)} planned stations, "
                      f"registers on planned sites {row['respread_sites']}, max hop {row['respread_max_hop_um']} um")
            rep.append(row)
            continue
        if exact is not None and EXACT_BANK_TCL not in tcl:
            tcl.append(EXACT_BANK_TCL)
        prev = sorted(int(m) for m in re.findall(rf"\bu_ist_{re.escape(n)}_(\d+)\b", txt))
        if prev and prev != list(range(len(prev))):
            raise SystemExit(f"kit_istations: {tn} {bus}: stations already inserted (re-application requires "
                             "a complete u_ist_ chain; run on a fresh kit-rtl copy)")
        pads = sorted(int(m) for m in re.findall(rf"\bu_b(?:in|out)_{re.escape(n)}_pad(\d+)\b", txt))
        have = len(pads) + len(prev)
        need = len(regs) - have
        if need < 0:
            raise SystemExit(f"kit_istations: {tn} {bus}: bound module has {have} pad stages > {len(regs)} planned")
        names = [f"u_b{'in' if b['dir'] == 'in' else 'out'}_{n}_pad{j}" for j in pads] + [f"u_ist_{n}_{j}" for j in prev]
        bgrp = None
        if (bit_groups != "off" and e.get("merged_entries", 1) > 1 and exact is None
                and not e.get("bit_route") and (bit_groups == "force" or t.get("bus_bit_groups")
                or BG.merged_violates(e["per_core_rows"], regs, b["dir"] == "in"))):
            hard = [h["inst"] for h in t.get("hard_cores", [])]
            cores = sorted({BG.core_of_entry(r, hard) for r in e["per_core_rows"]} - {None})
            owners = (BG.in_bit_owners(txt, n, cores) if b["dir"] == "in" else BG.out_bit_owners(txt, n, W, cores))
            bgrp = BG.plan_groups(e["per_core_rows"], b["dir"] == "in", len(regs), W, owners, hard)
        if b["dir"] == "in":
            # the last bound stage on the bus: the pad chain end, else the face register
            q, eq = (f"{n}_is{prev[-1]}_q", f"{n}_is{prev[-1]}_eq") if prev else \
                (f"{n}_p{pads[-1]}_q", f"{n}_p{pads[-1]}_eq") if pads else (f"{n}_q", f"{n}_eq")
            j0 = len(prev)
            if need:
                decl, body = [], []
                cq, ceq = q, eq
                for j in range(j0, j0 + need):
                    decl.append(f"    wire [{W - 1}:0] {n}_is{j}_q;\n    wire {n}_is{j}_eq;  // kit_istations")
                    body.append(f"    ot_dp_st #(.W({W})) u_ist_{n}_{j} (.clk(clk), .rst_n(rst_n), .d({cq}), .ea({ceq}), "
                                f".q({n}_is{j}_q), .eq({n}_is{j}_eq));  // kit_istations: FIRM plan station")
                    cq, ceq = f"{n}_is{j}_q", f"{n}_is{j}_eq"
                    names.append(f"u_ist_{n}_{j}")
                # re-point readers (every use of q / eq outside its driver line and declaration)
                out = []
                for ln in txt.splitlines(keepends=True):
                    if re.search(rf"\b(u_bin_{re.escape(n)}(_pad\d+)?|u_ist_{re.escape(n)}_\d+)\s*\(", ln) or \
                            re.match(r"^\s*(wire|reg|logic)\b", ln):
                        out.append(ln)
                        continue
                    ln = re.sub(rf"\b{re.escape(q)}\b", cq, ln)
                    ln = re.sub(rf"\b{re.escape(eq)}\b", ceq, ln)
                    out.append(ln)
                txt = "".join(out)
                txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
        else:
            m = re.search(rf"^(\s*ot_dp_ste?\s+#\(\.W\({W}\)\)\s+u_bout_{re.escape(n)}\s*\(.*?\.d\()([^)]*)(\),\s*\.ea\()([^)]*)(\).*)$",
                          txt, re.M)
            if need and not m:
                raise SystemExit(f"kit_istations: {tn}: no u_bout_{n} face register line to feed")
            if need:
                d0, ea0 = m.group(2), m.group(4)
                decl, body = [], []
                cq, ceq = d0, ea0
                for j in range(len(prev), len(prev) + need):
                    decl.append(f"    wire [{W - 1}:0] {n}_is{j}_q;\n    wire {n}_is{j}_eq;  // kit_istations")
                    body.append(f"    ot_dp_st #(.W({W})) u_ist_{n}_{j} (.clk(clk), .rst_n(rst_n), .d({cq}), .ea({ceq}), "
                                f".q({n}_is{j}_q), .eq({n}_is{j}_eq));  // kit_istations: FIRM plan station")
                    cq, ceq = f"{n}_is{j}_q", f"{n}_is{j}_eq"
                    names.append(f"u_ist_{n}_{j}")
                line = m.group(1) + cq + m.group(3) + ceq + m.group(5)
                line = re.sub(r"^(\s*)ot_dp_ste\b", r"\1ot_dp_st", line)   # ea is now a station epoch, not a reset net
                txt = txt[:m.start()] + line + txt[m.end():]
                txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
            # out bus: the stations run from the leaf toward the face, regs_um is ordered from_um -> to_um.
            # KW-FIX-27: a planner entry launched at the face lists the face side first; site stage 0 at the leaf side.
            if not pads and str(e.get("launch", "")).startswith("face bus"):
                regs = regs[::-1]
        if exact is not None:
            banks, (fw, fh), face = exact
            for nm, bank in zip(names, banks):
                sites = " ".join("{%0.9g %0.9g}" % tuple(xy) for xy in bank)
                tcl.append(f"is_exact_bank {{{nm}}} {W} {{{sites}}} {fw:.9g} {fh:.9g} ist:{bus} @EPOCH:{nm}@")
            if face is not None:
                face_inst = f"u_b{'in' if b['dir'] == 'in' else 'out'}_{n}"
                sites = " ".join("{%0.9g %0.9g}" % tuple(xy) for xy in face)
                tcl.append(f"is_exact_bank {{{face_inst}}} {W} {{{sites}}} {fw:.9g} {fh:.9g} face:{bus} @EPOCH:{face_inst}@")
        elif e.get("bit_route") == "chain":
            # D-QC-FE-REACH 10-26: per-bit sites on each bit's own in-pin -> landing-register route (is_chain)
            if b["dir"] != "in" or "face" not in b:
                raise SystemExit(f"kit_istations: {tn} {bus}: bit_route chain needs an in bus with a face")
            tcl.append(f"is_chain {n} {W} {{{' '.join(names)}}} {b['face']} {{{e.get('core_glob', 'u_core')}.}} ist:{bus}")
        elif e.get("bit_route") == "per_bit":
            if "leaf_um" not in e or "face" not in b:
                raise SystemExit(f"kit_istations: {tn} {bus}: bit_route per_bit needs leaf_um and a bus face")
            lx, ly = e["leaf_um"]
            leaf = next((c for c in t.get("contents", []) if c["inst"] == b.get("leaf", "").split(".")[0]), {})
            box = leaf.get("outline_um", [0, 0])
            offset = max(0.0, min(15.0, box[0 if b["face"] in "EW" else 1] / 2.0 - 2.0))
            for k, nm in enumerate(names):
                tcl.append(f"is_bits {nm} {n} {b['face']} {W} {lx} {ly} {k} {len(names)} {b['dir']} ist:{bus} {offset:g}")
        elif bgrp is not None:
            if BG.BITS_TCL not in tcl:
                tcl.append(BG.BITS_TCL)
            tcl.extend(BG.tcl_lines(names, bgrp, regs, bus))
            print(f"kit_istations: {tn} {bus}: per-bit-group sites for {len(bgrp['groups'])} cores (max planned hop "
                  f"{max(g['hop_um'] for g in bgrp['groups'].values())} um, {bgrp['unresolved_bits']} bits keep the merged site)")
        elif floating:
            print(f"kit_istations: {tn} {bus}: sites=float, {len(names)} stages left to placement")
        else:
            for (x, y), nm in zip(regs, names):
                tcl.append(f"is_place {{*{nm}[./]*}} {x} {y} ist:{bus}")
        rep.append(dict(conn=conn, planned=len(regs), bound_pads=have, inserted=need, stations=names,
                        plan_width=b["width"], bound_width=W,
                        **({"bit_groups": bgrp["groups"]} if bgrp is not None and exact is None else {}),
                        **({"exact_bank_sites": True} if exact is not None else {})))
    txt = core_stations(t, txt, apply, htree, tcl, rep)
    # plan cells with a FIRM site (no hard view): their flops at the site
    for c in soft_plan_cells(tn, t):
        ox, oy = c["origin_um"]
        w, h = c.get("outline_um", [0.0, 0.0])
        inst = gen_rtl.sv_id(c["inst"])
        inst = inst if inst.startswith("u_") else "u_" + inst
        tcl.append(f"is_place {{*{inst}[./]*}} {ox + w / 2:g} {oy + h / 2:g} cell:{c['inst']}")
        rep.append(dict(cell=c["inst"], site=[ox, oy]))
    # existing RTL stage flops at plan relay sites (0 cycles; DIE-KV-59 10-31)
    rs = relay_sites_lines(tn, t)
    if rs:
        tcl.extend(rs)
        man["kit_relay_sites"] = len(t["relay_sites"])       # not a station entry: receipts list stations only
    tcl += macro_cross_lines(tn, t)
    tcl.append("close $is_fh\nputs \"OT_ISTATIONS placed $is_n flops FIRM (missing: [llength $is_miss] $is_miss)\"")
    from kit_epoch_observability import inspect as epoch_inspect
    epochs = {}
    for index, line in enumerate(tcl):
        for match in re.finditer(r'@EPOCH:(\w+)@', line):
            inst = match[1]
            epochs[inst] = epoch_inspect(txt, inst)
            line = line.replace(match[0], str(int(epochs[inst]['unobserved'])))
        tcl[index] = line
    if epochs:
        import hashlib
        man['kit_epoch_observability'] = dict(source_sha256=hashlib.sha256(txt.encode()).hexdigest(), stations=epochs)
    bfile.write_text(txt)
    (kd / "istations.tcl").write_text("\n".join(tcl) + "\n")
    man["kit_istations"] = rep
    (kd / "kit_rtl.json").write_text(json.dumps(man, indent=1))
    print(json.dumps(dict(type=tn, entries=rep)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
