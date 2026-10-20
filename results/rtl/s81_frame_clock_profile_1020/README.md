# Actual-source S81 frame clock preflight (REFUSED)

`tools/s81_dv/frame_clock_profile.py` is an opt-in auditor and guarded clock
classification/SDC emitter. It changes no existing kit, LP generator, gate,
clock constraint or hard view. Current h9 and h10 both **REFUSE**. No FRAME
clock adoption, physical launch, shared-landing phase certificate or prefetch
age is authorized by this packet.

The two JSONs bind every inspected source/view by SHA256. They validate each
actual xk[k] fanout to u_cf/xk[k] and u_xo{k}/ck and both corresponding 276-bit
input slices; CFIFO g_lane[k] uses W276/D4, ck_f=xk[k], ck=cr and the real lk
strap. They include all eight clock pins, including the four FIFO writer-only
pins with setup/hold checks and no clock-to-Q launch arcs. Per-clock routed
insertion.json references exist at TT and FF. These are child reference
measurements, **not parent linked-child timing**.

The sole actual-view error in each frame is at BOTH corners of
physical/ref_tile/s81dv_rly_276_ns/views/dsfd_dvrly_276_NS:

* Source RTL has u_ck0 ck->ckn and u_ck1 ckn->ck_o, each kept inverter, so
  the intended physical forward phase is noninverted.
* Both Liberty ck_o blocks instead have related_pin="ck_o" rising_edge and
  falling_edge SELF arcs. Neither has a real positive_unate combinational
  ck->ck_o arc. Exact source and TT/FF Liberty SHAs and the offending arc
  classifications are in each JSON.
* The auditor refuses to emit any SDC on these inputs. It never repairs a
  Liberty arc, manufactures insertion, reclassifies xk as core data, adds a
  false path/multicycle, or treats a maximum data arrival as a clock arrival.

Five pure parser/emitter regression tests pass (`unit.log`), including
regenerated-manifest wrong-clock/lane-output mutants; missing/wrong setup,
hold, forwarding related pin, sense/type/table and nonfinite/negative delay
rejections. The synthetic emitter coupon asserts four separate real root
create_clock commands. No synthetic library is installed in a hard view.

Truthful forwarding view re-extraction remains necessary, followed by actual
parent TT/FF propagated clock/phase measurements, all eight child clock pins,
linked u_cf/u_xo boundary intervals <=80ps, finite writer setup/hold and the
compiler's real K/reader-phase/reset-first-active-edge certificate. Null
certificate fields are deliberate. No default read age or epoch is supplied.

## Unqualified native stopping point

`unqualified_native_repro/` is a separate, explicitly **UNQUALIFIED SYNTHETIC**
OpenROAD algorithm experiment, kept only to make its failure reproducible.
It contains exact hard.lib/LEF, top.v and run.tcl (clock SDC is inline), the
prototype audit.tcl and failure.log. It does not use or fix production views.
The actual clock pins yield propagated clock tags, but the synthetic relay
CKO has no unique propagated min-rise clock tag; the prototype therefore
fails closed before any clock PASS. The fixture includes a combinational
create_generated_clock only after its synthetic claimed CK->CKO arc; that
command does not establish the missing production-view edge/phase.

Reproduction on the fleet (OpenROAD 26Q3-1510-g6cb3f2b704 as in failure.log):

```
docker run --rm -v "$PWD:/w" openroad/orfs:latest \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad \
  -no_init -exit /w/run.tcl
```

Do not source that prototype into a production kit. There is no native clock
qualification claim, no tested production runtime gate hook in this change,
and no permission to omit the actual forwarding path.
