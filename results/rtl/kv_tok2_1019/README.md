# KV-TOK2 10-19: Qwen KV attention token vehicles, collection and classification

Scope: TOK.QW.KV (1u/4u KV attention), MU.QW.KVATT, KV side of TOK.QW.XDIE. There are NO measured cycles yet: none of the
vehicles has a valid application PASS. The priced references stay in force: kv_service 1,555 busy / 1,816 window /
unit 1,561 @T8192 per layer, plus the accepted per-layer retirement (STATUS 1982 / end 1983, +7,680 edges/token,
249,600 -> 257,280, +2.985%).

## Vehicle table (ep5 unless noted)
| Vehicle | State | Classified cause | Action |
|---|---|---|---|
| G7 WSQK u1 (original fixture) | TERMINAL SMOKE_FAIL19 (rc0) | FIXTURE: grp_model/face monitor not reset/authority-qualified; a bogus startup STATUS @6 counts as retirement, so the programme skips its scheduled run | preserved (3fdbc1e3d); the fix is the authority-monitor fixture 7512369a3 |
| controlled G7 u1 (fixture 7512369a3), unit 2272781 | TERMINAL compile rc2 | TOOL: GCC15 cc1plus SIGSEGV on Vtb_qwk_stk_WS__Syms__Slow.o (22 MB Syms.h) under the 8 MB default stack; this is the same class as old QK/WSri. Not RTL, not fixture | r2 (below) |
| controlled G7 u1 r2, unit oth-ubuntu-2356307-1792452476 | compile rc0 (2:46, 5.6 GB, only the Syms__Slow TU + link, under `ulimit -s unlimited`); u1 sim RUNNING | -- | `/srv/opentallas-scratch/claude/kv-tok2-1019/controlled_r2/simulation.json` gives the strict verdict |
| G7 WSQK u4cal 2188542 / u4pack 2188543 | LIVE 99.9% CPU (3h20) | PRE-DETERMINED FAIL: the partial log already shows the same 17 startup SMOKE_ERRs as u1 (kind14 @1, the cycle-1 out-of-window K rows). Original fixture, so any cycles from it are contaminated | kept (cheap, 1.3 GB each) for KVA_STACK spans only; never counted as a verdict or as cycles |
| old kvs14p QK u1 | TERMINAL SMOKE_FAIL1 | RTL/calendar: ECTL WS_7 sticky fault run+148 (the bad_rq/go-overlap/return predicates are not separable in the trace). Old die, diagnostic only | preserved; no rerun (old die) |
| old QK u4cal 2221872 | LIVE (2h45) | no early SMOKE_ERR in its buffered 16 KB | diagnostic; collect on terminal |
| G7 P0 2022334 / P1 2022634 top builds | LIVE: C++ PCH compile (stack already unlimited) | they carry the original fixture (the 9 boot words are missing, plus the startup contamination) | collect on terminal; expect a fixture FAIL. The useful output is the child objects |

u4 under the controlled fixture is BLOCKED: g7_identity_bind.svh `$fatal`s unless kva_n==1 (the adapter covers u1 only).
The next step after the r2 u1 PASS is to generalise the identity adapter to NSTEP 4/8 programmes, then run u4cal/u4pack
from the r2 binary (no rebuild of the RTL children).

## GEN9 token waiter (armed)
gen9_waiter.sh (local PID 3163282, log /home/ubuntu/artifacts/kv-tok2-1019/gen9_waiter.log) is the v3 waiter retargeted
to the STRICT GEN9 run ep6 kvs14r-7f9501c62-gen9s (the gen9d PARAM_DIAG run is not a die result). It gates on
port_bind_v2/die_bound.v + json, case_kv/relay_stages.json, case_kv/boot_ages.json, relay_check.json and STAGED. If prep
fails it stops without a launch. Otherwise it launches WSQK:128 / P0:300 / P1:300 unpinned into
kv-token-pickup-1019/g9_7f9501c62_gen9s/. These use the ae997 boot-word fixture, but NOT the authority/startup repair:
the sims are diagnostic, and the hier child objects are what gets reused for a controlled top. GEN9 does not enable the
STATUS_DELAY 197 retirement, so it cannot price the +2.985% retirement path yet.
