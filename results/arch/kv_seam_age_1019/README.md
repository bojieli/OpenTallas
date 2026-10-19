# KV source-to-pin effective age audit

Source tool revision: 7e99dc4d0, branch codex/kv-recovery-1019. Fleet runs use ot-run on ot-epyc4; no local simulations.

The old bound source is 219049242d2656c808ee554b5a9ba8436e76b171 at /srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-219049242-mu. Its fwd_lanes metadata is enriched from the source-pinned KVR-FWDAGE contract (E=E_planned, cal=h0, K checked against actual straps), not from a maximum observed path. Explicit post stages and plain prefixes are counted only after the complete forwarded-instance set matches. Packed relay self-chains are tracked by instance AND bit position. The PV trunk y data/V/T roles are split only for the exact canonical RTL SHA.

NetlistWalk: 12 tests PASS. Relay schedule Check: 9 tests PASS, including unchanged legacy digest with drifted, unknown, or missing effective ages rejected. Historical stage digests retain their format.

Actual old netlist: 51,580 buses, 48 unresolved findings representing 16 genuinely torn PV payload buses. All originate vport_ES_2.out_v_hi/lo and reach pvw_0 b2/b6; high-half paths have ages57/58 and low-half69/70. These remain strict failures. This is diagnostic evidence, not release qualification. Full table and exact replay tools remain at /srv/opentallas-scratch/claude/codex-kv-proof/{kv_table.enriched.json,export_enriched.py}.
