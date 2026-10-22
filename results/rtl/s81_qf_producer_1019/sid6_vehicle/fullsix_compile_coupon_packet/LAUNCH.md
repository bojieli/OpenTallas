# Actual full-model PCH and largest-TU compilation: proposed admission

Frontend02 succeeded with the pinned guard:932.54s total, maxRSS42603960KiB, Verilator316modules/1968CPP. All1977 generated files/2970592285 bytes are SHA-pinned by fullsix_frontend02_result/frontend_inventory.json. No compilation, link or simulation has run.

The generated real make graph shows the largest TU object depends on Vtb_fullsix_trace__pch.h.slow.gch. That PCH includes __Syms.h and the128817531-byte full root header (previous measured input coupon header was5131793 bytes). Its parsing cost cannot be estimated from the prior input build. The selected TU is the actual largest generated file:__131__Slow.cpp,5149328 bytes; no reduced module/operator is substituted.

The proposed next command is:

```
ot-run --mem 256 --threads 1 --disk 80 --dir /srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_frontend_02 -- bash compile_coupon.sh
```

The script verifies every guarded input, then separately times actual make targets Vtb_fullsix_trace__pch.h.slow.gch and Vtb_fullsix_trace___024root__131__Slow.o with -j1 and existing OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0. Both are useful products retained for the whole build. GCC15.2.0 and make/runtime-makefile hashes are pinned in contract.json. The PCH is genuine full-model state, the TU is an actual whole-build dependency, and the step performs no numerical test.

The256GB is a conservative admission reservation while PCH/compiler memory cost is unknown, not a process/cgroup/address-space cap or measured need. The latest actual reading has900.4GB available RAM and466.0GB scratch; refresh before launch. No arbitrary wall limit, no duplicate frontend, no source/weights/gold/CTL/epoch/clock/reset/settings change and no deletion/restart of useful objects. Preserve failure logs and partial outputs. Use measured PCH/TU RSS/time/object sizes and current headroom to propose whole-build parallel admission later. Root technical admission precedes compilation. No link/simulation/CAP/row-coverage/native/token qualification is granted by generation or by this compilation coupon.
