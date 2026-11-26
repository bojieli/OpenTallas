"""Plan key logic_cluster_rects_um (QC-GLUE, QC-ALLFIX 11-25): a per-type list of placement clusters
{"name", "patterns": [regex on the flat instance name], "rect_um": [x0, y0, x1, y1]} in the type frame.

gen_phys emits logic_cluster.tcl, sourced at the end of face_flops.tcl (PRE_GLOBAL_PLACE, after the face / landing hooks).  It creates an
INCLUSIVE odb region over the rect and a group holding every movable matched instance; GPL (per-group nesterov) and DPL (fence) keep
those cells inside the rect.  Fixed / FIRM / block cells are counted and left alone.  Fail closed (error in the kit hook, before GPL)
when a pattern matches no instance or the matched cell area exceeds MAX_UTIL of the rect; gen fails on a bad rect or key.
A plan without the key emits nothing (byte-identical kit)."""
import re

MAX_UTIL = 0.70


def validate(t, tn):
    rows = t.get("logic_cluster_rects_um")
    if rows is None:
        return []
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{tn}: logic_cluster_rects_um must be a non-empty list")
    w, h = t["outline_um"]
    seen = set()
    for r in rows:
        name = r.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or name in seen:
            raise ValueError(f"{tn}: logic_cluster name {name!r} invalid or repeated")
        seen.add(name)
        pats = r.get("patterns")
        if not isinstance(pats, list) or not pats:
            raise ValueError(f"{tn}: logic_cluster {name} needs patterns")
        for p in pats:
            if not isinstance(p, str) or not p or any(c in p for c in "{}\n"):
                raise ValueError(f"{tn}: logic_cluster {name} pattern {p!r} must be a non-empty regex without braces")
            re.compile(p)
        rect = r.get("rect_um")
        if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(type(v) not in (int, float) for v in rect):
            raise ValueError(f"{tn}: logic_cluster {name} rect_um needs four numbers")
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError(f"{tn}: logic_cluster {name} rect outside the outline or empty: {rect}")
    return rows


def tcl(P, tn, *, no_core_rows=()):
    rows = validate(P.types[tn], tn)
    if not rows:
        return ""
    out = ["# Generated (gen_phys logic_cluster_rects_um): INCLUSIVE odb region + group per cluster; GPL and DPL keep the cells inside.",
           "# HEAD-INT-R2 11-26 (C-GPL-TD-INFLATION, opt-in OT_LOGIC_CLUSTER_POST_GPL=1): the regions are created AFTER the global_placement call,",
           "# cells snapped into their rect, so GPL has no region groups and its timing-driven trigger reads the top-level overflow only.",
           "uplevel #0 {",
           "set lc_b [ord::get_db_block]",
           "set lc_u [[ord::get_db_tech] getDbUnitsPerMicron]",
           "set lc_post [expr {[info exists ::env(OT_LOGIC_CLUSTER_POST_GPL)] && $::env(OT_LOGIC_CLUSTER_POST_GPL) eq \"1\"}]",
           "set lc_pending {}",
           "set lc_applied 0",
           # members: movable matched instances; fail closed exactly as before (no match / already grouped / area)
           "proc ot_lc_members {name x0 y0 x1 y1 pats} {",
           "  global lc_b lc_u",
           "  set mem {}; set skipped 0; set area 0.0",
           "  foreach pat $pats {",
           "    set pn 0",
           "    foreach i [$lc_b getInsts] {",
           "      if {![regexp $pat [$i getName]]} continue",
           "      incr pn",
           "      if {[$i isBlock] || [$i getPlacementStatus] in {FIRM LOCKED}} { incr skipped; continue }",
           "      if {[$i getGroup] ne \"NULL\"} { error \"OT_LOGIC_CLUSTER $name: [$i getName] already in a group\" }",
           "      lappend mem $i",
           "      set m [$i getMaster]; set area [expr {$area + double([$m getWidth]) * [$m getHeight] / ($lc_u * $lc_u)}]",
           "    }",
           "    if {$pn == 0} { error \"OT_LOGIC_CLUSTER $name: pattern $pat matches no instance\" }",
           "  }",
           "  set ra [expr {double($x1-$x0)*($y1-$y0)}]",
           f"  if {{$area > {MAX_UTIL} * $ra}} {{ error \"OT_LOGIC_CLUSTER $name: cell area $area um2 exceeds {MAX_UTIL:g} of rect $ra um2\" }}",
           "  return [list $mem $skipped $area $ra]",
           "}",
           "proc ot_lc_region {name x0 y0 x1 y1 mem} {",
           "  global lc_b lc_u",
           "  set reg [odb::dbRegion_create $lc_b $name]",
           "  $reg setRegionType INCLUSIVE",
           "  odb::dbBox_create $reg [expr {round($x0*$lc_u)}] [expr {round($y0*$lc_u)}] [expr {round($x1*$lc_u)}] [expr {round($y1*$lc_u)}]",
           "  set grp [odb::dbGroup_create $reg $name]",
           "  foreach i $mem { $grp addInst $i }",
           "}",
           "proc ot_logic_cluster {name x0 y0 x1 y1 pats} {",
           "  global lc_post lc_pending",
           "  lassign [ot_lc_members $name $x0 $y0 $x1 $y1 $pats] mem skipped area ra",
           "  if {$lc_post} {",
           "    lappend lc_pending [list $name $x0 $y0 $x1 $y1 $pats]",
           "  } else {",
           "    ot_lc_region $name $x0 $y0 $x1 $y1 $mem",
           "  }",
           "  puts [format \"OT_LOGIC_CLUSTER %s cells=%d skipped_fixed=%d cell_um2=%.1f rect_um2=%.1f util=%.3f%s\" $name [llength $mem] $skipped $area $ra [expr {$area/$ra}] [expr {$lc_post ? \" region=after_gpl\" : \"\"}]]",
           "}",
           # after global_placement: region + group, every member snapped fully inside its rect (DPL then legalises inside the fence)
           "proc ot_logic_cluster_apply {} {",
           "  global lc_b lc_u lc_pending lc_applied",
           "  if {$lc_applied} return",
           "  set lc_applied 1",
           "  foreach p $lc_pending {",
           "    lassign $p name x0 y0 x1 y1 pats",
           "    lassign [ot_lc_members $name $x0 $y0 $x1 $y1 $pats] mem skipped area ra",
           "    ot_lc_region $name $x0 $y0 $x1 $y1 $mem",
           "    set X0 [expr {round($x0*$lc_u)}]; set Y0 [expr {round($y0*$lc_u)}]; set X1 [expr {round($x1*$lc_u)}]; set Y1 [expr {round($y1*$lc_u)}]",
           "    set snapped 0; set maxd 0.0",
           "    foreach i $mem {",
           "      set bb [$i getBBox]",
           "      set bx [$bb xMin]; set by [$bb yMin]; set w [expr {[$bb xMax]-$bx}]; set h [expr {[$bb yMax]-$by}]",
           "      set nx [expr {max($X0, min($bx, $X1-$w))}]; set ny [expr {max($Y0, min($by, $Y1-$h))}]",
           "      if {$nx == $bx && $ny == $by} continue",
           "      $i setLocation $nx $ny",
           "      incr snapped; set d [expr {(abs($nx-$bx)+abs($ny-$by))/double($lc_u)}]; if {$d > $maxd} { set maxd $d }",
           "    }",
           "    puts [format \"OT_LOGIC_CLUSTER_POST %s cells=%d snapped=%d max_snap_um=%.1f\" $name [llength $mem] $snapped $maxd]",
           "  }",
           "  set lc_pending {}",
           "}",
           # the wrapper: the apply runs once, after the first successful non-skip_io global_placement of this kit stage
           "if {$lc_post && [info commands ::ot_lc_gpl_native] eq \"\" && [info commands ::global_placement] ne \"\"} {",
           "  rename ::global_placement ::ot_lc_gpl_native",
           "  proc ::global_placement {args} {",
           "    set rc [catch {uplevel 1 [list ::ot_lc_gpl_native {*}$args]} res opts]",
           "    if {$rc == 0 && [lsearch -exact $args -skip_io] < 0} { ot_logic_cluster_apply }",
           "    return -options $opts $res",
           "  }",
           "}"]
    for r in rows:
        x0, y0, x1, y1 = r["rect_um"]
        for domain, (px0, py0, px1, py1) in no_core_rows:
            if px0 <= x0 and py0 <= y0 and x1 <= px1 and y1 <= py1:
                raise ValueError(f"{tn}: logic_cluster {r['name']} is fully inside PHY domain {domain}, "
                                 f"which removes its core placement rows: {r['rect_um']}")
        pats = " ".join("{" + p + "}" for p in r["patterns"])
        out.append(f"ot_logic_cluster {r['name']} {x0:g} {y0:g} {x1:g} {y1:g} [list {pats}]")
    out.append("}")
    return "\n".join(out) + "\n"
