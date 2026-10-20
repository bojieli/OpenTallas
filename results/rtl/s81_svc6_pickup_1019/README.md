SVC6 pickup

Terminal subset, not qualification: production ST2 short300/tail46 pass (four cases); registered-pin ST0 tail46 and landed-parent ST2 short300/tail46 fail with 128 PV errors (six cases total). Original KPV55 is being investigated by the existing K58/62/70/85 sweep; no replacement price or successful candidate is claimed. The rest of each original suite was still live at pickup.

Source recipes: svc4 job.sh uses src.tar (source e82cde6b4 according to recipe); pin/lp use src2.tar @2bf768084. Numerical and scheduling fields are preserved in the verdicts.

SVC5 SM failure is diagnosed by Claude commit95d63f254: SE-only vectors omit SOT configuration, causing the active SO target to flag writes. The new SO protocol bench is already running on ep6; do not duplicate it. No gate or route launched by this pickup. hgrp/ns gates continue CTS hold repair on ep8; no terminal verdict.
