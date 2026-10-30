#!/usr/bin/env python3
"""Uniform sign-off of a closed block (lane SIGNOFF, 2026-10-24): one recipe applied to every block before it is
called closed.  Past "closed" records came from many lanes and flows: some were not die-bindable (pin-flop spread
> 80 ps), kit SDCs before main 4b7b2b3e64 waived the sender seam hold (no set_output_delay -min), and 27 of 43 tiles
once "closed" were unassemblable (docs/LESSONS_ARCH_PHYSICAL_1012.md).  This tool re-signs a block from its ROUTED
data only, with the same checks for everyone.

    signoff.py run (--run-dir ORFS_RUN | --base RESULTS_BASE) [--kit KITDIR] [--sdc SDC] [--name N] --out DIR
                   [--corners ss,ff,tt] [--image IMG] [--insertion-target PS] [--record gate_result.json]
    signoff.py verdict DIR/signoff.json           # re-evaluate a record (exit 0 SIGNED, 1 NOT SIGNED)

INPUTS: the routed ODB (<base>/6_final.odb, else <base>/5_route.odb of a GOAL=route kit) and its SPEF
(<base>/6_final.spef with 6_final.odb; when absent the parasitics are
re-extracted with OpenRCX: extract_parasitics -ext_model_file asap7 rcx_patterns.rules, recorded as 'rcx').  The
golden SDC is the kit's constraint.sdc (KIT = parent of the ORFS run dir) unless --sdc; else <base>/6_final.sdc.
Macro / hard-child liberty files come from the kit config.mk ADDITIONAL_LIBS (/work = KIT), per corner (_ss/_ff/_tt).

ENGINE: OpenSTA as built into OpenROAD in the pinned ORFS image (openroad/orfs:latest = :asap7lock), one process per
corner (MCMM = TT + FF (+ SS for information with --corners tt,ff,ss) x 1 functional mode, run in parallel), ASAP7 NLDM
RVT+LVT+SLVT liberty of that corner.

CORNER RULE (owner, restated 2026-10-24, AGENTS.md c7ce2ed69a; supersedes the 2026-09-30 SS rule): timing closes at the
TYPICAL corner -- setup at TT, hold at FF, 60 / 25 ps uncertainty, related flop-pair skew with CPPR <= 80 ps (spread is INFO).  SS never gates; with
--corners ...,ss it is reported for information only.

CHECKS (each PASS / FAIL / NOT RUN; SIGNED only if every blocking check PASSes):
  setup_tt      TT setup WNS >= 0 with the SDC's 60 ps setup uncertainty (AGENTS.md 2026-10-24)        blocking
  hold_ff       FF hold WNS >= 0 under the STANDARD boundary-hold overlay                                  blocking
                (set_output_delay -min 0 and set_input_delay -min -insertion_tol (40 ps) on every data port vs the
                IO virtual clock: the 4b7b2b3e64 kit standard; the raw-SDC hold is reported as hold_ff_sdc)
  ss            SS setup / hold, only with --corners ...,ss: information, never a reason                 report
  uncertainty   the SDC carries 60 ps setup / 25 ps hold (sdc_lint 'uncertainty'), period = 833 ps     (in sdc_lint)
  drv           max transition and max capacitance violations = 0 at TT and FF (liberty limits; SS info)  blocking
  fanout        nets with fanout > FANOUT_MAX (64; ASAP7 liberty has no max_fanout)                        WARN only
  unconstrained check_setup -unconstrained_endpoints = 0, no unclocked registers, no loops                blocking
                (12.2a1 kits: the declared die-timed ft outputs are listed as ft_die_timed, never counted as core IO)
  ft_interface  (only kits with ft_ports.json, COORD 10-26 12:55) every declared ft arc characterised TT + FF into the
                kit interface model ft_interface.json (port-to-port delay, clock = die clock pass-through, reset =
                interface arc for die STA); no core IO overlay on the ft ports                                 blocking
  clock         per corner: active-edge clock arrival at every register clock pin (insertion min/mean/max) and
                at the PIN FLOPS (registers whose D is in the fan-out of a data input or whose Q reaches a data
                output); related flop-pair skew with CPPR <= 80 ps at TT and FF (owner decision 5); spread INFO; with
                --insertion-target the pin-flop mean must be within +-insertion_tol (a hard-core kit whose core.json
                carries clock_contract.kind = hard_core_latency publishes its measured insertion instead:
                signoff.json core_latency; the target applies at the parent partition tap, COORD 10-24)     blocking
  sdc_lint      tools/die_plan/sdc_lint.py on the golden SDC (kit sdc_lint.json when present, else a context derived
                from the SDC + the routed netlist's ports with the plan period / insertion / tolerance)     blocking
  face_guard    tools/die_plan/face_guard.py on the synthesized netlist (<base>/1_synth.v | 1_2_yosys.v), with
                the kit pins.json when present                                                              blocking
  drc           routed DRC count = 0 (ORFS 5_2_route.json detailedroute__route__drc_errors, else the record /
                5_route_drc.rpt)                                                                            blocking
  antenna       antenna violating nets = 0 (5_2_route.json detailedroute__antenna__violating__nets)         blocking

OCV / DERATES: the verdict applies NO timing derate: the AGENTS.md 60 / 25 ps clock uncertainty is the project's
on-chip-variation + jitter margin (user decision 2026-09-30) and changing it needs an owner decision.  For visibility
each corner also reports the worst slack under a flat +-5 % OCV derate (late 1.05 / early 0.95, cell + net, data +
clock) as `ocv5_*` (information only, never a reason).  One SPEF (the flow's RCX, single ASAP7 rules file) serves all
three corners.

DROOP CHECK (METHODOLOGY 12.4a b2, OWNER 10-27; INFORMATION ONLY, never a reason, the verdict is unchanged): with
`run --droop-check` the TT session re-times setup at the 0.665 V (35 mV) droop with the shared data droop model
(tools/die_plan/data_droop.py, die_ci_margins.json data_droop): a LATE data cell derate, logic class +10 %, wire class
(repeater master driving >= 40 fF of SPEF net cap) +5 %; no clock derate (shared droop inside one core), no early /
hold term, the 60 ps uncertainty kept.  Recorded as corners.tt.droop665_wns_max and record info_droop665 (with the
nominal std_wns_max of the same session).  Rule: cores with TT setup slack < 25 ps get this rerun at their next
re-sign (information + fix if it fails).
"""
import argparse
import concurrent.futures as cf
import datetime
import gzip
import hashlib
import json
import os
import math
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if len(HERE.parents) > 1 else HERE  # standalone /work kit copy
sys.path.insert(0, str(HERE))

SCHEMA = "opentallas.signoff.v1"
IMAGE = os.environ.get("ORFS_IMAGE", "openroad/orfs:latest")
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
PERIOD_PS = 833.0
UNC_SETUP_PS, UNC_HOLD_PS = 60.0, 25.0
INSERTION_PS, INSERTION_TOL_PS = 250.0, 40.0
PAIR_SKEW_MAX_PS = 80.0
# IO virtual-clock reference: 'sdc' (kit SDC value), 'pin-flop-mean' (FF only, opt-in with a contract), 'rebind'
# (FLOW 10-25, default for kits with a per-corner insertion binding: TT and FF each rebound to their routed pin-register
# mean, clock check FAILs when a mean is more than the tolerance from the bound value)
VCLK_MODES = ("sdc", "pin-flop-mean", "rebind", "bound-ff")
PAIR_VERIFY_TOL_PS = 1.0             # credited path-end skew vs CK-arrival skew - CPPR (integrity check)
PAIR_CREDIT_MAX = 5000                 # exact-credit path searches per check before the worst becomes a bound
SPREAD_MAX_PS = PAIR_SKEW_MAX_PS  # legacy record field; spread is information only
FANOUT_MAX = 64
SPREAD_CORNERS = ("tt", "ff")
CORNERS = ("tt", "ff")                 # the sign-off corners; "ss" may be added for information
ALL_CORNERS = ("tt", "ff", "ss")
BLOCKING = ("setup_tt", "hold_ff", "drv", "unconstrained", "clock", "sdc_lint", "face_guard", "drc", "antenna", "pg")


# ---- discovery ----------------------------------------------------------------------------------------------------
ROUTED_DBS = ("6_final.odb", "5_route.odb")


def routed_db(base):
    """the routed ODB of a results base: 6_final.odb, else 5_route.odb (kits run with GOAL=route), else None"""
    return next((n for n in ROUTED_DBS if (Path(base) / n).is_file()), None)


def find_base(run_dir):
    """<run>/results/asap7/<design>/base (exactly one) or run_dir itself if it holds a routed ODB."""
    rd = Path(run_dir)
    if routed_db(rd):
        return rd
    for pat in ("results/asap7/*/base", "run/results/asap7/*/base", "work/orfs/results/asap7/*/base"):
        hits = sorted(p for p in rd.glob(pat) if routed_db(p))
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise SystemExit(f"signoff: several routed bases under {rd}: {hits}")
    raise SystemExit(f"signoff: no results/asap7/*/base/{{6_final,5_route}}.odb under {rd}")


def orfs_root(base):
    """ORFS work dir (holds results/ logs/ reports/) of a results base."""
    b = Path(base).resolve()
    if b.name == "base" and b.parent.parent.name == "asap7" and b.parent.parent.parent.name == "results":
        return b.parent.parent.parent.parent
    return None


def discover(base, kit=None, sdc=None, record=None):
    base = Path(base).resolve()
    root = orfs_root(base)
    design = base.parent.name if root else None
    if kit is None and root is not None:
        for k in (root.parent, root.parent.parent, root.parent.parent.parent):
            if (k / "config.mk").is_file() and ((k / "constraint.sdc").is_file() or (k / "run").is_dir()):
                kit = k
                break
    kit = Path(kit).resolve() if kit else None
    d = dict(base=str(base), orfs=str(root) if root else None, design=design, kit=str(kit) if kit else None,
             odb=str(base / (routed_db(base) or "6_final.odb")), spef=None, sdc=None, sdc_source=None, synth=None, final_v=None,
             metrics={}, drc_rpt=None, pins=None, sdc_lint_ctx=None, record=str(record) if record else None)
    if kit and (kit / "ft_ports.json").is_file():             # 12.2a1 die-timed ft declaration (key only when present)
        d["ft_ports"] = str(kit / "ft_ports.json")
    if (base / "6_final.spef").is_file() and Path(d["odb"]).name == "6_final.odb":
        d["spef"] = str(base / "6_final.spef")
    if sdc:
        d["sdc"], d["sdc_source"] = str(Path(sdc).resolve()), "arg"
    elif kit and (kit / "constraint.sdc").is_file():
        d["sdc"], d["sdc_source"] = str(kit / "constraint.sdc"), "kit"
    elif (base / "6_final.sdc").is_file():
        d["sdc"], d["sdc_source"] = str(base / "6_final.sdc"), "6_final.sdc"
    for n in ("1_synth.v", "1_2_yosys.v"):
        if (base / n).is_file():
            d["synth"] = str(base / n)
            break
    if (base / "6_final.v").is_file():
        d["final_v"] = str(base / "6_final.v")
    if root is not None:
        lg = root / "logs" / "asap7" / design / "base"
        for n in ("5_2_route.json", "5_1_grt.json", "6_report.json"):
            if (lg / n).is_file():
                try:
                    d["metrics"][n] = str(lg / n)
                except Exception:
                    pass
        r = root / "reports" / "asap7" / design / "base" / "5_route_drc.rpt"
        if r.is_file():
            d["drc_rpt"] = str(r)
    if kit:
        for n in ("pins.json",):
            if (kit / n).is_file():
                d["pins"] = str(kit / n)
        if (kit / "sdc_lint.json").is_file():
            d["sdc_lint_ctx"] = str(kit / "sdc_lint.json")
    return d


NATIVE_PDK_LIB = re.compile(
    r'/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_'
    r'(AO|INVBUF|OA|SEQ|SIMPLE)_(RVT|LVT|SLVT)_(TT|FF|SS)_nldm_[^/]+\.lib(?:\.gz)?')


def macro_libs(kit, corner):
    """(host paths of the corner's macro liberty files, missing corner list) from shared or corner-scoped KIT/config.mk libraries."""
    if not kit or not (Path(kit) / "config.mk").is_file():
        return [], []
    txt = (Path(kit) / "config.mk").read_text(errors="replace").replace("\\\n", " ")
    libs, missing = [], []
    field = {"tt": "TC_LIB_FILES", "ff": "BC_LIB_FILES", "ss": "WC_LIB_FILES"}[corner]
    for m in re.finditer(r"^[ \t]*(?:export[ \t]+)?(ADDITIONAL_LIBS|TC_LIB_FILES|BC_LIB_FILES|WC_LIB_FILES)[ \t]*[:+?]?=[ \t]*(.*)$", txt, re.M):
        if m.group(1) not in ("ADDITIONAL_LIBS", field):
            continue
        scoped = m.group(1) == field
        for w in m.group(2).split():
            if re.fullmatch(r"\$\((TC|BC|WC)_NLDM_LIB_FILES\)", w):
                continue  # standard cells are loaded independently for this corner
            w = w.replace("$(KIT)", "/work").replace("${KIT}", "/work")
            native = NATIVE_PDK_LIB.fullmatch(w)
            if native:
                # The corner's standard-cell selector loads and validates these;
                # they are not host-staged composed-child Liberty files.
                if scoped and native.group(3).lower() != corner:
                    missing.append(f"{w} (native PDK corner != {corner})")
                continue
            if not w.startswith("/work/"):
                missing.append(f"{w} (not under /work)")
                continue
            p = Path(kit) / w[len("/work/"):]
            cand = None
            mm = re.match(r"^(.*)_(ss|tt|ff|typ)(\.lib(?:\.gz)?)$", p.name)
            if mm:
                for suf in ([corner] if corner != "tt" else ["tt", "typ"]):
                    q = p.with_name(f"{mm.group(1)}_{suf}{mm.group(3)}")
                    if q.is_file():
                        cand = q
                        break
            elif p.is_file() and (corner == "tt" or scoped):
                cand = p
            if cand is None:
                missing.append(f"{p.name} ({corner})")
            else:
                libs.append(str(cand))
    return list(dict.fromkeys(libs)), missing


SIGNOFF_BUNDLE = ("signoff.py", "sdc_lint.py", "face_guard.py", "io_hold_qualification.py", "pair_skew.tcl", "clock_family.tcl",
                  "kit_modes.py", "data_droop.py", "core_io_reference.py")


def signoff_bundle_sources(source=HERE):
    source = Path(source)
    paths = {name: source / name for name in SIGNOFF_BUNDLE}
    if not paths["clock_family.tcl"].is_file():
        paths["clock_family.tcl"] = source.parents[1] / "physical/common_flow/clock_family.tcl"
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError("signoff: incomplete tool bundle: " + ", ".join(missing))
    return paths


def require_signoff_bundle():
    return signoff_bundle_sources()


# Dependencies of standalone kit hooks.  Existing custom hooks stay byte-identical;
# their missing shared helpers are shipped by the same bundle as the sign-off tool.
KIT_TOOL_DEPENDENCIES = {
    "orfs_hold_mm.tcl": ("macro_cts_cluster.tcl",),
    "die_sta_related.py": ("clock_components.py", "data_droop.py"),
    "kit_preflight.py": ("sdc_lint.py", "rtl_lint.py", "master_slice.py", "core_infra.py", "core_infra.tcl", "ft_ports.py",
                         "kit_contract.py", "die_sta_related.py", "data_droop.py"),
    "postcts_gate.tcl": ("pinreg_measure.tcl", "clock_family.tcl"),
    "pinreg_pad.tcl": ("pinreg_measure.tcl", "clock_family.tcl"),
    "tap_balance.tcl": ("clock_family.tcl",),
    "cts_post.tcl": ("tap_balance.tcl", "leaf_affinity.tcl", "pg_connect.tcl"),
    "grt_post.tcl": ("pg_connect.tcl",),
    "tapbal_grt.tcl": ("tap_balance.tcl", "pinreg_pad.tcl"),
    "hold_gate.tcl": ("vclk_corner.tcl",),
    "face_guard_core.py": ("face_guard.py",),
    "core_preflight.py": ("signoff.py", "face_guard.py"),
    "kit_contract.py": ("core_io_reference.py",),
}


def copy_signoff_bundle(destination, source=HERE, extra=()):
    paths = signoff_bundle_sources(source)
    destination, source = Path(destination), Path(source)
    requested = list(extra)
    if any(Path(name).name != name for name in requested):
        raise ValueError("signoff: bundle helper names must be basenames")
    pending = requested + [name for name in KIT_TOOL_DEPENDENCIES
                           if (destination / name).is_file()]
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        # Preserve an already copied kit-specific hook; explicit --with roots and
        # the canonical sign-off family are copied from the requested tool source.
        if name not in paths and (name in requested or not (destination / name).is_file()):
            path = source / name
            if name in ("clock_family.tcl", "macro_cts_cluster.tcl") and not path.is_file():
                path = source.parents[1] / "physical/common_flow" / name
            paths[name] = path
        pending.extend(KIT_TOOL_DEPENDENCIES.get(name, ()))
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError("signoff: incomplete kit tool bundle: " + ", ".join(missing))
    destination.mkdir(parents=True, exist_ok=True)
    for name, path in paths.items():
        target = destination / name
        if path.resolve() != target.resolve():
            shutil.copyfile(path, target)
    return list(paths)


def copy_core_tap_overlay(golden, destination):
    golden, destination = Path(golden), Path(destination)
    text = golden.read_text()
    lines = [line.strip() for line in text.splitlines() if line.startswith("# OT_CORE_TAP_CORNER_FILE")]
    if not lines:
        return False
    if lines != ["# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc"]:
        raise ValueError("signoff: malformed or ambiguous core-tap FF overlay marker")
    overlay = golden.with_name("core_taps_ff.sdc")
    if not overlay.is_file():
        raise ValueError("signoff: missing marked core_taps_ff.sdc")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(overlay, destination / overlay.name)
    return True


def _lib_groups(text, keyword):
    """Yield named Liberty groups while respecting quoted strings and escapes."""
    pattern = re.compile(r'\b' + re.escape(keyword) + r'\s*\(([^)]*)\)\s*\{')
    position = 0
    while (match := pattern.search(text, position)):
        depth, quoted, escaped = 1, False, False
        index = match.end()
        while index < len(text) and depth:
            char = text[index]
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted:
                depth += (char == '{') - (char == '}')
            index += 1
        if depth:
            raise ValueError('unterminated Liberty group')
        yield match.group(1).strip().strip('"'), text[match.end():index - 1]
        position = index


def clock_model_coverage(library_files, instantiated_masters, expected_sha256=None):
    """Pure, fail-closed composed-child endpoint detector, reusable by die STA.

    Inputs are the actual selected libraries and exact sequential endpoint
    master names. Clock-to-Q alone is not a composed-child marker: an ordinary
    SRAM has that arc too. Nonzero clock_tree_path + is_macro_cell is the
    capability marker here. No latency correction or expansion is performed.
    """
    result = dict(schema='opentallas.clock_endpoint_coverage.v1',
                  raw_pair_basis='visible_clock_pins', models=[])
    try:
        if instantiated_masters is None:
            raise ValueError('actual instantiated clock endpoint masters unavailable')
        masters = set(instantiated_masters)
        result['instantiated_masters'] = sorted(masters)
        for filename in library_files:
            path = Path(filename)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected_sha256 is not None and expected_sha256.get(str(path)) != digest:
                raise ValueError(f'consumed Liberty hash mismatch: {path}')
            text = gzip.open(path, 'rt').read() if path.suffix == '.gz' else path.read_text()
            text = re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*',
                          lambda match: match.group(0) if match.group(0).startswith('"') else ' ', text, flags=re.S)
            unit = re.search(r'\btime_unit\s*:\s*"([^"]+)"', text)
            if not re.search(r'\b(?:min|max)_clock_tree_path\b', text):
                continue
            for master, body in _lib_groups(text, 'cell'):
                if master not in masters or not re.search(r'\bis_macro_cell\s*:\s*true\s*;', body):
                    continue
                tree_paths = {}
                for _, timing in _lib_groups(body, 'timing'):
                    marker = re.search(r'\btiming_type\s*:\s*((?:min|max)_clock_tree_path)\s*;', timing)
                    if not marker:
                        continue
                    values = []
                    for table in re.findall(r'\bvalues\s*\(\s*"([^"]*)"\s*\)', timing, re.S):
                        values.extend(float(word) for word in re.split(r'[,\s]+', table.replace('\\\n', ' ')) if word)
                    if not values or not all(math.isfinite(value) for value in values):
                        raise ValueError(f'invalid clock_tree_path values: {path}:{master}')
                    tree_paths.setdefault(marker.group(1), []).extend(values)
                if not any(value != 0 for values in tree_paths.values() for value in values):
                    continue
                model = dict(master=master, liberty=str(path), liberty_sha256=digest,
                             marker='is_macro_cell + nonzero clock_tree_path', clock_tree_path_values=tree_paths,
                             liberty_time_unit=unit.group(1) if unit else None)
                corner = re.search(r'_(tt|ff|ss)\.lib(?:\.gz)?$', path.name)
                export = path.parent / ('export_' + corner.group(1) + '.tcl') if corner else None
                if export and export.is_file():
                    producer = export.read_text()
                    model['export_provenance'] = dict(path=str(export),
                        sha256=hashlib.sha256(export.read_bytes()).hexdigest(),
                        write_timing_model='write_timing_model' in producer,
                        read_spef='read_spef' in producer, propagated_clock='set_propagated_clock' in producer)
                result['models'].append(model)
        unexpanded = bool(result['models'])
        result.update(status='UNEXPANDED_CHILD_ETM' if unexpanded else 'NO_UNEXPANDED_CHILD_ETM',
                      verdict='NOT RUN' if unexpanded else 'PASS',
                      expanded_child_flop_pairs='NOT RUN' if unexpanded else 'NO_LUMPED_CHILD_CLOCKS')
    except (OSError, ValueError, TypeError) as error:
        result.update(status='UNAVAILABLE', verdict='NOT RUN', expanded_child_flop_pairs='NOT RUN', reason=str(error))
    return result


def consumed_clock_model_coverage(receipt_path, disc, masters, mapping_errors=0):
    """Map exact container-library receipt paths to their immutable host inputs."""
    try:
        if mapping_errors != 0:
            raise ValueError('clock endpoint master inventory incomplete')
        receipt = json.loads(Path(receipt_path).read_text())
        if receipt.get('status') != 'LOADED' or not isinstance(receipt.get('libraries'), list):
            raise ValueError('exact loaded-library receipt unavailable')
        root = Path(disc['kit']) if disc.get('kit') else Path(disc['library_config']).parent
        files, expected, consumed = [], {}, {}
        for row in receipt['libraries']:
            source = row['path']
            # These are the exact native PDK groups, not composed child models.
            if NATIVE_PDK_LIB.fullmatch(source):
                continue
            if not source.startswith('/work/') or '..' in Path(source).parts:
                raise ValueError(f'consumed non-PDK Liberty host mapping unavailable: {source}')
            host = root / source[len('/work/'):]
            files.append(host); expected[str(host)] = row['sha256']; consumed[str(host)] = source
        result = clock_model_coverage(files, masters, expected)
        for model in result['models']:
            model['consumed_liberty'] = consumed[model['liberty']]
        result['library_receipt'] = str(receipt_path)
        return result
    except (OSError, ValueError, TypeError, KeyError) as error:
        return dict(schema='opentallas.clock_endpoint_coverage.v1', status='UNAVAILABLE', verdict='NOT RUN',
                    raw_pair_basis='visible_clock_pins', expanded_child_flop_pairs='NOT RUN', models=[], reason=str(error))

# ---- the OpenSTA session (one corner) -----------------------------------------------------------------------------
def _clock_family_tcl():
    for p in (REPO / "physical/common_flow/clock_family.tcl", HERE / "clock_family.tcl"):   # repo, or a kit copy
        if p.is_file():
            return p.read_text()
    return ""



# Opt-in corner-specific core clock reference.  Preserve the golden-SDC timing
# above and change the ONE shared virtual clock, hence both input and output
# budgets coherently.  Never change clock period, uncertainty, or IO delays.
FF_VCLK_TCL = r"""
@CLOCK_FAMILY@
set so_ff_regs {}
foreach p [all_registers -clock_pins] { dict set so_ff_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_ff_data {}
set so_ff_async {}
foreach p [all_registers -async_pins] { dict set so_ff_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $so_ff_async $n]} { dict set so_ff_data $n 1 }
}
set so_ff_bnd {}
if {[llength $so_din]} {
  foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_ff_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $so_ff_regs $i]} { dict set so_ff_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $so_ff_regs $i]} { dict set so_ff_bnd $i 1 }
  }
}
set so_ff_sum 0.0
set so_ff_n 0
set so_ff_bad 0
set so_ff_clocks {}
if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
dict for {i unused} $so_ff_bnd {
  set p [dict get $so_ff_regs $i]
  set cl [get_property $p clocks]
  set a ""
  if {[llength $cl] == 1} {
    dict set so_ff_clocks [get_full_name [lindex $cl 0]] 1
    if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
    if {$a eq ""} { catch {set a [get_property $p arrival_max_rise]} }
  }
  if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} { incr so_ff_bad; continue }
  set so_ff_sum [expr {$so_ff_sum + $a}]
  incr so_ff_n
}
if {[llength $so_vclk] == 1 && $so_ff_n > 0 && $so_ff_bad == 0 && [dict size $so_ff_clocks] == 1} {
  set so_ff_mean [expr {$so_ff_sum / $so_ff_n}]
  set_clock_latency -source $so_ff_mean [lindex $so_vclk 0]
  so FF_VCLK applied mode pin_flop_mean clock [get_full_name [lindex $so_vclk 0]] latency_ps [format %.6f $so_ff_mean] samples $so_ff_n missing $so_ff_bad clocks [dict size $so_ff_clocks]
} else {
  set so_reference_ok 0
  so FF_VCLK unavailable mode pin_flop_mean vclks [llength $so_vclk] samples $so_ff_n missing $so_ff_bad
}
"""

# FLOW-FIX 10-25 'bound-ff' (hard-core latency contract kits, ROOT-MERGE2: no rebind inside a core): the FF session
# times IO against the kit's DECLARED FF insertion (sdc_lint ctx insertion_ff_ps, the same value the in-flow FF hold
# repair bound), never silently against the single SDC (TT) vclk latency.
FF_BOUND_TCL = r"""
if {[llength $so_vclk] == 1} {
  set_clock_latency -source @FF_BOUND@ [lindex $so_vclk 0]
  so FF_VCLK applied mode bound_ff clock [get_full_name [lindex $so_vclk 0]] latency_ps @FF_BOUND@
} else {
  set so_reference_ok 0
  so FF_VCLK unavailable mode bound_ff vclks [llength $so_vclk]
}
"""

EXACT_TIMING_LIBRARIES_TCL = r"""# Resolve the exact libraries selected by this kit's ORFS make configuration.
# No directory glob or installed-version fallback is permitted.
proc ot_lib_json_string {value} {
  return "\"[string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $value]\""
}
proc ot_lib_validate {corner files} {
  if {$corner ni {TT FF SS}} {error "OT_TIMING_LIBS: unsupported corner $corner"}
  if {![llength $files]} {error "OT_TIMING_LIBS: empty exact library list"}
  set seen {}; set groups {}; set present {}
  foreach f $files {
    if {[file pathtype $f] ne "absolute"} {error "OT_TIMING_LIBS: relative library $f"}
    if {[regexp {[*?\[\]$]} $f] || ![file isfile $f]} {error "OT_TIMING_LIBS: missing or unresolved library $f"}
    set path [file normalize $f]
    if {[dict exists $seen $path]} {error "OT_TIMING_LIBS: duplicate library $f"}
    dict set seen $path 1
    if {[regexp {^asap7sc7p5t_([^_]+)_(RVT|LVT|SLVT)_(TT|FF|SS)_nldm_} [file tail $f] -> group vt actual]} {
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong corner $f"}
      set key $group/$vt
      if {[dict exists $groups $key]} {error "OT_TIMING_LIBS: ambiguous installed versions for $key"}
      dict set groups $key $path
      dict set present $group 1
    } elseif {[regexp -nocase {_(tt|ff|ss|typ)\.lib(?:\.gz)?$} [file tail $f] -> actual]} {
      set actual [string toupper $actual]
      if {$actual eq "TYP"} {set actual TT}
      if {$actual ne $corner} {error "OT_TIMING_LIBS: wrong macro corner $f"}
    }
  }
  foreach group {AO INVBUF OA SEQ SIMPLE} {
    if {![dict exists $present $group]} {error "OT_TIMING_LIBS: missing standard-cell group $group"}
  }
  return $files
}
proc ot_lib_resolve {corner {config /work/config.mk}} {
  if {![file isfile $config]} {error "OT_TIMING_LIBS: missing exact ORFS config $config"}
  set field [dict get {TT TC_LIB_FILES FF BC_LIB_FILES SS WC_LIB_FILES} $corner]
  set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=$1" "print-$2"} otlibs $config $field]
  set records {}
  foreach line [split $output \n] {
    if {[regexp "^${field}\\s*\[:=\]\\s*(.*)$" $line -> value]} {lappend records $value}
  }
  if {[llength $records] != 1} {error "OT_TIMING_LIBS: missing or ambiguous make $field result"}
  set files [regexp -all -inline {\S+} [lindex $records 0]]
  return [ot_lib_validate $corner $files]
}
proc ot_lib_load {corner receipt {config /work/config.mk}} {
  if {[file exists $receipt]} {file rename $receipt ${receipt}.previous.[clock clicks]}
  set files [ot_lib_resolve $corner $config]
  set rows {}
  foreach f $files {
    set digest [lindex [exec sha256sum -- $f] 0]
    lappend rows "{\"path\":[ot_lib_json_string $f],\"sha256\":[ot_lib_json_string $digest]}"
  }
  set digest [lindex [exec sha256sum -- $config] 0]
  foreach f $files {read_liberty $f}
  set fp [open $receipt w]
  puts $fp "{\"status\":\"LOADED\",\"corner\":[ot_lib_json_string $corner],\"source\":\"ORFS make print corner LIB_FILES\",\"config\":[ot_lib_json_string $config],\"config_sha256\":[ot_lib_json_string $digest],\"libraries\":\[[join $rows ,]\]}"
  close $fp
  puts "OT_TIMING_LIBS $corner exact_count [llength $files] receipt $receipt"
  return $files
}
"""

SESSION_TCL = r"""
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
@TIMING_LIBRARIES@
ot_lib_load @C@ /out/libraries.json
read_db /base/@ODB@
# FLOW 10-26 PG: every POWER/GROUND MTerm of every instance master bound to a net of that type in the signed ODB
# (global_connect skips dont_touch cells: s8b ot_ms_* spine buffers had VDD/VSS open in 6_final.odb).
set so_pg_terms 0; set so_pg_open 0; set so_pg_first "-"
foreach so_i [[ord::get_db_block] getInsts] {
  foreach so_mt [[$so_i getMaster] getMTerms] {
    set so_r [$so_mt getSigType]
    if {$so_r ni {POWER GROUND}} continue
    incr so_pg_terms
    set so_t [$so_i findITerm [$so_mt getName]]
    set so_n NULL
    if {$so_t ne "NULL" && $so_t ne ""} { set so_n [$so_t getNet] }
    if {$so_n eq "NULL" || $so_n eq "" || [$so_n getSigType] ne $so_r} {
      incr so_pg_open
      if {$so_pg_first eq "-"} { set so_pg_first "[$so_i getName]/[$so_mt getName]" }
    }
  }
}
so PG $so_pg_terms $so_pg_open $so_pg_first
@PARASITICS@
read_sdc /sdc/golden.sdc
@CORE_TAPS_FF@
set_propagated_clock [all_clocks]
so CORNER @C@
so PARASITICS @PARSRC@
so DESIGN [current_design]
so CELLS [llength [get_cells *]]
# Inventory actual sequential endpoint masters; a Liberty loaded but unused is
# not evidence of an unexpanded child. Keep the raw pair census unchanged.
set so_endpoint_masters {}; set so_endpoint_mapping_errors 0
foreach p [all_registers -clock_pins] {
  if {[catch {
    set owners [get_cells -quiet -of_objects [list $p]]
    if {[llength $owners] != 1} {error "nonunique clock endpoint owner"}
    set master [get_property [lindex $owners 0] ref_name]
    if {$master eq ""} {error "empty clock endpoint master"}
  }]} {incr so_endpoint_mapping_errors; continue}
  dict set so_endpoint_masters $master 1
}
so CLOCK_ENDPOINT_MASTERS {*}[lsort [dict keys $so_endpoint_masters]]
so CLOCK_ENDPOINT_MAPPING_ERRORS $so_endpoint_mapping_errors
# ---- ports (for sdc_lint context) and IO virtual clock ----
set so_ck_ports {}
foreach c [all_clocks] { foreach s [get_property $c sources] { if {[llength [get_ports -quiet [get_full_name $s]]]} { lappend so_ck_ports [get_full_name $s] } } }
set so_ck_ports [lsort -unique $so_ck_ports]
so CLOCK_PORTS {*}$so_ck_ports
set so_din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }
so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
so OUTPUTS {*}[lsort -unique [lmap p [all_outputs] {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
set so_vclk {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend so_vclk $c } }
so CLOCKS {*}[lmap c [all_clocks] {get_full_name $c}]
so VCLKS {*}[lmap c $so_vclk {get_full_name $c}]
foreach c [all_clocks] { so PERIOD [get_full_name $c] [get_property $c period] }
# ---- timing with the block's own SDC ----
proc so_timing {tag} {
  so ${tag}_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
  so ${tag}_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
  so ${tag}_TNS_MAX [so_ps [sta::total_negative_slack_cmd max]]
  so ${tag}_TNS_MIN [so_ps [sta::total_negative_slack_cmd min]]
  so ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  so ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
so_timing SDC
puts "SO_PATH_BEGIN SDC_MAX"
report_checks -path_delay max -format full_clock_expanded -digits 2 -fields {slew cap fanout}
puts "SO_PATH_END"
# ---- standard boundary-hold overlay (4b7b2b3e64 kit standard) ----
set so_reference_ok 1
@FF_VCLK@
if {[llength $so_vclk] == 1 && $so_reference_ok} {
  if {[llength $so_din]} { set_input_delay -min @IN_MIN@ -clock [lindex $so_vclk 0] $so_din }
  if {[llength [all_outputs]]} { set_output_delay -min @OUT_MIN@ -clock [lindex $so_vclk 0] [all_outputs] }
@IN_MIN_PORTS@
@OUT_MIN_PORTS@
  so OVERLAY applied [get_full_name [lindex $so_vclk 0]] in_min @IN_MIN_LOG@ out_min @OUT_MIN@
} else {
  so OVERLAY skipped vclks [llength $so_vclk]
}
so_timing STD
puts "SO_PATH_BEGIN STD_MIN"
report_checks -path_delay min -format full_clock_expanded -digits 2
puts "SO_PATH_END"
# ---- DRV ----
so SLEW_VIOL [sta::max_slew_violation_count]
so CAP_VIOL [sta::max_capacitance_violation_count]
set so_fo_max 0; set so_fo_n 0; set so_fo_worst ""
foreach n [get_nets -hierarchical *] {
  set k [llength [get_pins -quiet -of_objects $n -filter "direction==input"]]
  if {$k > $so_fo_max} { set so_fo_max $k; set so_fo_worst [get_full_name $n] }
  if {$k > @FANOUT_MAX@} { incr so_fo_n }
}
so FANOUT_MAX $so_fo_max $so_fo_worst
so FANOUT_VIOL $so_fo_n
puts "SO_PATH_BEGIN DRV"
report_check_types -max_slew -max_capacitance -violators -max_count 10
puts "SO_PATH_END"
# ---- constraint coverage ----
puts "SO_PATH_BEGIN CHECK_SETUP"
check_setup -verbose -unconstrained_endpoints -no_clock -loops -generated_clocks -multiple_clock
puts "SO_PATH_END"
# ---- OCV sensitivity (information only) ----
set_timing_derate -late 1.05
set_timing_derate -early 0.95
so OCV5_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
so OCV5_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
unset_timing_derate
@DROOP665@# ---- related flop-pair skew with CPPR (owner gate, BRIEFING decision 5) ----
# Measured on the golden SDC exactly as loaded (source latencies, propagated clocks, derate removed), BEFORE the
# insertion diagnostic below zeroes clock source latency; only the clock uncertainty is zeroed (clk_skew must not
# carry it) and nothing after this block reads slack.
set ::ot_ps_lib_only 1
@PAIR_SKEW@
unset ::ot_ps_lib_only
@PAIR_TARGETS@ot_ps_zero_unc
set so_t0 [clock seconds]
set so_pm [ot_ps_measure @PAIR_CREDIT_MAX@]
ot_ps_write $so_pm /out/pair_skew.tsv @C@
so PAIR_COUNTS regs [dict get $so_pm regs] no_clock_arrival [dict get $so_pm no_clock_arrival] data_pins [dict get $so_pm data_pins] pairs [dict get $so_pm pairs] inter_clock [dict get $so_pm inter_clock]
foreach dly {max min} {
  set m [dict get $so_pm $dly]
  so PAIR_$dly {*}[concat {*}[lmap k {n worst bounded signed launch capture crpr p99_raw searched nopath verify} {list $k [dict get $m $k]}]]
}
@PAIR_TGT_SO@so PAIR_METHOD [dict get $so_pm method]
so PAIR_SECONDS [expr {[clock seconds] - $so_t0}]
unset so_pm
so PAIR_DONE 1
# ---- clock: active-edge arrival at register clock pins, pin flops ----
@CLOCK_FAMILY@
set so_regs {}
foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_bnd {}
set so_data {}
set so_async {}
foreach p [all_registers -async_pins] { dict set so_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $so_async $n]} { dict set so_data $n 1 } }
if {[llength $so_din]} {
  foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set so_ck_err 0
set so_cf [llength [info commands ot_cf_wire]]
if {$so_cf} { catch {ot_cf_refresh} }
dict for {i p} $so_regs {
  set cl [get_property $p clocks]
  if {[llength $cl] != 1} { incr so_ck_err; continue }
  set a ""
  if {$so_cf} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
  if {$a eq ""} {
    # get_property returns display units already (PropertyValue timeUnit);
    # converting again multiplies ASAP7 ps arrivals by 1e12.
    catch {set a [get_property $p arrival_max_rise]}
  }
  if {$a eq "" || ![string is double -strict $a]} { incr so_ck_err; continue }
  puts "SO_CK [expr {[dict exists $so_bnd $i] ? 1 : 0}] [format %.2f $a] [get_full_name [lindex $cl 0]]"
}
so CK_ERRORS $so_ck_err
so DONE 1
exit
"""


def ft_char_tcl(decl, env=None):
    """12.2a1 declared ft arcs (COORD 10-26 12:55): characterise each port-to-port arc for the kit interface model
    under the kit IO environment, AFTER every constrained check of the session (it changes none of them)."""
    env = env or dict(driving_cell="BUFx4_ASAP7_75t_R", load_ff=2.0)
    L = ["# ---- 12.2a1 declared ft arcs: interface-model characterisation (after all checks) ----"]
    for a in decl["arcs"]:
        L += [f"set_driving_cell -lib_cell {env['driving_cell']} -pin Y [get_ports {{{a['source']}}}]",
              f"set_load {float(env['load_ff']):g} [get_ports {{{a['sink']}}}]"]
    for a in decl["arcs"]:
        s_, d_ = a["source"], a["sink"]
        L.append(f"foreach so_ft_w {{min max}} {{ set so_ft_p [find_timing_paths -unconstrained -path_delay $so_ft_w "
                 f"-from [get_ports {{{s_}}}] -to [get_ports {{{d_}}}]]; set so_ft_v($so_ft_w) [expr {{[llength $so_ft_p] "
                 f"? [format %.2f [get_property [lindex [get_property [lindex $so_ft_p 0] points] end] arrival]] : \"NA\"}}] }}")
        # (QC-SU-F4D: OpenSTA path ENDS have no "arrival" / "data_arrival_time" property -> the F4A rp1 session stopped
        # here and every corner check read NOT RUN.  The last path POINT carries arrival, already in display units (ps),
        # so no so_ps re-conversion; probed on the F4A rp1 6_final: ft_ck_i->ft_ck_o min 21.20 / max 24.12 ps.)
        L.append(f"puts \"SO_FT_ARC {s_} {d_} $so_ft_v(min) $so_ft_v(max)\"")
    return "\n".join(L) + "\n"


def ft_parse(text):
    """SO_FT_ARC src sink min max -> {"src->sink": {min, max} | None}"""
    r = {}
    for m in re.finditer(r"^SO_FT_ARC (\S+) (\S+) (\S+) (\S+)\s*$", text, re.M):
        try:
            r[f"{m.group(1)}->{m.group(2)}"] = dict(min=float(m.group(3)), max=float(m.group(4)))
        except ValueError:
            r[f"{m.group(1)}->{m.group(2)}"] = None
    return r


def ft_fill_model(decl, model, corners):
    """corner results -> the kit interface model's tt_ps / ff_ps {min, max} per declared arc."""
    for a in model["arcs"]:
        for c in ("tt", "ff"):
            a[f"{c}_ps"] = ((corners.get(c) or {}).get("ft_arcs") or {}).get(f"{a['source']}->{a['sink']}")
    ok = all(isinstance(a.get(k), dict) for a in model["arcs"] for k in ("tt_ps", "ff_ps"))
    model["status"] = "characterised" if ok else "partial"
    return model


def session_tcl(corner, mlibs_ctr, spef, ins_tol=INSERTION_TOL_PS, fanout_max=FANOUT_MAX, odb="6_final.odb",
                ff_vclk="sdc", ff_bound_ps=None, hold_in_min=None, hold_out_min=None, hold_in_min_ports=None, core_taps_ff=False, hold_out_min_ports=None,
                ft_decl=None, tap_window=None, droop=None, pair_targets=False, fwd_ring=None):
    """pair_targets: True = the corner's planned core clock-pin earliness file is mounted at /sdc/pair_targets.txt
    (pair_target_file): the related pair skew is then also measured target-relative (pair_skew.tcl ot_ps_load_targets)
    and the gate reads that; False = no target lines (session byte-identical).  tap_window: the plan's per-tap latency window (sdc_lint.json tap_window_ps, gen_phys.tap_window_ps): the
    golden SDC times every clock port W early, so the overlay's min output delay is the contract + W (exact IO shift);
    None = no window.  hold_in_min / hold_out_min: the kit's seam hold contract (sdc_lint.json hold_in_min_ps / hold_out_min_ps,
    CLOCK-RESET IO-HOLD 10-25); None = legacy overlay (min input -ins_tol, min output 0).  hold_in_min_ports
    {input port: ps}: IO-HOLD option A per-port min input delays (sdc_lint.json hold_in_min_ports_ps) applied after
    the uniform one; None / {} = no per-port lines (session byte-identical).  droop: data_droop.derate_tcl text
    (12.4a b2 0.665 V re-time, INFO, --droop-check); None = no droop block (session byte-identical)."""
    hin = -float(ins_tol) if hold_in_min is None else float(hold_in_min)
    hout = 0.0 if hold_out_min is None else float(hold_out_min)
    if hout > 0:
        raise ValueError(f"hold overlay: min output delay {hout:g} > 0 waives the sender hold check")
    hout += float(tap_window or 0.0)
    if spef:
        par, src = "read_spef /base/6_final.spef", "spef"
    else:
        par, src = (f"source {PLAT}/setRC.tcl\nextract_parasitics -ext_model_file {PLAT}/rcx_patterns.rules\n"
                    "write_spef /out/rcx.spef\nread_spef /out/rcx.spef"), "rcx"
    if ff_vclk not in VCLK_MODES:
        raise ValueError("unsupported FF virtual-clock reference")
    # FLOW 10-25 'rebind' (ruling 9.7 / 5e): EVERY sign-off corner times its IO paths against that corner's routed
    # RCX pin-register mean; the clock check bounds it against the kit's per-corner bound insertion
    on = (corner == "ff" and ff_vclk == "pin-flop-mean") or (corner in ("tt", "ff") and ff_vclk == "rebind")
    if corner == "ff" and ff_vclk == "bound-ff":
        if ff_bound_ps is None:
            raise ValueError("bound-ff needs the declared FF insertion (ff_bound_ps)")
        t = SESSION_TCL.replace("@FF_VCLK@", FF_BOUND_TCL.replace("@FF_BOUND@", f"{float(ff_bound_ps):.6f}"))
    else:
        t = SESSION_TCL.replace("@FF_VCLK@", FF_VCLK_TCL if on else "")
    if ft_decl:
        # 12.2a1: the declared ft ports are die-timed -- the boundary-hold overlay never reaches them; the arcs are
        # characterised for the interface model after all checks (no ft declaration: session text unchanged)
        fi = " ".join(p["name"] for p in ft_decl["ports"] if p["direction"] == "INPUT")
        fo = " ".join(p["name"] for p in ft_decl["ports"] if p["direction"] == "OUTPUT")
        a_ = "foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }\n"
        b_ = "  if {[llength [all_outputs]]} { set_output_delay -min @OUT_MIN@ -clock [lindex $so_vclk 0] [all_outputs] }\n"
        if t.count(a_) != 1 or t.count(b_) != 1 or t.count("so DONE 1\n") != 1:
            raise ValueError("signoff: session template anchors for the ft exclusion changed")
        t = t.replace(a_, a_ + f"set so_ft_in {{{fi}}}; set so_ft_out {{{fo}}}\n"
                          "set so_din [lmap p $so_din {if {[get_full_name $p] in $so_ft_in} continue; set p}]\n"
                          "set so_dout [lmap p [all_outputs] {if {[get_full_name $p] in $so_ft_out} continue; set p}]\n"
                          "so FT_DIE_TIMED in $so_ft_in out $so_ft_out\n")
        t = t.replace(b_, "  if {[llength $so_dout]} { set_output_delay -min @OUT_MIN@ -clock [lindex $so_vclk 0] $so_dout }\n")
        t = t.replace("so DONE 1\n", ft_char_tcl(ft_decl) + "so DONE 1\n")
    if fwd_ring:
        t = _fwd_ring_tcl(t, fwd_ring, hin, hold_in_min_ports)
        hold_in_min_ports = {k: v for k, v in (hold_in_min_ports or {}).items()
                             if k not in {sel.split("[")[0] for _ck, sels in fwd_ring for sel in sels}}
    t = t.replace("@DROOP665@", "" if not droop else (
        "# ---- 12.4a b2 0.665 V data droop re-time (INFORMATION only, never a reason) ----\n" + droop +
        "so DROOP665_WNS_MAX [so_ps [sta::worst_slack_cmd max]]\n"
        "puts \"SO_PATH_BEGIN DROOP665\"\nreport_checks -path_delay max -format full_clock_expanded -digits 2\n"
        "puts \"SO_PATH_END\"\nunset_timing_derate\n"))
    for k, v in (("@ODB@", odb), ("@PLAT@", PLAT), ("@C@", corner.upper()), ("@PARASITICS@", par), ("@PARSRC@", src),
                 ("@TIMING_LIBRARIES@", EXACT_TIMING_LIBRARIES_TCL),
                 ("@CORE_TAPS_FF@", "read_sdc /sdc/core_taps_ff.sdc" if corner == "ff" and core_taps_ff else ""),
                 ("@INS_TOL@", f"{ins_tol:g}"), ("@IN_MIN@", f"[expr {{-{ins_tol:g}}}]" if hold_in_min is None else f"{hin:g}"),
                 ("@IN_MIN_LOG@", f"{hin:g}"), ("@OUT_MIN@", f"{hout:g}"),
                 ("@IN_MIN_PORTS@\n", _port_hold_overlay("input", hold_in_min_ports, ft_decl)),
                 # Sender-owned demand is shifted by the same tap window as the uniform output contract.
                 ("@OUT_MIN_PORTS@\n", _port_hold_overlay("output", hold_out_min_ports, ft_decl,
                                                         float(tap_window or 0.0))),
                 ("@FANOUT_MAX@", str(int(fanout_max))),
                 ("@CLOCK_FAMILY@", _clock_family_tcl()),
                 ("@PAIR_SKEW@", (HERE / "pair_skew.tcl").read_text()),
                 ("@PAIR_TARGETS@", "ot_ps_load_targets /sdc/pair_targets.txt\n" if pair_targets else ""),
                 ("@PAIR_TGT_SO@", PAIR_TGT_SO_TCL if pair_targets else ""),
                 ("@PAIR_CREDIT_MAX@", str(int(PAIR_CREDIT_MAX)))):
        t = t.replace(k, v)
    return t


FWD_RING_TAG = "# OT_FWD_RING_INPUTS"


def fwd_ring_inputs(sdc_text):
    """[(forwarded clock, [port selectors])] from the golden SDC's landing_contract.ring_input_sdc tags; [] = none."""
    out = []
    for ln in sdc_text.splitlines():
        if ln.startswith(FWD_RING_TAG + " "):
            w = ln.split()[2:]
            if len(w) < 2:
                raise ValueError(f"signoff: malformed {FWD_RING_TAG} line: {ln}")
            out.append((w[0], w[1:]))
    return out


def _fwd_ring_tcl(t, fwd_ring, hin, hold_in_min_ports):
    """DIE-HEAD-36 (COORD 10-29 21:11 (3)): source-synchronous ring inputs are timed against their forwarded write
    clock (golden SDC).  (a) The clock insertion measure uses the pinreg_measure.tcl flop set: the forwarded ring
    writers (registers clocked only by a forwarded ring clock) are not local-clock pin flops.  (b) Those inputs leave
    $so_din (the vclk boundary-hold overlay would replace their forwarded-clock input delays, OpenSTA drops a port's
    other-clock delays) and get the same overlay min re-referenced to their own forwarded clock."""
    regs_ff = "foreach p [all_registers -clock_pins] { dict set so_ff_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }\n"
    regs = "foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }\n"
    inputs = "so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\\[[0-9]+\\]$} [get_full_name $p] {}}]]\n"
    ov = "@IN_MIN_PORTS@\n"
    for a in (regs, inputs, ov):
        if t.count(a) != 1:
            raise ValueError("signoff: session template anchors for the forwarded-ring scope changed")
    if t.count(regs_ff) > 1:
        raise ValueError("signoff: session template anchors for the forwarded-ring scope changed")
    clocks = " ".join(sorted({ck for ck, _ in fwd_ring}))
    sel = " ".join(s for _ck, sels in fwd_ring for s in sels)
    keep = "if {[llength [get_property $p clocks]] == 1 && [get_full_name [lindex [get_property $p clocks] 0]] in $::so_fwd_clks} continue; "
    t = t.replace(regs_ff, regs_ff.replace("{ dict set", "{ " + keep + "dict set"))
    t = t.replace(regs, regs.replace("{ dict set", "{ " + keep + "dict set"))
    t = t.replace(inputs, inputs + f"set so_fwd_clks {{{clocks}}}\n"
                  f"set so_fwd_in [lmap p [get_ports {{{sel}}}] {{get_full_name $p}}]\n"
                  "set so_din [lmap p $so_din {if {[get_full_name $p] in $so_fwd_in} continue; set p}]\n"
                  "so FWD_RING_INPUTS clocks $so_fwd_clks ports [llength $so_fwd_in]\n")
    lines = []
    for ck, sels in fwd_ring:
        for s in sels:
            v = float((hold_in_min_ports or {}).get(s.split("[")[0], hin))
            lines.append(f"  set_input_delay -min {v:g} -clock {ck} [get_ports {{{s}}}]\n")
    return t.replace(ov, ov + "".join(lines))


def _port_hold_overlay(direction, values, ft_decl, shift=0.0):
    """Keep die-timed FT endpoints out of per-port overrides after bus expansion."""
    out = []
    for value, ports in _group_ports(values):
        selected = f"[get_ports {{{' '.join(p + '[*]' for p in ports)}}}]"
        command = f"set_{direction}_delay -min {value + shift:g} -clock [lindex $so_vclk 0]"
        if ft_decl:
            excluded = "$so_ft_in" if direction == "input" else "$so_ft_out"
            # Filter resolved pins, not bus strings: an override can contain a mix
            # of core-owned and die-owned bits of the same bus.
            out += [f"  set so_override_ports {selected}\n",
                    f"  set so_override_ports [lmap p $so_override_ports {{if {{[get_full_name $p] in {excluded}}} continue; set p}}]\n",
                    f"  if {{[llength $so_override_ports]}} {{ {command} $so_override_ports }}\n"]
        else:
            out.append(f"  {command} {selected}\n")
    return "".join(out)


def _group_ports(m):
    """{port: ps} -> [(ps, [ports])] sorted (one overlay command per distinct value)."""
    g = {}
    for p, v in (m or {}).items():
        g.setdefault(float(v), []).append(p)
    return sorted((v, sorted(ps)) for v, ps in g.items())


def parse_session(text):
    """SO lines -> dict; SO_CK -> clock arrays; SO_PATH blocks -> text."""
    r = dict(kv={}, ck=[], blocks={})
    blk, buf = None, []
    for ln in text.splitlines():
        if ln.startswith("SO_PATH_BEGIN "):
            blk, buf = ln.split(None, 1)[1].strip(), []
            continue
        if ln.startswith("SO_PATH_END"):
            if blk:
                r["blocks"][blk] = "\n".join(buf)[-20000:]
            blk = None
            continue
        if blk is not None:
            buf.append(ln)
            continue
        if ln.startswith("SO_CK "):
            f = ln.split()
            try:
                r["ck"].append((int(f[1]), float(f[2]), f[3] if len(f) > 3 else ""))
            except (ValueError, IndexError):
                pass
            continue
        if ln.startswith("SO "):
            f = ln.split(None, 2)
            if len(f) >= 2:
                k = f[1]
                v = f[2] if len(f) > 2 else ""
                if k == "PERIOD":
                    c, p = v.split()
                    r["kv"].setdefault("PERIOD", {})[c] = _f(p)
                else:
                    r["kv"][k] = v
    return r


def _f(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def stats(v):
    if not v:
        return None
    return dict(n=len(v), min=round(min(v), 2), mean=round(sum(v) / len(v), 2), max=round(max(v), 2),
                spread=round(max(v) - min(v), 2))


def check_setup_counts(text, ft_out=()):
    """counts from check_setup output.  ft_out: declared 12.2a1 die-timed ft outputs -- listed (verbose) unconstrained
    endpoints among them are counted as ft_die_timed, not as unconstrained core IO."""
    c = dict(unconstrained=0, unclocked=0, loops=0, multiple_clock=0, generated=0)
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = re.search(r"There (?:are|is) (\d+) unconstrained endpoints?", ln)
        if m:
            c["unconstrained"] = int(m.group(1))
            if ft_out:
                listed = []
                for x in lines[i + 1:]:
                    if not x.startswith((" ", "\t")) or not x.strip():
                        break
                    listed.append(x.strip())
                ft = sorted(set(listed) & set(ft_out))
                c["unconstrained"] -= len(ft)
                c["ft_die_timed"] = len(ft)
        m = re.search(r"There (?:are|is) (\d+) register/latch pins? with no clock", ln)
        if m:
            c["unclocked"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) combinational loops?", ln)
        if m:
            c["loops"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) pins? with multiple clocks", ln)
        if m:
            c["multiple_clock"] = int(m.group(1))
        m = re.search(r"There (?:are|is) (\d+) generated clocks? that (?:are|is) not connected", ln)
        if m:
            c["generated"] = int(m.group(1))
    return c


def corner_result(parsed):
    kv = parsed["kv"]
    allck = [a for _, a, _ in parsed["ck"]]
    bnd = [a for b, a, _ in parsed["ck"] if b]
    out = dict(done=kv.get("DONE") == "1", design=kv.get("DESIGN"), cells=_f(kv.get("CELLS")),
               parasitics=kv.get("PARASITICS"), clocks=(kv.get("CLOCKS") or "").split(),
               vclks=(kv.get("VCLKS") or "").split(), periods=kv.get("PERIOD", {}),
               clock_ports=(kv.get("CLOCK_PORTS") or "").split(), inputs=(kv.get("INPUTS") or "").split(),
               outputs=(kv.get("OUTPUTS") or "").split(), overlay=kv.get("OVERLAY"),
               ff_vclk_reference=kv.get("FF_VCLK"))
    for tag in ("SDC", "STD"):
        for k in ("WNS_MAX", "WNS_MIN", "TNS_MAX", "TNS_MIN", "NVIOL_MAX", "NVIOL_MIN"):
            out[f"{tag.lower()}_{k.lower()}"] = _f(kv.get(f"{tag}_{k}"))
    out["slew_viol"] = _f(kv.get("SLEW_VIOL"))
    out["cap_viol"] = _f(kv.get("CAP_VIOL"))
    fo = (kv.get("FANOUT_MAX") or "").split()
    out["fanout_max"] = _f(fo[0]) if fo else None
    out["fanout_worst_net"] = fo[1] if len(fo) > 1 else None
    out["fanout_viol"] = _f(kv.get("FANOUT_VIOL"))
    ftd = (kv.get("FT_DIE_TIMED") or "").split()
    ft_out = ftd[ftd.index("out") + 1:] if "out" in ftd else []
    out["check_setup"] = check_setup_counts(parsed["blocks"].get("CHECK_SETUP", ""), ft_out)
    if ftd:
        out["ft_die_timed"] = " ".join(ftd)
    out["ck_errors"] = _f(kv.get("CK_ERRORS"))
    pg = (kv.get("PG") or "").split()
    out["pg_terms"] = _f(pg[0]) if pg else None
    out["pg_open"] = _f(pg[1]) if len(pg) > 1 else None
    out["pg_first_open"] = pg[2] if len(pg) > 2 and pg[2] != "-" else None
    out["insertion_all"] = stats(allck)
    out["insertion_pinflops"] = stats(bnd)
    out["pair_skew"] = pair_skew_result(kv)
    out["clock_endpoint_masters"] = kv["CLOCK_ENDPOINT_MASTERS"].split() if "CLOCK_ENDPOINT_MASTERS" in kv else None
    out["clock_endpoint_mapping_errors"] = _f(kv.get("CLOCK_ENDPOINT_MAPPING_ERRORS"))
    out["ocv5_wns_max"] = _f(kv.get("OCV5_WNS_MAX"))
    out["ocv5_wns_min"] = _f(kv.get("OCV5_WNS_MIN"))
    if "DROOP665_WNS_MAX" in kv:                    # 12.4a b2 --droop-check only (key absent otherwise)
        out["droop665_wns_max"] = _f(kv.get("DROOP665_WNS_MAX"))
    return out


def _kvlist(text):
    """'k1 v1 k2 v2 ...' -> dict (values as text)"""
    f = (text or "").split()
    return dict(zip(f[0::2], f[1::2]))


PAIR_TGT_SO_TCL = (
    "so PAIR_TARGETS pins [dict get $so_pm target_pins] unmatched [dict get $so_pm target_unmatched]\n"
    "foreach dly {max min} {\n"
    "  set m [dict get $so_pm tgt_$dly]\n"
    "  so PAIR_TGT_$dly {*}[concat {*}[lmap k {n worst bounded signed launch capture crpr p99_raw searched nopath verify} "
    "{list $k [dict get $m $k]}]]\n"
    "}\n")
PAIR_TARGET_HEADER = "# inst pin mean_pin_register_insertion_ps"
PAIR_TARGET_FILES = {"tt": "core_latency.txt", "ff": "core_latency_ff.txt"}


def pair_target_file(disc, corner):
    """the kit's planned core clock-pin earliness file for this corner, or None (COORD 2026-10-28 21:33 rule 2: skew =
    arrival minus planned target).  Only a kit with early core taps has one: config.mk exports OT_CORE_LAT (gen_phys:
    tap_balance plans core pins to effective = pin + L) and the corner file is a signed mean contract
    (core_latency.txt TT / core_latency_ff.txt FF, header PAIR_TARGET_HEADER; the legacy ETM_MAX_BOUND diagnostic is not
    a target).  SS / no kit / no table -> None (pin-arrival skew only, session unchanged)."""
    kit = disc.get("kit")
    name = PAIR_TARGET_FILES.get(corner)
    if not kit or not name:
        return None
    cfg, f = Path(kit) / "config.mk", Path(kit) / name
    if not cfg.is_file() or not re.search(r"^export OT_CORE_LAT\s*=", cfg.read_text(), re.M) or not f.is_file():
        return None
    lines = f.read_text().splitlines()
    if not lines or not lines[0].startswith(PAIR_TARGET_HEADER):
        return None
    return f


def _pair_checks(kv, prefix):
    checks = {}
    for dly in ("max", "min"):
        d = _kvlist(kv.get(f"{prefix}{dly}"))
        if not d:
            continue
        checks[dly] = dict(n=_f(d.get("n")), worst_abs_ps=_f(d.get("worst")), bounded=d.get("bounded") == "1",
                           worst_signed_ps=_f(d.get("signed")), worst_launch=d.get("launch"),
                           worst_capture=d.get("capture"), worst_crpr_ps=_f(d.get("crpr")),
                           p99_raw_ps=_f(d.get("p99_raw")), searched=_f(d.get("searched")),
                           nopath=_f(d.get("nopath")), verify_ps=_f(d.get("verify")))
    return checks


def pair_skew_result(kv):
    """the SO PAIR_* lines of a corner session (pair_skew.tcl ot_ps_measure): per check (max = setup, min = hold) the
    EXHAUSTIVE related-pair count, the worst CPPR-credited damage (setup: launch late vs capture early; hold: capture
    late vs launch early; = the die_sta.py pair skew), whether it is exact or a bound, and the uncredited p99.
    With a target file (PAIR_TGT_* lines, pair_target_file) 'checks' is the TARGET-RELATIVE measurement the gate reads
    (effective arrival = pin arrival + planned core earliness L; skew + L_capture - L_launch) and the pin-arrival one
    moves to 'checks_pin_arrival' (information); without one the record is unchanged."""
    checks = _pair_checks(kv, "PAIR_")
    cnt = {k: _f(v) for k, v in _kvlist(kv.get("PAIR_COUNTS")).items()}
    out = dict(done=kv.get("PAIR_DONE") == "1", checks=checks, counts=cnt, method=kv.get("PAIR_METHOD"), seconds=_f(kv.get("PAIR_SECONDS")),
               measurement="every same-clock register pair with a timing fan-in relation (exhaustive); worst "
                           "damage CPPR-credited from the pair's own path end (exact unless bounded); p99 uncredited",
               tsv="pair_skew.tsv")
    if "PAIR_TARGETS" in kv:
        tgt = _pair_checks(kv, "PAIR_TGT_")
        out.update(checks=tgt, checks_pin_arrival=checks, basis="target_relative",
                   targets={k: _f(v) for k, v in _kvlist(kv.get("PAIR_TARGETS")).items()},
                   basis_note="gate = arrival minus planned target: effective arrival = pin arrival + planned core "
                              "earliness L (kit core_latency file), skew + (L_capture - L_launch), CPPR unchanged; "
                              "checks_pin_arrival = raw pin arrivals (information)")
    return out


def run_corner(corner, disc, out, image=IMAGE, docker="sudo docker", dry=False, ff_vclk="sdc", droop=None):
    od = Path(out) / corner
    od.mkdir(parents=True, exist_ok=True)
    mlibs, mmiss = macro_libs(disc["kit"], corner)
    mounts = [("base", disc["base"]), ("sdc", str(od / "sdcdir")), ("out", str(od))]
    (od / "sdcdir").mkdir(exist_ok=True)
    (od / "sdcdir" / "golden.sdc").write_text(Path(disc["sdc"]).read_text())
    libconfig = Path(disc["library_config"]) if disc.get("library_config") else (Path(disc["kit"]) / "config.mk" if disc.get("kit") else None)
    if libconfig is None or not libconfig.is_file():
        raise ValueError("signoff: exact corner libraries require --kit/config.mk or explicit --library-config")
    mounts.append(("work", disc.get("kit") or str(libconfig.parent)))
    mounts.append(("work/config.mk", str(libconfig)))
    core_overlay = copy_core_tap_overlay(Path(disc["sdc"]), od / "sdcdir")
    ptf = pair_target_file(disc, corner)
    if ptf is not None:
        shutil.copyfile(ptf, od / "sdcdir" / "pair_targets.txt")
    ml_ctr = []
    lctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text()) if disc.get("sdc_lint_ctx") else {}
    ftd = json.loads(Path(disc["ft_ports"]).read_text()) if disc.get("ft_ports") else None
    (od / "session.tcl").write_text(session_tcl(corner, ml_ctr, disc["spef"], odb=Path(disc["odb"]).name, ff_vclk=ff_vclk,
                                                ft_decl=ftd,
                                                ff_bound_ps=disc.get("ff_bound_ps"),
                                                hold_in_min=lctx.get("hold_in_min_ps"),
                                                hold_out_min=lctx.get("hold_out_min_ps"),
                                                hold_in_min_ports=lctx.get("hold_in_min_ports_ps"), core_taps_ff=core_overlay,
                                                hold_out_min_ports=lctx.get("hold_out_min_ports_ps"),
                                                tap_window=lctx.get("tap_window_ps"),
                                                droop=droop if corner == "tt" else None,
                                                pair_targets=ptf is not None,
                                                fwd_ring=fwd_ring_inputs(Path(disc["sdc"]).read_text())))
    vol = " ".join(f"-v {shlex.quote(h)}:/{c}" + ("" if c == "out" or c == "sdc" else ":ro") for c, h in mounts)
    cmd = (f"{docker} run --rm --name so_{os.getpid()}_{corner}_{abs(hash(disc['base'])) % 100000} {vol} {image} "
           f"{OPENROAD} -no_init -exit /out/session.tcl")
    (od / "cmd.sh").write_text(cmd + "\n")
    if dry:
        return dict(corner=corner, cmd=cmd, macro_libs=mlibs, macro_missing=mmiss)
    with open(od / "sta.log", "w") as lf:
        rc = subprocess.call(cmd, shell=True, stdout=lf, stderr=subprocess.STDOUT)
    text = (od / "sta.log").read_text(errors="replace")
    res = corner_result(parse_session(text))
    res.update(corner=corner, rc=rc, macro_libs=mlibs, macro_missing=mmiss,
               errors=re.findall(r"\[ERROR[^\n]*", text)[:5])
    if ftd:
        res["ft_arcs"] = ft_parse(text)
    res["clock_endpoint_coverage"] = consumed_clock_model_coverage(od / "libraries.json", disc,
        res.get("clock_endpoint_masters"), res.get("clock_endpoint_mapping_errors"))
    (od / "corner.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


# ---- record checks -------------------------------------------------------------------------------------------------
def route_counts(disc):
    """DRC / antenna counts from the ORFS route metrics, else the gate record, else the DRC report."""
    r = dict(drc=None, antenna_nets=None, drc_source=None, antenna_source=None)
    mp = disc["metrics"].get("5_2_route.json")
    if mp:
        m = json.loads(Path(mp).read_text())
        if "detailedroute__route__drc_errors" in m:
            r["drc"], r["drc_source"] = int(m["detailedroute__route__drc_errors"]), "5_2_route.json"
        if "detailedroute__antenna__violating__nets" in m:
            r["antenna_nets"] = int(m["detailedroute__antenna__violating__nets"])
            r["antenna_source"] = "5_2_route.json"
    if r["drc"] is None and disc.get("record"):
        rec = json.loads(Path(disc["record"]).read_text())
        for k in ("drc", "drc_errors", "route_drc"):
            if isinstance(rec.get(k), (int, float)):
                r["drc"], r["drc_source"] = int(rec[k]), f"record:{k}"
        for k in ("antenna", "antenna_nets", "antenna_violating_nets"):
            if isinstance(rec.get(k), (int, float)):
                r["antenna_nets"], r["antenna_source"] = int(rec[k]), f"record:{k}"
    if r["drc"] is None and disc.get("drc_rpt"):
        txt = Path(disc["drc_rpt"]).read_text(errors="replace")
        r["drc"], r["drc_source"] = len(re.findall(r"violation type", txt)), "5_route_drc.rpt"
    return r


def run_sdc_lint(disc, ports):
    import sdc_lint
    text = Path(disc["sdc"]).read_text()
    if disc.get("sdc_lint_ctx"):
        ctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text())
        mode = "kit sdc_lint.json"
    else:
        ins = INSERTION_PS
        m = re.search(r"set_clock_latency\s+-source\s+([0-9.]+)", text)
        if m:
            ins = float(m.group(1))
        ctx = dict(period_ps=PERIOD_PS, insertion_ps=ins, insertion_tol_ps=INSERTION_TOL_PS,
                   clock_ports=ports["clock_ports"], inputs=ports["inputs"], outputs=ports["outputs"],
                   unc_setup_ps=UNC_SETUP_PS, unc_hold_ps=UNC_HOLD_PS, time_unit_ps=1.0)
        mode = "derived (plan period 833, insertion from SDC vclk latency, tol 40, 60/25)"
    if disc.get("ft_ports"):                  # 12.2a1: the characterised kit interface model must carry every arc
        ctx["ft_ports"] = json.loads(Path(disc["ft_ports"]).read_text())
        ctx["ft_interface"] = disc.get("ft_interface_model")
        ctx["ft_require_characterised"] = True
    try:
        err = sdc_lint.lint(text, **ctx)
    except Exception as e:                    # parser limits are a FAIL with the reason, never a pass
        err = [f"sdc_lint could not evaluate the SDC: {e}"]
    return dict(verdict="PASS" if not err else "FAIL", mode=mode, errors=err[:40], n_errors=len(err),
                sdc=disc["sdc"], sdc_source=disc["sdc_source"])


def boundary_controls(disc):
    """Read a generated core's typed control contract; never exempt data pins."""
    if not disc.get("kit"):
        return [], None
    manifest = Path(disc["kit"]) / "boundary_guard_context.json"
    if not manifest.is_file():
        return [], None
    ctx = json.loads(manifest.read_text())
    if ctx.get("schema") != "opentallas.core_boundary_guard_context.v1":
        raise ValueError("unsupported boundary guard context schema")
    if ctx.get("data_pin_exemptions") != []:
        raise ValueError("boundary context cannot exempt data pins")
    source = Path(ctx["source_core_json"])
    if not source.is_absolute():
        source = manifest.parent / source
    roles = json.loads(source.read_text()).get("boundary_role")
    if not isinstance(roles, dict):
        raise ValueError("source core metadata lacks typed boundary_role map")
    controls = []
    for field, role in (("clock_ports", "clk"), ("unused_clock_ports", "clk_unused"), ("reset_ports", "reset")):
        ports = ctx.get(field, [])
        if not isinstance(ports, list) or any(not isinstance(x, str) or not x or "\n" in x for x in ports):
            raise ValueError(f"invalid {field} in boundary context")
        for port in ports:
            if port in controls or roles.get(port) != role:
                raise ValueError(f"boundary role mismatch or duplicate: {port} expected {role}")
            controls.append(port)
    return controls, dict(manifest=str(manifest), source_core_json=str(source), controls=controls)


def hard_core_latency_contract(disc):
    """the kit's typed hard-core clock contract (boundary_guard_context.json -> core.json clock_contract), or None.
    Only kind 'hard_core_latency' is recognised: the core publishes its measured insertion instead of meeting the
    partition-tap target (COORD 10-24)."""
    if not disc.get("kit"):
        return None
    manifest = Path(disc["kit"]) / "boundary_guard_context.json"
    if not manifest.is_file():
        return None
    ctx = json.loads(manifest.read_text())
    source = Path(ctx.get("source_core_json", ""))
    if not source.is_absolute():
        source = manifest.parent / source
    if not source.is_file():
        return None
    cc = json.loads(source.read_text()).get("clock_contract")
    if not isinstance(cc, dict) or cc.get("kind") != "hard_core_latency":
        return None
    if cc.get("io_reference_ps") is not None:
        import core_io_reference as CIR
        reference = CIR.load(disc["kit"])
        errors = CIR.binding_errors(disc["kit"], reference)
        if errors:
            raise ValueError("inconsistent typed core IO reference: " + "; ".join(errors))
    return cc


def run_face_guard(disc, clock_ports=(), library_receipt=None):
    import face_guard
    if not disc.get("synth"):
        return dict(verdict="NOT RUN", reason="no synthesized netlist (1_synth.v / 1_2_yosys.v) in the routed base")
    pins = json.loads(Path(disc["pins"]).read_text()) if disc.get("pins") else None
    if isinstance(pins, dict):
        pins = pins.get("pins")
    if pins is not None and not (isinstance(pins, list) and pins and isinstance(pins[0], dict) and "bus" in pins[0]):
        pins = None
    try:
        typed_controls, context = boundary_controls(disc)
    except Exception as e:
        return dict(verdict="FAIL", reason=f"invalid boundary control context: {e}", fail_counts={"context": 1})
    skip = sorted(set(clock_ports) | set(typed_controls) | {"arst_n", "rst_n"})
    # HBM-CORES-KITS-28 10-30: the guard matches PORT names (bus roots), while STA reports a clock bus by its bits
    # (clk_pair[0], clk_pair[1]); exempt the root only when every bit of that bus is a clock port (never a data bit).
    clock_bits = {}
    for c in clock_ports:
        m = re.fullmatch(r"(.+)\[(\d+)\]", c)
        if m:
            clock_bits.setdefault(m.group(1), set()).add(int(m.group(2)))
    for root, bits in clock_bits.items():
        bus_bits = {x.get("bit") for x in (pins or []) if x.get("bus") == root}
        if bus_bits and bus_bits <= bits:
            skip = sorted(set(skip) | {root})
    # 12.2a1 (COORD 10-26 12:55): declared die-timed ft ports (kit ft_ports.json) are not core IO, so not face registers;
    # their structure (port -> fixed BUF -> port) is checked by the kit's own ft gate (KV core_preflight island_ft)
    ftp = Path(disc["kit"]) / "ft_ports.json" if disc.get("kit") else None
    if ftp is not None and ftp.is_file():
        skip = sorted(set(skip) | {p["name"] for p in json.loads(ftp.read_text()).get("ports", [])})
    # Keep the guard's canonical clock/reset contract (including registered wavefront rst_o_<k>
    # controls). Supplying the native-clock override must not turn reset-tree fanout into a data-face failure.
    skip_re = r"(?:" + face_guard.SKIP_RE + r")|^(?:" + "|".join(re.escape(x) for x in skip) + r")$"
    if pins is not None:                      # the clock / reset pins are not face registers
        pins = [x for x in pins if not re.match(skip_re, str(x.get("bus")))]
    ft_file = Path(disc["kit"]) / "ft_stations.txt" if disc.get("kit") else (
        Path(disc["pins"]).with_name("ft_stations.txt") if disc.get("pins") else None)
    try:
        ft1 = face_guard.read_ft1(ft_file) if ft_file and ft_file.is_file() else set()
        # OWNER 10-25 option B: declared ID straps (kit straps.json / core.json id_strap) need no pin register
        sl = face_guard.kit_strap_list(disc["kit"]) if disc.get("kit") else []
        # QK-CORES-5 10-27: declared proven-dead inputs (kit dead_inputs.json + proof receipt), verified unloaded
        dl = face_guard.kit_dead_list(disc["kit"]) if disc.get("kit") else []
        # S81-CORE-LAT-R21: declared landing-ring slots (kit land_slots.json), as the kit face_guard_core / CLI pass them
        lf = Path(disc["kit"]) / "land_slots.json" if disc.get("kit") else None
        land = face_guard.kit_land(lf) if lf is not None and lf.is_file() else None
        pad_clocks, native_clock_pins = face_guard.kit_pad_clocks(disc['kit'], library_receipt) if disc.get('kit') else ([], set())
        exports = face_guard.sdc_clock_exports(Path(disc['sdc']).read_text()) if pad_clocks else []
        r = face_guard.guard(Path(disc["synth"]).read_text(errors="replace"), pins=pins, skip_re=skip_re, ft1=ft1,
                             straps=sl, dead=dl, land=land, exports=exports,
                             pad_clocks=pad_clocks, native_clock_pins=native_clock_pins,
                             clocks=[p['name'] for p in pad_clocks if p['dir'] == 'in'])
    except Exception as e:
        return dict(verdict="NOT RUN", reason=f"face_guard error: {e}", netlist=disc["synth"])
    return dict(verdict=r["verdict"], top=r.get("top"), checked=r.get("checked"), ok=r.get("ok"),
                fail_counts=r.get("fail_counts"), fails={k: v[:5] for k, v in (r.get("fails") or {}).items()},
                dead_declared=r.get("dead_declared", []),
                netlist=disc["synth"], pins=disc.get("pins"), boundary_context=context,
                one_station_ft_slots=sorted(ft1))


# ---- verdict -------------------------------------------------------------------------------------------------------
FF_REF_TOL_PS = 10.0   # COORD 10-25 (GEOM-REVIEW-3 HBM argmax la1/s2f2): FF IO latency == TT vs measured FF mean


def ff_reference_problem(rec, cff, requested):
    """COORD 10-25: FF hold must be timed against a per-corner FF insertion reference, never silently against the
    kit SDC's single (TT) IO vclk latency.  HBM argmax la1/s2f2 signed FF hold vs 250 ps while its routed FF
    pin-register mean was 198.4 ps (-27.8 reported, ~+24 real).  -> 'FAIL_SIGNOFF ff_ref_missing: ...' or None.
      * ff_vclk 'sdc' (no rebind / pin-flop-mean reference) and no per-corner FF bound -> FAIL;
      * a FF bound equal to the TT value while the measured FF pin-register mean differs from it by > 10 ps -> FAIL."""
    pol = rec.get("policy", {})
    b = pol.get("insertion_bound") or {}
    ffm = (cff.get("insertion_pinflops") or {}).get("mean")
    if requested == "bound-ff":
        if pol.get("ff_vclk_bound_ps") is None:
            return "FAIL_SIGNOFF ff_ref_missing: bound-ff requested without a declared FF insertion"
        return None
    if requested == "sdc" and b.get("ff") is None:
        return ("FAIL_SIGNOFF ff_ref_missing: no per-corner FF insertion reference (ff_vclk sdc: FF hold timed against "
                "the single SDC/TT IO vclk latency" + (f"; measured FF pin-register mean {ffm:.1f} ps" if ffm is not None
                                                       else "") + "); regenerate the kit with the per-corner binding")
    if b.get("ff") is not None and b.get("tt") is not None and abs(float(b["ff"]) - float(b["tt"])) < 0.5 \
            and ffm is not None and abs(ffm - float(b["ff"])) > FF_REF_TOL_PS:
        return (f"FAIL_SIGNOFF ff_ref_missing: FF IO latency {float(b['ff']):g} ps equals the TT value while the measured "
                f"FF pin-register mean is {ffm:.1f} ps (> {FF_REF_TOL_PS:g} ps apart)")
    return None


def timing_modes_check(kit, ff_bound_ps=None):
    """SIGNOFF-MODES-2: kit_modes.signoff_record on the kit; None when there is no kit config.mk (die-level record /
    re-evaluation away from the kit) or the kit predates the per-corner binding.  Missing helper -> FAIL (re-bundle)."""
    if not kit or not (Path(kit) / "config.mk").is_file():
        return None
    try:
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        import kit_modes
    except ImportError as e:
        return dict(verdict="FAIL", reason=f"kit_modes.py missing next to signoff.py ({e}): re-bundle the kit")
    r = kit_modes.signoff_record(kit, ff_bound_ps)
    return r if r.get("applicable", True) else None


ROUTED_NETLIST = re.compile(r"(^6_|final|route)", re.I)


def lec_superset_problems(receipts):
    """COORD RULING HBM-CORE-LAT-R4 (3) / R5 collar: OT_LEC_SUPERSET_VEC=1 is accepted only with a per-run list of the
    extra kept gate bits shown unobservable (lec.py superset_vec in lec.json), and the routed LEC must pass the same
    flag explicitly.  receipts: [(path, lec.json dict)] of one kit.  -> None when no receipt used the flag (no
    obligation), else the list of problems ([] = PASS)."""
    used = [(p, r) for p, r in receipts if isinstance(r, dict) and (r.get("superset_vec") or {}).get("enabled")]
    if not used:
        return None
    probs = []
    for p, r in used:
        sv = r["superset_vec"]
        bits = sv.get("extra_bits")
        if r.get("verdict") != "EQUIVALENT":
            probs.append(f"{p}: verdict {r.get('verdict')}")
        if not isinstance(bits, list) or sv.get("n_extra") != len(bits) or \
                any(not isinstance(e, dict) or "shown" not in e for e in bits):
            probs.append(f"{p}: no per-bit superset_vec.extra_bits list (lec.py before ROOT-MERGE-30)")
            continue
        bad = [e.get("bit") for e in bits if not e["shown"]]
        if bad or not sv.get("all_shown"):
            probs.append(f"{p}: {len(bad)} extra bit(s) not shown unobservable (first: {', '.join(map(str, bad[:4]))})")
    routed = [(p, r) for p, r in receipts if isinstance(r, dict) and
              ROUTED_NETLIST.search(Path(str(r.get("netlist") or "")).name)]
    if not routed:
        probs.append("no routed-netlist LEC receipt (lec.json whose netlist is 6_*.v / *final* / *route*)")
    for p, r in routed:
        if not (r.get("superset_vec") or {}).get("enabled"):
            probs.append(f"{p}: routed LEC did not pass OT_LEC_SUPERSET_VEC=1 explicitly")
    return probs


def kit_lec_receipts(kit):
    """[(path, dict)] of KIT/lec.json and KIT/*/lec.json (lec, lec_post, lec_routed, ...); unreadable ones as None."""
    out = []
    if not kit or not Path(kit).is_dir():
        return out
    for p in sorted([Path(kit) / "lec.json"] + list(Path(kit).glob("*/lec.json"))):
        if p.is_file():
            try:
                out.append((str(p), json.loads(p.read_text())))
            except (OSError, ValueError):
                out.append((str(p), None))
    return out


def evaluate(rec, insertion_target=None):
    """fills rec['checks'] and rec['verdict'] / rec['reasons'] from rec['corners'] + record checks."""
    C = rec.get("corners", {})
    ch = {}

    def ok_corner(c):
        x = C.get(c)
        return x is not None and x.get("done")

    def put(name, verdict, **kw):
        ch[name] = dict(verdict=verdict, **kw)

    # setup TT (the sign-off corner, AGENTS.md 2026-10-24)
    requested = rec.get("policy", {}).get("ff_vclk", "sdc")
    if requested == "rebind" and ok_corner("tt") and C["tt"].get("std_wns_max") is not None:
        w = C["tt"]["std_wns_max"]
        ref = C["tt"].get("ff_vclk_reference") or ""
        v = ("PASS" if w >= 0 else "FAIL") if ref.startswith("applied mode pin_flop_mean ") else "NOT RUN"
        put("setup_tt", v, wns_ps=w, tns_ps=C["tt"].get("std_tns_max"), violators=C["tt"].get("std_nviol_max"),
            sdc_wns_ps=C["tt"].get("sdc_wns_max"), vclk_reference=ref,
            reason=None if v != "NOT RUN" else "TT vclk rebind to the routed pin-register mean unavailable")
    elif ok_corner("tt") and C["tt"].get("sdc_wns_max") is not None:
        w = C["tt"]["sdc_wns_max"]
        put("setup_tt", "PASS" if w >= 0 else "FAIL", wns_ps=w, tns_ps=C["tt"].get("sdc_tns_max"),
            violators=C["tt"].get("sdc_nviol_max"))
    else:
        put("setup_tt", "NOT RUN")
    # hold FF (standard overlay)
    if ok_corner("ff") and C["ff"].get("std_wns_min") is not None:
        w = C["ff"]["std_wns_min"]
        ov = C["ff"].get("overlay") or ""
        v = "PASS" if w >= 0 else "FAIL"
        # STD_* is printed even when the overlay could not be applied. In that
        # case it is only another raw-SDC measurement, not boundary-hold proof.
        reference = C["ff"].get("ff_vclk_reference")
        reference_ok = (requested == "sdc" or (reference or "").startswith("applied mode pin_flop_mean ")
                        or (requested == "bound-ff" and (reference or "").startswith("applied mode bound_ff ")))
        if not ov.startswith("applied ") or not reference_ok:
            v = "NOT RUN"
        why = None if v != "NOT RUN" else "standard boundary-hold overlay was not applied or requested FF clock reference was unavailable"
        ffr = ff_reference_problem(rec, C["ff"], requested)
        if ffr:
            v, why = "FAIL", ffr
        put("hold_ff", v, wns_ps=w, tns_ps=C["ff"].get("std_tns_min"), violators=C["ff"].get("std_nviol_min"),
            sdc_wns_ps=C["ff"].get("sdc_wns_min"), overlay=ov, ff_vclk_reference=reference, reason=why)
    else:
        put("hold_ff", "NOT RUN")
    if ok_corner("ss"):
        put("ss", "REPORT", setup_wns_ps=C["ss"].get("sdc_wns_max"), hold_wns_ps=C["ss"].get("std_wns_min"),
            slew_viol=C["ss"].get("slew_viol"), cap_viol=C["ss"].get("cap_viol"),
            label="SS: information only, never gates (AGENTS.md 2026-10-24)")
    # DRV at the sign-off corners
    done = [c for c in CORNERS if ok_corner(c)]
    if len(done) == len(CORNERS):
        bad = {c: dict(slew=C[c].get("slew_viol"), cap=C[c].get("cap_viol")) for c in done
               if (C[c].get("slew_viol") or 0) > 0 or (C[c].get("cap_viol") or 0) > 0
               or C[c].get("slew_viol") is None or C[c].get("cap_viol") is None}
        put("drv", "FAIL" if bad else "PASS", by_corner={c: dict(slew=C[c].get("slew_viol"), cap=C[c].get("cap_viol"))
                                                         for c in done}, failing=bad)
        fo = {c: C[c].get("fanout_viol") for c in done}
        put("fanout", "WARN" if any((v or 0) > 0 for v in fo.values()) else "PASS", limit=FANOUT_MAX,
            violators=fo, max_fanout=C[done[0]].get("fanout_max"), worst_net=C[done[0]].get("fanout_worst_net"))
        cs = C["tt"]["check_setup"]
        bad = {k: v for k, v in cs.items() if v and k in ("unconstrained", "unclocked", "loops")}
        put("unconstrained", "FAIL" if bad else "PASS", counts=cs)
    else:
        put("drv", "NOT RUN", corners_done=done)
        put("fanout", "NOT RUN")
        put("unconstrained", "NOT RUN")
    # clock
    if all(ok_corner(c) for c in SPREAD_CORNERS):
        sp, why = {}, []
        for c in [x for x in ALL_CORNERS if ok_corner(x)]:
            pf = C[c].get("insertion_pinflops")
            sp[c] = dict(pinflops=pf, all=C[c].get("insertion_all"), ck_errors=C[c].get("ck_errors"),
                         pair_skew=C[c].get("pair_skew"))
        for c in SPREAD_CORNERS:
            pf = C[c].get("insertion_pinflops")
            if not pf:
                why.append(f"{c.upper()}: no pin flops measured")
            ps = C[c].get("pair_skew") or {}
            checks = ps.get("checks", {})
            if not ps.get("done") or any(k not in checks for k in ("max", "min")):
                why.append(f"{c.upper()}: related pair skew NOT RUN")
            else:
                na = (ps.get("counts") or {}).get("no_clock_arrival") or 0
                if na > 0:
                    why.append(f"{c.upper()}: {int(na)} registers without a unique propagated clock arrival are "
                               f"missing from the related pair skew")
                for k, value in checks.items():
                    n, worst = value.get("n"), value.get("worst_abs_ps")
                    side = "setup" if k == "max" else "hold"
                    if not n or worst is None or not math.isfinite(worst):
                        why.append(f"{c.upper()} {side}: no finite related pair measurement")
                    elif worst > PAIR_SKEW_MAX_PS:
                        why.append(f"{c.upper()} {side} related pair skew {worst:.1f} ps > {PAIR_SKEW_MAX_PS:g} "
                                   f"({value.get('worst_launch')} -> {value.get('worst_capture')}"
                                   f"{', bound' if value.get('bounded') else ''})")
                    if (value.get("verify_ps") or 0.0) > PAIR_VERIFY_TOL_PS:
                        why.append(f"{c.upper()} {side}: pair skew path/arrival cross-check differs by "
                                   f"{value['verify_ps']:.2f} ps > {PAIR_VERIFY_TOL_PS:g} (measurement suspect)")
            if (C[c].get("ck_errors") or 0) > 0:
                why.append(f"{c.upper()}: {int(C[c]['ck_errors'])} register clock pins without a unique clock arrival")
        bound = dict(rec.get("policy", {}).get("insertion_bound") or {})
        if insertion_target is not None:
            bound["tt"] = insertion_target
        tol = float(bound.get("tol", INSERTION_TOL_PS))
        for c in ("tt", "ff"):          # FLOW 10-25: the routed I of each corner within tol of the bound I
            if bound.get(c) is None:
                continue
            pf = C[c].get("insertion_pinflops")
            if not pf:
                continue
            if abs(pf["mean"] - float(bound[c])) > tol:
                why.append(f"{c.upper()} pin-flop insertion {pf['mean']:.1f} ps not within bound {float(bound[c]):g} +- "
                           f"{tol:g}")
        raw_clock_verdict = "FAIL" if why else "PASS"
        coverage = {c: C[c]["clock_endpoint_coverage"] for c in SPREAD_CORNERS if C[c].get("clock_endpoint_coverage")}
        unqualified = {c: value for c, value in coverage.items() if value.get("verdict") != "PASS"}
        if unqualified:
            why.extend(f"{c.upper()}: expanded child-flop pair coverage NOT RUN ({value.get('status')})"
                       for c, value in unqualified.items())
        put("clock", "NOT RUN" if unqualified else ("FAIL" if why else "PASS"),
            endpoint_model_coverage=coverage, raw_clock_verdict=raw_clock_verdict,
            raw_pair_basis="visible_clock_pins", pair_skew_max_ps=PAIR_SKEW_MAX_PS, spread_info_only=True,
            by_corner=sp, problems=why,
            insertion_target_ps=insertion_target, insertion_bound=bound or None)
    else:
        put("clock", "NOT RUN")
    # macro liberty coverage (part of setup/hold validity)
    mm = {c: C[c].get("macro_missing") for c in done if C[c].get("macro_missing")}     # sign-off corners only
    if mm:
        put("macro_libs", "FAIL", missing=mm)
    for k in ("sdc_lint", "face_guard"):
        ch[k] = rec.get(k) or dict(verdict="NOT RUN")
    rc = rec.get("route") or {}
    put("drc", "NOT RUN" if rc.get("drc") is None else ("PASS" if rc["drc"] == 0 else "FAIL"),
        count=rc.get("drc"), source=rc.get("drc_source"))
    put("antenna", "NOT RUN" if rc.get("antenna_nets") is None else ("PASS" if rc["antenna_nets"] == 0 else "FAIL"),
        count=rc.get("antenna_nets"), source=rc.get("antenna_source"))
    # FLOW 10-26 PG: supply binding of the signed ODB (census in every corner session; NOT RUN blocks too)
    pgc = {c: C[c] for c in ("tt", "ff") if ok_corner(c)}
    if not pgc or any(x.get("pg_open") is None or not x.get("pg_terms") for x in pgc.values()):
        put("pg", "NOT RUN", reason="no PG census in the corner sessions")
    else:
        n = max(int(x["pg_open"]) for x in pgc.values())
        put("pg", "PASS" if n == 0 else "FAIL", open_terms=n, pg_terms=int(max(x["pg_terms"] for x in pgc.values())),
            first=next((x.get("pg_first_open") for x in pgc.values() if x.get("pg_first_open")), None))
    reasons = []
    fm = rec.get("ft_interface")
    if fm is not None:                        # 12.2a1 declared ft arcs (only kits with ft_ports.json)
        import sdc_lint
        e = sdc_lint.ft_model_errors(fm.get("declaration") or {}, fm.get("model"), require_characterised=True)
        put("ft_interface", "FAIL" if e else "PASS", errors=e[:10], model=fm.get("path"),
            arcs=(fm.get("model") or {}).get("arcs"))
    # OT_LEC_SUPERSET_VEC obligation (only kits whose LEC receipts used the flag; re-read on every evaluation, so a
    # 'verdict' re-run sees a routed LEC finished after the corner sessions)
    lp = lec_superset_problems(kit_lec_receipts((rec.get("inputs") or {}).get("kit")))
    if lp is not None:
        put("lec_superset", "FAIL" if lp else "PASS", problems=lp[:10])
    # SIGNOFF-MODES-2 10-27: one timing mode per corner (kit_modes.py, re-read like lec_superset): kit binding
    # config.mk OT_VCLK_TT == constraint.sdc vclk == sdc_lint insertion_ps, OT_VCLK_FF == insertion_ff_ps == the
    # bound-ff value this record timed FF hold against.  A wrong-mode flow step is an advisory, not a FAIL.
    tm = timing_modes_check((rec.get("inputs") or {}).get("kit"), (rec.get("policy") or {}).get("ff_vclk_bound_ps"))
    if tm is not None:
        put("timing_modes", tm.get("verdict", "NOT RUN"), **{k: v for k, v in tm.items() if k != "verdict"})
    for k in BLOCKING + (("macro_libs",) if "macro_libs" in ch else ()) + (("ft_interface",) if "ft_interface" in ch else ()) + \
            (("lec_superset",) if "lec_superset" in ch else ()) + (("timing_modes",) if "timing_modes" in ch else ()):
        v = ch[k]["verdict"]
        if v != "PASS":
            reasons.append(f"{k}: {v}" + _detail(k, ch[k]))
    rec["checks"] = ch
    rec["reasons"] = reasons
    rec["verdict"] = "SIGNED" if not reasons else "NOT SIGNED"
    # Option-A local closure is provisional until its actual assembled parent
    # proves all assumed input ports. Legacy records take the identical path.
    ctx_file = (rec.get('inputs') or {}).get('sdc_lint_ctx')
    a_context = bool(ctx_file and Path(ctx_file).is_file() and
                     json.loads(Path(ctx_file).read_text()).get('hold_in_min_ports_ps'))
    if rec.get('io_hold') or a_context:
        from io_hold_qualification import apply_obligation
        apply_obligation(rec)
    return rec


def _detail(k, c):
    if k in ("setup_tt", "hold_ff") and c.get("wns_ps") is not None:
        r = f"; {c['reason']}" if k == "hold_ff" and str(c.get("reason") or "").startswith("FAIL_SIGNOFF") else ""
        return f" WNS {c['wns_ps']:+.2f} ps, {int(c.get('violators') or 0)} endpoints{r}"
    if k == "drv" and c.get("failing"):
        return " " + ", ".join(f"{x.upper()} slew {v['slew']} cap {v['cap']}" for x, v in c["failing"].items())
    if k == "unconstrained" and c.get("counts"):
        return " " + ", ".join(f"{a} {b}" for a, b in c["counts"].items() if b)
    if k == "clock" and c.get("problems"):
        return " " + "; ".join(c["problems"])
    if k == "sdc_lint" and c.get("n_errors"):
        return f" {c['n_errors']} errors (first: {c['errors'][0]})"
    if k == "face_guard":
        if c.get("fail_counts"):
            return f" {c['fail_counts']}"
        if c.get("reason"):
            return f" ({c['reason']})"
    if k in ("drc", "antenna") and c.get("count") is not None:
        return f" {c['count']} ({c.get('source')})"
    if k == "macro_libs":
        return f" {c.get('missing')}"
    if k == "lec_superset" and c.get("problems"):
        return " " + "; ".join(c["problems"][:3])
    if k == "pg" and c.get("open_terms"):
        return f" {c['open_terms']} of {c.get('pg_terms')} supply terminals unbound (first {c.get('first')})"
    return ""


def summary_line(rec):
    C = rec.get("checks", {})

    def g(k, f):
        return (C.get(k) or {}).get(f)
    pf, ps = {}, {}
    for c in ("tt", "ff"):
        x = ((((C.get("clock") or {}).get("by_corner") or {}).get(c) or {}).get("pinflops") or {})
        pf[c] = x.get("spread")
        ck = (((((C.get("clock") or {}).get("by_corner") or {}).get(c) or {}).get("pair_skew") or {}).get("checks") or {})
        w = [v.get("worst_abs_ps") for v in ck.values() if v.get("worst_abs_ps") is not None]
        ps[c] = max(w) if w else float("nan")
    return (f"{rec.get('name')}: {rec.get('verdict')} | TT setup {g('setup_tt', 'wns_ps')} | FF hold "
            f"{g('hold_ff', 'wns_ps')} (sdc {g('hold_ff', 'sdc_wns_ps')}) | SS setup (info) {g('ss', 'setup_wns_ps')} | "
            f"pair skew TT/FF {ps['tt']:.1f}/{ps['ff']:.1f} (spread info {pf['tt']}/{pf['ff']}) | DRC {g('drc', 'count')} ant {g('antenna', 'count')} | "
            f"sdc_lint {g('sdc_lint', 'verdict')} face_guard {g('face_guard', 'verdict')}")


# ---- CLI -----------------------------------------------------------------------------------------------------------
def cmd_run(a):
    base = Path(a.base).resolve() if a.base else find_base(a.run_dir)
    disc = discover(base, kit=a.kit, sdc=a.sdc, record=a.record)
    if not disc["sdc"]:
        raise SystemExit("signoff: no SDC (kit constraint.sdc / 6_final.sdc / --sdc)")
    require_signoff_bundle()
    disc["library_config"] = str(Path(a.library_config).resolve()) if getattr(a, "library_config", None) else None
    out = Path(a.out).resolve()
    core_contract = hard_core_latency_contract(disc)
    if core_contract and core_contract.get("io_reference_ps") is not None:
        import core_io_reference as CIR
        CIR.validate_ff_override(core_contract["io_reference_ps"], getattr(a, "ff_bound_ps", None))
    # An explicit source-pinned FF reference applies to every kit family.  Keep
    # it outside the hard-core branch: die-plan kits otherwise reach the FF
    # session with bound-ff selected but no value, despite a valid CLI request.
    if getattr(a, "ff_bound_ps", None) is not None:
        disc["ff_bound_ps"] = float(a.ff_bound_ps)
    bound = None
    if core_contract:
        # COORD ruling 10-24: a hard core carries a core-latency contract -- its measured insertion is published
        # (core.json / the ETM max_clock_tree_path) and the parent tap balance subtracts it (early tap); the plan
        # 250 +- 40 target applies at the PARTITION tap, not inside the core.  Spread / unique-arrival still gate.
        # (ROOT-MERGE2 10-25: no FLOW per-corner insertion binding inside a hard-core contract kit either.)
        if a.insertion_target is not None:
            raise SystemExit("signoff: --insertion-target conflicts with the kit's hard-core latency contract")
        # FLOW-FIX 10-25 (COORD: no silent FF fallback to the SDC/TT vclk): a core kit whose sdc_lint ctx declares the
        # per-corner FF insertion (insertion_ff_ps: HBM / KV / QC core generators, the value the in-flow FF-only GRT
        # hold repair bound) times FF hold against that declared value ('bound-ff'); no rebind, no clock-check bound
        # (ROOT-MERGE2).  Without it the FF hold check FAILs ff_ref_missing.
        if getattr(a, "ff_bound_ps", None) is not None:                # explicit declared value (CLI-checked)
            disc["ff_bound_ps"] = float(a.ff_bound_ps)
        elif disc.get("sdc_lint_ctx"):
            lctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text())
            if lctx.get("insertion_ff_ps") is not None and a.ff_vclk in ("auto", "bound-ff"):
                a.ff_vclk = "bound-ff"
                disc["ff_bound_ps"] = float(lctx["insertion_ff_ps"]) / float(lctx.get("time_unit_ps") or 1.0)
                a.ff_vclk_contract = a.ff_vclk_contract or f"declared core FF insertion {disc['sdc_lint_ctx']}"
    elif disc.get("sdc_lint_ctx"):                                  # die-plan kit: the bound (plan) insertion
        lctx = json.loads(Path(disc["sdc_lint_ctx"]).read_text())
        if a.insertion_target is None:
            a.insertion_target = float(lctx["insertion_ps"])
        if lctx.get("insertion_ff_ps") is not None:                 # FLOW 10-25 per-corner binding
            bound = dict(tt=float(lctx["insertion_ps"]), ff=float(lctx["insertion_ff_ps"]),
                         tol=float(lctx.get("insertion_tol_ps", INSERTION_TOL_PS)), source=disc["sdc_lint_ctx"])
    if a.ff_vclk == "auto":
        a.ff_vclk = "rebind" if bound else "sdc"
        if bound:
            a.ff_vclk_contract = a.ff_vclk_contract or f"kit per-corner insertion binding {bound['source']}"
    out.mkdir(parents=True, exist_ok=True)
    corners = [c for c in a.corners.split(",") if c]
    rec = dict(schema=SCHEMA, name=a.name or disc["design"] or base.name, generated=datetime.datetime.now()
               .astimezone().isoformat(timespec="seconds"), host=os.uname().nodename, inputs=disc,
               policy=dict(period_ps=PERIOD_PS, uncertainty_setup_ps=UNC_SETUP_PS, uncertainty_hold_ps=UNC_HOLD_PS,
                           spread_max_ps=SPREAD_MAX_PS, spread_corners=list(SPREAD_CORNERS),
                           insertion_tol_ps=INSERTION_TOL_PS, fanout_max=FANOUT_MAX,
                           ff_vclk=a.ff_vclk, ff_vclk_contract=a.ff_vclk_contract, insertion_bound=bound,
                           ff_vclk_bound_ps=disc.get("ff_bound_ps"),
                           hold_overlay="set_output_delay -min 0 / set_input_delay -min -40 vs the IO virtual clock",
                           derate="none in the verdict (60/25 ps uncertainty is the OCV+jitter margin); "
                                  "ocv5_* = flat late 1.05 / early 0.95, information only",
                           engine=f"OpenSTA in OpenROAD ({a.image}), one process per corner",
                           libs="Exact routed-kit ORFS make TC/BC_LIB_FILES including macro views; hashed receipt",
                           corner_rule="setup TT / hold FF / 60-25 ps / related pair skew CPPR <= 80 TT+FF; spread INFO; SS information only "
                                       "(owner 2026-10-24, AGENTS.md c7ce2ed69a)"),
               tool_commit=_git_head())
    droop, dinfo = None, None
    if getattr(a, "droop_check", False):
        droop, dinfo = droop_check_tcl(disc)
    with cf.ThreadPoolExecutor(len(corners)) as ex:
        futs = {c: ex.submit(run_corner, c, disc, out, a.image, a.docker, a.dry, a.ff_vclk, droop) for c in corners}
        rec["corners"] = {c: f.result() for c, f in futs.items()}
    if dinfo is not None and "tt" in rec["corners"]:
        tt = rec["corners"]["tt"]
        dinfo.update(nominal_tt_setup_wns_ps=tt.get("std_wns_max"), droop665_tt_setup_wns_ps=tt.get("droop665_wns_max"))
        if tt.get("std_wns_max") is not None and tt.get("droop665_wns_max") is not None:
            dinfo["delta_ps"] = round(tt["droop665_wns_max"] - tt["std_wns_max"], 2)
            dinfo["info_verdict"] = "PASS" if tt["droop665_wns_max"] >= 0 else "FAIL (info: fix at next re-sign)"
        rec["info_droop665"] = dinfo
    if a.dry:
        print(json.dumps(rec["corners"], indent=1))
        return 0
    ports = next((dict(clock_ports=x["clock_ports"], inputs=x["inputs"], outputs=x["outputs"])
                  for x in rec["corners"].values() if x.get("done")), None)
    if disc.get("ft_ports"):
        # 12.2a1 (COORD 10-26 12:55): characterised ft arcs -> the kit interface model (+ a copy with the record)
        import sdc_lint
        decl = json.loads(Path(disc["ft_ports"]).read_text())
        mp = Path(disc["kit"]) / "ft_interface.json"
        model = json.loads(mp.read_text()) if mp.is_file() else None
        if model is not None and not sdc_lint.ft_model_errors(decl, model):
            model = ft_fill_model(decl, model, rec["corners"])
            mp.write_text(json.dumps(model, indent=1) + "\n")
            (out / "ft_interface.json").write_text(json.dumps(model, indent=1) + "\n")
        disc["ft_interface_model"] = model
        rec["ft_interface"] = dict(declaration=decl, model=model, path=str(mp))
    rec["sdc_lint"] = run_sdc_lint(disc, ports) if ports else dict(verdict="NOT RUN", reason="no STA session finished")
    rec["face_guard"] = run_face_guard(disc, (ports or {}).get("clock_ports", ()), out / "tt" / "libraries.json")
    rec["route"] = route_counts(disc)
    evaluate(rec, a.insertion_target)
    if core_contract:
        rec["core_latency"] = dict(contract=core_contract, measured={
            c: rec["corners"][c].get("insertion_pinflops") for c in rec["corners"] if rec["corners"][c].get("done")})
        rec["checks"]["clock"]["core_latency_contract"] = core_contract.get("kind")
    (out / "signoff.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("SIGNOFF " + summary_line(rec))
    for r in rec["reasons"]:
        print(f"  - {r}")
    return 0 if rec["verdict"] == "SIGNED" else 1


def droop_check_tcl(disc, margins_path=None):
    """(Tcl derate text, info dict) of the 12.4a b2 0.665 V re-time: TT class fractions of the shared data droop
    model, wire class from the routed 6_final.v + SPEF (all logic when either is missing: the pessimistic class)."""
    import data_droop as DD
    m = DD.margins(margins_path)
    fr = DD.fracs(m, "class", "TT")
    cls = DD.classify(disc["final_v"], disc["spef"], m) if disc.get("final_v") and disc.get("spef") else None
    info = dict(rule="METHODOLOGY 12.4a b2: INFORMATION only, never a reason; data late derate at 0.665 V, no clock "
                     "derate (shared droop), no hold term, 60 ps uncertainty kept",
                fractions=fr, wire_class=None if cls is None else {k: v for k, v in cls.items() if k != "wire"},
                wire_instances_sample=None if cls is None else cls["wire"][:20])
    return DD.derate_tcl(fr, cls["wire"] if cls else ()), info


def _git_head():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def cmd_verdict(a):
    rec = json.loads(Path(a.record).read_text())
    evaluate(rec, a.insertion_target)
    print("SIGNOFF " + summary_line(rec))
    for r in rec["reasons"]:
        print(f"  - {r}")
    return 0 if rec["verdict"] == "SIGNED" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-dir")
    g.add_argument("--base")
    r.add_argument("--kit")
    r.add_argument("--library-config", help="Explicit exact ORFS library config for no-kit runs; macro paths resolve under its directory")
    r.add_argument("--sdc")
    r.add_argument("--record")
    r.add_argument("--name")
    r.add_argument("--out", required=True)
    r.add_argument("--corners", default=",".join(CORNERS))
    r.add_argument("--image", default=IMAGE)
    r.add_argument("--docker", default=os.environ.get("SIGNOFF_DOCKER", "sudo docker"))
    r.add_argument("--insertion-target", type=float)
    r.add_argument("--ff-vclk", choices=("auto",) + VCLK_MODES, default="auto",
                   help="IO virtual-clock reference: auto = rebind when the kit carries a per-corner insertion "
                        "binding (FLOW 10-25), else sdc; pin-flop-mean = opt-in FF-only measured reference")
    r.add_argument("--ff-vclk-contract", help="source-pinned measured core clock contract authorizing the FF reference")
    r.add_argument("--ff-bound-ps", type=float,
                   help="bound-ff: declared FF IO insertion (ps) for an already-routed core kit whose sdc_lint ctx has no "
                        "insertion_ff_ps; requires --ff-vclk bound-ff and --ff-vclk-contract naming its source")
    r.add_argument("--dry", action="store_true")
    r.add_argument("--droop-check", action="store_true",
                   help="12.4a b2 INFO: also re-time TT setup at the 0.665 V droop (data_droop.py class derate); "
                        "recorded as info_droop665, never a reason (cores with TT setup slack < 25 ps)")
    v = sub.add_parser("verdict")
    v.add_argument("record")
    v.add_argument("--insertion-target", type=float)
    lc = sub.add_parser("lec-check", help="OT_LEC_SUPERSET_VEC obligation of one kit's LEC receipts (exit 0 PASS / "
                                         "no obligation, 1 FAIL)")
    lc.add_argument("kit")
    b = sub.add_parser("bundle", help="Copy the complete standalone signoff tool bundle")
    b.add_argument("out")
    b.add_argument("--with", dest="extra", action="append", default=[],
                   help="Additional kit hook with its standalone helper dependencies (repeatable)")
    a = ap.parse_args(argv)
    if a.cmd == "lec-check":
        lp = lec_superset_problems(kit_lec_receipts(a.kit))
        print("LEC_SUPERSET " + ("NONE (no receipt used OT_LEC_SUPERSET_VEC)" if lp is None else
                                 ("PASS" if not lp else "FAIL")))
        for x in lp or ():
            print(f"  - {x}")
        return 1 if lp else 0
    if a.cmd == "bundle":
        print("SIGNOFF_BUNDLE " + " ".join(copy_signoff_bundle(a.out, extra=a.extra)))
        return 0
    if a.cmd == "run" and a.ff_bound_ps is not None and a.ff_vclk != "bound-ff":
        ap.error("--ff-bound-ps requires --ff-vclk bound-ff")
    if a.cmd == "run" and a.ff_bound_ps is not None and not (a.ff_vclk_contract or "").strip():
        ap.error("--ff-bound-ps requires --ff-vclk-contract (source of the declared FF insertion)")
    if a.cmd == "run" and a.ff_vclk == "pin-flop-mean" and not (a.ff_vclk_contract or "").strip():
        ap.error("--ff-vclk pin-flop-mean requires --ff-vclk-contract (measured core clock contract)")
    return cmd_run(a) if a.cmd == "run" else cmd_verdict(a)


if __name__ == "__main__":
    sys.exit(main())
