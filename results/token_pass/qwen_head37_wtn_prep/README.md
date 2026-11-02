HEAD37 witness source PREP, inactive by default

The candidate expands the finite WTN1 template from 13 records / 1742 bits to
15 records / 2010 bits behind HEAD_STAGE37=0. Source cost is 268 payload bits,
2 loaded bits and 30 kept select bits = 300 FFs. PW400..438 remain the BASE
positions and PW439..444 hold HEAD records. The existing 1024-word replay covers
all six additional occupied words, with zero added replay cycles.

The packer derives 114 BASE events from the actual corrected CALR source. It
compares those events to the historical image: all dates and masks match; only
record11 local PC1 becomes PC2 for the canonical RES2 caller correction. Historical
lockstep uses the historical image and its original digest. The corrected BASE
records are only exercised with the new 15-record profile identity.

The HEAD fixture is test-only. Group13 localPC17 covers slice0 and group14
localPC16 covers slices1..11. Their masks are disjoint and cover0xfff. The manifest
joins every user/slice to its actual lower-half PC16 word; slice0 upper-half PC17
must be an exact monitored copy, while the other upper halves are zero. Different
slices have different kernel words. No production calendar dates or auth adoption
are established. Profile digest is a content-derived component fixture identity.

Audit fixed SAFE_PHYS's separate profile comparator, which otherwise still
required the historical digest/epoch when HEAD37 was enabled. The HEAD digest and
epoch must differ from BASE. Default-off source preserves the old profile path.

Preparation checks: Python packer assertions passed. Simulation is prepared and
awaits parent resource admission (2 GB / 1 thread proposal); no simulator result,
physical closure, production HEAD date or token-rate claim is made here.

Generate with tools/qwen_layerbench/head37_witness_prep.py and explicit
--calendar, --head, --legacy-pw and --out paths. The committed profile.json pins
this preparation's readset. After resource admission, use
run_head37_witness_prep.sh PACKET BUILD_SCRATCH from this worktree. It exercises
actual observer composition, default-off historical edge lockstep, new-profile
BASE and HEAD37 all4users, SAFE_SELECT and SAFE_PHYS, with missing/late/duplicate,
wrongPC, old digest and stage controls.
