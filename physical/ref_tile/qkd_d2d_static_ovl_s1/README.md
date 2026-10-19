# qkd_d2d_static_ovl_s1: production codec2 safe structural successor

Root approved this parallel candidate geometry on10-19; final submission still
requires root PNG/checklist review. Prior r7w/ovl_m1 attempts remain immutable
evidence. Sources use TXDP_K0x03030416, NTX3, SAFE_RC1.

The475.2x280.8um outline and portfaces fit the actual KV GEN d2ds frame
777.576x518.376um (KV lead confirmed). Outline area133436.16um2 is unchanged;
new child LEF coordinates require parent boundary/relay pin target regeneration
and native audit. There are zero new data cycles and no reset release edge
change. The codec2 capture edge is already charged in shared1a73e1e7a X8.

SAFE checklist:
1. FIXED: RTL PR1 captures/launches every data pin; kit lands por_n/rst_n in
   two kept stages. Hook anchors actual por_n__ot_rl[01]/rst_n__ot_rl[01].
2. PASS structural reach: native registered boundaries unchanged; gate must
   confirm no critical single-cycle wire >405um after safe placement.
3. FIXED: SAFE_RC1 grows4reset regions to7equal-depth KEPT copies and gives
   TXcalendar/control/slotlink/RXcalendar distinct end resets (NRC4 shared
   mechanism from compute d68c7b7a3). Release/assert edges unchanged. Verify
   copies survive synthesis and report all remaining fanout in gate packet.
4. PASS structural depth: prior codec2 source was483/490ps atTT; reset-only
   changes add no logic/data stage. Reject any new critical arbitration/mux.
5. PASS payload storage: four real64x512 SRAMs store native64x137 replay;
   unused columns masked. Fixed per-port valid marker shift is22/4/3/3 bits,
   control only, not a payload array; flag this literal small-control delay
   exception for root review rather than hiding it as SRAM.
6. FIXED geometry: macro origins(43.2,43.2),(259.2,43.2),(43.2,172.8),
   (259.2,172.8); xgap44.712um, ygap51.816um. W/E pin-face halo20um, N/S5.4um,
   preserving a full-width standard-cell band between macro rows. All exact
   pin groups use full-face track-snapped positions; per-face actual counts
   and used spans in pin_geometry_plan.json (max4.722pins/um). Clock E near
   band centre. Total fill from measured predecessor~45.5%; gate remeasures.
7. PASS structural clock plan: single sub-mm root with local20sink/40um CTS;
   io_hold_margin0.030; TT/FF pin-flop spread must be<=80ps and every native
   macro/parent boundary must pass matched reference checks.
8. PASS static schedule: no credit/backpressure, no new functional edges;
   shared production codec2 calendar/list ages pinned to1a73e1e7a.

Native macro escape is NOT inferred from raw pin count: each physical macro
face has~10.43pins/um, including constant masks/unused columns. Only137 read
+137 write payload bits are live, plus addresses/writeenable/clock; native
route/pin access and clock-boundary proof remain required. The20um W/E halo
is reserved for real escape rather than standard-cell packing. Gate trial
GRT0 and subsequent native audit are required; no raw-density waiver claimed.

Bench KRC1/KDLY19 runs full pair, NTX3lockstep and OVLuser slots; mutants
slot/portlock/user/RXstart must fail with distinct committed safe witnesses.
Legacy SAFE_RC0 remains default for closed masters.
