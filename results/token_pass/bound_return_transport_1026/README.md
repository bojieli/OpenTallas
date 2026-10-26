# Actual VN_b partial return to XR (and XR rb broadcast to VN_b)

Source e7461708c, canonical top 1c11db22 / source 003a165c, 381-unit inventory plus exact in-scope
`$buf` glue records from the same-source full inventory (hash-checked). Actual ot-run unit
oth-ubuntu-2697504-1793015027 exit 0: **80/80 leaves PASS_BOUND_RETURN**, entry re-proved
PASS_BOUND_TRANSPORT in the same run (command ages identical to bound_entry_transport_1026).

Return path per RTL (slice/ot_s81sl_slice.sv, ot_s81sl_vn.sv): leaf `ot_s81sl_vn_sp.u_b`
(`ot_s81sl_vn_b`) drives leaf p_v/p_d -> slice `u_up` relay -> XR `p_v[k]`/`p_d[32k+:32]`;
XR `rb_v`/`rb_d` (one copy) -> `u_dn` -> every leaf VN. Each leaf is identified by the actual
bound driver of XR `p_v[k]` (after exact `$buf` A[i]->Y[i] stitching); that driver must be one
VN_b `p_v` output, unique per slice; all 32 `p_d` bits must come from the same VN_b bit-for-bit
with the same age as `p_v`; the VN_b must sit in the same leaf instance as the VP reached by
XR `sw_v[k]`; all 33 `rb_v/rb_d` VN_b inputs must come from XR `rb_*` bit-for-bit with one age.
2,560 p_d + 2,640 rb bits checked; 63,252 buffer-bit proofs across 210 buffers.

Ages (edges, leaf ordinal 0..4) are not uniform, e.g. partial return 0N [3,3,8,11,15],
3N [2,2,6,6,10], 3S [2,2,7,8,14]; range 2..15. rb broadcast equals the command-transport age
per leaf (same u_dn relay), range 2..16. Full per-slice table + VN_b paths in integration.json.

First run (unit oth-ubuntu-2681661-1793014806, exit 2) blocked 56/80: XR p_v inputs are driven by
slice-parent 668-bit `$buf` glue ($23/$25/$27/$29) missing from the 381-unit inventory's
leaf_interfaces; fixed by `--buffer-inventory` (only `$buf`/glue in XR-parent/leaf/VN scopes,
schema/top/asbuilt hashes equal). Initial log retained.

Not included: VN_a->VN_b c_v/c_s split and VN local partial latency, XR capture/reduction,
XG/XFIN/NX returns. Transport only; no production RTL, no token-rate claim.

Rerun (via ot-run, ~1.6 min, 1.6 GB RSS):

```
cd tools/s81_dv && PYTHONPATH=. python3 -m layer_prog.bound_return_transport \
 --bound /srv/opentallas-scratch2/claude/tok-ds/s81_877/v2/out \
 --inventory /srv/opentallas-scratch2/claude/codex-bound-inventory-1026/inventory.vp.json \
 --buffer-inventory /srv/opentallas-scratch2/claude/codex-bound-inventory-1026/inventory.json \
 --out FRESH.json
```

Full record: intel1:/srv/opentallas-scratch2/claude/tok-ds-return-1026/return_transport2.json
(sha256 339ad540...cb834).
