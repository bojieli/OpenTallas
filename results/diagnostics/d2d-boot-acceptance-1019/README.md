# Boot acceptance: ordering prerequisite falsified at HOST boundary

The selected HOST source does **not** order boot_go after accepted calendar installation. This is a source transition proof, not a claim that a native GEN8 application counterexample has been simulated. The frozen GEN8 D2D is FRAME/bind=null, so a fully composed native receiver/reset/first-use trace is unavailable. The certified clone partition stays empty and all original canonical endpoints remain required.

Source is 5f2ce19bc; continuation driver cda9d9f9d. DCAL_BC=1, no BC4/FLT; actual TXDP=0x03030416. `manifest.json` hashes exact remote HOST/reset inputs and the prior packet's matching calendar sources. `die_connections.json` records actual pre-expansion connections (die SHA00a3de7c). The frozen run's stale READY_FOR_CHAIN marker is not token readiness; strict bind still failed, and this packet changes nothing live.

## Exact finite countertrace at the HOST source interface

Choose a stable legal die_id and raw POR assertion/release. Let the existing link training complete while no host program image is sent. An idle host program channel has no requirement to deliver target11 before link training. Do not force any internal reset or boot signal. The trace can wait for real link training; it does not depend on a particular early reset-arrival race.

`ot_qwen_sys_rst_seq` has only POR, soft_rst, link_up, boot_done and boot_ok inputs. It has no programme-installation or calendar-acceptance input. Its actual transitions are:

| Source edge / condition | Actual transition | Accepted target11 words |
|---|---|---:|
| S_POR, t>=4 | link_rst_n=1, S_LINK, t=0 | 0 |
| S_LINK, all real link_up high | hbm_rst_n=1, S_HBM, t=0 | 0 |
| S_HBM, old t=0..3 | remain S_HBM | 0 |
| S_HBM, old t=4 | boot_go=1, S_HBMW | 0 |

No boot_done/boot_ok input is required until the later S_HBMW state. `qkd_host_rst_role_pins` registers the selected bg[peer] into boot_go when role_valid and !role_fault. It does not inspect static_setup_ready. The selected admission root uses static_setup_ready in program_ready and service readiness; its reset-control path passes through independently. The exact die connects host.boot_go to d2d_kv.host_boot_begin directly, d2d_kv.fwd_epoch to dcal.ego directly, and both D2D/DCAL to the link-reset family. Consequently even **emission** of the first target11 word is not a prerequisite of the real HOST boot pulse. The stronger proposed theorem, all66 accepted before that pulse, is false at this interface.

This trace does not assert that external link_up may be forged. It applies when actual link training finishes without a host image; no source dependency from installed image to this transition exists. Source/native binding of the real FRAME producer and its training/reset timing remains missing. A claim of an absolute first consumer edge or integrated failure would exceed this evidence.

## Downstream consequence, with its precise qualification

The existing recovery source in `ot_qwen_d2d_services.sv` launches fep from S_RUN when MASTER && boot_begin && !bq; installation is not an input. Its local eq/BUMP and epoch outputs also lack installation state. In the private mapped SF family the same branch exists, with real copied state and priority. These sources support the same logical hazard, but neither is promoted into a missing GEN8 native binding by this packet.

For an epoch received after DCAL local reset and its suppressed constant-init sequence have completed, the **actual selected BC source** sets its inner epoch counter and emits the admission start at EP_SKEW-2+D2D_ADM_OFS (1+72). That start is independent of btx_seen/brx_seen. With no boot words, both seen bits remain zero: n_early becomes1, fault becomes sticky, and cal_start is still registered high. The 66 inner init writes were suppressed by s_rdy/rdy_q, so they do not install the D2D table. This is an exact source implication, conditional on the real epoch delivery and no intervening halt; it is not a native or full-die execution receipt. An already asserted halt/abort may stop the path, and cannot be assumed absent from arbitrary uninitialised D2D histories.

The last-write W / prefetch W+1 / start>=W+2 lemma therefore cannot be applied to the HOST trace: W does not exist. Fault detection is not a table-installation handshake. G7 fixture kind4 is unrelated to this GEN8 source; the frozen MU calendar's real early token STATUS is kind15 at+15, preceding CMD at+891. Neither can be discarded to manufacture a later valid frontier.

## Stale replay SRAM obligation

Because the actual boot/reset/epoch prerequisite fails, this packet does not certify the downstream SRAM lifetime theorem. The existing SF slot controller has a real useful guard: an unread v1 sets epoch_abort before the corresponding v3 can assert p_tx_v (with aligned reset, epoch, clock and slot-copy identities). A same-slot cmd_wv is the explicit immediate-write exception; age0/age1 storage bypasses must then carry that exact owned write. The source also clears written-map quarters on their actual resets/epoch copies. Those facts do not prove the absent native composition, nor permit assuming old SRAM, wq/aq/dq/dqq/select/output registers equal after reset. A residual unreset macro write is allowed; its contents become safe only when a later authoritative read is dominated by a correct owned write or the exact bypass. No zero SRAM or quiet interval is assumed.

## Implementable guard direction for ROOT review

Separate the existing power/HBM boot pulse from launch of the first D2D calendar epoch. Derive a registered installation receipt at the **actual acceptance point**, tracking all64 table entries plus both bases while their calendars are stopped, with image/epoch identity. After the last accepted write W, include the real prefetch update at W+1 and allow the first sampled start at W+2 or later, with no intervening reset/configuration divergence. Join this receipt to the actual producer-reset/valid frontier before launching the epoch. Preserve EARLY/COL/RUN faults and fail-stop semantics; do not silently postpone ordinary anchored token starts or retract accepted HOST transactions.

This is a structural proposal for review, not authorized RTL. It needs a priced initial-epoch/reset contract and actual native FRAME replacement/binding. A dispatcher emitted-count flag, cal_ready, a fixed waiting mask, or a token-CMD/A0 window cannot implement this proof. Re-run the minimum exact source cone with early epoch, one rejected write, wrong base, residual SRAM-write and first-authoritative STATUS mutants only after ROOT selects that contract. No constructor, integration, simulation, synthesis or physical run was launched here.
