# Old QK ECTL7: source and retained-log diagnosis

Read-only diagnosis; no build, simulation rerun, or git mutation. Original failure remains **SMOKE_FAIL errors 1**; process exit 0 is not the verdict.

The retained u1 log reports run cycle 2648, first ECTL issuer fault cycle 2796 (run +148), K request observations run +156 through +432, 1730 total, and zero row/header errors. This is a source fault after actual programme start, unlike the independent G7 startup-scoreboard failure.

The selected instance in `receipt/old_qk/.../cut/qwk_stk_WS.sv:15073` is `qkd_ectl3_kiss_st`, RESPONSE_LAT=14, QK_ISSUE_AGE=62, HXK=13, MUT=0, clock core_WS. The bench connects core_WS directly to ck (`tb_qwk_stk_WS.sv:473`). `kva_grp_map.svh:68` probes **dut.ectl_WS_7.fault directly**, not the 17-edge fault transport output. Its group-7 K-request observation, however, is `o_n_krq_WS_7__r17` (`kva_grp_map.svh:41`). The cut contains one pinfix capture plus r1 through r17 on this request path: **18 positive-edge registers**. Thus a fault at +148 can follow a local request that will only reach the observer at or after +156. Calling the fault “before any K request” is unsupported.

Exact remote sources were fetched read-only and matched to the archived compiled-input SHA256 manifest:

- `old_frozen_qkd_static_k_issuer.sv`: f690f70271960a1f2f8edab2fae1b4f4826c8a1e9084f4bd5f87369bb6a7b20b.
- `old_frozen_qkd_static_ectla_kiss.sv`: be83ddf8599fd7cb00c03850d41f50dc61e3dd16ce741f2faf9bd34c801b452c.

The current checkout copies do **not** have these hashes. In particular, the frozen fused A wrapper lacks the later rst_q pin capture. Do not diagnose this run from current source without matching hashes.

The four sticky-fault alternatives in the frozen issuer are:

1. `bad_rq`, registered from `rq[0] && (!active || rq[2:1]!=0 || rq[16]!=ly[0])`.
2. `go_q && ((|ev) || req_valid || rq[0])` (a new start while K work is in flight).
3. `(rv_q && !vv_q) != ev[14]` (missing/unexpected K response).
4. `rv_q && !vv_q && returned != ident[14]` (wrong identity).

**Narrowing supported by the timing:** the first local req_valid cannot precede the earliest observed K request by more than those 18 edges, i.e. approximately +138 (NBA sampling convention can shift the named edge by one). The ev[14] deadline therefore cannot cause the first fault at +148: it occurs later, around +153/+154. The return model emits no K response before observing a K request, waits LG=8, then the cut adds 17 inbound captures. It reports no V requests. Hence no programme K/V response can reach this issuer by +148 either. Subject to the recorded idle-zero histories and no unlogged pre-window request, these facts exclude response alternatives 3 and 4 for this **first** transition. They leave **bad_rq or overlapping go_q**, not a unique cause. The 5+ edge separation makes this conclusion insensitive to one-edge observation convention.

This does not qualify the return path. The frozen transport itself has **18 outbound +8 landing +17 inbound =43 clock intervals**, before issuer comparison capture convention, while RESPONSE_LAT is 14. That independent contract mismatch needs exact schedule composition; it must not be called the cause of the earlier +148 transition or fixed by blindly changing the parameter.

The existing log does not record local rq, active, go_q, ly, bad_rq, ev, rv_q/vv_q or the compared identities. A minimal future diagnostic must observe those actual frozen local signals around the first transition and retain the original log. It must distinguish inactive request, malformed rq[2:1], layer parity, overlapping start, deadline and identity independently. No source alteration or rerun is authorized by this note.
