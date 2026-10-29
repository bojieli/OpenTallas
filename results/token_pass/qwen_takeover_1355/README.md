# Qwen takeover 2026-10-29 13:55 PDT

Source branch starts at current KV source ad3075728c2b86bd08bb75f0bc0e1f144fdfb0a2 (not stale FETCH_HEAD).

Actual inherited jobs collected without replay:
- intel2 chain /home/ubuntu/tok-kv-2-chain.sh PID645254. Both actual native b5 probe and v2 builds passed at11:42.
- Probe intel1 /srv/opentallas-scratch2/claude/tok-kv-2-1029/kvl/boot_probe terminal FAIL. Shell chain reports rc0 because inherited wrapper swallows simulation status; actual log is authoritative.
- Probe reload33397 clears both installed-base seen bits; first cal_start38393 then f_early1/dcal_fault1 at38394. This confirms the proposed reload fault cause on actual vehicle.
- Repaired v2 actual run retains both base seen bits through reload33397 and cal_start38393; dcal_fault remains0. Independent epoch_abort STILL rises38406, FAR_FAULT follows, transport80/link_up10 at38558. BOOT_PASS at40085 qualifies loading only, not native calendar execution. No full layer/result exists and no36layer continuation is authorized by this result.
- v2 long POST24000 run remains live and unchanged. Partial log is a snapshot at14:00, not terminal evidence. Old watcher2207412 had exited without launching after original fault (lane TOK-R09:45); do not revive it.

Next smallest useful diagnosis: actual bound sys_c uses qkd_d2d_static_sfm FEG1/NL2/NTX3/SAFE_RC1/SRAMV2/TXDP030304aa. Abort output comes solely from u_d2d_kv.u_core.ab = u_end.u_link.u_ctl epoch_abort, separate from u_dcal. Inspect first new_fault and sticky fault_cause in that exact link control on the next already-needed native run. The generated existing model retains these names (including new_fault), so a C++ main observer can be added without re-Verilating the full die. Eight fault bits [7:0] = missing observed producer, write collision, unread slot, TX link down, unexpected RX, missing RX, slot/epoch mismatch, CRC mismatch. Do not infer which bit from delayed transport80; it arrives152cycles after initial abort. Existing logs do not publish this first cause.

QC current source is independently strict clean23ef9f36b1 (377parts119types; results/qc_die33_1029/bind/README.md). Previous0845 stale-cache/R8 bind4 failures have been superseded, not rerun. Current source/physical mismatch: native PROG u_pg MIF0 vs SIGNED ffh10r/4513968c1 MIF1(+1 read/write). QC owner owns plain OWNER? adoption versus MIF0 hardening; no silent profile change. Fresh QC programme/GEN/HOST integration must use an explicitly agreed profile.

No RTL changes or cycle/rate claims in this receipt. No new jobs, kills or merges.
