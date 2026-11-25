# FABLE-FIX-KV-LOCKUP-INERT handoff (updated 11-25, lane RESUMED by COORD ruling)

Goal: reset_replicate `lockup_regions` has no effect in real KV strict binds (hgi_v2__cle0015330: 11 tail copies + "rest" 40 loads instead of 18).

## Known (11-22)
- HGI-R6 wrapper binds (gen/bind_dump_all.py, runpy + early `import reset_replicate`) give 18 with and without private HOME: HOME is not the cause.
- My UNWRAPPED probe bind (R6h plan 64ec19c3d027, rt fda4eaad0e94, unit oth-ubuntu-3304862-1795344180): LOCKUP copies 11 rest 1. Fault reproduced.
- Text handed to reset_replicate.apply is identical in both; so the difference is wrapper vs no wrapper (import order / runpy / forked emit workers).
- epyc8 lane clone + probe log were cleaned; nothing of mine is running.

## Plan (COORD ruling 11-25)
1. Check hub + an A5t8 hgi bound text for the replica count. Fixed -> post CLOSE with evidence, stop.
2. Else: own fork via ot-tree-fork, one instrumented bind without the wrapper then with it (ot-run --priority die --hosts epyc12 --disk 5), find the import-order / runpy difference, fix on main + test, ot-push-main.

## State
- step 1 in progress.
