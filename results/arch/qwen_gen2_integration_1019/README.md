# Qwen successor GEN integration model

This is a source-pinned inventory and lower-bound cost model, not physical adoption or token qualification. Input is the original regional trial `claude/qw-dieclk-1019@bbe250fb5`, copied unmodified from ep6 `qw-dieclk-1019/d/land_owed_rA.json`.

The original dv2f18dh2 chain terminated at 10:22 PT: 43/55 neighbour pairs exceed 80 ps; GRT then failed because a protected root-owned clock ODB could not be hard-linked. No GRT/STA resume process was present at 12:40 PT. The separate rA/rB regional trial remains progressing (unit2527398, OpenROAD PIDs2531257/2531259); preserve it. rA uses an unpadded forwarded spine, rB ideal-root control. No final verdict exists yet. The old PG-safe-sites experiment proves only legality methodology, not adoption of the rejected balanced spine.

## Cost and correctness blockers

Exact inventory:446 links,186347 payload bits. Naively storing four slots costs at least745388 data FF before pointers, masks, reset, face registers or clock trees.307 links exceed2048 stored payload bits and therefore cannot become indexed flop rings under the owner storage rule.264 CB16-related links carry136080 bits (73.0%); landing at real CB16 regional boundaries or narrowing the transport must be modelled before generic replication. Payload bits cannot be silently omitted or reduced without source/lifetime proof.

15 links have nonunique source or destination root sets. For example c16_E0_0 advertises both pll_r48 and pll_r99. An instance-level root list cannot select ck_s for a particular bus. Resolve actual child port/pin ownership and ordered record bits first. Native measured child insertion is also absent for126/146 masters; model arrivals are not release evidence.

Landing E, individual channel storage depth, clock-phase tolerance, SRAM old-data/collision semantics, throughput and single-/multi-user token deltas remain NULL. Their exact values must come from measured TT/FF child clocks and static producer/consumer schedules. Four slots is a proposal, not a universal proof.

## Minimum runnable successor

1. Preserve original die/v/hashes and record the full stand-in manifest. Use the existing dh2 case only for a separately labelled diagnostic GRT/STA resume, with exact patched source, safe copy fallback and compiled relay-table comparison; never claim that repairs regional closure.
2. First source-integrated GEN may retain explicitly labelled old diagnostic views while binding actual new module/ports/slot contracts. It must distinguish semantic source binding from a qualified physical view. Never bind old views under new master names or mark stand-ins safe.
3. Bind D2D `qfd_d2d_static_ovl_sf` with actual TXDP_C and sf5 slot/pins; native59 `_r1`; SYSFACE bc2 exact physical wrapper; CTLM safe2 native_cmd E face; closed dhuser k3. Until those exact gates close, retain each as a labelled diagnostic dependency, not fabricated hardened closure.
4. Carry actual existing reset foreign-clock fix, HR/ROM last-k, relay record seam stages and closed xstn E/W identities. Regenerate MU calendar image from the bound C[8,3,1,10]/K[21,4,3,3] or successor measured ages; stale C[8,3,1,9]/K23 is forbidden.
5. Integrate CB16 regional parent first, resolve all15 multi-root links, then regenerate all446 bus obligations from source. A minimum partial GEN may expose unresolved crossings in its FAIL ledger; it cannot claim regional timing closure while they remain.
6. Run strict bind, parameter/view SHA checks and producer/consumer record bundle checks before physical work. Then real placement/PG, regional native clock census and actual single-/multi-user stage cuts. Final complete closure requires zero unlanded crossings, intra-region <=80ps TT+FF, static landed-lane phase proof, all pins/reset registered, reach<=405um and exact storage semantics.

No new full die GEN or physical build was launched from this inventory: source/clock/area/latency model blockers are explicit. The existing regional A/B trial is the bounded physical experiment already in hand.
