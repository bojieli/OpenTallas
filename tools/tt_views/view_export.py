#!/usr/bin/env python3
"""Macro view export at SS / FF / TT (OWNER OPTION B 2026-10-07: setup signs off at TT, hold at FF, SS = sensitivity).

write_timing_model from the routed 6_final odb + spef (write_abstract_lef in the SS pass), at SS, FF and TT (ASAP7 NLDM
libraries and each sub-macro's <name>_<corner>.lib).  Self-contained (no repo imports) so it can be copied to any host
and run next to the route:

    python3 view_export.py --orfs-dir W/work/orfs --name NAME --out DIR [--interface-sdc F] [--macro-view D ...]
                           [--corners ss,ff,tt] [--image openroad/orfs:latest] [--tmp-dir T]
                           [--verdict-json F | --no-verdict] [--sdc-name N] [--post-sdc F ...] [--verdict-tol PS]
                           [--job-json F --src DIR [--cl-dir D] [--job-extra-sdc F]] [--expect-tt PS] [--expect-ff PS] [--require-check]

CONSTRAINT SEQUENCE (export-sdc 2026-10-13).  A view must carry the timing its route was SIGNED OFF with, so the
constraints are read in the verdict's own order, never a substitute:
  1. VERDICT REPLAY (default whenever the route sits in a closure-loop run: <RUN>/routes/<L>/work/orfs with
     <RUN>/cl/routed_ioref.a<N>*.json, or --verdict-json F): the constraint section of the verdict's own STA Tcl
     (<json stem>_meas/meas_{ss,ff}.tcl, from read_db up to the reports: routed 6_final.sdc, SPEF, propagated clocks,
     every post-SDC, io_ref_routed.sdc last) is replayed VERBATIM with the verdict's mounts (/work = the verdict's ORFS
     dir, /src = <RUN>/src, /meas).  SS and TT replay the setup Tcl, FF the hold Tcl.  The session slack is then checked
     against the verdict (TT setup, FF hold; --verdict-tol, default 0.05 ps): a mismatch FAILS the export.  A verdict
     timed on another ODB / SPEF than the one being exported is refused (stale verdict), not skipped.
  2. CORNER_STA REPLAY (a loop run without a routed_ioref verdict): the constraint section of the route's own
     corner_sta Tcl (<orfs>/w18_sta_{ss,ff}.tcl), verbatim; recorded as unchecked.
  2b. JOB REPLAY (--job-json F --src DIR; an ARCHIVED or legacy-lane route whose verdict Tcl is gone: closed_archive
     <block>/<run>/job.json, <RUN>/cl/job.json): the sequence is rebuilt from the job record's OWN sign-off fields --
     metrics.sdc_name, SPEF, set_propagated_clock, metrics.post_sdc in order (read from DIR = the job commit's tree plus
     its flow overlay, mounted /src; setup_post_sdc in the SS / TT sessions only), then what the routed_ioref re-STA
     inserted / replaced / appended (files of --cl-dir, default F's directory or its run/cl) -- and CHECKED against the
     job's verdict (routed_ioref.a<N>.json when clean, else metrics tt_ps / ff_ps).  A post-SDC that is not in DIR fails
     the export.  (el1013-s81-wfcstg: three WFC views were exported by hand with --no-verdict --post-sdc
     cl/io_ref_routed.sdc only; the jobs' post_sdc -- signoff_unc60.sdc, region_die150_union.sdc: the 833 ps sign-off
     clock / uncertainty over a 770 ps route SDC -- were left out, TT read -55 / +37 against verdicts +7.75 / +141.65
     and nothing failed, because a --post-sdc export had no expectation to fail against.)
  3. --post-sdc F ... (no verdict to replay): routed <--sdc-name>, SPEF, set_propagated_clock, then each F in order
     (tools/w18/corner_sta.py's order).  UNCHECKED unless --expect-tt / --expect-ff name the sign-off slack; the record
     says checked=false and --require-check turns an unchecked export into a failure (exit 5).
  4. legacy (none of these): the routed 6_final.sdc, or --interface-sdc read INSTEAD of it.  This is an interface extraction
     for hand flows; it is NOT the sign-off sequence (s81su SMT: FF -19.69 exported vs +3.66 verdict).
With a verdict replay --interface-sdc is recorded but does not change the sequence.

--corners tt alone adds <name>_tt.lib to a view whose LEF / SS / FF were already written from the SAME route by
hbm_fmax_attn_abstract.py (pass the same --interface-sdc / --macro-view it used).  Exit 0 iff every corner finished.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
CELLS = ["asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz",
         "asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib",
         "asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz"]
VT = {"L": ("LVT", "L"), "SL": ("SLVT", "SL")}   # odb cell suffix -> (lib tag, lef tag)


# A generated clock at the output makes write_timing_model emit clk_out -> clk_out
# arcs. Keep the sign-off slack above this extraction intact, then remove only the
# output boundary clock so the ETM describes the real clk_in -> clk_out path.
FORWARDED_CLOCK_TCL = r"""
if {[llength [get_ports -quiet clk_in]] && [llength [get_ports -quiet clk_out]]} {
  set ot_fc_block [ord::get_db_block]
  set ot_fc_in [[$ot_fc_block findBTerm clk_in] getNet]
  set ot_fc_out [[$ot_fc_block findBTerm clk_out] getNet]
  set ot_fc_drivers {}
  foreach it [$ot_fc_out getITerms] {
    if {[$it getIoType] eq "OUTPUT"} {lappend ot_fc_drivers $it}
  }
  if {[llength $ot_fc_drivers] != 1} {error "forwarded clk_out must have exactly one physical driver"}
  set ot_fc_it [lindex $ot_fc_drivers 0]
  set ot_fc_inst [$ot_fc_it getInst]
  set ot_fc_inputs 0
  foreach it [$ot_fc_inst getITerms] {
    if {[$it getIoType] ne "INPUT"} {continue}
    incr ot_fc_inputs
    if {[$it getNet] ne $ot_fc_in} {error "forwarded clk_out is not directly buffered from clk_in"}
  }
  if {$ot_fc_inputs != 1} {error "forwarded clk_out driver must have one input"}
  puts "OT_FC_DRIVER [[$ot_fc_inst getMaster] getName] [$ot_fc_inst getName]"
  set ot_fc_root {}
  foreach c [all_clocks] {
    foreach source [get_property $c sources] {
      if {[get_full_name $source] eq "clk_in"} {lappend ot_fc_root $c}
      if {[get_full_name $source] eq "clk_out"} {delete_clock $c}
    }
  }
  if {[llength $ot_fc_root] != 1} {error "forwarded clk_in needs exactly one source clock"}
  set ot_fc_root [lindex $ot_fc_root 0]
  set ot_fc_wave [$ot_fc_root waveform]
  if {[llength $ot_fc_wave] != 2} {error "forwarded clock needs exactly two waveform edges"}
  set_clock_latency -source 0 $ot_fc_root
  unset_input_delay [get_ports clk_in]
  set_propagated_clock [all_clocks]
  sta::find_timing_paths -path_delay max -group_path_count 1
  set ot_fc_driver_pin [get_pins "[$ot_fc_inst getName]/[[$ot_fc_it getMTerm] getName]"]
  set ot_fc_pin [sta::get_port_pin [lindex [get_ports clk_out] 0]]
  foreach prop {arrival_max_rise arrival_min_rise arrival_max_fall arrival_min_fall slew_max_rise slew_max_fall} {
    set value [get_property $ot_fc_pin $prop]
    set driver_value [get_property $ot_fc_driver_pin $prop]
    if {[string match arrival_* $prop]} {
      set edge [expr {[string match *_fall $prop] ? 1 : 0}]
      set phase [sta::time_sta_ui [lindex $ot_fc_wave $edge]]
      set value [expr {$value - $phase}]
      set driver_value [expr {$driver_value - $phase}]
    }
    puts "OT_FC_METRIC $prop $value"
    puts "OT_FC_DRIVER_METRIC $prop $driver_value"
  }
  puts "OT_FC_ROOT clk_in"
}
"""


def forwarded_clock_receipt(log, corner, odb_sha256, spef_sha256):
    """Parse native propagated STA; absence is ordinary for non-forwarded tiles."""
    driver = re.findall(r"^OT_FC_DRIVER (\S+) (.+)$", log, re.M)
    if not driver:
        if re.search(r'^OT_FC_(?:METRIC|ROOT) ', log, re.M):
            raise VerdictError('forwarded-clock provenance has no physical driver')
        return None
    raw_values = re.findall(r"^OT_FC_METRIC (\S+) (\S+)$", log, re.M)
    values = dict(raw_values)
    required = ('arrival_max_rise', 'arrival_min_rise', 'arrival_max_fall',
                'arrival_min_fall', 'slew_max_rise', 'slew_max_fall')
    import math
    if len(driver) != 1 or len(raw_values) != len(required) or 'OT_FC_ROOT clk_in' not in log or set(values) != set(required):
        raise VerdictError('incomplete native forwarded-clock measurement')
    values = {k: float(v) for k, v in values.items()}
    if not all(math.isfinite(v) and v >= 0 for v in values.values()):
        raise VerdictError('nonphysical native forwarded-clock measurement')
    for edge in ('rise', 'fall'):
        if values['arrival_min_' + edge] > values['arrival_max_' + edge]:
            raise VerdictError('reversed native forwarded-clock early/late bounds')
    raw_driver = re.findall(r"^OT_FC_DRIVER_METRIC (\S+) (\S+)$", log, re.M)
    driver_values = dict(raw_driver)
    if len(raw_driver) != len(required) or set(driver_values) != set(required):
        raise VerdictError('missing physical driver-to-boundary provenance')
    driver_values = {k: float(v) for k, v in driver_values.items()}
    if not all(math.isfinite(v) and v >= 0 for v in driver_values.values()):
        raise VerdictError('nonphysical forwarded-clock driver measurement')
    return dict(corner=corner, input_pin='clk_in', output_pin='clk_out',
                driver_cell=driver[0][0], driver_instance=driver[0][1],
                direct_root_buffer=True, units='ps', clk_in_to_clk_out_ps=values,
                driver_y_ps=driver_values,
                output_net_delta_ps={k: values[k]-driver_values[k] for k in required},
                measured_at='physical clk_out STA terminal including output-net routed SPEF; propagated primary clock',
                odb_sha256=odb_sha256, spef_sha256=spef_sha256)


def liberty_pin_group(text, pin):
    matches = list(re.finditer(r'\bpin\s*\(\s*"?' + re.escape(pin) + r'"?\s*\)\s*\{', text))
    if len(matches) != 1:
        raise VerdictError(f'need one native {pin} Liberty group')
    start = matches[0].start()
    depth, quoted, escaped = 0, False, False
    for i in range(matches[0].end() - 1, len(text)):
        char = text[i]
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            depth += (char == '{') - (char == '}')
            if depth == 0:
                return start, i + 1
    raise VerdictError('unterminated native forwarded-clock Liberty group')


def merge_forwarded_clock_model(main, combinational):
    """Use the native clock-free characterization for the one combinational path.

    Main ETM registers/setup/hold remain byte-identical. OpenSTA's sequential
    extraction invents cross-polarity clock arcs; a clock-free second extraction
    naturally characterizes the actual buffer as clk_in -> clk_out instead.
    """
    a, b = liberty_pin_group(main, 'clk_out')
    x, y = liberty_pin_group(combinational, 'clk_out')
    group = combinational[x:y]
    related = re.findall(r'related_pin\s*:\s*"([^";]+)"', group)
    types = re.findall(r'timing_type\s*:\s*(\w+)\s*;', group)
    if related != ['clk_in'] or types != ['combinational']:
        raise VerdictError('native forwarding characterization is not one clk_in combinational arc')
    if not re.search(r'timing_sense\s*:\s*positive_unate\s*;', group):
        raise VerdictError('native forwarding characterization is not a noninverting buffer')
    for table in ('cell_rise', 'cell_fall', 'rise_transition', 'fall_transition'):
        if not re.search(r'\b' + table + r'\s*\(', group):
            raise VerdictError('native forwarding characterization is missing load tables')
    return main[:a] + group + main[b:]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def extra_vts(odb):
    data = Path(odb).read_bytes()
    out = []
    for t in ("L", "SL"):
        import re
        if re.search(rb"_ASAP7_75t_" + t.encode() + rb"(?![A-Za-z0-9_])", data):
            out.append(t)
    return out


class VerdictError(Exception):
    pass


def abstract_obs_layers(text):
    obs = {}
    for block in re.findall(r"(?ms)^\s*OBS\s*$\n(.*?)^\s*END\s*$", text):
        for layer in re.findall(r"\bLAYER\s+(M\d+)\s*;", block):
            obs[layer] = obs.get(layer, 0) + 1
    return obs


def audit_signal_abstract(text, signal_cap, pg_cap, routed):
    """Tie abstract metal above the signal ceiling to final-ODB PG evidence."""
    sig, pg = int(signal_cap[1:]), int(pg_cap[1:])
    if (routed.get("schema") != "opentallas.ref_tile.routed-signal-cap.v1"
            or routed.get("violations") != {} or routed.get("signal_cap") != signal_cap
            or routed.get("pg_cap") != pg_cap):
        raise VerdictError("final routed net-type audit is missing, inconsistent, or failed")
    for key, maximum in (("non_pg_layers", sig), ("pg_layers", pg)):
        if key not in routed or any(int(layer[1:]) > maximum for layer in routed[key]):
            raise VerdictError("routed layer counts exceed their net-type ceiling")
    obs = abstract_obs_layers(text)
    pins = set()
    for match in re.finditer(r"(?m)^\s*PIN\s+(\S+)\s*$", text):
        end = re.search(r"(?m)^\s*END\s+" + re.escape(match[1]) + r"\s*$", text[match.end():])
        if end is None:
            raise VerdictError("unterminated abstract pin")
        body = text[match.end():match.end() + end.start()]
        if not re.search(r"\bUSE\s+(?:POWER|GROUND)\s*;", body):
            pins.update(re.findall(r"\bLAYER\s+(M\d+)\s*;", body))
    if any(int(layer[1:]) > sig for layer in pins):
        raise VerdictError("abstract signal/clock pin exceeds signal_max_layer")
    high = {layer for layer in obs if int(layer[1:]) > sig}
    if any(int(layer[1:]) > pg for layer in obs):
        raise VerdictError("abstract OBS exceeds the PG ceiling")
    if not high <= {layer for layer, count in routed.get("pg_layers", {}).items() if count > 0}:
        raise VerdictError("abstract OBS above signal_max_layer lacks actual PG metal evidence")
    return dict(signal_cap=signal_cap, pg_cap=pg_cap, obs_layers=obs,
                signal_pin_layers=sorted(pins), pg_backed_high_obs_layers=sorted(high))


# EXACT-ABSTRACT FALLBACK (RLYH0-NE 2026-10-19): write_abstract_lef's default obstruction closing (bloat, merge,
# shrink) fills the gaps between nearby own shapes, so three min-width M4 via landings 0.3-0.5 um apart in the pin
# column of qfd_rlyh0_128_NE_65x30 became ONE 0.041-um-wide rect 0.024 um from two pins.  child_lint (i) (KV-ECTL5)
# then needs the wide-metal spacing 0.072 for those pins and FAILED the export of a CLOSED route
# (qfwd_rlyh0_128_ne_65x30-f1-fc2236d82, collect 4x rc=1 -> LOST_CLOSED); the real shapes are min-width, 0.024 legal.
# The SS pass also writes the exact-shape abstract (-bloat_factor 0); when the default one leaves a signal pin without
# DRC-clean access and the exact one does not, the exact one is published (same pins / outline, real geometry).
EXACT_LEF_SUFFIX = ".lef.exact"


# exact-shape abstracts of big tiles are huge (hbm_sfu_lg_pair_tap_leaf 216x216 um: 1.13 M RECTs, 47 MB): the finalize
# step (abstract_pin_stub.process) and the detector are pure python over all rects and did not finish in 13 min there.
# Above this many RECTs the exact LEF is NOT published or judged whole; only its shapes inside the pin windows are used.
EXACT_FULL_MAX_RECTS = 200000


def _aps():
    """the abstract_pin_stub module of this tree (tools/hier_contract), or None"""
    import importlib.util
    p = Path(__file__).resolve().parents[2] / "tools/hier_contract/abstract_pin_stub.py"
    try:
        if "def pin_spacing_violations" not in p.read_text(errors="replace"):
            return None
        spec = importlib.util.spec_from_file_location("ot_aps_view_export", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001
        return None


def exact_window_patch(text, exact_lines):
    """default abstract TEXT with its same-layer OBS replaced by the EXACT shapes inside every signal pin's wide-spacing
    window (TW3-LGTAP 2026-10-19).  Window = the pin rect widened by the layer's wide-metal spacing across the layer's
    preferred direction (M5 vertical: +-0.072 in x over the pin's y run; M4 horizontal: +-0.072 in y).  Inside a
    window the default OBS (closing-bloat merges, e.g. a 189-um M5 edge band over the top-face pin bases) is cut out
    and the real routed shapes of the exact abstract (EXACT_LINES: an iterable of its lines) are put back, clipped to
    the window; outside the windows the default abstract is unchanged.  Real metal is never dropped: every exact shape
    that meets a window stays as OBS (or becomes the pin's own stub in the finalize step).  -> (text, record)"""
    mod = _aps()
    U = mod.U
    iu = mod._iu
    norm = lambda r: (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]))
    head, obs = mod.split_lef(text)
    sig, _ = mod.pin_rects(head)
    BIN = 2 * U  # 2-um x bins
    wins = {}
    for rs in sig.values():
        for r in rs:
            lay = r[0]
            if lay not in mod.WIDE_SPACING_UM:
                continue
            w = iu(mod.WIDE_SPACING_UM[lay])
            a, b, c, e = norm(tuple(map(iu, r[1:])))
            win = (a - w, b, c + w, e) if int(lay[1:]) % 2 else (a, b - w, c, e + w)
            for k in range(win[0] // BIN, win[2] // BIN + 1):
                wins.setdefault((lay, k), []).append(win)

    def hits(lay, r):
        out = set()
        for k in range(r[0] // BIN, r[2] // BIN + 1):
            out.update(x for x in wins.get((lay, k), ()) if mod._ov(r, x))
        return sorted(out)

    rect_re = re.compile(r"\s*" + mod._RECT)
    lay_re = re.compile(r"\s*LAYER (\S+)")
    out, cur, cut = [], None, 0
    for line in obs.split("\n"):
        m = lay_re.match(line)
        if m:
            cur = m.group(1); out.append(line); continue
        m = rect_re.match(line)
        if m and cur:
            r = norm(tuple(map(iu, map(float, m.groups()))))
            hs = hits(cur, r)
            if hs:
                cut += 1
                ind = re.match(r"\s*", line).group()
                out += [f"{ind}RECT  {mod._um(a)} {mod._um(b)} {mod._um(c)} {mod._um(e)} ;"
                        for a, b, c, e in mod.rect_minus(r, hs)]
                continue
        out.append(line)
    add, in_obs, cur = {}, False, None
    for line in exact_lines:
        s = line.strip()
        if not in_obs:
            in_obs = s == "OBS"
            continue
        if s.startswith("END"):
            break
        m = lay_re.match(line)
        if m:
            cur = m.group(1); continue
        m = rect_re.match(line)
        if m and cur in mod.WIDE_SPACING_UM:
            r = norm(tuple(map(iu, map(float, m.groups()))))
            for x in hits(cur, r):
                add.setdefault(cur, set()).add((max(r[0], x[0]), max(r[1], x[1]), min(r[2], x[2]), min(r[3], x[3])))
    obs = "\n".join(out)
    k = obs.rstrip().rfind("\n  END")
    assert k > 0, "no OBS END in the default abstract"
    blk = "".join(f"\n    LAYER {lay} ;" + "".join(f"\n      RECT  {mod._um(a)} {mod._um(b)} {mod._um(c)} {mod._um(e)} ;"
                                                for a, b, c, e in sorted(rs)) for lay, rs in sorted(add.items()))
    obs = obs[:k] + blk + obs[k:]
    return head + obs, dict(windows=len({w for v in wins.values() for w in v}), default_rects_cut=cut,
                            exact_rects_added=sum(map(len, add.values())))


def pin_access_violations(text):
    """abstract_pin_stub.pin_spacing_violations (the child_lint (i) detector) on a LEF text, raw AND as published (after
    the finalize step abstract_pin_stub.process: stub move + 1b band carve + pocket closing), or None when the detector
    is not next to this copy (tools/hier_contract of the same tree); a pin counts once if either the raw or the
    processed text blocks it.
    TW3-LGTAP 2026-10-19 (hbm_sfu_lg_pair_tap_leaf_rt24_1019-b1-72af5d8b1 LOST_CLOSED): the raw default abstract had 0
    violations (its 189-um M5 edge band OVERLAPS the top-face pins, which the detector does not count), but the 1b band
    carve left 0.036-um slivers between the pins, 0.048 from the next pin -> child_lint (i) FAIL on the published LEF and
    the exact-shape fallback never ran.  Judging the processed text runs the fallback whenever the published LEF fails."""
    try:
        mod = _aps()
        if mod is None:
            return None
        bad = mod.pin_spacing_violations(text)
        if hasattr(mod, "process") and re.search(r"\n[ \t]*OBS[ \t]*(?=\n)", text):
            seen = {(b[0], b[1]) for b in bad}   # raw OR published: either one failing is a blocked pin
            bad += [b for b in mod.pin_spacing_violations(mod.process(text)[0]) if (b[0], b[1]) not in seen]
        return bad
    except Exception:  # noqa: BLE001 - no detector: keep the default abstract
        return None


def choose_abstract(out, name, base, image, mounts=()):
    """publish the exact-shape abstract instead of the default one when only the default one blocks pin access (the
    exact one is written by an extra session only then); returns the decision record (always removes the side file)"""
    lef, exact = out / f"{name}.lef", out / f"{name}{EXACT_LEF_SUFFIX}"
    if not lef.is_file():
        return dict(mode="default", why="no abstract written")
    bad = pin_access_violations(lef.read_text(errors="replace"))
    rec = dict(mode="default", default_pin_access_violations=None if bad is None else len(bad))
    if not bad:
        return rec
    tcl = out / "export_exact_abstract.tcl"
    tcl.write_text(f"read_db /base/6_final.odb\nwrite_abstract_lef -bloat_factor 0 /out/{exact.name}\nexit\n")
    cmd = ["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{out}:/out", *mounts, image,
           "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit", f"/out/{tcl.name}"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    (out / "export_exact_abstract.log").write_text(p.stdout + p.stderr)
    rec.update(exact_returncode=p.returncode, exact_command=cmd)
    try:
        if p.returncode == 0 and exact.is_file():
            with exact.open(errors="replace") as f:
                n_rects = sum(1 for l in f if "RECT" in l)
            rec["exact_rects"] = n_rects
            bad_x = pin_access_violations(exact.read_text(errors="replace")) if n_rects <= EXACT_FULL_MAX_RECTS else None
            rec["exact_pin_access_violations"] = None if bad_x is None else len(bad_x)
            if bad_x is None or len(bad_x) >= len(bad):
                # TW3-LGTAP: exact geometry only inside the pin windows, default abstract elsewhere
                with exact.open(errors="replace") as f:
                    win_text, wrec = exact_window_patch(lef.read_text(errors="replace"), f)
                bad_w = pin_access_violations(win_text)
                rec.update(window_patch=wrec, window_pin_access_violations=None if bad_w is None else len(bad_w))
                if bad_w is not None and len(bad_w) < len(bad):
                    default_sha = sha(lef)
                    tmp = out / f".{name}.lef.windows"
                    tmp.write_text(win_text)
                    tmp.replace(lef)  # rename, not an in-place write: the container leaves the LEF root-owned
                    rec.update(mode="exact_windows", default_sha256=default_sha, exact_sha256=sha(exact),
                               why=f"default (closing-bloat) abstract leaves {len(bad)} signal pins without DRC-clean "
                                   f"access (e.g. {', '.join(f'{b[0]} {b[1]} {b[2]:g}' for b in bad[:4])}); exact shapes "
                                   f"in {wrec['windows']} pin windows leave {len(bad_w)}")
            elif len(bad_x) < len(bad):
                rec.update(mode="exact", default_sha256=sha(lef), exact_sha256=sha(exact),
                           why=f"default (closing-bloat) abstract leaves {len(bad)} signal pins without DRC-clean "
                               f"access (e.g. {', '.join(f'{b[0]} {b[1]} {b[2]:g}' for b in bad[:4])}); exact-shape "
                               f"abstract leaves {len(bad_x)}")
                exact.replace(lef)
    finally:
        exact.unlink(missing_ok=True)
    return rec


PF_ENV_RE = re.compile(r"set ::env\(OT_PF_MACRO_LIBS\) \[list ([^\]]*)\]\s*$")


def verdict_section(tcl_text):
    """the constraint section of a verdict STA Tcl (corner_sta.py / meas_resta.py form): every line from read_db up to
    the first report (puts "OT_CORNER ..."), without meas_resta's register census"""
    lines = tcl_text.splitlines()
    a = next((i for i, l in enumerate(lines) if l.startswith("read_db ")), None)
    b = next((i for i, l in enumerate(lines) if l.startswith('puts "OT_CORNER')), None)
    if a is None or b is None or b <= a:
        raise VerdictError("verdict Tcl has no read_db ... OT_CORNER section")
    sec = [l for l in lines[a:b] if l.strip() and "OT_REGS" not in l]
    # PF-HARDCHILD-EXPORT (S81-CAPC2 2026-10-19): the verdict session sets OT_PF_MACRO_LIBS (corner_sta.py /
    # meas_resta.with_pf_macro_libs) just BEFORE read_db; the sign-off SDC's PINFLOP reference (pinflop_ref.tcl) reads
    # the hard-child ETM insertion from it.  Without it the export session referenced the raw child clock pin and
    # could never reproduce the verdict (s81sl_capc d8836674d: export FF -158.19 / TT -27.41 vs verdict +18.21 / +198.74).
    sec = [l for l in lines[:a] if PF_ENV_RE.match(l)] + sec
    if not any(l.startswith("read_sdc ") for l in sec) or not any(l.startswith("read_spef ") for l in sec):
        raise VerdictError("verdict Tcl section reads no SDC / SPEF")
    return sec


def export_corner_sequence(sequence, corner):
    """Replay constraints with ownership metadata matching the linked Liberty."""
    if corner not in ("ss", "tt", "ff"):
        raise VerdictError("unsupported export corner")
    out = []
    seen = False
    for line in sequence:
        m = PF_ENV_RE.match(line)
        if m:
            # the verdict's setup section carries the TT ETMs, its hold section the FF ones: name this corner's
            line = pf_env_line([re.sub(r"_(ss|tt|ff)(\.lib(?:\.gz)?)$", rf"_{corner}\2", f) for f in m.group(1).split()])
        if line.startswith("set ::ot_ce_corner "):
            if not re.fullmatch(r"set ::ot_ce_corner (?:ss|tt|ff|\{(?:ss|tt|ff)\})", line):
                raise VerdictError("unrecognized explicit clock-entry corner selector")
            line = f"set ::ot_ce_corner {corner}"
            seen = True
        out.append(line)
    if not seen:
        at = next((i + 1 for i, line in enumerate(out) if line.startswith("read_db ")), 0)
        out.insert(at, f"set ::ot_ce_corner {corner}")
    return out


def section_files(sec):
    """[(command, container path)] of the files a section reads (incl. the OT_PF_MACRO_LIBS hard-child ETMs)"""
    out = [tuple(l.split()[:2]) for l in sec if re.match(r"(read_db|read_sdc|read_spef|source) /", l)]
    for l in sec:
        m = PF_ENV_RE.match(l)
        if m:
            out += [("pf_macro_lib", f) for f in m.group(1).split()]
    return out


def pf_env_line(libs):
    """the OT_PF_MACRO_LIBS line pinflop_ref.tcl reads hard-child ETM clock insertion from"""
    return f"set ::env(OT_PF_MACRO_LIBS) [list {' '.join(libs)}]"


def find_verdict(orfs, explicit=None):
    """the closure loop's routed-insertion verdict of the route at ORFS: newest <RUN>/cl/routed_ioref.a*.json"""
    if explicit is not None:
        if not Path(explicit).is_file():
            raise VerdictError(f"--verdict-json {explicit}: no such file")
        return Path(explicit).resolve()
    if len(orfs.parents) < 4:
        return None
    cl = orfs.parents[3] / "cl"                    # <RUN>/routes/<LABEL>/work/orfs
    if orfs.parents[2].name != "routes" or not cl.is_dir():
        return None
    c = sorted(cl.glob("routed_ioref.a*.json"), key=lambda p: p.stat().st_mtime)
    return c[-1].resolve() if c else None


def load_verdict(vj, orfs, base):
    """-> dict(json, meas, src, work, sec{ss,ff}, expect{tt,ff}, files) for a verdict timed on exactly BASE's odb+spef"""
    res = json.loads(vj.read_text())
    meas = vj.parent / (vj.stem + "_meas")
    exp = {}
    for corner, key in (("tt", "setup_tt"), ("ff", "hold_ff")):
        r = res.get(key) or {}
        if r.get("worst_slack_ps") is None or r.get("errors") or r.get("error") or r.get("rc") not in (0, None):
            raise VerdictError(f"{vj}: {key} is not a clean verdict ({json.dumps(r)[:200]})")
        exp[corner] = float(r["worst_slack_ps"])
    sec = {}
    for c in ("ss", "ff"):
        f = meas / f"meas_{c}.tcl"
        if not f.is_file():
            raise VerdictError(f"{f}: verdict Tcl missing")
        sec[c] = verdict_section(f.read_text())
    src = vj.parent.parent / "src"
    used = {p for s in sec.values() for _, p in section_files(s)}
    bad = sorted(p for p in used if not p.startswith(("/work/", "/src/", "/meas/")))
    if bad:
        raise VerdictError(f"verdict Tcl reads outside /work /src /meas: {bad}")
    # the ORFS dir the verdict was timed in: recorded by meas_resta (orfs), else the installed hold-ECO dir, else the
    # route's own; only one whose 6_final odb + spef ARE the exported ones qualifies
    cands = ([Path(res["orfs"])] if res.get("orfs") else []) + [vj.parent / "eco" / "orfs", orfs]
    want = {n: sha(base / n) for n in ("6_final.odb", "6_final.spef")}
    why = []
    for w in dict.fromkeys(c.resolve() for c in cands if c.is_dir()):
        roots = {"/work/": w, "/src/": src, "/meas/": meas}
        host = {p: next(r / p[len(k):] for k, r in roots.items() if p.startswith(k)) for p in used}
        miss = [p for p, h in host.items() if not h.is_file()]
        if miss:
            why.append(f"{w}: missing {miss[:3]}")
            continue
        stale = [p for p, h in host.items() if h.name in want and sha(h) != want[h.name]]
        if stale or not all(any(h.name == n for h in host.values()) for n in want):
            why.append(f"{w}: verdict timed another {' / '.join(Path(p).name for p in stale) or 'db'}")
            continue
        return dict(json=vj, meas=meas, src=src, work=w, sec=sec, expect=exp,
                    files={p: dict(host=str(h), sha256=sha(h)) for p, h in sorted(host.items())})
    raise VerdictError(f"{vj}: the verdict is not of the ODB / SPEF being exported (stale verdict) -- " + "; ".join(why))


def corner_sta_sections(orfs):
    """no routed_ioref verdict (spec opt-out / unavailable): the route's own corner_sta Tcl (w18_sta_{ss,ff}.tcl, /work =
    the ORFS dir, /src = <RUN>/src) IS the sign-off sequence.  None unless every file it reads is there (then legacy)."""
    try:
        sec = {c: verdict_section((orfs / f"w18_sta_{c}.tcl").read_text()) for c in ("ss", "ff")}
    except (OSError, VerdictError):
        return None
    src = orfs.parents[3] / "src"
    host = {}
    for p in {p for s in sec.values() for _, p in section_files(s)}:
        h = orfs / p[6:] if p.startswith("/work/") else src / p[5:] if p.startswith("/src/") else None
        if h is None or not h.is_file():
            return None
        host[p] = dict(host=str(h), sha256=sha(h))
    return dict(sec=sec, src=src, work=orfs, files=dict(sorted(host.items())))


def load_job(jobj, src, cl, rel, extra_sdc=None):
    """JOB REPLAY: -> dict(seq{ss,ff}, expect{tt,ff}, files, basis) rebuilt from a closure-loop job record"""
    j = json.loads(jobj.read_text())
    m = j.get("metrics") or {}
    if "post_sdc" not in m or "sdc_name" not in m:
        raise VerdictError(f"{jobj}: metrics carry no sdc_name / post_sdc (not a corner_sta sign-off record)")
    if cl is None:
        cl = next((d for d in (jobj.parent / "run" / "cl", jobj.parent) if d.is_dir()
                   and (list(d.glob("routed_ioref.a*.json")) or d.name == "cl")), jobj.parent)
    exp, basis, ins, rpl, app = {}, "job metrics", [], {}, []
    for vj in sorted(cl.glob("routed_ioref.a*.json"), key=lambda p: p.name, reverse=True):
        r = json.loads(vj.read_text())
        ok = all((r.get(k) or {}).get("worst_slack_ps") is not None and not (r.get(k) or {}).get("errors")
                 and not (r.get(k) or {}).get("error") for k in ("setup_tt", "hold_ff"))
        if ok:
            exp = dict(tt=float(r["setup_tt"]["worst_slack_ps"]), ff=float(r["hold_ff"]["worst_slack_ps"]))
            ins, rpl, app = r.get("inserted") or [], r.get("replaced") or {}, r.get("appended") or []
            basis = vj.name
        break                                  # the NEWEST attempt decides (an unclean one = corner_sta metrics stand)
    if not exp:
        tt = m.get("tt_ps", m.get("ss_ps") if str(m.get("setup_corner", "")).lower() == "tt" else None)
        if tt is None or m.get("ff_ps") is None:
            raise VerdictError(f"{jobj}: no TT setup / FF hold verdict in metrics")
        exp = dict(tt=float(tt), ff=float(m["ff_ps"]))
    files = {}

    def need(cont, host):
        if not host.is_file():
            raise VerdictError(f"job replay: {cont} -> {host} missing (pass --src = the job commit tree + flow overlay)")
        files[cont] = dict(host=str(host), sha256=sha(host))
        return f"read_sdc {cont}"
    seq = {}
    for c in ("ss", "ff"):
        s = [f"read_db /in/{rel}/6_final.odb", f"read_sdc /in/{rel}/{m['sdc_name']}",
             f"read_spef /in/{rel}/6_final.spef", "set_propagated_clock [all_clocks]"]
        # Legacy corner_sta wrappers recorded their literal extra SDC separately
        # from metrics.post_sdc. Replay that original file before the post-SDCs.
        if extra_sdc is not None:
            s.append(need("/job_extra.sdc", extra_sdc))
        s += [need(f"/cl/{Path(f).name}", cl / Path(f).name) for f in ins]
        s += ["set_propagated_clock [all_clocks]"] if ins else []
        for p in list(m["post_sdc"]) + (list(m.get("setup_post_sdc") or []) if c == "ss" else []):
            s.append(need(f"/cl/{Path(rpl[p]).name}", cl / Path(rpl[p]).name) if p in rpl else need(f"/src/{p}", src / p))
        s += [need(f"/cl/{Path(f).name}", cl / Path(f).name) for f in app]
        seq[c] = s
    return dict(seq=seq, expect=exp, files=files, basis=basis, cl=cl, job=j.get("name"),
                commit=(j.get("spec") or {}).get("source", {}).get("commit"), overlay=(j.get("flow_overlay") or {}).get("commit"))


def ws_ps(line):
    m = re.match(r"OT_WS max (\S+) min (\S+)", line or "")
    return (float(m.group(1)) * 1e12, float(m.group(2)) * 1e12) if m else (None, None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--interface-sdc", type=Path)
    ap.add_argument("--macro-view", action="append", default=[], type=Path)
    ap.add_argument("--corners", default="ss,ff,tt")
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--tmp-dir", type=Path)
    ap.add_argument("--verdict-json", type=Path, help="routed_ioref verdict json to replay (default: the run's newest)")
    ap.add_argument("--no-verdict", action="store_true", help="never replay a verdict (interface extraction)")
    ap.add_argument("--sdc-name", default="6_final.sdc", help="routed SDC under the base dir (--post-sdc sequence)")
    ap.add_argument("--post-sdc", action="append", default=[], type=Path,
                    help="read after the routed SDC, SPEF and set_propagated_clock, in order (corner_sta.py's order)")
    ap.add_argument("--verdict-tol", type=float, default=0.05, help="ps; export session slack vs the verdict")
    ap.add_argument("--job-json", type=Path, help="closure-loop job record to rebuild the sign-off sequence from (2b)")
    ap.add_argument("--job-extra-sdc", type=Path,
                    help="original corner_sta.json extra_sdc saved as a file; replay before the job's post-SDCs")
    ap.add_argument("--src", type=Path, help="job commit tree (+ flow overlay) holding the job's post-SDCs (/src)")
    ap.add_argument("--cl-dir", type=Path, help="the run's cl/ dir (routed_ioref json + appended SDCs); default by --job-json")
    ap.add_argument("--expect-tt", type=float, help="ps; sign-off TT setup slack the export session must reproduce")
    ap.add_argument("--expect-ff", type=float, help="ps; sign-off FF hold slack the export session must reproduce")
    ap.add_argument("--require-check", action="store_true", help="an export with no verdict to check against fails (5)")
    ap.add_argument("--pin-only-tech", action="store_true", help="snapshot exact read-tech LEF for M6 contact-via audit")
    ap.add_argument("--signal-max-layer", help="optional stricter signal/clock ceiling, independent of PG")
    ap.add_argument("--pg-max-layer", help="PG ceiling for the final routed net-type audit")
    ap.add_argument("--signal-audit-tcl", type=Path, help="source-pinned actual OpenDB net-type audit helper")
    a = ap.parse_args()
    strict = a.signal_max_layer is not None
    if strict:
        if (not re.fullmatch(r"M[2-9]", a.signal_max_layer)
                or not re.fullmatch(r"M[2-9]", a.pg_max_layer or "")
                or int(a.signal_max_layer[1:]) > int(a.pg_max_layer[1:])
                or a.signal_audit_tcl is None or not a.signal_audit_tcl.is_file()):
            ap.error("signal audit requires valid signal<=PG ceilings and an existing --signal-audit-tcl")
        for view in a.macro_view:
            text = (view / f"{view.name}.lef").read_text()
            if any(int(layer[1:]) > int(a.signal_max_layer[1:]) for layer in abstract_obs_layers(text)):
                ap.error("stricter signal cap cannot qualify hard-macro OBS above it without net-type evidence")
    elif a.pg_max_layer is not None or a.signal_audit_tcl is not None:
        ap.error("PG/audit helper options require --signal-max-layer")
    orfs, out = a.orfs_dir.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = base.relative_to(orfs)
    mounts = []
    if a.tmp_dir is not None:
        a.tmp_dir.mkdir(parents=True, exist_ok=True)
        mounts += ["-v", f"{a.tmp_dir.resolve()}:/tmp", "-e", "TMPDIR=/tmp"]
    recp = out / "abstract.json"
    rec = json.loads(recp.read_text()) if recp.exists() else dict(name=a.name, orfs_dir=str(orfs), corners={})
    rec.setdefault("corners", {})
    if a.interface_sdc is not None:
        isdc = a.interface_sdc.resolve()
        mounts += ["-v", f"{isdc}:/interface.sdc:ro"]
        rec["interface_sdc"] = dict(path=str(isdc), sha256=sha(isdc),
                                    purpose="interface timing extraction, not a new leaf signoff verdict")
    vd = jb = None
    for k in ("verdict", "sdc_sequence", "checked"):
        rec.pop(k, None)
    try:
        if a.job_json is not None:
            if a.src is None:
                raise VerdictError("--job-json needs --src")
            jb = load_job(a.job_json.resolve(), a.src.resolve(), a.cl_dir.resolve() if a.cl_dir else None, rel,
                          a.job_extra_sdc.resolve() if a.job_extra_sdc is not None else None)
        vj = None if (a.no_verdict or jb is not None) else find_verdict(orfs, a.verdict_json)
        if vj is not None:
            vd = load_verdict(vj, orfs, base)
    except (VerdictError, OSError, ValueError) as ex:
        # a route WITH a verdict whose sequence cannot be reproduced exports nothing: a view at other constraints
        # than the sign-off is the bug this guards (never fall back silently)
        rec.update(ok=False, verdict=dict(error=str(ex)))
        recp.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"VIEW_EXPORT FAIL verdict sequence: {ex}")
        raise SystemExit(4)
    cs = None
    expect = dict(vd["expect"]) if vd is not None else dict(jb["expect"]) if jb is not None else {}
    for c, v in (("tt", a.expect_tt), ("ff", a.expect_ff)):
        if v is not None:
            expect[c] = v
    if jb is not None:
        mounts += ["-v", f"{a.src.resolve()}:/src:ro", "-v", f"{jb['cl']}:/cl:ro"]
        if a.job_extra_sdc is not None:
            mounts += ["-v", f"{a.job_extra_sdc.resolve()}:/job_extra.sdc:ro"]
        rec["verdict"] = dict(json=None, job_json=str(a.job_json.resolve()), job=jb["job"], commit=jb["commit"],
                              overlay=jb["overlay"], basis=jb["basis"], expect_ps=jb["expect"], tol_ps=a.verdict_tol,
                              files=jb["files"], check={})
    if vd is None and jb is None and not a.no_verdict and len(orfs.parents) > 3 and (orfs.parents[3] / "cl").is_dir():
        cs = corner_sta_sections(orfs)
        if cs is not None:
            mounts += ["-v", f"{cs['work']}:/work:ro", "-v", f"{cs['src']}:/src:ro"]
            rec["verdict"] = dict(json=None, corner_sta_tcl=True, files=cs["files"],
                                  note="no routed_ioref verdict: the route's corner_sta sequence, unchecked")
    if vd is not None:
        mounts += ["-v", f"{vd['work']}:/work:ro", "-v", f"{vd['src']}:/src:ro", "-v", f"{vd['meas']}:/meas:ro"]
        rec["verdict"] = dict(json=str(vd["json"]), sha256=sha(vd["json"]), expect_ps=vd["expect"], tol_ps=a.verdict_tol,
                              work=str(vd["work"]), files=vd["files"], check={})
        if a.interface_sdc is not None:
            rec["interface_sdc"]["in_verdict_sequence"] = rec["interface_sdc"]["sha256"] in \
                {f["sha256"] for f in vd["files"].values()}
    elif a.post_sdc and jb is None:
        for i, f in enumerate(a.post_sdc):
            mounts += ["-v", f"{f.resolve()}:/post{i}.sdc:ro"]
    rec.pop('forwarded_clock', None)
    rec.pop('forwarded_clock_errors', None)
    (out / 'forwarded_clock.json').unlink(missing_ok=True)
    rec["sdc_sequence"] = {}
    mv = []
    for i, d in enumerate(a.macro_view):
        d = d.resolve()
        mounts += ["-v", f"{d}:/mv{i}:ro"]
        mv.append((i, d.name))
    rec["macro_views"] = [str(d) for d in a.macro_view]
    vts = extra_vts(base / "6_final.odb")
    if vts:
        rec["vt_flavours_added"] = vts
    for c in a.corners.split(","):
        C = c.upper()
        libs = [f"read_liberty {PLAT}/lib/NLDM/{x.format(C=C)}" for x in CELLS]
        libs += [f"read_liberty {PLAT}/lib/NLDM/{x.format(C=C).replace('_RVT_', '_' + VT[v][0] + '_')}"
                 for v in vts for x in CELLS]
        libs += [f"read_liberty /mv{i}/{n}_{c}.lib" for i, n in mv]
        lefs = [f"read_lef {PLAT}/lef/asap7sc7p5t_28_{VT[v][1]}_1x_220121a.lef" for v in vts]
        lefs += [f"read_lef /mv{i}/{n}.lef" for i, n in mv]
        if vd is not None:
            # Verdict constraints: SS/TT use setup, FF uses hold; only corner ownership metadata is retagged.
            seq, mode = list(vd["sec"]["ff" if c == "ff" else "ss"]), "verdict"
        elif jb is not None:
            seq, mode = list(jb["seq"]["ff" if c == "ff" else "ss"]), "job_replay"
        elif cs is not None:
            seq, mode = list(cs["sec"]["ff" if c == "ff" else "ss"]), "corner_sta_tcl"
        elif a.post_sdc:
            seq, mode = [f"read_db /in/{rel}/6_final.odb", f"read_sdc /in/{rel}/{a.sdc_name}",
                         f"read_spef /in/{rel}/6_final.spef", "set_propagated_clock [all_clocks]",
                         *(f"read_sdc /post{i}.sdc" for i in range(len(a.post_sdc)))], "post_sdc"
        else:
            sdc = "/interface.sdc" if a.interface_sdc is not None else f"/in/{rel}/6_final.sdc"
            # Interface SDC derives its clock reference immediately; routed parasitics
            # must be loaded before it evaluates clock arrivals.
            seq, mode = [f"read_db /in/{rel}/6_final.odb", f"read_spef /in/{rel}/6_final.spef", f"read_sdc {sdc}",
                         "set_propagated_clock [all_clocks]"], "legacy"
        if mv and not any(PF_ENV_RE.match(l) for l in seq):
            # no verdict line (job replay / post_sdc / legacy): the PINFLOP reference must still see the hard
            # children's ETM insertion, as the route (ADDITIONAL_LIBS) and the verdict did -- this session's own ETMs
            at = next((i for i, l in enumerate(seq) if l.startswith("read_db ")), 0)
            seq.insert(at, pf_env_line([f"/mv{i}/{n}_{c}.lib" for i, n in mv]))
        seq = export_corner_sequence(seq, c)
        rec["sdc_sequence"][c] = dict(mode=mode, tcl=seq)
        audit = []
        if strict:
            audit = [a.signal_audit_tcl.read_text(),
                     f"ot_ref_audit_signal_layers {a.signal_max_layer} {a.pg_max_layer} /out/signal_layer_audit_{c}.json"]
        tcl = "\n".join([f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef",
                         f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef", *lefs, *libs, *seq, *audit,
                         "puts \"OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]\"",
                         FORWARDED_CLOCK_TCL,
                         f"write_timing_model -library_name {a.name}_{c} /out/{a.name}_{c}.lib",
                         f"write_abstract_lef /out/{a.name}.lef" if c == "ss" else "",
                         f"file copy -force {PLAT}/lef/asap7_tech_1x_201209.lef /out/pin_only_tech.lef"
                         if c == "ss" and a.pin_only_tech else "",
                         'if {[info exists ot_fc_root]} {', 'delete_clock [all_clocks]',
                         f'write_timing_model -library_name {a.name}_{c}_forwarded /out/forwarded_{c}.lib.raw', '}',
                         "puts \"OT_EXPORT_DONE\"", "exit", ""])
        (out / f"export_{c}.tcl").write_text(tcl)
        if strict:
            (out / f"signal_layer_audit_{c}.json").unlink(missing_ok=True)
        cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/in:ro", "-v", f"{out}:/out", *mounts, a.image,
               "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit", f"/out/export_{c}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (out / f"export_{c}.log").write_text(log)
        ws = [l for l in log.splitlines() if l.startswith("OT_WS")]
        done = "OT_EXPORT_DONE" in log
        if c in expect:
            # the exported session IS the verdict session: TT setup / FF hold must reproduce the verdict's numbers
            got = ws_ps(ws[-1] if ws else None)[0 if c == "tt" else 1]
            want = expect[c]
            ok = got is not None and abs(got - want) <= a.verdict_tol + 0.005     # the verdict json is rounded to 0.01
            rec.setdefault("verdict", dict(json=None, expect_ps=expect, tol_ps=a.verdict_tol,
                                           basis="--expect-tt / --expect-ff")).setdefault("check", {})[c] = \
                dict(export_ps=got, verdict_ps=want, ok=ok)
            if not ok:
                print(f"VIEW_EXPORT FAIL {c}: export session {got} ps vs verdict {want} ps (tol {a.verdict_tol})")
            done = done and ok
        try:
            fc = forwarded_clock_receipt(log, c,
                sha(base / '6_final.odb') if 'OT_FC_DRIVER ' in log else '',
                sha(base / '6_final.spef') if 'OT_FC_DRIVER ' in log else '')
            if fc is not None:
                main_lib = out / f'{a.name}_{c}.lib'
                comb_lib = out / f'forwarded_{c}.lib.raw'
                fc['native_combinational_lib_sha256'] = sha(comb_lib)
                fc['sequential_etm_before_merge_sha256'] = sha(main_lib)
                merged = merge_forwarded_clock_model(main_lib.read_text(), comb_lib.read_text())
                # Docker writes the native ETM as root; replace through our output
                # directory, rather than trying to truncate its root-owned file.
                with tempfile.NamedTemporaryFile(mode='w', dir=out, delete=False) as tmp:
                    tmp.write(merged)
                Path(tmp.name).chmod(0o644)
                Path(tmp.name).replace(main_lib)
                fc['exported_etm_sha256'] = sha(main_lib)
                fc['extraction_tcl_sha256'] = sha(out / f'export_{c}.tcl')
                rec.setdefault('forwarded_clock', {})[c] = fc
        except (OSError, ValueError, VerdictError) as exc:
            rec.setdefault('forwarded_clock_errors', {})[c] = str(exc)
            done = False
        rec["corners"][c] = dict(returncode=p.returncode, done=done, ws=ws[-1] if ws else None,
                                 image=a.image, command=cmd)
    if rec.get('forwarded_clock'):
        (out / 'forwarded_clock.json').write_text(json.dumps(dict(
            schema='opentallas.forwarded_clock.routed.v1', corners=rec['forwarded_clock'],
            scope='clock arc only; actual communicating-pair setup/hold remains a die check'), indent=2) + '\n')
    rec["abstract"] = choose_abstract(out, a.name, base, a.image) if "ss" in a.corners.split(",") else \
        dict(mode="default", why="no SS pass: abstract not written by this export")
    if rec["abstract"]["mode"] in ("exact", "exact_windows"):
        print(f"VIEW_EXPORT exact-shape abstract published: {rec['abstract']['why']}")
    rec["files"] = {f.name: sha(f) for f in sorted(out.iterdir()) if f.suffix in (".lef", ".lib")}
    want = [f"{a.name}.lef"] + [f"{a.name}_{c}.lib" for c in ("ss", "ff", "tt")]
    rec["ok"] = all(v.get("done") for v in rec["corners"].values()) and all(w in rec["files"] for w in want)
    # CHECKED = the TT setup and FF hold of this export session were both compared with a sign-off verdict
    chk = (rec.get("verdict") or {}).get("check") or {}
    rec["checked"] = all(chk.get(c, {}).get("ok") for c in ("tt", "ff"))
    if strict:
        proof = dict(helper_sha256=sha(a.signal_audit_tcl), corners={})
        try:
            text = (out / f"{a.name}.lef").read_text()
            for c in a.corners.split(","):
                path = out / f"signal_layer_audit_{c}.json"
                report = json.loads(path.read_text())
                proof["corners"][c] = dict(path=str(path), sha256=sha(path),
                    abstract=audit_signal_abstract(text, a.signal_max_layer, a.pg_max_layer, report))
        except (OSError, ValueError, VerdictError) as exc:
            proof["error"] = str(exc)
            for c in a.corners.split(","):
                rec["corners"][c]["done"] = False
        rec["signal_layer_audit"] = proof
        rec["ok"] = rec["ok"] and "error" not in proof
    unchecked = [c for c in a.corners.split(",") if c in ("tt", "ff") and c not in chk]
    if unchecked:
        print(f"VIEW_EXPORT UNCHECKED {','.join(unchecked)}: no sign-off verdict to compare this session with "
              "(pass --job-json/--src, --verdict-json or --expect-tt/--expect-ff)")
    recp.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({k: rec[k] for k in ("name", "ok", "checked", "files")}))
    if not all(rec["corners"][c]["done"] for c in a.corners.split(",")):
        raise SystemExit(1)
    raise SystemExit(5 if unchecked and a.require_check else 0)


if __name__ == "__main__":
    main()
