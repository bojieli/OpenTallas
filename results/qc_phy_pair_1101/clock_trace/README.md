# Actual QC SerDes clock-source failure and missing binding contract

This is a source-specific diagnosis of the current `82190c1ff`/`f79c1e228`
acceptance cohort. `trace.json` was extracted read-only from frozen `bd55b15b452`
and its actual `bind_complete4` output. `capture.py` reproduces the extraction
without elaborating, rebinding, compiling or rewriting RTL. The typed candidate
inside the trace is **disabled and refuses emission**. No canonical source or
clock root was changed.

The native design already has the required core/FDI boundary inside each
`qfd_coll_static_face`. Its TX channel writes on `tx_wck=pll_coll` and reads on
`tx_rck=pll_serdesN`; RX writes on `rx_wck=pll_serdesN` and reads on
`rx_rck=pll_coll`. Codec clocks and the link calendar also use `pll_serdesN`.
`qfd_static_ch546` implements the actual storage/channel crossing. The native
face separately synchronizes reset release on its core and link roots.
The physical source design explicitly distinguishes 1.2 GHz core from 1 GHz FDI.

The three native PHY `.clk` pins are driven by `clk_rx.pll_serdes0/1/2`.
The existing source manifest classifies all three with the explicit rule
`pll_serdes(\d) -> serdes`. The binder therefore already has an existing
`clk_serdes` source domain; no new slow mission region is needed.

Two generator choices break that native boundary:

1. `bind.py` emits every normal input/output/FT `ot_dp_st` on the partition's
   default `.clk(clk)`, including the FDI frame buses. `coll_n` and `coll_s`
   have multiple native clock domains and no per-bus station clock contract;
   their default is the manifest's `core`. Their native face still receives
   separate `clk_coll` and `clk_serdes` ports. Therefore even before the landing
   rewrite the newly inserted FDI frame stations do not retain the native FDI
   clock identity.
2. `clock_landings.py` then rewrites every partition's default `.clk(clk_*)`
   to `.clk(clk_region_<region>)`. That includes the bare registered-pin PHYs,
   whose binder-derived sole native domain was `serdes`. The actual wrappers
   now connect the three PHYs to the regions of `coll_n`, `coll_s`, and
   `c_W5_bf_01`. The verifier's generic `clock()` expectation also assumes the
   regional root, so passing that expectation does not establish the original
   FDI clock authority.

The actual failure is consequently wider than three PHY clock pins:

| Current structure | Actual inventory | Current clock |
|---|---:|---|
| FDI RX data/valid/up and TX data/valid bin/bout groups | 15 groups, 3606 payload+epoch FFs | Default regional clock |
| Third PHY's FT stations in `c_W5_bf_00` and `c_W5_bf_01` | 95 groups, 22838 payload+epoch FFs | Default regional clock |
| Native face codec, TX-read and RX-write roots | Three FDI faces | Explicit `clk_serdes` |
| Bare SerDes PHYs | Three | Regional clock substituted for native `serdes` |

The FT counts are the actual emitted `ot_dp_st` groups. They exclude CA landing
rings, FSTART/reset infrastructure, and other storage; they are not a complete
count of every sequential element that a new domain contract would affect.

Direct PHY0/1 data, valid and up lanes each have two bound stages. The routed
logical path to PHY2 is `coll_s -> c_W5_bf_00 -> c_W5_bf_01 -> io_serdes_2`;
its TX lanes have 26 bound stages and RX/up lanes 28. Returning data and FCLK/
FSTART cross those regions in the reverse direction. Existing CA landings and
their fixed count/phase contracts cannot silently be treated as a 6:5 core/FDI
CDC. The native storage channels are inside the face, before/after this added
transport, so they do not protect these newly introduced intermediate sampling
boundaries.

A minimal **coherent** future fix needs typed per-bus domain authority rather
than a three-port string replacement:

- Preserve the proven native `serdes` domain for the three hard PHY `.clk` pins.
- Give all fifteen FDI frame/valid/up boundary groups explicit FDI clock/reset
  roles. Preserve the existing core-domain side of the native CDC channels.
- Carry the same typed roles through both FT regions, including their CA,
  FCLK, FSTART and reset members, or introduce an explicitly priced valid CDC
  contract at a named boundary. A generic count-aligned landing is insufficient.
- Rederive the frame calendars and latency model in explicit domain units for
  direct two-stage and third-path 26/28-stage transport. Keep LS436 and the
  selected profile held until this join; no cycle/time conversion is adopted.
- Update binding and its verifier together. The vehicle may then drive only
  the existing typed FDI source at 1 GHz while mission regions remain 833 ps.
  Driving all regional clocks at 1 GHz would change unrelated mission hardware.

`trace.json.candidate` records the three correct native hard-pin bindings but
has `enabled=false` and `emit_allowed=false` because the rest of this contract
is absent. No partial RTL fix is emitted. This is the precise remaining CDC/
clock-binding dependency, not a claim that the design lacks its native CDC.
The private two-peer models remain useful boundary diagnostics; they do not
qualify this complete interface or any real hard clock provider.
