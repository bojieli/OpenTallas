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
LEGACY_REPAIRS = (LEGACY_REPAIR, [c for c in LEGACY_REPAIR if not c.startswith('repair_timing -hold')])
# DIE-S81-48 11-02: kits that got the generic final repair (core_final_repair.tcl, Codex 9ca922d85) append exactly
# this tail to the legacy wrapper: a pre-repair state dump and the final TT/FF data repair.  It is a second, unbounded
# data repair like post_grt_drv.tcl, so after the PRD hook (which already did the repair) it is skipped the same way;
# grt_post.tcl (the gate chain) still runs.  Any other extra line still refuses.
FINAL_REPAIR_TAIL = ['write_db /work/pre_final_state.odb', 'write_sdc -no_timestamp /work/pre_final_state.sdc',
                     'set_debug_level EST estimate_parasitics 2', 'source /work/core_final_repair.tcl']


def stage(kit):
    kit = Path(kit)
    core = kit / 'grt_post_core.tcl'
    rec = dict(schema='opentallas.prd_post_grt_chain.v1', skipped_generated_repair=False)
    chain = ''
    if core.is_file():
        lines = commands(core)
        if any('post_grt_drv.tcl' in line for line in lines):
            drv = kit / 'post_grt_drv.tcl'
            tail = lines[len(LEGACY_WRAPPER):]
            final_tail = tail == FINAL_REPAIR_TAIL and (kit / 'core_final_repair.tcl').is_file()
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
            chain = 'source /work/grt_post_core.tcl\n'
    (kit / 'prd_post_grt_chain.tcl').write_text(chain)
    (kit / 'PRD_POST_GRT_CHAIN.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


if __name__ == '__main__':
    import sys
    print(json.dumps(stage(sys.argv[1])))
