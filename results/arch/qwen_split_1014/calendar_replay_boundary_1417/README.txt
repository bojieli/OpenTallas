COMPONENT ONLY: actual native replay/controller/front/return ABI proof.

The DUT instantiates source-current real PROFILE0 persistent controller,
pcport/ECC, the4x8 elastic front, DEPTH8 dualclock return ring and two actual
boot-sealed replay leaves (HBM64,CORE33). Only the off-chip PHY return data and
latencies are modeled. One full8-sector/256-bit block is the smallest vehicle
that exercises a real block-ready boundary, fixed front release and CDC ring.
No PROFILE1 discovery, controller output trace, actual-arrival-derived calendar
or runtime ready chooses reservation/release/expected slots. The first refresh
still runs normally; the declared PC0 descriptor/read window precedes it.

Six production-shaped COMPONENT stimuli (phase137/637ps x PHYextra0/8/16cycles)
all return8sectors exactly: 8read/8land/8put/8return/1freed, maxocc8, stall0,
errors0. Four corruptions fail: reservation+1, front release-1, expected sector
XOR1, last PHY response+32beyondwindow. They are failing cases, not production
successes. Late PHY case exercises real front hold; native sequencer pause is
still unimplemented and is NOT qualified by this test.

The independent fixture roots are booted through actual pin-capture/boot FFs.
Epoch7, layer3, row67 and unused HOST signals are declared component boundary
stimuli. This is not a deployed tie for a missing on-chip native producer.
The controller ownership input is held for the declared whole component run;
actual HOST/reader ownership and identity-root parent composition remain OPEN.

Full512sector K+V, all128PC, all36 source programme calendars, writeback/ingest
persistence, clock phases/physical relays, landing consumers and image storage
are absent. Existing static writer and return physical adoption remain HELD.
This result provides no die bind, physical home/slot grant, TT/FF/DRC/native pin
or full-token rate qualification. The default leaf has64events; this one-block
proof cannot be broadened into all36 support. Literal all36 sparse FF replay
is not an accepted production storage design.

Initial fixture failures are preserved separately; source target RTL was not
modified to pass. Final source_manifest and gate SHA were checked against the
current source tree after collecting the real ot-run verdict. Full build and
binary stay in the remote artifact directory until routine cleanup.

Reproduce prepare: python3 tools/qwen_static_kv/check_replay_boundary.py OUT --prepare-only
Run through ot-run: python3 OUT/execute.py OUT --execute-only
