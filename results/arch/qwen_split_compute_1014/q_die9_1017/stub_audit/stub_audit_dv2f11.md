# Qwen compute die dv2f11: stub / tie audit (0da rules), 10-17

Netlist `ot-epyc4:.../qwen-split-compute/dv2f11/chain/case_r22k/die.v` (sha256 0ba499b6…), strap manifest `q_slice_1017/straps_dv2f8.json`.
Full record: `stub_audit_dv2f11.json`.

**Verdict: the die FAILS the no-stub rule.** The recorded port-bind PASS holds at the die top level, but that tool does not look inside masters.

## Independent re-check at the die top
- 716 instances: 17 functional masters (80 instances) plus 96 relay and reset-repeater masters (636 instances).
- All RTL resolves. 0 unconnected inputs, 0 undriven bits, 0 driven-but-unread bits.
- The constants are exactly the 16 manifest strap ports, 19,421 bits in total.

## Rules (a) to (d)
| rule | verdict | content |
|---|---|---|
| (a) identity | PASS | Cluster `cid` (576 b) feeds only the ROM-leaf tile_id. Cluster `far` (48 b) feeds only the xcst sidx. Off-chip strap bumps: pkg_s0, pkg_s1, die_ps. |
| (b) spare relay bits | N/A | 0 pad bits; every relay is exact width. |
| (c) unused mode | PASS, listed | **Far-cluster `rs_i`** (12,336 b): feeds only the rs_i -> rs_o feedthrough, and rs_o is open on every far instance. That leaves **197k dead flops**; a far variant removes them. **Slice chain ends W5/E5** (3,377 b). **L9 sender `l9_wi`** (3,084 b): the zero word is the idle word. |
| (d) functional config | PASS | No functional config strap at the die top. |

Listed RTL-internal ties:
- documented ones: SFH=0 SFU ports, heads aw_*, tt_ctlm me_mem_ok / cp_active, d2d recovery controls;
- about 20 ties inherited inside qfd_tt_ctlm_head_static, which are NOT individually proven unused.

The open-output classes (chain ends, root-only replicas) still need to be added to the manifest.

## FAIL classes
- **F1 (768 blackbox leaves).** The cluster's children `qfd_tile_{nk,nl}_rp2_romleaf_rr` (48 × 16 instances) have no RTL in `dv2f11/src`.
  - The src overlay is not commit 0df705a29: the ROM-leaf files are absent, and `qfd_tile_nk_rp2_45.sv` and `qfd_dv_slice2.sv` differ from it.
  - The RTL does exist at 0df705a29 (55b6fda33).
  - Owners: **Q-DIEPLAN** (sync src) and **Q-BIND** (die_port_bind must resolve the full child closure).
- **F2 (stale real view).** The `qfd_sys_face` view is from @4458091af, before the G8 re-port. It still carries the pins crom_fault_code and res_issue_fault, which the RTL dropped. Owner: **Q-CTLM** (re-close).
- **F3 (unobservable fault).** `qfd_embedding_word_provider.fault` (preload | store) has no consumer. Owner: **Q-CTLM** (route it into sys_face face_fault / result_cause).
- **F4 (stand-in physical views).** Only 7 masters / 9 of 80 instances have real views, 6 / 8 once the stale sys_face is excluded. The other 71 instances use assumed abstracts, so die GRT/STA is DIAGNOSTIC. Owners:
  - Q-CLUSTER3: c_b16_dv ×48
  - Q-SLICE: slice2 ×12
  - Q-CTLM: tt_ctlm_dv
  - Q-N59: native59_dv_service
  - QC: collective_static_io_production

## WARN
- Fault detail outputs are open, though each summary fault is observed: collective fault_code / cause, d2d transport_fault.
- native59 `completed` is open.
- rstseq `rso_s` is open (the spine reset region is absent on the DV die).
- d2d_static_r5 view provenance is unverified: the RTL changed after gate commit c38379ae2.
