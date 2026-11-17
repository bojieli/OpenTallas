"""Opt-in R369 placement of the two source-qualified SVC pilot types.

The original 31 declared form-A sites and all original placement commands stay
in the packet. Only the exact eight zero/unobserved banks may be absent. This
does not make other planned macros optional, or change RTL, clocks or outline.
"""
from collections import Counter
import re


PREFIX = {
    "svc_hi_dsdv_svc_rs__t3": "u_bound.u_u_rsv_07_u_u_att",
    "svc_lo_dsdv_svc_rs__t7": "u_bound.u_u_rsv_14_u_u_att",
}


def expected_names(type_name):
    p = PREFIX[type_name]
    return tuple(
        [f"{p}_g_wqm_{c}_g_pc_{pc}_u_wq_mem.g_m[2].g_32.u_mem"
         for c in range(3) for pc in range(2)]
        + [f"{p}_u_qmem_mem.g_m[{b}].g_32.u_mem" for b in (2, 3)]
    )


def _normal(name):
    name = name.lstrip("\\")
    while True:
        n = re.sub(r"\\([\[\]])", r"\1", name)
        if n == name:
            return n
        name = n


PREAMBLE = r'''
# R369: retain the declared 31 form-A sites; only this exact cohort of eight
# source-proven dead high banks may be absent in these two qualified pilots.
if {[namespace exists ::s81_svc_r369]} {
    error "SVC_R369 placement callback re-entry"
}
namespace eval ::s81_svc_r369 {
    variable allowed {@ALLOW@}
    variable present {}
    variable skipped 0
    proc normal {name} {
        set name [string trimleft $name "\\"]
        while {[regsub -all {\\([\[\]])} $name {\1} next]} { set name $next }
        return $name
    }
}
# Inspect actual macro names, rather than assuming an escaped findInst alias
# is absent. The scan cannot hide an unexpected SV escape or duplicate alias.
foreach svc_r369_i [[ord::get_db_block] getInsts] {
    if {![[$svc_r369_i getMaster] isBlock]} continue
    set svc_r369_n [::s81_svc_r369::normal [$svc_r369_i getName]]
    if {$svc_r369_n ni $::s81_svc_r369::allowed} continue
    if {[[$svc_r369_i getMaster] getName] ne "ot_sram_1r1w_32x128_m1_r0c0"} {
        namespace delete ::s81_svc_r369
        error "SVC_R369 qualified bank has an unexpected master: $svc_r369_n"
    }
    if {[dict exists $::s81_svc_r369::present $svc_r369_n]} {
        namespace delete ::s81_svc_r369
        error "SVC_R369 ambiguous normalized bank name: $svc_r369_n"
    }
    dict set ::s81_svc_r369::present $svc_r369_n 1
}
set svc_r369_count [dict size $::s81_svc_r369::present]
if {$svc_r369_count ni {0 8}} {
    namespace delete ::s81_svc_r369
    error "SVC_R369 mixed bank presence: $svc_r369_count of 8; no partial missing-macro waiver"
}
set ::s81_svc_r369::absent [expr {$svc_r369_count == 0}]
rename ::place_macro ::s81_svc_r369::original_place_macro
proc ::place_macro {args} {
    set k [lsearch -exact $args -macro_name]
    if {$k >= 0 && $k+1 < [llength $args]} {
        set n [::s81_svc_r369::normal [lindex $args [expr {$k+1}]]]
        if {$::s81_svc_r369::absent && $n in $::s81_svc_r369::allowed} {
            incr ::s81_svc_r369::skipped
            puts "SVC_R369 declared_unused_bank $n"
            return
        }
    }
    # Every other call, including every unrelated missing macro, retains the
    # native OpenROAD behavior and error. Do not catch MPL failures here.
    return [uplevel 1 [list ::s81_svc_r369::original_place_macro {*}$args]]
}
try {
'''

EPILOGUE = r'''
    puts "SVC_R369 declared_formA=31 skipped=$::s81_svc_r369::skipped original_slots_and_outline_retained=1"
} finally {
    rename ::place_macro {}
    rename ::s81_svc_r369::original_place_macro ::place_macro
    namespace delete ::s81_svc_r369
}
'''


def wrap(type_name, placement_tcl, enabled=False):
    """Return byte-identical default output, or the exact-two-type callback.

    Source-zero semantics and canonical netlist qualification are recorded in
    the R369 packet. This callback additionally requires all eight declaration
    commands, and atomically accepts only all-present or all-absent at runtime.
    """
    if not enabled or type_name not in PREFIX:
        return placement_tcl
    expected = expected_names(type_name)
    calls = Counter(_normal(n) for n in re.findall(
        r"(?m)^[ \t]*place_macro[ \t]+-macro_name[ \t]+\{([^}]+)\}", placement_tcl))
    if any(calls[n] != 1 for n in expected):
        raise ValueError("SVC_R369 requires each of the exact eight declared bank sites once")
    allow = " ".join("{" + n + "}" for n in expected)
    return PREAMBLE.replace("@ALLOW@", allow) + placement_tcl + EPILOGUE


# PDN (S81-CORES-R 11-16): the copied hi3 resume passed 2_2 with wrap() and then stopped in 2_4 with PDN-1030 at the
# same first dead bank: pdn.tcl names all 31 declared macros in its macro grids.  wrap_pdn() applies the identical
# all-absent / all-present / mixed-fail contract to define_pdn_grid -macro -instances; nothing else changes.
PDN_PREAMBLE = PREAMBLE.split("rename ::place_macro")[0].replace(
    "SVC_R369 placement callback re-entry", "SVC_R369 PDN callback re-entry") + r"""rename ::define_pdn_grid ::s81_svc_r369::original_define_pdn_grid
proc ::define_pdn_grid {args} {
    set k [lsearch -exact $args -instances]
    if {$::s81_svc_r369::absent && $k >= 0 && $k+1 < [llength $args]} {
        set keep {}
        foreach p [lindex $args [expr {$k+1}]] {
            set n [::s81_svc_r369::normal [string trimright [string trimleft $p "^"] "$"]]
            regsub -all {\\} $n {} n
            if {$n in $::s81_svc_r369::allowed} {
                incr ::s81_svc_r369::skipped
                puts "SVC_R369 pdn declared_unused_bank $n"
                continue
            }
            lappend keep $p
        }
        set args [lreplace $args [expr {$k+1}] [expr {$k+1}] $keep]
    }
    return [uplevel 1 [list ::s81_svc_r369::original_define_pdn_grid {*}$args]]
}
try {
"""

PDN_EPILOGUE = r"""
    puts "SVC_R369 pdn skipped=$::s81_svc_r369::skipped"
} finally {
    rename ::define_pdn_grid {}
    rename ::s81_svc_r369::original_define_pdn_grid ::define_pdn_grid
    namespace delete ::s81_svc_r369
}
"""


def wrap_pdn(type_name, pdn_tcl, enabled=False):
    """Byte-identical default; otherwise the exact-two-type PDN callback (same R369 contract as wrap())."""
    if not enabled or type_name not in PREFIX:
        return pdn_tcl
    expected = expected_names(type_name)
    pats = Counter(_normal(re.sub(r"\\+", "", p)) for p in re.findall(
        r"\{\^([^{}]*)\$\}", "\n".join(l for l in pdn_tcl.splitlines() if l.startswith("define_pdn_grid -macro"))))
    found = [n for n in expected if pats[n] >= 1]
    if not found:
        return pdn_tcl          # no macro grid names the cohort: nothing for PDN to resolve
    if len(found) != len(expected):
        raise ValueError("SVC_R369 PDN requires each of the exact eight declared banks in a macro grid")
    allow = " ".join("{" + n + "}" for n in expected)
    return PDN_PREAMBLE.replace("@ALLOW@", allow) + pdn_tcl + PDN_EPILOGUE
