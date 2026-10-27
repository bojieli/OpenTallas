#!/bin/bash
# HBM-MU-QUAD-7 plan event on top of Codex C11 (codex/hbm-plan-0815 data c11b, sha a9bd76a8fe81)
# data: intel2:/srv/opentallas-scratch2/claude/hbm-mu-quad-7-1027
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-hbm-plan-0815
cp -a $B/c11b c12 && python3 apply_core_outlines.py c12            # 5 content outlines (pretree 164.16x241.92, vm_query 216x138.24, wr_q 142.56x216, inj_join 211.68x207.36, xq 181.44x276.48)
cp -a c12 c12b && python3 fixgrow.py c12b apply                    # vm_query growth: q0 instances keep a neighbour channel
cp -a c12b c12c && python3 restation.py c12c $B/c11b/die_plan.json # endpoints onto actual new pins, same face
cp -a c12c c13 && python3 relax_internal.py c13 400                # internal station regs: count kept, hops/in-core
cp -a c13 c14 && python3 lattice.py c14 && python3 relax_internal.py c14 400   # 8.64 lattice
