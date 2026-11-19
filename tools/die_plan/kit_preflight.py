#!/usr/bin/env python3
"""Cheap kit admission checks before an expensive synthesis/route allocation.

Runs the existing SDC/FF-binding, cast-form, master-slice and staged-file checks.
This is a static gate; RTL elaboration, netlist LEC/face/fanout, PG and routed
corner checks remain mandatory later stages, and are not reported as passed here.
"""
import math
import argparse
import bisect
import functools
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sdc_lint
import rtl_lint
import kit_contract
import re

# Inputs consumed by make must survive removal of the generator worktree.
INPUT_VARS = ('VERILOG_FILES', 'VERILOG_INCLUDE_DIRS', 'SYNTH_INCLUDE_DIRS',
              'SDC_FILE', 'ADDITIONAL_LEFS', 'ADDITIONAL_LIBS', 'ADDITIONAL_GDS',
              'PRE_SYNTH_TCL', 'POST_SYNTH_TCL', 'PRE_FLOORPLAN_TCL',
              'POST_FLOORPLAN_TCL', 'PRE_CTS_TCL', 'POST_CTS_TCL',
              'POST_GLOBAL_ROUTE_TCL', 'LAYER_PARASITICS_FILE', 'SET_RC_TCL')
REQUIRED = ('config.mk', 'constraint.sdc', 'sdc_lint.json', 'pins.json',
            'lec.py', 'rtl_lint.py', 'face_guard.py', 'signoff.py')


# DIE-HEAD-7 10-28: the HEAD r2 hd_tile kit staged ot_dp_clk_landing.sv without ot_meso_fifo.sv (ot_meso_ring u_ring)
# and passed preflight, then failed RTL_LINT in the container.  Static closure check: every module instantiated in a
# staged source is defined by a staged source (incl. *_bb.v blackbox headers), by a staged macro liberty
# (macros/*.lib*) or is an ASAP7 platform cell name (rtl_lint checks those cells against the platform liberty).
_INST = re.compile(r"(^|;|\bbegin\b(?:\s*:\s*\w+\b)?|\bend\b(?:\s*:\s*\w+\b)?|\belse\b|\bgenerate\b|\))\s*"
                   r"([A-Za-z_][\w$]*)\s+(?:#\s*\(|(\\\S+|[A-Za-z_][\w$]*)\s*(?:\[[^\]]*\]\s*)?\()", re.M)
_BLOCK = re.compile(r"\b(begin|end)\b")
_ROUTINE = re.compile(r"\b(?:function|task)\s+(?:automatic\s+|static\s+)?(?:[\w$:]+\s*(?:\[[^\]]*\]\s*)*)*?"
                      r"([A-Za-z_][\w$]*)\s*[(;]")
_TYPEDEF = re.compile(r"\btypedef\b[^;]*?([A-Za-z_][\w$]*)\s*;")
_SV_WORDS = set("""module macromodule interface endmodule input output inout wire reg logic bit byte int integer
    shortint longint real time genvar parameter localparam assign always always_ff always_comb always_latch initial
    final if else for foreach while do repeat forever case casez casex unique priority default begin end generate
    endgenerate function endfunction task endtask return typedef struct union enum packed signed unsigned const var
    automatic static import export package endpackage wait disable fork join assert assume cover property sequence
    tri tri0 tri1 wand wor supply0 supply1 posedge negedge or and not nand nor xor xnor buf bufif0 bufif1 notif0
    notif1 pullup pulldown string void type let defparam specify endspecify""".split())
_PLATFORM_CELL = re.compile(r"[A-Za-z_]\w*_ASAP7_75t_[A-Za-z0-9_]+$")


def _strip_src(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', text)
    # QC-A0-KITS-3 10-28: an attribute is (* ... *); the event control @(*) is NOT one (the old pattern matched its
    # "(*" and ate the text up to the next "*)", dropping every module in between from the closure census).
    return re.sub(r"\(\*(?!\s*\)).*?\*\)", " ", text, flags=re.S)


def _cond_before(text, i):
    """True when the `begin` at i opens a generate if/else/case branch body."""
    j = len(text[:i].rstrip())
    if j and text[j - 1] == ')':
        depth, k = 0, j - 1
        while k >= 0:
            depth += {')': 1, '(': -1}.get(text[k], 0)
            if depth == 0:
                break
            k -= 1
        return re.search(r"\bif\s*$", text[:k]) is not None
    return re.search(r"(\belse|:)\s*$", text[:j]) is not None and not re.search(r"\bbegin\s*:\s*$", text[:j])


@functools.lru_cache(maxsize=8)
def _block_state(text):
    """(end offsets of the begin/end tokens, any-guarded-branch-open after each token) for one module body, computed
    ONCE per body (QC-A0-KITS-3 10-28: the per-instance rescan was O(body) per instance -- the 15.6 MB mapped rawleaf
    netlist spent ~0.09 s per instance in preflight, about 1.5-2 h in total)."""
    ends, state, stack = [], [], []
    for m in _BLOCK.finditer(text):
        if m.group(1) == 'begin':
            stack.append(_cond_before(text, m.start()))
        elif stack:
            stack.pop()
        ends.append(m.end())
        state.append(any(stack))
    return ends, state


def _guarded(text, pos):
    """True when `pos` sits under a generate if/else/case branch (a guarded instance elaborates only when its branch
    is live, e.g. the closed-view refusal instances; rtl_lint's hierarchy -check still covers the live ones).
    Same answer as replaying every begin/end token wholly before `pos` (finditer(text, 0, pos))."""
    ends, state = _block_state(text)
    k = bisect.bisect_right(ends, pos)
    return state[k - 1] if k else False


_PP = re.compile(r"`(ifdef|ifndef|elsif|else|endif|define|undef)\b[ \t]*([A-Za-z_]\w*)?")


def _preprocess(text, defines):
    """drop `ifdef/`ifndef/`elsif/`else branches not taken for `defines` (updated by `define/`undef in order)."""
    out, pos, stack = [], 0, []          # stack rows: [taking, any branch taken, parent taking]
    def live():
        return all(r[0] for r in stack)
    for m in _PP.finditer(text):
        if live():
            out.append(text[pos:m.start()])
        d, name = m.group(1), m.group(2)
        if d in ('ifdef', 'ifndef'):
            t = (name in defines) == (d == 'ifdef')
            stack.append([t, t])
        elif d == 'elsif' and stack:
            t = not stack[-1][1] and name in defines
            stack[-1][0] = t
            stack[-1][1] = stack[-1][1] or t
        elif d == 'else' and stack:
            stack[-1][0] = not stack[-1][1]
            stack[-1][1] = True
        elif d == 'endif' and stack:
            stack.pop()
        elif d == 'define' and name and live():
            defines.add(name)
        elif d == 'undef' and name and live():
            defines.discard(name)
        # `else/`endif take no name: code after them on the same line stays (S81 seqhost dsdv_sh_lk names its
        # host instance as "`endif u_h (...)"; KIT-WAVE-7 10-31)
        pos = m.end(1) if d in ('else', 'endif') else m.end()
    if live():
        out.append(text[pos:])
    return ''.join(out)


_MODSPAN = re.compile(r"\b(?:module|macromodule|interface)\s+(?:automatic\s+|static\s+)?([A-Za-z_][\w$]*)(.*?)"
                      r"\b(?:endmodule|endinterface)\b", re.S)


_INCLUDE = re.compile(r'`include\s+"([^"]+)"')


def missing_includes(kit, cfg, defines):
    """live `include "x" lines of the staged sources that resolve neither next to the including file nor under
    VERILOG_INCLUDE_DIRS / SYNTH_INCLUDE_DIRS (RISK-SWEEP-2 10-28: HEAD hd_serdes lacked 3 s81_link .svh)."""
    dirs = []
    for v in cfg.get('VERILOG_INCLUDE_DIRS', []) + cfg.get('SYNTH_INCLUDE_DIRS', []):
        p = Path(v)
        dirs.append(kit / v[len('/work/'):] if v.startswith('/work/') else p)
    errors, todo, seen = [], [p for p in rtl_lint._kit_sources(kit) if p.is_file()], set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        text = _preprocess(re.sub(r"/\*.*?\*/|//[^\n]*", " ", p.read_text(errors='replace'), flags=re.S), set(defines))
        for inc in _INCLUDE.findall(text):
            hit = next((d / inc for d in [p.parent] + dirs if (d / inc).is_file()), None)
            if hit is None:
                errors.append(f'`include "{inc}" in {p.name} resolves neither beside it nor in the include dirs')
            else:
                todo.append(hit)
    return errors


def unresolved_modules(kit):
    """['module M instantiated in F has no definition ...'] for every module type instantiated (unguarded) in the
    hierarchy reachable from DESIGN_NAME that no staged source, blackbox header or macro liberty defines and that is
    not an ASAP7 platform cell; [] when the closure is complete.  Sources are read as the flow reads them: SYNTHESIS +
    VERILOG_DEFINES `ifdef branches; modules nothing reachable instantiates are not elaborated (yosys -defer)."""
    kit = Path(kit)
    cfg = rtl_lint.config(kit)
    top = cfg.get('DESIGN_NAME', [])
    defines = {'SYNTHESIS'} | {re.sub(r'^-D', '', v).split('=')[0] for v in cfg.get('VERILOG_DEFINES', [])}
    mods, errors = {}, []                 # module -> (file, {instantiated type})
    for p in rtl_lint._kit_sources(kit):
        if not p.is_file():
            errors.append(f'source {p} missing')
            continue
        text = _strip_src(_preprocess(_strip_src(p.read_text(errors='replace')), defines))
        for mm in _MODSPAN.finditer(text):
            body, uses = mm.group(2), set()
            local = set(_ROUTINE.findall(body)) | set(_TYPEDEF.findall(body))
            for m in _INST.finditer(body):
                kind, name, inst = m.group(1), m.group(2), m.group(3)
                if name in _SV_WORDS or name in local or (inst and inst in _SV_WORDS):
                    continue
                if kind in ('else', ')') or _guarded(body, m.start(2)):
                    continue      # guarded by a generate condition: left to rtl_lint hierarchy -check
                uses.add(name)
            mods.setdefault(mm.group(1), (p.name, uses))
    macros = sorted((kit / 'macros').glob('*.lib*')) if (kit / 'macros').is_dir() else []
    cells = rtl_lint.liberty_cells(macros) if macros else set()
    errors += missing_includes(kit, cfg, defines)
    if len(top) == 1 and top[0] not in mods and top[0] not in cells:
        errors.append(f'top {top[0]} (DESIGN_NAME) is not defined by any VERILOG_FILES source')
    seen, todo, missing = set(), list(top[:1]), {}
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        if m in cells:
            continue          # S81-FAILS-1118: a hard macro with a macros/ liberty is a black box; a behavioural body of it (dsdv_eng_rr_h0 in dsdv_eng_rr_split.sv) is never elaborated
        if m in mods:
            f, uses = mods[m]
            for u in sorted(uses):
                if u in mods:
                    todo.append(u)
                elif u not in cells and not _PLATFORM_CELL.match(u):
                    missing.setdefault(u, f)
    errors += [f'module {u} instantiated in {f} has no definition in VERILOG_FILES, no *_bb blackbox and no '
               f'macros/ liberty cell' for u, f in sorted(missing.items())]
    return errors



def _plan_doc(plan_dir):
    for name in ('die_plan.json', 'plan_c.json'):
        f = Path(plan_dir) / name
        if f.is_file():
            return json.loads(f.read_text())
    return None


def _plan_cells(kit, plan_dir):
    """cells.py estimate of the kit's type from the plan directory: (cells, basis, type entry), or None."""
    try:
        import cells
        raw = _plan_doc(plan_dir)
        tn = json.loads((Path(kit)/'budget.json').read_text())['type']
        est, _ = cells.estimate(raw, plan_dir)
        n, basis = est[tn]
        return n, basis, raw['partition_types'].get(tn) or {}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def plan_pins_source(kit, plan_dir=None):
    """KIT-OPS-1 11-12 (DIE-HBM-101 18:1x, wbq g1): a core kit frozen with plan_pins_source = another type's pin table (the g0
    table, pitch 0.096, instead of the g1 vC5 table, 0.192) builds every later result on the wrong pins.  When freeze.json
    records plan_pins_source and the plan is reachable: the kit's module (narrowed to its partition type when freeze names one
    the plan has) must list that file as a hard_cores[].pins_file, and the file's bytes must still hash to
    plan_pins_source_sha256.  -> errors ([] when freeze.json has no plan_pins_source or there is no plan to compare with)."""
    import hashlib
    kit = Path(kit)
    fz = kit / 'freeze.json'
    if not fz.is_file() or not plan_dir:
        return []
    F = json.loads(fz.read_text())
    src = F.get('plan_pins_source')
    if not src:
        return []
    plan = _plan_doc(plan_dir)
    if plan is None:
        return []
    module = F.get('module') or F.get('design')
    types = plan.get('partition_types') or {}
    narrow = next((t for t in (F.get('canonical_type'), F.get('type')) if t and t in types), None)
    want = set()
    for tname, t in types.items():
        if narrow and tname != narrow:
            continue
        for h in (t or {}).get('hard_cores') or []:
            if h.get('pins_file') and (not module or h.get('module') == module):
                want.add(h['pins_file'])
    if not want:
        return []                                  # the plan names no pin table for this module: not this check's class
    norm = lambda f: str((Path(plan_dir) / f).resolve()) if not Path(f).is_absolute() else str(Path(f).resolve())
    if norm(src) not in {norm(f) for f in want}:
        return [f'freeze plan_pins_source {src} is not the plan pins_file of {module}'
                + (f' in type {narrow}' if narrow else '') + f' ({", ".join(sorted(want))}): the kit was built on another pin table']
    sha = F.get('plan_pins_source_sha256')
    f = Path(norm(src))
    if sha and f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() != sha:
        return [f'plan pins_file {src} changed since the kit froze (sha256 {sha[:12]} recorded): the kit pins are stale']
    return []


# R-CLOCK-5 (HOLD-TAP-1 11-13, RULEBOOK-1113): an early core tap port clk_c<k> drives ONE hard-core clock pin, CTS skips
# a single-sink net, so the port -> pin leg is one unbuffered wire.  S81 ot_s81sl_leaf__t41 (wave 7073a6b4a59): 9 of the
# 16 u_vp.g_ln[k].u_l core taps sat on ANOTHER ln core's site, 283-1,054 um from their own core; the leg delay follows the
# distance (35 um -> 0 ps, 1,054 um -> 470 ps), the core captured 729 ps after the tap target 250 and the post-CTS FF
# hold gate stopped the kit at -432 ps after place + CTS (8 leaf types on 11-13).  The check reads the kit's own files
# (core_taps.txt, io.tcl, macro_place.tcl, macros/*.lef) and fails the kit in seconds instead.
CORE_TAP_REACH_UM = 300.0     # blocks: >= ~150 ps of unbuffered clock leg (t41: 383 um 155 ps, 486 um 196 ps, 939 um 470 ps)
CORE_TAP_NOTE_UM = 100.0      # named in the message (t41: 135-178 um = 35-82 ps); correct taps measure 0-50 um
_PLACE_PIN = re.compile(r'place_pin -pin_name (\S+) .*?-location \{([-\d.]+) ([-\d.]+)\}')
_PLACE_MACRO = re.compile(r'place_macro -macro_name \{([^}]+)\} -location \{([-\d.]+) ([-\d.]+)\}(?: -orientation (\S+))?')
_LEF_SIZE = re.compile(r'MACRO\s+(\S+).*?\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', re.S)


def core_tap_reach_rows(kit):
    """[(port, core inst, distance um from the port to the core outline, nearest other macro or '')] of the kit's early
    core taps; [] when the kit has none or a file is missing (nothing to judge)."""
    kit = Path(kit)
    taps, io, mp = kit/'core_taps.txt', kit/'io.tcl', kit/'macro_place.tcl'
    if not (taps.is_file() and io.is_file() and mp.is_file()):
        return []
    pins = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in _PLACE_PIN.finditer(io.read_text())}
    sizes = {}
    for lef in sorted((kit/'macros').glob('*.lef')) if (kit/'macros').is_dir() else []:
        for m in _LEF_SIZE.finditer(lef.read_text(errors='replace')):
            sizes.setdefault(m.group(1), (float(m.group(2)), float(m.group(3))))
    masters = {}
    cfg = kit/'bound_macro_paths.json'
    if cfg.is_file():
        for row in json.loads(cfg.read_text()).get('rows', []):
            if row.get('physical_inst') and row.get('physical_master'):
                masters[row['physical_inst']] = row['physical_master']
    cl = kit/'core_latency.json'
    if cl.is_file():
        # HEAD-97 11-13: a kit without bound_macro_paths.json still names each hard core's module in core_latency.json;
        # without it the core box had size 0 (its origin point), so the distance was measured to the core's corner
        # (hd_lep0N: 437-989 um reported, 40-120 um real)
        try:
            for row in json.loads(cl.read_text()).get('rows', []):
                if row.get('inst') and row.get('module'):
                    masters.setdefault(row['inst'], row['module'])
        except (ValueError, AttributeError):
            pass
    boxes = {}
    for m in _PLACE_MACRO.finditer(mp.read_text()):
        inst, x, y, orient = m.group(1).replace('\\', ''), float(m.group(2)), float(m.group(3)), m.group(4) or 'R0'
        w, h = sizes.get(masters.get(inst), (0.0, 0.0))
        if orient in ('R90', 'R270', 'MXR90', 'MYR90'):
            w, h = h, w
        boxes[inst] = (x, y, x+w, y+h)
    def dist(p, b):
        return max(b[0]-p[0], 0.0, p[0]-b[2]) + max(b[1]-p[1], 0.0, p[1]-b[3])
    by_port = {}
    for line in taps.read_text().splitlines():
        f = line.split()
        if len(f) >= 2 and not line.startswith('#'):
            by_port.setdefault(f[0], []).append(f[1].replace('\\', ''))
    rows = []
    for port, insts in sorted(by_port.items()):
        own = [(dist(pins[port], boxes[i]), i) for i in insts if port in pins and i in boxes]
        if not own:
            continue
        if len(insts) != 1:
            continue        # a tap of several clock pins (core group / all pins of a core) gets a CTS tree: not this check
        d, inst = min(own)
        others = [(dist(pins[port], b), i) for i, b in boxes.items() if i not in insts]
        near = min(others)[1] if others and min(others)[0] < d else ''
        rows.append((port, inst, round(d, 1), near))
    return rows


def core_tap_reach(kit, limit=None):
    """errors: early core tap ports farther than the reach limit from their own hard core (config.mk
    `export OT_CORE_TAP_REACH_UM = N` overrides the default; 0 turns the check off)."""
    if limit is None:
        limit = CORE_TAP_REACH_UM
        cfg = Path(kit)/'config.mk'
        m = re.search(r'(?m)^export OT_CORE_TAP_REACH_UM\s*:?=\s*([\d.]+)\s*$', cfg.read_text()) if cfg.is_file() else None
        if m:
            limit = float(m.group(1))
    if limit <= 0:
        return []
    rows = core_tap_reach_rows(kit)
    far = [r for r in rows if r[2] > limit]
    if not far:
        return []
    noted = [r for r in rows if CORE_TAP_NOTE_UM < r[2] <= limit]
    out = [f'core tap {port} is {d:g} um from its core {inst} (limit {limit:g}): one unbuffered clock wire'
           + (f'; it sits at {near}' if near else '') + ' -- fix the plan tap xy / core site binding (R-CLOCK-5)'
           for port, inst, d, near in far]
    if noted:
        out.append(f'{len(noted)} more core taps are {CORE_TAP_NOTE_UM:g}-{limit:g} um from their core: '
                   + ' '.join(f'{r[0]}={r[2]:g}' for r in noted))
    return out


# FABLE-FIX-S81-RINGS 11-16 (FABLE-PD-S81-0117 lever 3b, COORD r268): an S81 kit whose landing ring of >= 256 bits is not
# flops-only (plan band without ring_place=ff, or a landing_placement.tcl tag without +ff) packs the whole ring FIRM in
# netlist order and fails GRT inside the band (13 of 13 leaf kits, 38k-250k overflow).  A certain tool failure, so it
# is an error here.  Only S81 kits are judged (freeze.json die s81): KV still has hub types on the old form (KV-102 rows).
RING_FF_MIN_BITS = 256
def ring_ff(kit, min_bits=RING_FF_MIN_BITS):
    kit = Path(kit)
    lc_path, tcl_path = kit/'landing_contract.json', kit/'landing_placement.tcl'
    if not lc_path.is_file():
        return []
    freeze = kit/'freeze.json'
    if not freeze.is_file() or json.loads(freeze.read_text()).get('die') != 's81':
        return []
    bands = (json.loads(lc_path.read_text()).get('bands') or {})
    tags = {}
    if tcl_path.is_file():
        for m in re.finditer(r'\{\S+\s+\{[^}]*\}\s+ring:([^@+}\s]+)([^}\s]*)\}', tcl_path.read_text()):
            tags.setdefault(m.group(1), []).append(m.group(2))
    errors = []
    for bus, b in sorted(bands.items()):
        if bus.startswith('monitor_') or not isinstance(b, dict) or not b.get('rect_um') or b.get('hard_core'):
            continue
        width = int(b.get('width') or 0)
        if width < min_bits:
            continue
        if b.get('ring_place') != 'ff':
            errors.append(f'landing ring {bus} ({width} bits) has no ring_place=ff in landing_contract.json: the whole '
                          f'ring would be placed FIRM in netlist order (compose --band-ring ff)')
        elif bus in tags and not all('+ff' in t for t in tags[bus]):
            errors.append(f'landing ring {bus} ({width} bits): landing_placement.tcl tag ring:{bus}{tags[bus][0]} has no +ff')
    return errors


def reset_tree_coherence(kit):
    """Match generated relay placement keys to the actual staged wrapper q nets.

    A moved macro can change reset-tree numbering while --kit-rtl retains an
    older wrapper. Matching instance counts alone cannot detect that mismatch.
    """
    tree = kit / 'reset_tree.tcl'
    if not tree.is_file():
        return []
    rows = re.findall(r'^rtr_place\s+(\w+)\s+\{\*(u_[rs]rl_\d+)\[\./\]\*\}',
                      tree.read_text(), re.M)
    if not rows:
        return []
    cfg = rtl_lint.config(kit)
    top = cfg.get('DESIGN_NAME', [])
    if len(top) != 1:
        return ['relay placement requires exactly one DESIGN_NAME']
    bodies = []
    for path in rtl_lint._kit_sources(kit):
        if not path.is_file():
            continue  # staged_inputs/module_closure report missing sources
        text = _strip_src(path.read_text())
        bodies += re.findall(r'\bmodule\s+' + re.escape(top[0]) + r'\b(.*?)\bendmodule\b',
                             text, re.S)
    if len(bodies) != 1:
        return [f'relay placement requires one staged top {top[0]}, found {len(bodies)}']
    errors = []
    for key, inst in rows:
        matches = re.findall(r'\b[A-Za-z_]\w*\s+' + re.escape(inst) + r'\s*\((.*?);',
                             bodies[0], re.S)
        q = re.findall(r'\.q\s*\(\s*(\w+)\s*\)', matches[0]) if len(matches) == 1 else []
        if q != [key]:
            errors.append(f'{inst}: reset_tree.tcl key {key}, staged RTL q {q or "MISSING/AMBIGUOUS"}; regenerate a coherent wrapper/tree')
    return errors


# ---- landing band legal-site preflight (KV-R 11-16, KV-HUB-WO class f5fa4d600f) ---------------------------------------
CLAND_FAMILY_W_UM = 1.188   # widest master of the drive family the placer reserves per landing cell (cland_family_w)
CLAND_ROW_H_UM = 0.27


def cland_band_sites(kit, family_w=CLAND_FAMILY_W_UM, row_h=CLAND_ROW_H_UM):
    """Fail when a literal-local-reset landing band has no row with a free x gap >= the placer's family width once the FIRM ft-station
    cells (ft_bit_sites.tcl explicit sites) are in place.  A comb of ft flops landed FIRM first (1.08 um DFF every 2.16 um) leaves
    1.08 um gaps, no 1.188 um cell fits, and global_place dies with 'OT_CLAND no legal nonoverlapping row/site in reserved band'
    (kv3_hub_Wo, 8 min into place).  Static twin of the place-time dry pass: rows are assumed full width (only FIRM ft cells
    block), so a band that passes here can still fail on a macro, but a band that fails here always fails at place."""
    kit = Path(kit)
    lp, fs = kit/'landing_placement.tcl', kit/'ft_bit_sites.tcl'
    if not lp.is_file() or not fs.is_file():
        return []
    sizes = {m.group(1): (float(m.group(2)), float(m.group(3)))
             for m in re.finditer(r'dict set ff_bit_site_cells \{(\w+)\} \{([\d.]+) ([\d.]+)\}', fs.read_text())}
    cells = []
    for m in re.finditer(r'dict set ff_bit_sites \{(\w+),\d+,\d+\} \{(-?[\d.]+) (-?[\d.]+)\}', fs.read_text()):
        w, h = sizes.get(m.group(1), (None, None))
        if w:
            cells.append((float(m.group(2)), float(m.group(3)), w, h))
    errors = []
    seen = set()
    for m in re.finditer(r'\{(u_cland_\S+)\s+\{(-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)\}\s+literal-local-reset\}', lp.read_text()):
        name, (x0, y0, x1, y1) = m.group(1), map(float, m.groups()[1:])
        if name in seen:
            continue
        seen.add(name)
        near = [c for c in cells if c[0] < x1 and c[0] + c[2] > x0 and c[1] < y1 and c[1] + c[3] > y0]
        r0, r1 = int(math.ceil(y0 / row_h - 1e-6)), int(math.floor(y1 / row_h + 1e-6))
        best = 0.0
        for r in range(r0, r1):
            blocked = sorted((max(x0, c[0]), min(x1, c[0] + c[2])) for c in near if c[1] < (r + 1) * row_h - 1e-6 and c[1] + c[3] > r * row_h + 1e-6)
            at = x0
            for lo, hi in blocked:
                best = max(best, lo - at)
                at = max(at, hi)
            best = max(best, x1 - at)
        if best < family_w - 1e-6:
            errors.append(f'{name}: landing band {x0:g},{y0:g} {x1:g},{y1:g} has no free gap >= {family_w:g} um in any of its '
                          f'{max(0, r1 - r0)} rows after {len(near)} FIRM ft-station cells (best gap {best:.3f} um): the placer would '
                          f'die with "no legal nonoverlapping row/site in reserved band"; move the raw-branch stage to a comb-free strip')
    return errors


RETIRED_GRT_STOP = re.compile(r"gstop=timecap|OT_GRT_TIMECAP|OT_GRT_EARLY(?!_SETTLE)|GRT_NO_PROGRESS|grt_early_stop")


def retired_grt_stop(kit):
    """COORD 11-17 (KV-ABSPIN kv3_hgi_v2 kit GRT killed by an OT_GRT_STOP timecap, rc 137): GRT early stops and the post-route time cap were DELETED 11-14 (OWNER); a kit
    carries its own copy of grt183_make.sh, so one generated from an older tree still stops GRT.  A kit whose copy still has a retired stop, or whose config.mk sets a positive
    OT_GRT_POST_MAX_S / any OT_GRT_STOP*, fails: regenerate it with current tools (tools_refresh the die tree).  A hung GRT is the 2 h hung-job watchdog's (CPU-checked)."""
    errors = []
    f = kit / 'grt183_make.sh'
    if f.is_file():
        for n, ln in enumerate(f.read_text(errors='replace').splitlines(), 1):
            if ln.strip() and not ln.lstrip().startswith('#') and RETIRED_GRT_STOP.search(ln):
                errors.append(f'grt183_make.sh:{n}: retired GRT stop in a kit copy ({ln.strip()[:90]}); regenerate the kit with current tools')
                break
    cfgmk = kit / 'config.mk'
    if cfgmk.is_file():
        for ln in cfgmk.read_text(errors='replace').splitlines():
            m = re.match(r'\s*export\s+(OT_GRT_STOP\w*|OT_GRT_POST_MAX_S)\s*[:?]?=\s*(\S+)', ln)
            if m and (m.group(1) != 'OT_GRT_POST_MAX_S' or m.group(2) not in ('0', '')):
                errors.append(f'config.mk sets {m.group(1)} = {m.group(2)}: GRT stops are retired')
    return errors


def check(kit, plan_dir=None, contract=False):
    kit = Path(kit).resolve()
    issues, checks = [], {}
    def run(name, fn):
        try:
            errors = fn()
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors = [f'{type(error).__name__}: {error}']
        checks[name] = dict(verdict='FAIL' if errors else 'PASS', errors=errors)
        issues.extend(f'{name}: {error}' for error in errors)
    run('staged_tools', lambda: [f'missing {name}' for name in REQUIRED if not (kit/name).is_file()])
    cfg = rtl_lint.config(kit) if (kit/'config.mk').is_file() else {}
    def staged_inputs():
        errors = []
        if len(cfg.get('DESIGN_NAME', [])) != 1 or not cfg.get('VERILOG_FILES'):
            errors.append('one DESIGN_NAME and nonempty VERILOG_FILES required')
        for var in INPUT_VARS:
            for value in cfg.get(var, []):
                # ORFS platform references expand inside the admitted container;
                # all literal /work references, including hooks, must be staged.
                if value.startswith('/work/') and not (kit/value[6:]).exists():
                    errors.append(f'{var}: unstaged {value}')
                elif value.startswith('/') and not value.startswith(('/work/', '/OpenROAD-flow-scripts/')):
                    errors.append(f'{var}: host-only path {value}; stage under /work')
        for name in ('run_kit.sh', 'run_kit_kv.sh'):
            if (kit/name).is_file():
                # Parse syntax without executing the runner or any shell substitution.
                import subprocess
                result = subprocess.run(['bash', '-n', str(kit/name)], capture_output=True, text=True)
                if result.returncode:
                    errors.append(f'{name}: {result.stderr.strip()}')
        return errors
    run('staged_inputs', staged_inputs)
    run('sdc_and_ff_binding', lambda: sdc_lint.lint_kit_files(kit))
    run('retired_grt_stop', lambda: retired_grt_stop(kit))
    def cast_forms():
        hits = rtl_lint.yosys_cast_scan(rtl_lint._kit_sources(kit))
        return [f'{path}:{line}: {rule}: {snippet}' for path, entries in hits.items()
                for line, rule, snippet in entries]
    run('yosys_cast_forms', cast_forms)
    run('module_closure', lambda: unresolved_modules(kit))
    run('reset_tree_coherence', lambda: reset_tree_coherence(kit))
    run('plan_pins_source', lambda: plan_pins_source(kit, plan_dir))
    run('cland_band_legal_site', lambda: cland_band_sites(kit))
    # R-CAP (RULES-CAP-1, RULEBOOK 11-13): projected movable cells after place resize against the 400k place budget,
    # before any allocation.  Synth count, best first: a MEASURED count of the kit's synthesized top
    # (cap_estimate.measured_synth: native_cell_count.json, cap_projection.json, run/logs/.../1_synth.json), a staged
    # cap_budget.json, or the plan's cells.py estimate (--plan-dir).  KV-RCAP-MEAS 11-13: the cap counts the soft std
    # cells of the run, never a hard core's contents, so a plan estimate of a type built from hard cores that is not
    # its own type.cells (a flat by_type / module row counts the cores: kv3_pc_v1 850,612 flat vs 227,619 measured)
    # is recorded as CORED and not judged here, as cap_estimate.plan_rows does at G0; native_cell_cap.tcl projects the
    # measured synthesized top before floorplan.  No estimate = not judged.  Only OVER fails; the record keeps the
    # projection and its basis either way.
    cap_record = {}
    def cell_budget():
        try:
            import cap_estimate
        except ImportError:        # a kit staged before R-CAP carries no cap_estimate.py
            return []
        measured = getattr(cap_estimate, 'measured_synth', None)
        if measured is not None:
            has_measured = measured(kit) is not None
        else:                      # a kit staged before KV-RCAP-MEAS
            has_measured = (kit/'native_cell_count.json').is_file()
        synth = plan = None
        if not has_measured and not (kit/'cap_budget.json').is_file() and plan_dir:
            plan = _plan_cells(kit, plan_dir)
            if plan is not None:
                synth, basis, tdoc = plan
                cored = getattr(cap_estimate, 'cored_estimate', None)
                if cored is not None and cored(tdoc, basis):
                    cap_record.update(rule='R-CAP', verdict='CORED', plan_estimate=int(synth),
                                      hard_cores=len(tdoc.get('hard_cores') or []),
                                      synth_basis=f'plan estimate (cells.py {basis})',
                                      note='flat plan estimate counts the hard cores\' contents; not judged before '
                                           'synthesis: native_cell_cap.tcl projects the measured synthesized top')
                    return []
        errors, estimate = cap_estimate.check_kit(kit, synth)
        if estimate:
            if plan is not None:
                estimate['synth_basis'] = f'plan estimate (cells.py {plan[1]})'
            cap_record.update(estimate)
        return list(errors)      # WAVE-FLOW-R2 11-17: only SPLIT-NEEDED (over the one limit, no ruling-id waiver) is an error; the projection stays info
    run('cell_budget', cell_budget)
    if cap_record:
        checks['cell_budget']['estimate'] = cap_record
    run('ring_ff', lambda: ring_ff(kit))
    # WF-1 11-14 (OWNER: delete the conservative limits; S81 leaf t17 clk_c4 at 382 um was stopped): the core tap reach is ADVISORY.  The
    # rows are reported in checks['core_tap_reach']['advisory'] (and logged); CTS and STA judge the real effect.  Never an issue.
    def core_tap_advisory():
        try:
            return core_tap_reach(kit)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return [f'core_tap_reach unreadable ({type(error).__name__}: {error})']
    _ctr = core_tap_advisory()
    checks['core_tap_reach'] = dict(verdict='PASS', errors=[], advisory=_ctr)
    for _line in _ctr:
        print('KIT_PREFLIGHT ADVISORY core_tap_reach: ' + _line, flush=True)
    if (kit/'master_slice.json').is_file():
        def slice_check():
            import master_slice
            report = master_slice.check_kit(kit)
            return report.get('issues', [])
        run('master_slice', slice_check)
    # PREFLIGHT-2 (OWNER 10-27): the shared kit contract, one check per recent bug class (kit_contract.py)
    # Binding (fail-closed) on hard-core kits; recorded as advisory on other kits (partition tiles) unless forced.
    # OWNER 11-03 07:0x (rules are design targets, only sign-off blocks; KW-FIX-4): even when binding, only the checks
    # in kit_contract.TOOL_FAIL_CHECKS (a certain tool failure later in the flow) block; every other contract check
    # (macro_channels, clock_entry_clear, pins_canonical, ...) is reported in contract_advisory and never fails the kit.
    # PLAN-SRC-MACRO (GEN-CLASS-1 11-12, DIE-HBM-101 S00 on src_hbm_main_9446d18f5d): a TOOL_FAIL check is a certain
    # tool failure on ANY kit (place_macro on an instance the RTL does not have; Yosys re-definition), so it blocks
    # partition / tile kits too, not only core kits or --contract runs (HEAD runs preflight_args [] = no --contract).
    binding = contract or kit_contract.is_core_kit(kit)
    advisory = {}
    for name, row in kit_contract.run_all(kit, plan_dir).items():
        if name in kit_contract.TOOL_FAIL_CHECKS:
            checks[name] = row
            issues.extend(f'{name}: {error}' for error in row['errors'])
        else:
            advisory[name] = row
    return dict(schema='opentallas.kit_preflight.v2', kit=str(kit), contract=list(kit_contract.CHECKS),
                contract_binding=binding, contract_advisory=advisory,
                verdict='FAIL' if issues else 'PASS', checks=checks, issues=issues,
                deferred=['RTL elaboration/SELRANGE', 'synthesis face/fanout/port binding/LEC',
                          'placed and routed PG', 'TT setup / FF hold', 'routed LEC'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kit', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--plan-dir', type=Path, help='plan dir resolving freeze.json pins_file (optional)')
    ap.add_argument('--no-emit', action='store_true', help='do not write <kit>/preflight.json')
    ap.add_argument('--contract', action='store_true', help='kit contract binding on any kit (default: core kits)')
    args = ap.parse_args(argv)
    record = check(args.kit, args.plan_dir, args.contract)
    if not args.no_emit:
        # latest verdict beside freeze.json (timestamped --out receipts stay immutable)
        import os
        import tempfile
        kd = Path(record['kit'])
        with tempfile.NamedTemporaryFile('w', dir=kd, prefix='.preflight.', delete=False) as handle:
            handle.write(json.dumps(record, indent=1)+'\n')
        os.replace(handle.name, kd/'preflight.json')
    if args.out:
        # Never overwrite an existing failure/success receipt.
        with args.out.open('x') as handle:
            handle.write(json.dumps(record, indent=1)+'\n')
    print('KIT_PREFLIGHT', record['verdict'], 'issues', len(record['issues']))
    for issue in record['issues'][:30]:
        print('  -', issue)
    for name, row in sorted((record.get('contract_advisory') or {}).items()):
        if row.get('verdict') == 'FAIL':
            print('KIT_PREFLIGHT ADVISORY', name, (row.get('errors') or [''])[0][:200])
    return int(record['verdict'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
