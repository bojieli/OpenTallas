from pathlib import Path
import hashlib
import json

r = Path('/OpenROAD-flow-scripts/flow/scripts')
p = r/'global_route.tcl'
body = p.read_text()
anchor = 'load_design 4_cts.odb 4_cts.sdc'
if body.count(anchor) != 1:
    raise SystemExit('REFUSE: exact post-MM original loader anchor required')
load_prefix = body.split(anchor)[0]
# Only stock initialization before load_design. No upstream GRT/PRE hook or
# old repair runs. Native make retains the original environment and libraries.
(r/'global_route.before_fresh_pa.tcl').write_text(body)
p.write_text(load_prefix+'load_design REPAIR_DESIGN_CHECKPOINT.odb 4_cts.sdc\nsource /work/fresh_pa.tcl\n')
print(json.dumps(dict(kind='FRESH_PA_DIAGNOSTIC_ONLY',native_global_route_sha256=hashlib.sha256(body.encode()).hexdigest(),
                     input='actual named after-DRV REPAIR_DESIGN_CHECKPOINT.odb',sdc='genuine original 4_cts.sdc',
                     no_prior_stage_replay=True,no_gRT=True,no_setup=True)))
