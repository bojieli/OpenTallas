"""CDC registers survive Yosys FSM extraction under their RTL names (ROOT-FSMCDC 2026-10-18).

Lesson (lanes/HBM-WBK.md, ot_hbm_svc_wb_kport_q r2): ORFS `synth` runs `fsm`; fsm_detect/fsm_recode re-encoded the 16
u_wb.req_lane registers into 80 auto-named flops (_734171_ ...).  The reviewed CDC checks bind the mapped netlist to the
lint's RTL register names (OT_GF ::ot_gf_roles / ::ot_gf_gated, OT_CDC ::ot_cdc_roles), so a legal gated storage read
was reported as "OT_GF: unapproved actual crossing mem -> _734171_".  The lint itself elaborates without `fsm`.

Two parts, scoped to kits with a reviewed CDC policy (clock_data_paths reviewed_gray_fifos, cdc_synchronizers):

  1. prevention: ref_tile.py gen emits ``--orfs-var OT_FSM_NONE_WIRES=<bases>``, the wire base names of every register
     the lint tagged; physical/common_flow/ot_keep_regs.tcl (the ORFS SYNTH_CANONICALIZE_TCL hook, before `proc`) sets
     fsm_encoding "none" on those wires in every module (``w:B``, ``w:B[*``, ``w:*.B``, ``w:*.B[*``: plain, mem2reg
     elements, generate-scoped).  fsm_detect skips them ("already has fsm_encoding attribute"); function unchanged,
     only the FSM re-encoding of those registers is skipped.  Over-matching a same-named non-CDC register is harmless.
  2. detection: the CDC SDC first reads the synthesis log ($LOG_DIR/1_2_yosys.log) and FAILS with
     "<TAG>: CDC register X was re-encoded by fsm_extract" when any "Found FSM state register" is a tagged register
     (e.g. a route with OT_KEEP_REGS=0 or its own SYNTH_CANONICALIZE_TCL), instead of a misleading crossing violation.

Gate-Rule: neutral -- the same reviewed lint and the same crossing rules; synthesis keeps the RTL encoding of the
already-reviewed registers.
"""
import re
import shlex

ENV = 'OT_FSM_NONE_WIRES'
_IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def _components(name):
    """Split a flattened name on '.' outside brackets: u_wb.g[0].req_lane[3][1] -> [u_wb, g[0], req_lane[3][1]]."""
    out, depth, cur = [], 0, ''
    for ch in name:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        if ch == '.' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return out


def register_names(record):
    """Every netlist name the CDC bindings match (lint roles + extension-mode gated consumers)."""
    return set((record or {}).get('roles', {})) | set((record or {}).get('gated', {}))


def wire_bases(names):
    """RTL wire base names of the tagged registers: last hierarchical component without its bit/element indices."""
    out = set()
    for n in names:
        last = _components(n.lstrip('\\'))[-1]
        base = re.sub(r'(\[\d+\])+$', '', last)
        if _IDENT.fullmatch(base):
            out.add(base)
    return sorted(out)


def policies(spec):
    import cdc_sync_constraints as S
    import gray_fifo_cdc_constraints as G
    out = []
    if spec.get('clock_data_paths') == G.POLICY:
        out.append((G.POLICY, G.lint, G.GrayFifoError, G._yosys))
    # The reviewed FIFO policy owns its event groups too, including their register
    # roles.  Its family-period/seen schema is deliberately richer than the
    # standalone CDC policy, so lint those groups only through their owning policy.
    elif spec.get('cdc_synchronizers') is not None:
        out.append((S.KEY, S.lint, S.CdcError, S._yosys))
    return out


def orfs_vars(spec, root):
    """ref_tile.py gen: the synthesis hook variable for a kit with a reviewed CDC policy (receipt-cached lint)."""
    import lint_receipt
    bases = set()
    for key, lint, error, yosys in policies(spec):
        bases.update(wire_bases(register_names(lint_receipt.record(key, lint, error, spec, root, yosys()))))
    return ['--orfs-var ' + shlex.quote(ENV + '=' + ' '.join(sorted(bases)))] if bases else []


TCL = r'''
# OT_FSM_CDC (cdc_fsm_guard.py): a CDC register re-encoded by yosys fsm_extract loses its RTL name; fail clearly.
proc ot_fsm_cdc_guard {tag vars} {
  if {![info exists ::env(LOG_DIR)]} return
  set log [file join $::env(LOG_DIR) 1_2_yosys.log]
  if {![file readable $log]} return
  set fh [open $log r]; set text [read $fh]; close $fh
  set found [regexp -all -inline -line {^Found FSM state register (\S+)\.$} $text]
  if {![llength $found]} return
  set regs [dict create]
  foreach v $vars {
    if {![info exists $v]} continue
    foreach k [dict keys [set $v]] {
      dict set regs $k 1
      regsub {\[[0-9]+\]$} $k {} k1
      dict set regs $k1 1
    }
  }
  set hit {}
  foreach {_ f} $found {
    set f [string map {\\ {}} $f]
    set i [string first . $f]
    if {$i >= 0} {set f [string range $f [expr {$i + 1}] end]}
    if {[dict exists $regs $f]} {lappend hit $f}
  }
  if {[llength $hit]} {
    error "$tag: CDC register [join [lsort -unique $hit] {, }] was re-encoded by fsm_extract (yosys 1_2_yosys.log 'Found FSM state register'); the CDC check binds RTL register names, so its crossings would be misreported. Keep the ot_keep_regs.tcl synthesis hook with OT_FSM_NONE_WIRES (ref_tile.py gen emits it) or put (* fsm_encoding = \"none\" *) on the register"
  }
}
'''


# (policy TCL header that follows its bindings, tag, binding dicts).  Spliced by ref_tile.py, so the receipt-keyed lint
# modules (lint_receipt.TOOL_FILES) stay byte-identical and no committed receipt is invalidated.
MARKERS = (('\n# OT_GF (gray_fifo_cdc_constraints.py)', 'OT_GF', ('::ot_gf_roles', '::ot_gf_gated')),
           ('\n# OT_CDC (cdc_sync_constraints.py)', 'OT_CDC', ('::ot_cdc_roles',)))


def splice(text, spec):
    """clock_entry_constraints.generate() output with the guard called right after each CDC policy's bindings."""
    if not policies(spec):
        return text
    for marker, tag, vars_ in MARKERS:
        n = text.count(marker)
        if n > 1:
            raise ValueError(f'cdc_fsm_guard: {tag} TCL header appears {n} times; revalidate the splice')
        if n:
            text = text.replace(marker, '\n' + TCL + f'ot_fsm_cdc_guard {tag} {{{" ".join(vars_)}}}' + marker)
    if 'ot_fsm_cdc_guard OT_' not in text:
        raise ValueError('cdc_fsm_guard: CDC policy without its OT_GF / OT_CDC TCL; revalidate the splice')
    return text
