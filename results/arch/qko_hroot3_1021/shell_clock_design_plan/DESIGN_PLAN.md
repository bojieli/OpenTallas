# Shell per-domain clock design plan only

Authorized bounded follow-up for terminal s3a/s3b source f102e8cbcb36e0c5f757bb57c44267ee8ea45b38. No RTL, ports, state, clock relationships or latency change. No source/kit/helper edit, new variant, gate, submit, merge or review. ROOTintegration exclusively owns the supported adapter and its qualification. This packet extracts existing mapped artifacts; it launches no synthesis, timing, formal or audit campaign.

## Exact existing load ownership

Both existing pre-CTS mapped netlists contain1471 standard FF CLK terminals: ck_core653, ck_host661, ck_ingest157; all direct root connections. Full actual instance/master/pin/root membership and mapped hashes are in root_load_ownership.json; compressed original mapped netlists are included. The six raw SRAM physical clock ITerms, all master ot_sram_1r1w2c_32x546_m1_p192_mir, match the frozen selected soft_root_macro_bindings:

| Domain | Standard FF CLK pins | Raw SRAM clock pins | Total direct physical terminals |
|---|---:|---|---:|
| ck_core |653|u_ot_pr_core.u_rank__u_qm.u_oxm/rclk|654|
| ck_host |661|u_ot_pr_core.u_rank__u_qm.u_hxm/wclk; u_ot_pr_core.u_rank__u_qm.u_cxm/rclk|663|
| ck_ingest |157|u_ot_pr_core.u_rank__u_qm.u_hxm/rclk; u_ot_pr_core.u_rank__u_qm.u_oxm/wclk; u_ot_pr_core.u_rank__u_qm.u_cxm/wclk|160|

These are unique mapped electrical terminals, not substitutes for OpenSTA all_registers clock-sink counts. The existing actual CTS measurements report core654/host727/ingest158 sinks (when reached); the reporting bases differ and are preserved explicitly. No subtraction of that difference is used as an exemption. Source ownership is unchanged: ox read/core output capture+flow core pin regs on core; host input capture/hx writer/cx reader/t_d/host reset on host; hx reader/ox+cx writers/engine-face control+ingest reset on ingest. All exact named FFs are listed, avoiding a name-based waiver.

Existing macro placement: s3a column x86.4, ox/hx/cx y43.2/237.6/432.0 (hx MY, othersR0), outline388.8x648; s3b exact geometry remains its frozen source spec. Existing clock entry domains and periods remain independent core833.333ps,host1000ps,ingest1666.667ps. No common-phase inference or CDC/reset-scope change.

## Existing supported primitive path; adapter remains open

physical/common_flow/clock_spine.tcl already provides ot_clock_spines with OT_SPINE_PORTS and independent uniquely named per-domain trees, rebuilding occupancy between roots. Its actual per-root input-pin traversal and legal-site placement offer the spatial distribution needed by these interleaved sinks. Plan: adapter selects exactly ck_core,ck_host,ck_ingest through this existing multi-port implementation; each tree owns only its original root net's clock terms. Keep six explicit raw-memory source bindings checked by clock_entries.tcl. OT_SPINE_MACRO_LEAF=1 and OT_SPINE_MACRO_PIN_LEAF=1 give every actual SRAM clock ITerm its own leaf; no macro pin is omitted or reassigned.

The read-only PCsr11a/b reference02f43ebef uses OT_SPINE_PORTS=ck,hck, OT_SPINE_BIN30,OT_SPINE_LEAF_N16,OT_SPINE_ITERS10,RC_CAL0 with symmetric/main or nonsymmetric/fallback distribution. It is a structural design reference, not a qualified shell setting. The existing spine default bin60/leaf8/segment150um and measured balancing are documented in the pinned helper; ROOTintegration must own final supported selection. No new wrapper or alternative helper is implemented here. There are no hard-child insertion offsets to invent: these are raw SRAM clock pins with actual macro Liberty timing, not closed child ETM clock entries.

The active schema blocks pre_cts_extra for multiple_cts_roots, and the generated pre_cts currently installs clock_entries.tcl without a spine. Copying the PC custom pre_cts hook would bypass that supported boundary and is forbidden. Required ROOT adapter must preserve root coverage/raw-memory ownership and the generated original clock_entry.sdc before/after independent spatial trees; no all-clock TritonCTS pass may rebalance already owned spine nets. Existing spine rest filtering excludes owned nets, but integration order/ownership is an adapter obligation, not solved by an unsupported spec edit.

Existing failure basis: s3a core55.1ps PASS/host123.6ps FAIL; s3b core58.6/host54.8PASS/ingest162.3FAIL. Final ordinary TT and FF boundary spread<=80, exact all-root coverage, native fanout, reset/CDC source binding and normal physical gate still decide any successor. This design plan makes no clock closure or adoption claim. Preserve e4a/n34b and all admitted routes unchanged.
