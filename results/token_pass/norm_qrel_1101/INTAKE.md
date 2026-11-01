# Source/evidence-only intake

This branch starts at current origin/main and carries only Python/compiler/test helpers, SV testbench text and recorded component evidence. It carries no RTL, physical source, plan, parameter default or canonical macro change. Required imports are norm_nx_candidate → existing dv_layer_compile and check_network → existing norm_q.finish_root; all remaining new runtime helper imports are standard Python libraries. The reproduction staging scripts intentionally refer to immutable remote source fixtures named in README and are not automatic production jobs.

All BK6, per-SID K, PDSK512 and nonzero QDELAYS source requirements remain unadopted candidates. The old compiled source observation is not a claim that current main hardware has those parameters. Fresh source arithmetic is not native CAP/RD/residency or final-layer HEAD input authority. The recorded stale SV literal remains a native harness failure. No canonical hardware adoption or production PASS is included.

Accepted original evidence commits:1a6397863,f7b41e943,07a89a934,fd9f793b3. Transitive missing helpers are included as complete source files, so this branch does not require those earlier branch commits or their RTL ancestry.
