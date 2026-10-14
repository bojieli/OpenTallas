# Concrete supplemental qualification proposal

This proposal remains unvalidated until explicit owner review. The physical job stays bound to bc2c93f92, whose testbench can hang because a shared integer k is overwritten by clock monitors. The corrected supplemental testbench is frozen at b2b1fc71a. The only RTL change is the attached monitor-index-only diff; all4669 other RTL/bench-script blobs are identical. Actual remote shipping RTL/script hashes and actual respective testbench hashes were also checked on both hosts.

Full exact/mutant simulation logs and build logs are retained under logs/bench, with the exact command script and ot-run admission/completion output. Exact nine-case check passes with zero mismatches. KSWAP finishes with121697 equality mismatches,128 mismatching roots and zero timeouts, exit1; this is an actual caught mutant, separate from the superseded test termination.

Proposed action: validate the source identities, only testbench diff, actual hashes and complete logs; then permit a source-bound supplemental bench receipt for this unchanged physical job. Preserve the original frozen defective test history and its invalid termination outcome. Do not mutate the frozen route source, synthesize btrack success or repeat the unchanged physical route. Parent adoption remains separately blocked on actual routed compensated phase proof.
