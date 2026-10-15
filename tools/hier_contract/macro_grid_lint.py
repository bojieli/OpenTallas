#!/usr/bin/env python3
"""MACRO-ON-GRID submit lint (owner 2026-10-11): refuse a job whose macro placement puts a macro's signal pins off the
routing tracks.  Measured twice on 2026-10-11: hcoll-port-tile4-b7891847f-g4a/b/c (INTERIOR=430/436: y0 = 19.88 um,
row pitch 61.04 um, 41 route failures) and hbm_sfu_lane_r4mpa/b (SRAM at y 182.25 um): M4 pins 8-24 nm off their track
-> DRT-0419 "No routing tracks pass through the center of Term" -> DRT-0255 maze failures.  Hard children placed by a
parent are checked the same way with their own LEF pin offsets: qkd_d2d_h-305021c34 put the ot_qkvd tiles on a
1.08 um grid (DRT-0418 / DRT-0073; fix 04612c41b snaps to 8.64 um).  Route scripts are followed with their positional
args and the files they source (route_master.sh CFG=$1 -> cfg/<CFG>.env EXTRA / MACRO_PLACEMENT_TCL / FW, FH).

How: the placement scripts a job names (MACRO_PLACEMENT_TCL, MACRO_PLACEMENT cfg, --step-tcl hooks that move macros,
MPT) are read at the source commit and EXECUTED in tclsh against a mock OpenDB (block / insts / masters from the job's
macro LEFs, die from --die-area / DIEW+DIEH / DIE_AREA, ::env from the commands), so computed placements are seen,
not only literal ones.  Every final macro origin + orientation is then checked pin by pin against the asap7 track
grid (tools/check_macro_track_alignment.py check_placement: the DRT-0419 centre test).

Verdicts: REFUSE when a placed macro has off-track signal pins AND an origin shift exists that puts more of them on
track (the placement's fault; the message names the macro, its position and the nearest on-grid origin).  WARN when
the LEF is off-lattice in its own frame (no shift helps), or when a script could not be evaluated.  SKIP when the job
places no macros by script.  Spec "macro_grid_lint": false opts out.

Usage: macro_grid_lint.py SPEC.json [...] [--repo DIR]
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import check_macro_track_alignment as cmta  # noqa: E402

MACRO_MOVE_RE = re.compile(r"setLocation|setOrigin|place_macro|\bplace_inst\b")
TIMEOUT_S = 60

# A move immediately preceded by this runtime check cannot move a BLOCK master.
# Require the exact receiver, an unconditional literal error, and no intervening
# command. Other guards, aliases, unresolved calls, or indirect object selection
# stay conservative. This is independent of filenames and declared macro counts.
STDCELL_MOVE_RE = re.compile(
    r'(?m)^[ \t]*if\s+\{\s*\[\[\$(?P<inst>[A-Za-z_]\w*)\s+getMaster\]\s+isBlock\]\s*\}'
    r'\s*\{\s*error\s+(?:"[^"$\[\\\n]*"|\{[^{}]*\})\s*\}'
    r'\s*;?\s*\$(?P=inst)\s+(?:setLocation|setOrigin)\b')


def has_macro_move(text: str) -> bool:
    """Unknown placement stays a macro candidate; only locally proven cells skip.

    Leave the arguments and subsequent commands in the text: removing an entire
    line could hide a second, genuine macro move after a semicolon.
    """
    # Tcl folds backslash-newlines even inside comments. A commented guard
    # must never establish a proof for the next real command.
    text = re.sub(r"\\\n[ \t]*", " ", text)
    return bool(MACRO_MOVE_RE.search(STDCELL_MOVE_RE.sub("", text)))


# ------------------------------------------------------------------------------------------- shell-ish expansion
def expand(s: str, env: dict) -> str:
    def rep(m):
        name, dflt = m.group(1) or m.group(4), m.group(3)
        if name in env:
            return env[name]
        return dflt if dflt is not None else m.group(0)
    for _ in range(8):
        n = re.sub(r"\$\{([A-Za-z_]\w*|\d)(:?[-=?]([^}]*))?\}|\$([A-Za-z_]\w*|\d)", rep, s)
        if n == s:
            break
        s = n
    return s


TEST_RE = re.compile(r'^\[\s+"?([^"\]]*?)"?\s+(=|!=)\s+"?([^"\]]*?)"?\s+\]$')
PREFIX_ASSIGN_RE = re.compile(r"\s*(?:export\s+|local\s+)?([A-Za-z_]\w*)=(\"[^\"]*\"|'[^']*'|[^\s;&|]*)")


def run_assigns(text: str, env: dict, keep: set) -> None:
    """leading assignments of each command (`A=b C='d e' cmd ...`, `export A=b`) and `[ "$X" = v ] && A=b && C=d`
    guards, in order; names in keep (the caller's env) win"""
    for line in re.sub(r"(?m)#.*$", "", text).splitlines():
        for seg in re.split(r";\s*", line.strip()):
            ok = True
            for p in (x.strip() for x in seg.split("&&")):
                t = TEST_RE.match(p)
                if t:
                    a, op, b = expand(t.group(1), env), t.group(2), expand(t.group(3), env)
                    ok = ok and ((a == b) if op == "=" else (a != b))
                    continue
                pos, got = 0, False
                while True:
                    m = PREFIX_ASSIGN_RE.match(p, pos)
                    if not m or m.end() == pos:
                        break
                    got, pos = True, m.end()
                    if ok and m.group(1) not in keep:
                        env[m.group(1)] = expand(m.group(2).strip("\"'"), env)
                if not got:
                    break


def norm(p: str) -> str | None:
    p = re.sub(r"^(/src/|\{SRC\}/|\{SRCDIR\}/|\$\{?SRC\}?/)", "", p.strip("\"'"))
    p = p[2:] if p.startswith("./") else p
    return None if (not p or p.startswith("/") or "{" in p) else p


# ------------------------------------------------------------------------------------------- job file discovery
def job_inputs(spec: dict, git) -> dict:
    """{"tcl": {path: wildcard_family|None}, "cfg": [paths], "lefs": {master: path}, "die": (w, h) | None, "env": {}}"""
    commit = str((spec.get("source") or {}).get("commit", ""))
    st = spec.get("stages") or {}
    cmds = [st[k]["cmd"] for k in ("route", "calibrate") if isinstance(st.get(k), dict) and st[k].get("cmd")]
    out = {"tcl": {}, "cfg": [], "lefs": {}, "die": None, "env": {}}
    for cmd in cmds:
        env: dict = {}
        run_assigns(cmd.replace("&&", ";"), env, set())
        texts = [(cmd, env)]
        for sc, argstr in re.findall(r"([\w./${}:-]+\.sh)\b([^;&|\n]*)", cmd):
            p = norm(expand(sc, env))
            body = git.show(commit, p) if p else None
            if body:
                senv = dict(env)
                for i, a in enumerate(argstr.split()[:9], 1):        # positional args: CFG=$1 in route_master.sh
                    senv[str(i)] = a
                run_assigns(body, senv, set(env))
                texts.append((body, senv))
                # files the script sources (cfg/<CFG>.env: MACROS, EXTRA --macro-view, MACRO_PLACEMENT_TCL, FW/FH)
                for src in re.findall(r"(?m)^\s*(?:source|\.)\s+(\S+)", body):
                    q = norm(expand(src, senv))
                    stxt = git.show(commit, q) if q and "$" not in q else None
                    if stxt:
                        run_assigns(stxt, senv, set(env))
                        texts.append((stxt, senv))
        for body, e in texts:
            for k, v in e.items():
                out["env"].setdefault(k, v)
            body = re.sub(r"(?m)#.*$", "", body)
            flat = expand(body.replace("\\\n", " "), e)
            for k, v in re.findall(r"--orfs-var\s+['\"]?([A-Z_][A-Z0-9_]*)=([^'\"\s]*)", flat):
                out["env"].setdefault(k, v)
            for tok in re.findall(r"(?:MACRO_PLACEMENT_TCL=|POST_MACRO_PLACE=|MACRO_PLACE\w*=|--step-tcl\s+\w+=|"
                                  r"MPT=)(\S+)", flat):
                p = norm(tok.rstrip(")'\""))
                if p and p.endswith(".tcl"):
                    out["tcl"].setdefault(p, None)
            out.setdefault("named", set()).update(re.findall(r"\b(ot_(?:sram|rom|rf|regfile)\w+)", flat))
            for tok in re.findall(r"MACRO_PLACEMENT=(\S+)", flat):
                p = norm(tok)
                if p:
                    out["cfg"].append(p)
            for name, d in re.findall(r"--macro-view\s+(?:([\w.-]+)=)?(\S+)", flat):
                d = norm(d.rstrip("/"))
                if d:
                    name = name or d.rsplit("/", 1)[-1]
                    out["lefs"].setdefault(name, f"{d}/{name}.lef")
            for tok in re.findall(r"(?:MACROV|LANEDIR|SD)=(\S+)", flat):
                d = norm(tok.rstrip("/"))
                if d:
                    out["lefs"].setdefault(d.rsplit("/", 1)[-1], f"{d}/{d.rsplit('/', 1)[-1]}.lef")
            da = re.search(r"--die-area\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", flat)
            if da and not out["die"]:
                x0, y0, x1, y1 = map(float, da.groups())
                out["die"] = (x1 - x0, y1 - y0)
            ca = re.search(r"--core-area\s+([-\d.]+)\s+([-\d.]+)", flat)
            if ca and "core_margin" not in out:
                out["core_margin"] = (float(ca.group(1)), float(ca.group(2)))
    env = out["env"]
    if not out["die"]:
        if env.get("FW") and env.get("FH"):
            try:
                out["die"] = (float(env["FW"]), float(env["FH"]))
            except ValueError:
                pass
        if not out["die"] and env.get("DIEW") and env.get("DIEH"):
            try:
                out["die"] = (float(env["DIEW"]), float(env["DIEH"]))
            except ValueError:
                pass
        elif env.get("DIE_AREA"):
            v = [float(x) for x in env["DIE_AREA"].split()[:4]]
            out["die"] = (v[2] - v[0], v[3] - v[1]) if len(v) == 4 else None
    # unresolved $vars in a script path: every file of that family at the commit (each evaluated; see check())
    resolved = {}
    for p in out["tcl"]:
        if "$" not in p:
            resolved[p] = None
            continue
        d, pat = p.rsplit("/", 1)
        rx = re.compile("^" + re.sub(r"\\\$\w+|\\\$\\\{[^}]*\\\}", ".*", re.escape(pat)) + "$")
        for f in git.ls(commit, d):
            if rx.match(f):
                resolved[f"{d}/{f}"] = p
    out["tcl"] = resolved
    for k, v in list(out["lefs"].items()):
        if "$" in v or git.show(commit, v) is None:
            del out["lefs"][k]
    return out


# ------------------------------------------------------------------------------------------- mock OpenDB run
TCL_PRELUDE = r"""
namespace eval ::mk { variable D; array set D {}; variable n 0; variable touched {}; variable srcroot "" }
proc ::mk::obj {kind data} { variable n; variable D; incr n; set id ::mk::o$n; set D($id) [dict merge $data [list kind $kind]]
  proc $id {method args} "::mk::call $id \$method {*}\$args"; return $id }
proc ::mk::get {id k} { variable D; return [dict get $D($id) $k] }
proc ::mk::set_ {id k v} { variable D; dict set D($id) $k $v }
proc ::mk::rect {x0 y0 x1 y1} { return [::mk::obj rect [list x0 $x0 y0 $y0 x1 $x1 y1 $y1]] }
proc ::mk::touch {id} { variable touched; if {[lsearch -exact $touched $id] < 0} { lappend touched $id } }
proc ::mk::call {id method args} {
  set k [::mk::get $id kind]
  switch -- $k/$method {
    block/getInsts { return $::mk::insts }
    block/getDbUnitsPerMicron { return 1000 }
    block/getDieArea { return $::mk::die }
    block/getCoreArea { return $::mk::core }
    block/getName { return mock_top }
    block/getBTerms - block/getNets - block/getRows { return {} }
    block/findInst { return [::mk::find_or_make [lindex $args 0]] }
    block/findMaster - db/findMaster { foreach m $::mk::masters { if {[::mk::get $m name] eq [lindex $args 0]} { return $m } }; return "NULL" }
    block/getTech - db/getTech { return $::mk::tech }
    tech/getDbUnitsPerMicron { return 1000 }
    db/getChip { return $::mk::chip }
    chip/getBlock { return $::mk::block }
    rect/xMin { return [::mk::get $id x0] } rect/yMin { return [::mk::get $id y0] }
    rect/xMax { return [::mk::get $id x1] } rect/yMax { return [::mk::get $id y1] }
    rect/dx { return [expr {[::mk::get $id x1]-[::mk::get $id x0]}] }
    rect/dy { return [expr {[::mk::get $id y1]-[::mk::get $id y0]}] }
    rect/getDX { return [expr {[::mk::get $id x1]-[::mk::get $id x0]}] }
    rect/getDY { return [expr {[::mk::get $id y1]-[::mk::get $id y0]}] }
    master/getName - master/getConstName { return [::mk::get $id name] }
    master/getType { return BLOCK }
    master/isBlock { return 1 }
    master/getWidth { return [::mk::get $id w] }
    master/getHeight { return [::mk::get $id h] }
    inst/getName - inst/getConstName { return [::mk::get $id name] }
    inst/getMaster { return [::mk::get $id master] }
    inst/isBlock { return 1 }
    inst/getOrient { return [::mk::get $id orient] }
    inst/setOrient { ::mk::set_ $id orient [lindex $args 0]; ::mk::touch $id; return }
    inst/setLocation { ::mk::set_ $id llx [expr {round([lindex $args 0])}]; ::mk::set_ $id lly [expr {round([lindex $args 1])}]; ::mk::touch $id; return }
    inst/setOrigin { set m [::mk::get $id master]; set w [::mk::get $m w]; set h [::mk::get $m h]
      set ox [expr {round([lindex $args 0])}]; set oy [expr {round([lindex $args 1])}]
      switch -- [::mk::get $id orient] { MX { set oy [expr {$oy-$h}] } MY { set ox [expr {$ox-$w}] } R180 { set ox [expr {$ox-$w}]; set oy [expr {$oy-$h}] } }
      ::mk::set_ $id llx $ox; ::mk::set_ $id lly $oy; ::mk::touch $id; return }
    inst/getLocation - inst/getOrigin { return [list [::mk::get $id llx] [::mk::get $id lly]] }
    inst/setPlacementStatus { ::mk::set_ $id status [lindex $args 0]; return }
    inst/getPlacementStatus { return [::mk::get $id status] }
    inst/isFixed { return [expr {[::mk::get $id status] eq "FIRM"}] }
    inst/getBBox { set m [::mk::get $id master]; set x [::mk::get $id llx]; set y [::mk::get $id lly]
      set w [::mk::get $m w]; set h [::mk::get $m h]; if {[::mk::get $id orient] in {R90 R270 MXR90 MYR90}} { lassign [list $h $w] w h }
      return [::mk::rect $x $y [expr {$x+$w}] [expr {$y+$h}]] }
    default { error "MOCK_UNSUPPORTED $k/$method" }
  }
}
proc ::mk::find_or_make {nm} {
  foreach i $::mk::insts { if {[::mk::get $i name] eq $nm} { return $i } }
  if {[string match __mk* $nm] || ![llength $::mk::masters]} { return "NULL" }
  # a literal instance name (place_macro / findInst): new instance of the master its name contains, else the first master
  set m [lindex $::mk::masters 0]
  foreach c $::mk::masters { if {[string first [::mk::get $c name] $nm] >= 0} { set m $c } }
  set i [::mk::obj inst [list name $nm master $m orient R0 llx 0 lly 0 status PLACED idx 0]]
  lappend ::mk::insts $i; dict set ::mk::byname $nm $i; return $i }
namespace eval ::ord {}
proc ::ord::get_db_tech {} { return $::mk::tech }
proc ::ord::get_db_block {} { return $::mk::block }
proc ::ord::get_db {} { return $::mk::db }
proc ::ord::get_db_core {} { return $::mk::die }
proc ::ord::dbu_to_microns {v} { return [expr {$v/1000.0}] }
proc ::ord::microns_to_dbu {v} { return [expr {round($v*1000)}] }
namespace eval ::utl {}
proc ::utl::info {args} { puts "utl: $args" }
proc ::utl::warn {args} { puts "utl: $args" }
proc ::utl::report {args} { puts "utl: $args" }
proc place_macro {args} { array set a {-orientation R0}; array set a $args
  set i [::mk::find_or_make $a(-macro_name)]
  if {$i eq "NULL"} { error "place_macro: no mock instance $a(-macro_name)" }
  $i setOrient $a(-orientation); $i setLocation [expr {[lindex $a(-location) 0]*1000}] [expr {[lindex $a(-location) 1]*1000}] }
rename source ::mk::_source
proc source {args} { set f [lindex $args end]; regsub {^/src/} $f "" f
  if {[file pathtype $f] ne "absolute"} { set f [file join $::mk::srcroot $f] }
  uplevel 1 [list ::mk::_source $f] }
rename regexp ::mk::_regexp
proc regexp {args} {
  set opts {}; while {[string match -* [lindex $args 0]]} { set o [lindex $args 0]; set args [lrange $args 1 end]; if {$o eq "--"} break; lappend opts $o }
  set pat [lindex $args 0]; set str [lindex $args 1]; set vars [lrange $args 2 end]
  if {![string match __mk* $str] || "-all" in $opts || "-inline" in $opts} { return [uplevel 1 [list ::mk::_regexp {*}$opts -- $pat $str {*}$vars]] }
  # a mock instance name matches every name pattern: captures cycle through the digit class of each group
  set idx [::mk::get [lindex [dict get $::mk::byname $str]] idx]
  set groups [::mk::_regexp -all -inline {\((?!\?)([^()]*)\)} $pat]
  set caps {}
  foreach {all g} $groups {
    if {[::mk::_regexp {^\\?\[(\d)-(\d)\\?\]$} $g -> a b]} { lappend caps [expr {$a + $idx % ($b-$a+1)}]
    } elseif {[::mk::_regexp {^\\?\[(\d+)\\?\]$} $g -> ds]} { lappend caps [string index $ds [expr {$idx % [string length $ds]}]]
    } else { lappend caps 0 }
  }
  set vals [concat [list $str] $caps]
  set k 0
  foreach v $vars { upvar 1 $v vv; set vv [lindex $vals $k]; incr k }
  return 1
}
"""


def build_mock(masters: dict, counts: dict, die, env: dict, srcroot: str, core_margin=None) -> str:
    t = [TCL_PRELUDE, f"set ::mk::srcroot {{{srcroot}}}"]
    for k, v in env.items():
        if re.fullmatch(r"[A-Za-z_]\w*", k) and "{" not in v and "}" not in v:
            t.append(f"set ::env({k}) {{{v}}}")
    t.append("set ::mk::tech [::mk::obj tech {}]; set ::mk::masters {}; set ::mk::insts {}; set ::mk::byname {}")
    if die:
        mx, my = (round(v * 1000) for v in (core_margin or (0.0, 0.0)))
        t.append(f"set ::mk::die [::mk::rect 0 0 {round(die[0] * 1000)} {round(die[1] * 1000)}]")
        t.append(f"set ::mk::core [::mk::rect {mx} {my} {round(die[0] * 1000) - mx} {round(die[1] * 1000) - my}]")
    else:
        t.append("set ::mk::die [::mk::obj nodie {}]; set ::mk::core $::mk::die")
    idx = 0
    for name, m in masters.items():
        t.append(f"set _m [::mk::obj master [list name {name} w {m['W']} h {m['H']}]]; lappend ::mk::masters $_m")
        for i in range(counts.get(name, 1)):
            nm = f"__mk{idx}"
            t.append(f"set _i [::mk::obj inst [list name {nm} master $_m orient R0 llx 0 lly 0 status PLACED idx {i}]]; "
                     f"lappend ::mk::insts $_i; dict set ::mk::byname {nm} $_i")
            idx += 1
    t.append("set ::mk::block [::mk::obj block {}]; set ::mk::chip [::mk::obj chip {}]; set ::mk::db [::mk::obj db {}]")
    return "\n".join(t) + "\n"


TCL_EPILOGUE = r"""
foreach i $::mk::touched { set m [::mk::get $i master]
  puts "MKPLACE [::mk::get $m name] [::mk::get $i name] [::mk::get $i llx] [::mk::get $i lly] [::mk::get $i orient]" }
"""


def run_mock(script_path: str, masters: dict, counts: dict, die, env: dict, files: dict,
             core_margin=None) -> tuple[list, str | None]:
    """execute the placement tcl (files = {repo path: text}, materialised under a temp srcroot); -> placements, error"""
    with tempfile.TemporaryDirectory(prefix="mgl-") as td:
        for p, txt in files.items():
            f = Path(td) / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(txt)
        drv = Path(td) / "_drive.tcl"
        drv.write_text(build_mock(masters, counts, die, env, td, core_margin)
                       + f"if {{[catch {{source {{{Path(td) / script_path}}}}} e]}} {{ puts \"MKERROR $e\" }}\n"
                       + TCL_EPILOGUE)
        r = subprocess.run(["tclsh", str(drv)], capture_output=True, text=True, timeout=TIMEOUT_S)
    out = r.stdout + r.stderr
    err = next((l[8:] for l in out.splitlines() if l.startswith("MKERROR ")), None)
    if r.returncode and not err:
        err = out.strip()[-300:]
    pl = []
    for l in out.splitlines():
        if l.startswith("MKPLACE "):
            _, master, inst, x, y, o = l.split()[:6]
            pl.append((master, inst, int(x), int(y), o))
    return pl, err


def with_sources(path: str, git, commit: str, files: dict, depth: int = 0) -> None:
    if path in files or depth > 4:
        return
    txt = git.show(commit, path)
    if txt is None:
        return
    files[path] = txt
    for s in re.findall(r"(?m)^\s*source\s+(\S+)", txt):
        p = norm(s)
        if p and "$" not in p:
            with_sources(p, git, commit, files, depth + 1)


def count_hint(text: str) -> int | None:
    n = [int(x) for x in re.findall(r"llength[^\]]*\]\s*(?:!=|==|<|>=|>)\s*(\d+)", text)]
    n += [int(x) for x in re.findall(r"(?:requires exactly|expected|found)\s+(\d+)", text)]
    return max(n) if n else None


# ------------------------------------------------------------------------------------------- track check
def offtrack(m: dict, orient: str, ox: int, oy: int) -> int:
    r = cmta.check_placement(m, orient, ox, oy)
    return sum(v["offtrack"] for v in r["layers"].values())


def best_shift(m: dict, orient: str, ox: int, oy: int) -> tuple[int, int, int]:
    """(fewest off-track pins over any origin shift, dx, dy) - each axis independently over its lattice period"""
    best = {}
    for axis in ("x", "y"):
        coords = []
        for p in m["pins"]:
            if p["use"] in ("POWER", "GROUND"):
                continue
            for lay, r in p["rects"]:
                if lay not in cmta.ASAP7_TRACKS_NM:
                    continue
                if (axis == "y") != (cmta.ASAP7_LAYERS[lay][0] == "H"):
                    continue
                q = cmta.transform_rect(r, orient, m["W"], m["H"])
                c2 = (q[1] + q[3] + 2 * oy) if axis == "y" else (q[0] + q[2] + 2 * ox)
                coords.append((lay, c2))
        if not coords:
            best[axis] = (0, 0)
            continue
        per = {lay: cmta.track_residues(cmta.ASAP7_TRACKS_NM[lay], axis) for lay in {c[0] for c in coords}}
        L = 1
        for P, _ in per.values():
            L = L * P // math.gcd(L, P)
        cnt = Counter((lay, c2 % (2 * per[lay][0])) for lay, c2 in coords)
        res = None
        for s in range(L):
            off = 0
            for (lay, c2), k in cnt.items():
                P, T = per[lay]
                if c2 % 2 or ((c2 // 2 + s) % P) not in T:
                    off += k
            sd = s if s <= L // 2 else s - L
            if res is None or off < res[0] or (off == res[0] and abs(sd) < abs(res[1])):
                res = (off, sd)
        best[axis] = res
    return best["x"][0] + best["y"][0], best["x"][1], best["y"][1]


# ------------------------------------------------------------------------------------------- driver
def check(spec: dict, git, max_list: int = 6) -> dict:
    if spec.get("macro_grid_lint", True) is False:
        return {"verdict": "SKIP", "message": "macro_grid_lint opted out"}
    commit = str((spec.get("source") or {}).get("commit", ""))
    ji = job_inputs(spec, git)
    scripts, sources = {}, {}
    for p, fam in ji["tcl"].items():
        files: dict = {}
        with_sources(p, git, commit, files)
        if any(has_macro_move(t) for t in files.values()):
            scripts[p], sources[p] = fam, files
    if not scripts and not ji["cfg"]:
        return {"verdict": "SKIP", "message": "no macro placement script named by the job"}
    named = set(ji.get("named", ()))
    for files in sources.values():
        for t in files.values():
            named |= set(re.findall(r"\b(ot_(?:sram|rom|rf|regfile)\w+)", t))
    for n in sorted(named - set(ji["lefs"])):
        lp = f"physical/asap7_memory_macros/{n}/{n}.lef"
        if git.show(commit, lp) is not None:
            ji["lefs"][n] = lp
    masters = {}
    for name, lp in ji["lefs"].items():
        for m in cmta.parse_lef(git.show(commit, lp) or ""):
            if m["W"] and m["H"]:
                masters[m["name"]] = m
    if not masters:
        return {"verdict": "WARN", "message": f"MACRO_GRID WARN: macro placement {sorted(scripts) or ji['cfg']} but no "
                                              f"macro LEF resolved from the commands"}
    findings, warns, evaluated = [], [], {}
    for p, fam in sorted(scripts.items()):
        files = sources[p]
        hint = count_hint("\n".join(files.values())) or 2
        counts = {n: hint for n in masters}
        try:
            pl, err = run_mock(p, masters, counts, ji["die"], ji["env"], files, ji.get("core_margin"))
        except (subprocess.TimeoutExpired, OSError) as ex:
            pl, err = [], f"{type(ex).__name__}"
        if err and not pl:
            if any(re.search(r"place_macro|\bBLOCK\b|isBlock|ot_(?:sram|rom)", t) for t in files.values()):
                warns.append(f"{p}: not evaluated ({err[:160]})")
            continue
        bad = []
        for master, inst, x, y, o in sorted(set((a, "", x, y, o) for a, _, x, y, o in pl)):
            m = masters.get(master)
            if m is None or o not in cmta.ORIENT:
                continue
            n_off = offtrack(m, o, x, y)
            if not n_off:
                continue
            b, dx, dy = best_shift(m, o, x, y)
            n_sig = sum(len(q["rects"]) for q in m["pins"] if q["use"] not in ("POWER", "GROUND"))
            bad.append({"master": master, "inst": inst, "x_um": x / 1000, "y_um": y / 1000, "orient": o, "off": n_off,
                        "pins": n_sig, "best": b, "to_um": ((x + dx) / 1000, (y + dy) / 1000), "fixable": b < n_off})
        evaluated[p] = {"family": fam, "placed": len(pl), "bad": bad, "error": err}
    fixable = {p: e for p, e in evaluated.items() if any(b["fixable"] for b in e["bad"])}
    # a $var-resolved family: refuse only when every evaluated member is off-grid (we cannot tell which one runs)
    fams: dict = {}
    for p, e in evaluated.items():
        fams.setdefault(e["family"] or p, []).append(p)
    refuse = [p for fam, ps in fams.items() for p in ps if all(q in fixable for q in ps) and p in fixable]
    msgs = []
    for p in sorted(fixable):
        e = evaluated[p]
        ex = "; ".join(f"{b['master']} at ({b['x_um']:.3f}, {b['y_um']:.3f}) {b['orient']}: {b['off']} of {b['pins']} "
                       f"signal pins off-track (nearest on-grid origin ({b['to_um'][0]:.3f}, {b['to_um'][1]:.3f}) leaves {b['best']})"
                       for b in [b for b in e["bad"] if b["fixable"]][:max_list])
        msgs.append(f"{p}: {sum(b['fixable'] for b in e['bad'])} of {e['placed']} placed macros off-grid: {ex}")
    lef_only = [b for e in evaluated.values() for b in e["bad"] if not b["fixable"]]
    if lef_only:
        warns.append(f"{len(lef_only)} macros with pins off-lattice in their own LEF frame (no origin fixes it): "
                     + ", ".join(sorted({b['master'] for b in lef_only})))
    rec = {"evaluated": {p: {k: v for k, v in e.items() if k != "bad"} | {"off_grid": len(e["bad"])}
                         for p, e in evaluated.items()}, "warns": warns}
    if refuse:
        return {"verdict": "REFUSE", **rec,
                "message": "MACRO_GRID: " + " || ".join(m for m in msgs if m.split(":")[0] in refuse)
                           + " -- place every macro at an origin that keeps its pins on the asap7 tracks (M4 y 0.012+0.048k, "
                             "M5 x 0.012+0.048k; tools/check_macro_track_alignment.py lists the legal residues per LEF)"}
    if msgs or warns:
        return {"verdict": "WARN", **rec, "message": "MACRO_GRID WARN: " + " || ".join(msgs + warns)}
    return {"verdict": "PASS", **rec, "message": "macro grid: " + ", ".join(
        f"{p} {e['placed']} macros on-grid" for p, e in evaluated.items())}


class Git:
    def __init__(self, repo):
        self.repo = str(repo)

    def show(self, commit, path):
        r = subprocess.run(["git", "-C", self.repo, "show", f"{commit}:{path}"], capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else None

    def ls(self, commit, d):
        r = subprocess.run(["git", "-C", self.repo, "ls-tree", "--name-only", f"{commit}:{d}"], capture_output=True,
                           text=True, timeout=60)
        return r.stdout.split() if r.returncode == 0 else []


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("specs", nargs="+", help="job spec json (or a loop state json with a 'spec' key)")
    ap.add_argument("--repo", default=str(HERE.parent.parent))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    g = Git(a.repo)
    rc = 0
    for s in a.specs:
        d = json.loads(Path(s).read_text())
        spec = d.get("spec", d)
        r = check(spec, g)
        print(json.dumps(r, indent=1) if a.json else f"{spec.get('name')}: {r['verdict']} {r['message'][:900]}")
        rc = max(rc, 1 if r["verdict"] == "REFUSE" else 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
