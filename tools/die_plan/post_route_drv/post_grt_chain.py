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


def stage(kit):
    kit = Path(kit)
    core = kit / 'grt_post_core.tcl'
    rec = dict(schema='opentallas.prd_post_grt_chain.v1', skipped_generated_repair=False)
    chain = ''
    if core.is_file():
        lines = commands(core)
        if any('post_grt_drv.tcl' in line for line in lines):
            drv = kit / 'post_grt_drv.tcl'
            if (lines != LEGACY_WRAPPER or not drv.is_file() or
                    commands(drv) != LEGACY_REPAIR or not (kit / 'grt_post.tcl').is_file()):
                raise ValueError('unrecognized post_grt_drv chain; refuse repair after PRD route accounting')
            rec.update(skipped_generated_repair=True,
                       reason='PRD hook already performs the selected TT/FF data repair before route accounting',
                       wrapper_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),
                       repair_sha256=hashlib.sha256(drv.read_bytes()).hexdigest())
            chain = 'source /work/grt_post.tcl\n'
        else:
            chain = 'source /work/grt_post_core.tcl\n'
    (kit / 'prd_post_grt_chain.tcl').write_text(chain)
    (kit / 'PRD_POST_GRT_CHAIN.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


if __name__ == '__main__':
    import sys
    print(json.dumps(stage(sys.argv[1])))
