# HA1 actual-capture integration

`ot_hbm_txcount_capture_join` is a hardware adapter, off by default. It captures
Euclid's actual `backend_go_valid && backend_go_ready` with the full239 tuple,
separate original owner55 and declared all-page mask. Native64 tag/generation
are never replaced by backend32 tag/gen4. It directly records accepted guarded
SM common ACKs and actual W6 visible handshakes by matching owner46/slot into
that captured range. The whole producer visibility is an independent accepted
full239 event. All declared ACKs, W6 visibility and whole producer visibility
are required. No timer, manifest-replay arrival, software dictionary or new
clock creates completion. The positive output pipeline contributes one edge;
W4 and W6 can each capture one page on every edge.

The observer retains the context through dependency capture AND actual matched
issuer FRAME retirement. It does not drive publish, RF range aggregate, frame
retirement, source retirement, drain, or next-row barrier readiness. Actual RF
and W6 consumer/source ownership stays canonical. Unsupported zero-RF and
multiple-output GO shapes are not inferred from the first output; the current
one-range issuer must be replaced by its owners before those shapes can enroll.

`install_capture_join.py` generates a sibling of the current real ranked
assembly. It retains every original authority connection byte-for-byte and
adds64 actual capture instances, explicit W6 probes, a portbook and extensions
to the existing pin driver. `canonical_capture_pins.ActualCapturePins` uses the
existing enclosing clock and single shared hook; component('ha1',rank*32+SM)
reads held hardware dependency tuples and drives only its input pin slices.
There is no provider emulation or authority dictionary.

Generate against Euclid's current clean installed source:

```
python3 tools/hbm_accel/install_capture_join.py --base ACTUAL_RANKED_DIRECTORY --out NEW_SIBLING_DIRECTORY
```

Select top `ot_gpu_qwen_hbm_integrated_ranked_ha1` with `ENABLE=1, HA1_ENABLE=1`
only for opt-in integration. The checked-in sibling was generated from main's
installed ranked source; `HA1_base_source_sha256` and `HA1_base_driver_sha256`
record the actual input bodies. The `sources.f` replaces the old top and selects
the additive modules. It does not create another engine, hook or clock.

**W6 binding required:** the original installed ranked top has external W6
receipt observer pins, not an actual W6 instance or visible output. Euclid's
caller must connect each `ha1_w6_visible_valid/ready/owner55/fault` to the actual
fence's `visible_valid/visible_ready/visible_identity/fault`. These cannot be
supplied from ACK, RF idle, a timer, or host state. `ot_hbm_w6_source_select`
selects that actual fence with its unchanged interface: baseline by default,
`LIVE_STATE=1` only for the separately unqualified live-state candidate. The
source-selected context bench binds real W6 outputs directly to the join.

The real guarded-SM + issuer + selected-W6 + capture-join context is
`tb_txcount_installed_context.sv`. Its producer/terminal callers are directed;
it does not stand in for Claude's actual native4 whole engine. The full64SM
source projection is tested; the physical context test uses actual SM leaf33,
not stub arithmetic or a synthetic RF. Both real RF operand mirrors are read
back; scheduler completion must preserve issuer input notifications and W6
consumer/drain debt. The one ongoing Icarus build uses the original arithmetic
and SRAM models; no duplicate build or timing campaign is launched.

Clock status remains unqualified: the known429MHz W6 path is not repaired by
this adapter or selector. The47-cycle target is not adopted. Actual canonical
W6 probe enrollment, whole-native exactness and measured serial composition
remain necessary before area/route/SS60/FF25 and gain adoption. No P&R was
launched, no failed candidate was rescued and the original failed compiler log
is preserved (selector port parsing was corrected before any functional result).
