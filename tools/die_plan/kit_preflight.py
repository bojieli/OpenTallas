#!/usr/bin/env python3
"""Cheap kit admission checks before an expensive synthesis/route allocation.

Runs the existing SDC/FF-binding, cast-form, master-slice and staged-file checks.
This is a static gate; RTL elaboration, netlist LEC/face/fanout, PG and routed
corner checks remain mandatory later stages, and are not reported as passed here.
"""
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
    return re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)


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
        pos = m.end()
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
    def cast_forms():
        hits = rtl_lint.yosys_cast_scan(rtl_lint._kit_sources(kit))
        return [f'{path}:{line}: {rule}: {snippet}' for path, entries in hits.items()
                for line, rule, snippet in entries]
    run('yosys_cast_forms', cast_forms)
    run('module_closure', lambda: unresolved_modules(kit))
    if (kit/'master_slice.json').is_file():
        def slice_check():
            import master_slice
            report = master_slice.check_kit(kit)
            return report.get('issues', [])
        run('master_slice', slice_check)
    # PREFLIGHT-2 (OWNER 10-27): the shared kit contract, one check per recent bug class (kit_contract.py)
    # Binding (fail-closed) on hard-core kits; recorded as advisory on other kits (partition tiles) unless forced.
    binding = contract or kit_contract.is_core_kit(kit)
    advisory = {}
    for name, row in kit_contract.run_all(kit, plan_dir).items():
        if binding:
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
    return int(record['verdict'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
