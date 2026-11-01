"""HEAD-TILE-C9 (KIT-WAVE-5 / COORD 10-31): the reviewed Codex canonical9 structural placement of the S81-HEAD hd_tile,
installed into every generated hd_tile kit of die_plan s81_head, on by default.

The recipe (physical/die_plan/s81_head/kit_recipes/hd_tile_c9, MANIFEST.json) is keyed by instance NAME on one exact
netlist (1_synth_odb.v md5 5d76693e8a50...).  It closed this frame (DIE-HEAD-39 LOOK PASS 10-30 10:37: r2r 397.93/0,
pin p90 29.27, clock reach 189.14, taps max 1120, GRT50 overflow 0, AUTO-GEOM PASS, results/die_head_39_1030/tile9).
The plain wave kit (same netlist, plain GPL) fails AUTO-GEOM (GEOM-86 10-31: r2r 1257.55, relay_collapse, clock reach).

Three kit-local steps, all in the ORFS place stage, so 3_place.odb (AUTO-GEOM, CTS, route queue) is the canonical one:
  (a) GPL hook (landing_placement.tcl, before the group loop): netlist md5 check, then Codex head_native_hook.tcl wraps
      cland_place_ff for u_cland_i (head_native_pack.py -> native ring layout);
      face_flops.tcl end: head_tile_core.tcl (TILE5..8 structural seeds), exactly as the reviewed kit;
  (b)+(c) POST_DETAIL_PLACE_TCL: dpl_canonical8.tcl (native8 + tile8_hop + row holes, DPL, check) then
      dpl_canonical9.tcl (canonical9_invperm same-master comb permutation, DPL, check) on the in-memory design; the
      reviewed files are applied byte-for-byte except their own read_db / write_db / exit lines (see _STANDALONE_EDITS)
      and the repair_design buffer names of the tile_v1 run (resolved by netlist input net, see _FLOWBUF_LEAF).
  (d) POST_DETAIL_PLACE after (c) (HEAD-TILE-C9d, DIE-HEAD-51 10-31): head_tile_c9_restore.tcl puts every netlist std
      cell on its reviewed tile_v1 site (tile_v1_place.tsv from the reviewed 3_place.odb md5 e5b68f95).  Without it
      the kit's own timing-driven GPL keeps a different buffer set and steps (a)-(c) pin only part of the cells, so the
      rest piles into the junction under elemB: c9b AUTO-GEOM GRT50 overflow 1916.  With it: GRT50 overflow 0, AUTO PASS
      (intel2 die-head-48/tile51/v1).  Run-specific flow-buffer names are never matched; each such buffer goes to the
      centroid of its nets, then DPL legalizes (FIRM cells keep FIRM) and check_placement must pass.
Fail closed: a different netlist, a missing named instance, a missing hook anchor, a recipe file whose sha256 differs
from MANIFEST.json, or a DPL/check failure stops gen or the place stage with a 'HEAD_TILE_C9 ... fails closed' message
(kit_wave classify: PLAN).  No fallback to the plain placement.  Every other die/type: install() returns False and
writes nothing (test_head_tile_c9.py)."""
import gzip
import hashlib
import json
import re
from pathlib import Path

RECIPE = Path(__file__).resolve().parents[2] / "physical" / "die_plan" / "s81_head" / "kit_recipes" / "hd_tile_c9"
DIE, TYPE = "s81_head", "hd_tile"
GPL_ANCHOR = "\nforeach spec $cland_groups {\n"
LANDING_HOOK = "uplevel #0 {source /work/landing_placement.tcl}"

# The reviewed post-place scripts ran standalone (read_db 3_place.odb, write_db, exit 1).  In the kit they run inside
# ORFS detail_place.tcl (POST_DETAIL_PLACE_TCL) on the loaded design, which ORFS then writes as 3_5_place_dp.odb ->
# 3_place.odb.  Each edit must match exactly once, otherwise gen fails closed.
_C9_DIR = "/work/head_tile_c9_out"
_STANDALONE_EDITS = {
    "dpl_canonical8.tcl": [
        ("set_thread_count 4\n", ""),
        ("set ::env(RESULTS_DIR) /work/diag_canonical8\n", f"set ::env(RESULTS_DIR) {_C9_DIR}\n"),
        ("read_db /work/run/results/asap7/dp_hd_tile/base/3_place.odb\n", ""),
        ("write_db /work/diag_canonical8/anchored.odb\n", ""),
        ("write_db /work/diag_canonical8/after_dpl.odb\n", ""),
        ("if {$dpl_rc || $chk_rc} {exit 1}\n",
         'if {$dpl_rc || $chk_rc} {error "HEAD_TILE_C9 canonical8 DPL rc=$dpl_rc check rc=$chk_rc fails closed: '
         '$dpl_msg $chk_msg"}\n'),
        ("write_db /work/diag_canonical8/3_place.odb\n", ""),
    ],
    "dpl_canonical9.tcl": [
        ("set_thread_count 4\n", ""),
        ("read_db /work/diag_canonical8/3_place.odb\n", ""),
        ("write_db /work/diag_canonical9/anchored.odb\n", ""),
        ("write_db /work/diag_canonical9/after_dpl.odb\n", ""),
        ("if {$rc || $cc} {exit 1}\n", 'if {$rc || $cc} {error "HEAD_TILE_C9 canonical9 DPL rc=$rc check rc=$cc fails closed: $msg $cm"}\n'),
        ("write_db /work/diag_canonical9/3_place.odb\n", ""),
    ],
}


# HEAD-TILE-C9b (10-31): native8_placement.tcl also names 298 OpenROAD repair_design buffers (leaf place<N> / wire<N>)
# of the Codex tile_v1 run.  Those names belong to that run, not to the md5-pinned netlist: the wave kit's own place
# run (newer kit generator) inserts a different buffer set, so 292 names did not exist and 6 named other buffers
# (canonical8 'TILE5 missing exact source register').  The kit resolves each such buffer by its netlist input net
# (flowbuf_inputs.json, from tile_v1's odb); an unresolved one is left where GPL/DPL put it and counted.  The 8
# canonical9 permutation pairs between such buffers (closed cycles) are dropped.  Netlist names still fail closed.
_FLOWBUF_LEAF = re.compile(r"(?:^|/)(?:place|wire)\d+$")
_N8_BLOCK = re.compile(r'set nri \[\$ff_blk findInst \{([^}]*)\}\]\n'
                       r'if \{\$nri eq "NULL"\} \{error "NATIVE_RING missing actual proved capture"\}\n'
                       r'(cland_put \$nri [^\n]*)\n')
_IP9_PAIR = re.compile(r"^\{\{([^}]*)\} \{([^}]*)\} \{([^}]*)\}\}$")
_FLOWBUF_EDITS = ("native8_placement.tcl", "canonical9_invperm.tcl")


def flowbuf_native8(text, fb):
    """Rewrite native8 blocks that name a repair_design buffer into a by-input-net lookup (head_tile_c9_flowbuf)."""
    seen = []

    def sub(mt):
        name = mt.group(1)
        if not _FLOWBUF_LEAF.search(name):
            return mt.group(0)
        if name not in fb:
            raise ValueError(f"HEAD_TILE_C9 flow buffer {name} not in flowbuf_inputs.json; fails closed")
        seen.append(name)
        e = fb[name]
        return f'set nri [head_tile_c9_flowbuf {{{name}}} {{{e["A"]}}}]\nif {{$nri ne "NULL"}} {{{mt.group(2)}}}\n'
    out = _N8_BLOCK.sub(sub, text)
    left = [x for x in re.findall(r"findInst \{([^}]*)\}\]", out) if _FLOWBUF_LEAF.search(x)]
    if left or sorted(seen) != sorted(fb):
        raise ValueError(f"HEAD_TILE_C9 native8 flow-buffer rewrite mismatch ({len(seen)} rewritten, {len(fb)} listed, "
                         f"{len(left)} left); fails closed")
    return out


def flowbuf_invperm(text):
    """Drop canonical9 permutation pairs between repair_design buffers; they must form closed cycles."""
    keep, dn, sn = [], [], []
    for ln in text.split("\n"):
        mt = _IP9_PAIR.match(ln)
        if mt and (_FLOWBUF_LEAF.search(mt.group(1)) or _FLOWBUF_LEAF.search(mt.group(2))):
            dn.append(mt.group(1))
            sn.append(mt.group(2))
            continue
        keep.append(ln)
    if sorted(dn) != sorted(sn) or not all(_FLOWBUF_LEAF.search(x) for x in dn + sn):
        raise ValueError("HEAD_TILE_C9 canonical9 flow-buffer pairs are not closed cycles; fails closed")
    return "\n".join(keep), len(dn)


def applies(P, tn):
    return getattr(P, "name", None) == DIE and tn == TYPE


def manifest():
    return json.loads((RECIPE / "MANIFEST.json").read_text())


def recipe_bytes(rel, m=None):
    """Raw bytes of one recipe file (gunzipped when stored as .gz), sha256-checked against MANIFEST.json."""
    m = m or manifest()
    ent = m["files"].get(rel)
    if ent is None:
        raise ValueError(f"HEAD_TILE_C9 recipe file {rel} not in MANIFEST.json; fails closed")
    p = RECIPE / ent["stored"]
    data = p.read_bytes()
    if p.suffix == ".gz":
        data = gzip.decompress(data)
    got = hashlib.sha256(data).hexdigest()
    if got != ent["sha256"]:
        raise ValueError(f"HEAD_TILE_C9 recipe file {rel} sha256 {got} != MANIFEST {ent['sha256']}; fails closed")
    return data


def _edit_once(text, old, new, what):
    n = text.count(old)
    if n != 1:
        raise ValueError(f"HEAD_TILE_C9 {what}: expected exactly one {old.strip()!r}, found {n}; fails closed")
    return text.replace(old, new)


def standalone_to_hook(name, text):
    for old, new in _STANDALONE_EDITS[name]:
        text = _edit_once(text, old, new, name)
    return text


def netlist_md5s(m):
    """The recipe netlist md5 plus the listed equivalent netlists (MANIFEST netlist_md5_equiv: same instance names and
    masters, only a reviewed pin/net delta, e.g. DIE-HEAD-52 l48c sender fix _48371_.A clk -> clk_t26)."""
    eq = m.get("netlist_md5_equiv", {})
    if not all(re.fullmatch(r"[0-9a-f]{32}", k) and isinstance(v, str) and v for k, v in eq.items()):
        raise ValueError("HEAD_TILE_C9 netlist_md5_equiv entries need a 32-hex md5 and a note; fails closed")
    return [m["netlist_md5"]] + sorted(eq)


def check_tcl(md5):
    md5 = [md5] if isinstance(md5, str) else list(md5)
    return f"""# GENERATED by tools/die_plan/head_tile_c9.py (HEAD-TILE-C9): the canonical9 recipe is keyed by instance name on
# ONE netlist (plus the reviewed equivalent netlists of MANIFEST netlist_md5_equiv).  Any other netlist fails closed
# (PLAN: regenerate the recipe for the new netlist), never a silent fallback.
proc head_tile_c9_check {{where}} {{
 set want {{{" ".join(md5)}}}
 set f /work/1_synth_odb.v
 if {{![file exists $f]}} {{error "HEAD_TILE_C9 netlist mismatch ($where): $f missing; canonical9 recipe fails closed (PLAN)"}}
 set got [lindex [exec md5sum $f] 0]
 if {{[lsearch -exact $want $got] < 0}} {{error "HEAD_TILE_C9 netlist mismatch ($where): 1_synth_odb.v md5 $got not in {{$want}}; canonical9 recipe fails closed (PLAN: regenerate the recipe for this netlist)"}}
 puts "HEAD_TILE_C9 netlist md5 $got OK ($where)"
}}
proc head_tile_c9_flowbuf {{name anet}} {{
 set net [[ord::get_db_block] findNet $anet]
 set hit {{}}
 if {{$net ne "NULL"}} {{
  foreach it [$net getITerms] {{
   if {{[[$it getMTerm] getName] ne "A"}} continue
   set i [$it getInst]
   if {{![regexp {{(^|/)(place|wire)[0-9]+$}} [$i getName]] || ![string match BUF* [[$i getMaster] getName]]}} continue
   if {{[info exists ::head_tile_c9_fb_used([$i getName])]}} continue
   lappend hit $i
  }}
 }}
 if {{[llength $hit] != 1}} {{incr ::head_tile_c9_fb_n(unresolved); return NULL}}
 set i [lindex $hit 0]
 set ::head_tile_c9_fb_used([$i getName]) $name
 incr ::head_tile_c9_fb_n(resolved)
 return $i
}}
proc head_tile_c9_run {{where script}} {{
 if {{[catch {{uplevel #0 $script}} msg]}} {{
  if {{[string match "HEAD_TILE_C9 *" $msg]}} {{error $msg}}
  error "HEAD_TILE_C9 recipe step $where fails closed (PLAN: named instance / inventory / legality mismatch): $msg"
 }}
}}
"""


PRE_TCL = """# GENERATED by tools/die_plan/head_tile_c9.py (HEAD-TILE-C9, step a): sourced by landing_placement.tcl after every
# cland_place_ff definition, before the group loop.  Netlist check first, then the reviewed head_native_hook.tcl.
source /work/head_tile_c9_check.tcl
head_tile_c9_check global_place
source /work/head_native_hook.tcl
rename cland_place_ff head_tile_c9_native_place_ff
proc cland_place_ff {prefix rect tag} {
 if {$prefix ne "u_cland_i"} {return [head_tile_c9_native_place_ff $prefix $rect $tag]}
 if {[catch {head_tile_c9_native_place_ff $prefix $rect $tag} n]} {
  if {[string match "HEAD_TILE_C9 *" $n]} {error $n}
  error "HEAD_TILE_C9 native ring u_cland_i fails closed (PLAN: band / ring inventory mismatch): $n"
 }
 set ::head_tile_c9_native $n
 return $n
}
"""

CORE_TCL = """# GENERATED by tools/die_plan/head_tile_c9.py (HEAD-TILE-C9, step a): end of face_flops.tcl, as in the reviewed kit.
if {![info exists ::head_tile_c9_native]} {error "HEAD_TILE_C9 native ring hook never ran on u_cland_i; canonical9 recipe fails closed (PLAN)"}
head_tile_c9_run head_tile_core {source /work/head_tile_core.tcl}
"""

RESTORE_TCL = r"""# GENERATED by tools/die_plan/head_tile_c9.py (HEAD-TILE-C9d, step d): restore the reviewed tile_v1 canonical9 placement (3_place.odb md5 e5b68f95, GRT50
# overflow 0, AUTO-GEOM PASS) on every netlist std cell with the same instance name (a resized master keeps its own size).  Flow buffers
# (place/wire/split/rebuffer<N>) are run-specific names, never matched by name: each goes to the centroid of the cells
# on its nets (2 passes, chains).  detailed_placement legalizes; fails closed on DPL/check errors.
set hr_blk [ord::get_db_block]
set hr_re {(^|/)(place|wire|split|rebuffer)[0-9]+$}
set hr_f [open /work/tile_v1_place.tsv r]
array set hr_n {moved 0 same 0 missing 0 master 0 locked 0 flowbuf_name 0}
while {[gets $hr_f ln] >= 0} {
 lassign [split $ln "\t"] nm ms x y o st
 if {[regexp $hr_re $nm]} {incr hr_n(flowbuf_name); continue}
 set i [$hr_blk findInst $nm]
 if {$i eq "NULL"} {incr hr_n(missing); continue}
 if {[[$i getMaster] getName] ne $ms} {incr hr_n(master)}
 set ps [$i getPlacementStatus]
 if {$ps eq "LOCKED" || $st eq "LOCKED"} {incr hr_n(locked); continue}
 set l [$i getLocation]
 if {[lindex $l 0] == $x && [lindex $l 1] == $y && [$i getOrient] eq $o} {incr hr_n(same); continue}
 if {$ps eq "FIRM"} {$i setPlacementStatus PLACED}
 $i setOrient $o
 $i setLocation $x $y
 $i setPlacementStatus $ps
 incr hr_n(moved)
}
close $hr_f
set hr_fb {}
foreach i [$hr_blk getInsts] {
 if {[[$i getMaster] isBlock] || ![regexp $hr_re [$i getName]]} continue
 if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
 lappend hr_fb $i
}
set hr_mv 0
foreach pass {1 2} {
 foreach i $hr_fb {
  set sx 0.0; set sy 0.0; set k 0
  foreach it [$i getITerms] {
   set n [$it getNet]
   if {$n eq "NULL" || [$n getSigType] in {POWER GROUND CLOCK}} continue
   foreach o [$n getITerms] {
    set j [$o getInst]
    if {$j eq $i} continue
    set b [$j getBBox]
    set sx [expr {$sx + ([$b xMin] + [$b xMax]) / 2.0}]; set sy [expr {$sy + ([$b yMin] + [$b yMax]) / 2.0}]; incr k
   }
   foreach o [$n getBTerms] {
    foreach bp [$o getBPins] { set b [$bp getBBox]; set sx [expr {$sx + ([$b xMin] + [$b xMax]) / 2.0}]; set sy [expr {$sy + ([$b yMin] + [$b yMax]) / 2.0}]; incr k; break }
   }
  }
  if {$k == 0} continue
  $i setLocation [expr {round($sx / $k)}] [expr {round($sy / $k)}]
  if {$pass == 2} {incr hr_mv}
 }
}
puts "HEAD_TILE_C9_RESTORE moved $hr_n(moved) same $hr_n(same) missing $hr_n(missing) master_diff(placed anyway) $hr_n(master) locked $hr_n(locked) skipped_flowbuf_names $hr_n(flowbuf_name); flow buffers to net centroid $hr_mv"
# Legalize every restored cell (FIRM ones too, they keep their status afterwards): sizes can differ from the reviewed
# run (resized masters), so a FIRM cell may overlap a neighbour by a site; DPL moves it the minimum distance.
set hr_firm {}
foreach i [$hr_blk getInsts] { if {[$i getPlacementStatus] eq "FIRM"} {lappend hr_firm $i; $i setPlacementStatus PLACED} }
set rc [catch {detailed_placement} msg]
foreach i $hr_firm {$i setPlacementStatus FIRM}
set cc [catch {check_placement -verbose} cm]
puts "HEAD_TILE_C9_RESTORE DPL=$rc $msg CHECK=$cc $cm"
if {$rc || $cc} {error "HEAD_TILE_C9 restore DPL rc=$rc check rc=$cc fails closed: $msg $cm"}
"""

POST_TCL = """# GENERATED by tools/die_plan/head_tile_c9.py (HEAD-TILE-C9, steps b+c): POST_DETAIL_PLACE_TCL.  The reviewed
# canonical8 + canonical9 placement on the loaded design; ORFS then writes it as 3_5_place_dp.odb -> 3_place.odb.
source /work/head_tile_c9_check.tcl
head_tile_c9_check post_detail_place
file mkdir /work/head_tile_c9_out
set ::head_tile_c9_rd $::env(RESULTS_DIR)
# The reviewed standalone DPL ran without the ORFS placement padding.
set_placement_padding -global -left 0 -right 0
try {
 array set ::head_tile_c9_fb_n {resolved 0 unresolved 0}
 head_tile_c9_run canonical8 {source /work/head_tile_c9_canonical8.tcl}
 puts "HEAD_TILE_C9 repair_design buffers by input net: $::head_tile_c9_fb_n(resolved) resolved, $::head_tile_c9_fb_n(unresolved) left at GPL/DPL"
 head_tile_c9_run canonical9 {source /work/head_tile_c9_canonical9.tcl}
 head_tile_c9_run restore {source /work/head_tile_c9_restore.tcl}
} finally {
 set ::env(RESULTS_DIR) $::head_tile_c9_rd
}
puts "HEAD_TILE_C9 canonical9 placement applied (POST_DETAIL_PLACE)"
"""


def install(P, tn, kd):
    """Install the recipe into kit dir kd when (die, type) = (s81_head, hd_tile).  Returns True when installed."""
    if not applies(P, tn):
        return False
    kd = Path(kd)
    m = manifest()
    if m.get("die") != DIE or m.get("type") != TYPE:
        raise ValueError("HEAD_TILE_C9 MANIFEST die/type mismatch; fails closed")
    lp, ff, cfg = kd / "landing_placement.tcl", kd / "face_flops.tcl", kd / "config.mk"
    if not lp.is_file() or LANDING_HOOK not in ff.read_text():
        raise ValueError("HEAD_TILE_C9 hd_tile kit has no landing placement hook; canonical9 recipe fails closed (PLAN)")
    txt = lp.read_text()
    if txt.rfind("proc cland_place_ff ") > txt.rfind(GPL_ANCHOR) or txt.count("cland_place_ff $prefix $rect $tag") < 1:
        raise ValueError("HEAD_TILE_C9 landing_placement.tcl group-loop anchor not after cland_place_ff; fails closed")
    cut = txt.rfind(GPL_ANCHOR) + 1
    lp.write_text(txt[:cut] + "source /work/head_tile_c9_pre.tcl\n" + txt[cut:])
    for rel in m["files"]:
        if rel in _STANDALONE_EDITS or rel in _FLOWBUF_EDITS:
            continue
        dst = kd / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(recipe_bytes(rel, m))
    fb = json.loads(recipe_bytes("flowbuf_inputs.json", m))["buffers"]
    (kd / "native8_placement.tcl").write_text(flowbuf_native8(recipe_bytes("native8_placement.tcl", m).decode(), fb))
    ip9, n_ip9 = flowbuf_invperm(recipe_bytes("canonical9_invperm.tcl", m).decode())
    (kd / "canonical9_invperm.tcl").write_text(ip9)
    for rel, out in (("dpl_canonical8.tcl", "head_tile_c9_canonical8.tcl"), ("dpl_canonical9.tcl", "head_tile_c9_canonical9.tcl")):
        (kd / out).write_text(standalone_to_hook(rel, recipe_bytes(rel, m).decode()))
    (kd / "head_tile_c9_check.tcl").write_text(check_tcl(netlist_md5s(m)))
    (kd / "head_tile_c9_pre.tcl").write_text(PRE_TCL)
    (kd / "head_tile_c9_core.tcl").write_text(CORE_TCL)
    (kd / "head_tile_c9_post.tcl").write_text(POST_TCL)
    (kd / "head_tile_c9_restore.tcl").write_text(RESTORE_TCL)
    with ff.open("a") as f:
        f.write("uplevel #0 {source /work/head_tile_c9_core.tcl}\n")
    c = cfg.read_text()
    if "POST_DETAIL_PLACE_TCL" in c:
        raise ValueError("HEAD_TILE_C9 config.mk already sets POST_DETAIL_PLACE_TCL; fails closed")
    cfg.write_text(c + "export POST_DETAIL_PLACE_TCL = /work/head_tile_c9_post.tcl\n")
    (kd / "head_tile_c9.json").write_text(json.dumps(dict(
        schema="opentallas.head_tile_c9.v1", die=DIE, type=TYPE, netlist_md5=m["netlist_md5"], netlist_md5_accepted=netlist_md5s(m),
        manifest_sha256=hashlib.sha256((RECIPE / "MANIFEST.json").read_bytes()).hexdigest(),
        review=m["review"], flow_buffers=dict(native8_by_input_net=len(fb), canonical9_pairs_dropped=n_ip9)),
        indent=1) + "\n")
    return True
