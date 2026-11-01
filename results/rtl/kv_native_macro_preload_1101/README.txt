Native macro activation mechanism PASS, pinned openroad/orfs:asap7lock via ot-run2GB/1CPU, epyc2 unit oth-ubuntu-3712331-1793546486 exit0.

No bind.py/gen_phys hook needed. gen_phys.type_macros copies each explicitly plan-declared hard-core/content LEF and Liberty into macros/. rtl_lint and ORFS preload Liberty (-lib) before read_verilog -defer. The existing concrete blackbox wins over the deferred native module.

Smallest frontend vehicle uses the actual canonical, nonparameterized qkd_astk_ex_s body and exact102port top. Matching synthetic Liberty preload yields1hardEX cell/0native logic. Removing Liberty or changing its master name causes hierarchy to enter the native body and fail on its unstaged exp dependency. The synthetic Liberty tests symbol-resolution ordering only: it is NOT a signed child, physical timing model or equivalence proof. Functional proof and published views must still refer to the signed exact native child/parameters/ports, with an unmodified canonical golden.

Current HG/HGI declared-package audit:336placements have exact LEF+Lib files and0 *_bb.v files; this existing Liberty path is how those declared packages activate. Prior exact module/pin-table matching and child SIGNED records remain their authority. This frontend test grants no new physical closure or route approval. EX must publish its real SIGNED views before those views replace this fixture in any parent run.

Replay: bash run.sh (under ot-run). Logs and preloaded.json retain the exact physical-front-end result. Native-only and wrong-master FAIL logs are expected controls, preserved verbatim.
