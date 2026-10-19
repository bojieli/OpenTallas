# D2D boot erasure and first use: HOLD

Read-only continuation of ce59f4b7e. The certified clone endpoint partition remains **empty**. Preserve the original mapped canonical roots on every affected endpoint. This packet supplies a narrower erasure obligation and actual boot event identities; it does not authorize a source constructor, startup waiver, integration, synthesis or physical run.

The mapped reset result is unchanged: with the primary reset continuously low and a running digital clock, face2 + regional2 guarantees local assertion only after edge E4. Clean release takes six updates, and the consumer samples active D on the next edge. Those counts concern the private mapped source c5449c82545c; they are not an absolute GEN8 first-use time or a physical POR/phase qualification. Arbitrary old-Q divergence before local assertion remains admissible and may gate unreset calendar writes.

## Exact selected boot path

`frozen_binding.json` captures the frozen v4 recipe, immutable pre-expansion die instance statements, exporter selection, and matching dependency-manifest hashes. Original generated source is 5f2ce19bc; continuation driver is cda9d9f9d. DCAL_BC=1 selects `qkd_d2d_cal_seq_pin_bc` (9c43fc17...), not the newer CLOSED BC4/fault-lane source. Its inner sequencer source is 5edaee7a..., MU wrapper 5ed29807..., dispatcher d98fa56b..., and selected public `_mu_ba` ctl df665451.... Actual D2D selection is FRAME / bind=null with TXDP 0x03030416. The private component's 0x03030403 cannot stand in for it.

The path is selected `_mu_ba` ctl / `qkd_static_kv_boot_dispatch(LINKCFG=1)` -> two die cfg relays -> DCAL boot pin capture -> DCAL merge output register -> D2D dcfg group. The D2D FRAME lacks the native internal binding needed to compose this with the mapped reset and consumer graph. The source of host boot_go and its global relation to all reset families and accepted calendar writes remains an explicit composition prerequisite.

## What boot can erase

Each TX/RX calendar contains 32 unreset 32-bit `e` registers; a write is accepted only on `cfg_we && !running && !cfg_addr[AW]` at its exact address. The two unreset one-hot segment-base copies accept the decoded base only on `cfg_we && !running && cfg_addr[AW]`. `first0_q`, `first1_q` and `cfg_recent` are also unreset and update every edge. Reset clears the running, pointer, interval, event and fault state, but does not clear these image/prefetch registers.

Target 11 emits 66 ordered words: even/odd words 0..63 write TX/RX entries 0..31; word64 writes the TX base and word65 the RX base at address32. The dispatcher checks address sequence, count, target, epoch, padding and execution_active. It marks linkcfg_done after its emitted count reaches66. It receives no acknowledgement of individual calendar acceptance. Therefore linkcfg_done/setup_ready cannot alone prove all calendar entries were overwritten.

BC deliberately suppresses the inner sequencer's 66 constant init writes. Its cal_ready reports completion of that suppressed init, rather than accepted boot-table installation. BC tracks two boot base words, not the 64 table writes. COL, RUN, STALE and EARLY set sticky fault; they do not suppress the registered cal_start or convert it into an acceptance handshake. The inner sequencer likewise raises fault and still emits start on an early admission/go. No full-table acceptance or no-early-start theorem follows merely from fault existence.

A sufficient calendar-only erasure lemma is precise: after actual local assertion has equalized both copies' reset state, require no start until every table entry and base has been ACCEPTED with the same correct values while stopped. Let W be the last accepted write. At W+1, both prefetch words reflect the final image; cfg_recent clears if cfg_we is low. A start sampled at W+2 or later then reads the settled prefetch and clears the cfg_recent overlap condition, provided no intervening configuration/start/halt divergence occurs. This is a source-derived necessary proof contract, not an established legal boot trace and not permission to impose a quiet interval. A bare full emission count is insufficient. If a start occurred earlier, equal image contents alone do not erase the divergent running/cur/cnt/fault history; a real later reset or an exact noninterference proof is still needed.

## Other persistent state

The first-state boundary of all eight proposed cloned roots is reset-capable, as ce59 records, but that is not a lifetime proof. Recovery begin_now/ebc can affect epoch increment, selective written-map clear, slot/epoch pipelines and fault priority before reset. POR resets epoch; link reset alone does not. Preserve the actual priority: recovery's state case can override begin_now, and end/link faults and epoch_begin have their existing ordering.

The replay SRAM and its wq/aq/dq/dqq/select/output registers are unreset. Old SRAM contents need not be erased to prove application noninterference, but every authoritative read must follow a real owned write or the exact age0/age1 bypass. The reset/epoch-cleared written map and valid pipeline provide candidate ownership guards; their complete first-use proof, including a residual write after local assertion and mismatched regional reset arrival, is not present here. No zero-initial SRAM, no fabricated epoch, and no assumed equality of old clone Q are allowed. Unreset payload/CRC/register chains similarly need their real valid frontier rather than numerical equality of irrelevant data.

## Earliest real event identities

`audit.py` decodes the exact frozen MU image (no RTL simulation). Offsets below are at the calendar engine relative to its sampled start; add actual producer, relay, receiver and reset identities before using them at a consumer.

| Run | First relevant event | Calendar offset |
|---|---|---:|
| Admission segment2 TX | HOST BEGIN/AUTH, port1 kind13 beats1/2 | +3 / +4 |
| Admission segment2 RX | HOST WITNESS, port1 kind14 beat1 | +1094 |
| Token segment1 RX | STATUS, port2 kind15 | +15 |
| Token segment1 RX | First attention CMD, port0 kind1 | +891 |
| Token segment1 RX | Attention Q, port0 kind2 beats0..31 | +892..923 |
| Token segment1 RX | STATUS, port2 kind15 | +924 |
| Layer segment0 RX | Attention CMD / Q | +619 / +620..651 |

Admission is anchored at72 and token at1176 in the image; these are compiled schedule values, not a measured release-relative first-authority edge. In particular, waiting until first CMD misses the legitimate earlier STATUS and HOST admission traffic. A monitor may become authoritative only from the real producer-reset/valid provenance and must then remain armed through idle; token A0 or trace_on is not an erasure proof.

## Implementable direction for ROOT review

Keep the eight original canonical roots and all current endpoint assignments. First compose the actual frozen host boot/reset path with the calendar accepted-write predicates and receiver valid frontier. A minimum source proof can compare arbitrary pre-reset histories through the real boot stream, record all66 accepted writes and actual base/prefetch states, and show no earlier start/observation or retained side effect. Include early start, skipped/rejected table write, wrong base, first-authoritative malformed STATUS/CMD, stale SRAM ownership and reset-arrival mutants; faults must be observed rather than masked. Only then propose a nonempty endpoint partition and price its real reset/copy/transport cost. If actual legal boot permits an observable divergence, return a counterexample and retain HOLD for a ROOT-approved structural source redesign. This packet establishes neither such a legal counterexample nor a safe clone partition.
