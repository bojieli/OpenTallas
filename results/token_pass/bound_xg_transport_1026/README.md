# Actual VQ xf -> XG forward, XG ring/V neighbour boundary (NX carrier), XG <-> XFIN endpoints

Source d101abeda, canonical top 1c11db22 / source 003a165c, 381-unit inventory + hash-checked in-scope `$buf`
glue from the same-source full inventory (1,900 slice/leaf + 48 slice-block/top buffers). Actual ot-run unit
oth-ubuntu-2728974-1793015563 on intel1, exit 0, 1:38, 1.57 GB RSS. Entry (PASS_BOUND_TRANSPORT) and return
(PASS_BOUND_RETURN) re-proved in the same run. 102,696 buffer-bit proofs.

| contract | verdict | count |
|---|---|---|
| XG: leaf VQ xf_v/xf_s/xf -> XG xf_v[k]/xf_s[k]/xf[276k+:276] | PASS_BOUND_XG_FORWARD | 80/80 leaves, 278 bits each |
| NX: XG ro_e->ri_w, ro_w->ri_e, vo->vi between slices | PASS_BOUND_NX_BOUNDARY | 38 neighbour hops, 10 die edges, 0 blocked (48 words) |
| XFIN: XG nx_wi/nx_ei -> XFIN wi_*/ei_*, XFIN eo_*/wo_* -> XG nx_eo/nx_wo, XFIN rb -> XR x_rb | PASS_BOUND_XFIN_ENDPOINTS | 16/16 slices, 725 bits each |

RTL correction to the task framing: the xf path is leaf `u_vq` -> slice `u_up` -> XG (XR is not on it), and
nx_* is the intra-slice XG<->XFIN port; NX crosses slices inside K_NX ring words (ro_e/ro_w) or V words (vo).

Ages (bound edges, transport only):
- XG forward per leaf ordinal 0..4 = the partial-return age of the same leaf (same u_up relay), e.g.
  0N [3,3,8,11,15], 3N [2,2,6,6,10], 3S [2,2,7,8,14]; range 2..15. Valid/strobe/payload one age per leaf.
- Ring E/W: each tier is a chain sid order 0..7 (N: 0N->1N->..->7N via ro_e->ri_w, back via ro_w->ri_e; S same);
  every hop 2 edges. Die edges: 0N/0S ri_w from u_hbc / u_lep (3 / 2), 7N/7S ri_e from u_lep (2).
- V (N<->S partner, vo->vi): 22..27 edges for slices 0,1,2,5,7 (e.g. 0N->0S 22, 0S->0N 27); slices 3,4,6 vi is
  driven by die services (u_gunit, u_bk_sel, u_seqhost, u_eng; 18..69), recorded as EDGE_EXTERNAL.
- XG <-> XFIN and XFIN -> XR: 0 edges (direct within u_sl) in every slice.

XFIN records: all 16 `ot_s81dv_xfin` leaf interfaces are already in both inventory.vp.json and inventory.json
(identical); no new inventory parse was needed.

Not included: ring-stop / XFIN / XR local latency, NX routing policy (map_e/map_w, tier), correctness of the
external drivers at die edges, output-side die edges (0N/0S ro_w, 7N/7S ro_e). Transport only; no RTL change,
no token-rate claim.

Rerun (via ot-run, ~1.6 min, 1.6 GB RSS):

```
cd tools/s81_dv && PYTHONPATH=. python3 -m layer_prog.bound_xg_transport \
 --bound /srv/opentallas-scratch2/claude/tok-ds/s81_877/v2/out \
 --inventory /srv/opentallas-scratch2/claude/codex-bound-inventory-1026/inventory.vp.json \
 --buffer-inventory /srv/opentallas-scratch2/claude/codex-bound-inventory-1026/inventory.json \
 --out FRESH.json
```

Full record = integration.json (also intel1:/srv/opentallas-scratch2/claude/tok-ds-xg-1026/xg_transport1.json,
sha256 76d05b46...d907d). Unit tests: `PYTHONPATH=. python3 -m unittest layer_prog.test_bound_xg_transport`.
