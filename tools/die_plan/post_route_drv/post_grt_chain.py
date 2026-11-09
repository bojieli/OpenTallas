"""Keep normal post-GRT gates while the PRD sequencer owns all data repair."""
import hashlib
import json
from pathlib import Path


def commands(path):
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


LEGACY_WRAPPER = ['source /work/post_grt_drv.tcl', 'source /work/grt_post.tcl']
LEGACY_REPAIR = ['global_route -start_incremental',
                 'repair_design -slew_margin 40 -cap_margin 20',
                 'repair_timing -hold -hold_margin 5 -max_buffer_percent 100',
                 'detailed_placement', 'check_placement -verbose',
                 'global_route -end_incremental', 'estimate_parasitics -global_routing']
# DIE-S81-49 11-02: the other generated legacy body, S81-CORES-KITS-11 variant A (gen_core_kit_legacy.py: no post-GRT
# hold pass, OT_HOLD_MM repairs FF hold; e.g. ROM ot_v41_rom_* kits) -- the same repair minus the hold line, skipped alike.
LEGACY_REPAIRS_BASE = (LEGACY_REPAIR, [c for c in LEGACY_REPAIR if not c.startswith('repair_timing -hold')])
# DIE-QC-66 11-03: the two-mode (OT_HOLD_MM) form of the same generated body (QC A0 NL/NK icg1 kits): the hold line is
# wrapped in the MM session (ot_mm_sync / ot_rc_cal_hold / ot_repair_hold_guarded) with the single-mode repair_timing
# -hold as fallback -- the same repair class, skipped alike.  Any other body still refuses.
LEGACY_REPAIR_MM = ['global_route -start_incremental', 'repair_design -slew_margin 40 -cap_margin 20',
                    'if {[llength [info commands ot_mm_sync]] && [info exists ::ot_mm_active]} {', 'ot_mm_sync',
                    'ot_rc_cal_hold { ot_repair_hold_guarded {-setup_margin 0 -hold_margin 5 -repair_tns 100 -verbose} }',
                    'ot_mm_unsync', '} else {', 'repair_timing -hold -hold_margin 5 -max_buffer_percent 100 -max_iterations 1000',
                    '}', 'detailed_placement', 'check_placement -verbose', 'global_route -end_incremental',
                    'estimate_parasitics -global_routing']
LEGACY_REPAIRS = LEGACY_REPAIRS_BASE + (LEGACY_REPAIR_MM,)
# DIE-S81-48 11-02: kits that got the generic final repair (core_final_repair.tcl, Codex 9ca922d85) append exactly
# this tail to the legacy wrapper: a pre-repair state dump and the final TT/FF data repair.  It is a second, unbounded
# data repair like post_grt_drv.tcl, so after the PRD hook (which already did the repair) it is skipped the same way;
# grt_post.tcl (the gate chain) still runs.  Any other extra line still refuses.
FINAL_REPAIR_TAIL = ['write_db /work/pre_final_state.odb', 'write_sdc -no_timestamp /work/pre_final_state.sdc',
                     'set_debug_level EST estimate_parasitics 2', 'source /work/core_final_repair.tcl']
# DIE-S81-50 11-03: tools/die_plan/core_flow.py itself writes the bare form (grt_post_core.tcl = kit hooks, grt_post.tcl,
# then only 'source /work/core_final_repair.tcl', e.g. S81 sstn_base566 bodyA): the same final data repair without the
# state dump, skipped alike.  Any other tail still refuses.
FINAL_REPAIR_TAILS = (FINAL_REPAIR_TAIL, FINAL_REPAIR_TAIL[-1:])


# ECO-CLOCK-HOOK (KW-FIX-44 11-09, COORD ruling): a post-route ECO re-runs the post-GRT chain on a routed, signed clock
# tree.  Kit hooks that EDIT that tree (subtree_balance.tcl added 552 / 1925 clock delay buffers on S81 tx_vS / tx_vD
# ECOs, then ot_clk_freeze rejected the ECO) are skipped like the final repair: the ECO repairs data only, the clock
# tree is the signed one.  Names: core_flow.py's subtree_balance + core_infra.ROOT_SCOPED_EDITORS (tap / leaf passes)
# + pinreg_pad.tcl (sourced by tapbal_grt) + the CTS-time clk_leaf_repeat hook.  The gates (grt_post.tcl) still run.
CLOCK_EDIT_HOOKS = frozenset((
    "subtree_balance.tcl", "tap_balance.tcl", "leaf_affinity.tcl", "tapbal_grt.tcl", "pinreg_pad.tcl",
    "clk_leaf_repeat.tcl", "clk_leaf_repeat_default.tcl",
    "regional_taps.tcl", "regional_taps_balance.tcl", "core_density_taps.tcl", "core_tap_align.tcl",
    "f4_chain_leaf.tcl", "multiport_clock_stage_hold.tcl", "head_lane_taps.tcl", "astk_zone_taps.tcl",
    "astk_face_taps.tcl"))


def clock_hook(line):
    """'source /work/<a clock-tree editor>' (any directory) -> its file name, else None"""
    w = line.split()
    return w[1].rsplit('/', 1)[-1] if len(w) == 2 and w[0] == 'source' and w[1].rsplit('/', 1)[-1] in CLOCK_EDIT_HOOKS \
        else None


def stage(kit):
    kit = Path(kit)
    core = kit / 'grt_post_core.tcl'
    rec = dict(schema='opentallas.prd_post_grt_chain.v1', skipped_generated_repair=False)
    chain = ''
    if core.is_file():
        lines = commands(core)
        clk = [clock_hook(x) for x in lines if clock_hook(x)]
        if clk:
            lines = [x for x in lines if not clock_hook(x)]
            rec.update(skipped_clock_hooks=clk,
                       clock_hooks_reason='ECO keeps the signed clock tree: kit clock-tree editors are not re-run')
        if any('post_grt_drv.tcl' in line for line in lines):
            drv = kit / 'post_grt_drv.tcl'
            tail = lines[len(LEGACY_WRAPPER):]
            final_tail = tail in FINAL_REPAIR_TAILS and (kit / 'core_final_repair.tcl').is_file()
            if ((lines != LEGACY_WRAPPER and not (lines[:len(LEGACY_WRAPPER)] == LEGACY_WRAPPER and final_tail))
                    or not drv.is_file() or
                    commands(drv) not in LEGACY_REPAIRS or not (kit / 'grt_post.tcl').is_file()):
                raise ValueError('unrecognized post_grt_drv chain; refuse repair after PRD route accounting')
            rec.update(skipped_generated_repair=True,
                       reason='PRD hook already performs the selected TT/FF data repair before route accounting',
                       wrapper_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),
                       repair_sha256=hashlib.sha256(drv.read_bytes()).hexdigest())
            if final_tail:
                rec.update(skipped_final_repair=True,
                           final_repair_sha256=hashlib.sha256((kit / 'core_final_repair.tcl').read_bytes()).hexdigest())
            chain = 'source /work/grt_post.tcl\n'
        else:
            chain = ('\n'.join(lines) + '\n' if lines else '') if clk else 'source /work/grt_post_core.tcl\n'
            # DIE-KV-67/CL 11-04: the form core_flow.py writes on kits with NO post_grt_drv.tcl (kit hooks, grt_post.tcl,
            # final repair; every native KV core).  The final repair's own global_route -end_incremental runs after
            # ot_clk_freeze_post_grt and after route-keep re-attached the parked wires, so it destroys clock wires nothing
            # restores and DRT re-routes them: CLK_GEOM_DIFF FAIL, route_rc 5 (KV astk 7, ZH 73, pcc_hhps 246 nets).
            # Skipped alike; the gates in grt_post.tcl and the kit's hooks still run.
            for final in sorted(FINAL_REPAIR_TAILS, key=len, reverse=True):
                head = lines[:-len(final)]
                if lines[-len(final):] == final and 'source /work/grt_post.tcl' in head \
                        and (kit / 'core_final_repair.tcl').is_file():
                    chain = '\n'.join(head) + '\n'
                    rec.update(skipped_final_repair=True,
                               reason='PRD hook already performs the selected TT/FF data repair before route accounting',
                               wrapper_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),
                               final_repair_sha256=hashlib.sha256((kit / 'core_final_repair.tcl').read_bytes()).hexdigest())
                    break
    (kit / 'prd_post_grt_chain.tcl').write_text(chain)
    (kit / 'PRD_POST_GRT_CHAIN.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


if __name__ == '__main__':
    import sys
    print(json.dumps(stage(sys.argv[1])))
