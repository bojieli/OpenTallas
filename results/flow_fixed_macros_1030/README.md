Actual native manual-placement coupon for source f91f720f2.

The coupon read the existing QC `coll_ucie` `2_1_floorplan.odb` through a read-only mount, installed the generated fully-fixed PRE hook, ran the native `place_macro -exact` command emitted by `gen_phys`, then called the intercepted `rtl_macro_placer`. Native manual placement reported MPL-0035 with the exact 0..777.600 um square, and the complete fixed-macro validator passed. This confirms the manual deck can execute before the validation-only optimizer entry; the earlier strict-validator check on the private trial's `2_2` database alone did not establish that.

Input on epyc2: `/srv/opentallas-scratch2/claude/codex-qc-kits-0336/gen46phy_fixed/coll_ucie/run/results/asap7/dp_coll_ucie/base/2_1_floorplan.odb`. The adjacent JSON records the exact generated parent-plan contract. The process used `openroad/orfs:asap7lock`; inspected native stage order hashes are recorded in `tools/die_plan/test_fully_fixed_macros.py`.

No source database was modified, no output database was written, and no physical placement/routing trial was duplicated. Full physical G1 and view adoption remain with the QC owner. This receipt qualifies the tool mechanism only.
