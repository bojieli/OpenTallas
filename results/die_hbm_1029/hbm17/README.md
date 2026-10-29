# DIE-HBM-17 (2026-10-29) — HBM plan fix event c25c_d16k, outline rulings, RR80 / VM estimates

All geometry numbers are plan estimates, UNCHECKED until NUMBER-CHECK (12.9f), unless marked CHECKED.

## 1. Plan candidate c25c_d16k (sha256 f20e424277f7), intel2:/srv/opentallas-scratch2/claude/die-hbm-17/c25c_d16k
Chain: c25c_d16 (6ba9f877d23f) -> DIE-HBM-16 d16f (KITS-12 asks: hcol_h0 cs_in/cf_in pins, vmdel 142.56x116.64,
idx_qctl 203.472x82.08) -> Codex g21 (466 secondary clock pins in 45 tables to M5 interior, keybuf 16 entries,
lane_exp0 six SRAM columns; sha 6ca3340bee27) -> Codex QCORE V1 293.76x207.36 + SFUSTORE V1 362.88x388.8 with stored
station endpoints + station_resite (NW 437 / NE 430 bad FF homes -> 0, +0 cycles; sha f71d59c2f98b) -> DIE-HBM-17:
 - entry_fix.py: sfustore V1 clock entry was over g_bank[1] (new G0C clock_entry_macro ERROR) -> core centre street.
 - core_face_repin.py (DIE-HBM-15 tool, --types q_hub_ne,q_hub_nw --suffix fr17): sfustore 'fault' port faced away
   on q_hub_ne u_sfus_Q__q1 after the reshape -> E face; all 4 instances score 0.65..0.99 (fr17_report.json).
Checks (CHECKED, check.py on main f483150e0): G0 PASS 0 errors; G0C 10 errors = exactly the 10 inherited d16f errors
(set diff empty): q_spb0(+pv1) u_ep_S0 sd_tx, 8 hub vmb ports (no face lowers the FAIL count). g21 alone also = 10;
f71d59c2f98b alone = 11 + clock_entry_macro (fixed here).
Visual: d16k_cores.png (sfustore x4, qcore q1 x2, vmdel, qctl neighbourhoods; viewed): grown cores clear of neighbours
+ 4.32 halo, stations (blue) outside the bodies.

## 2. Outline rulings for the KITS-14 ASK (2 variants each; built by HBM-CORES-KITS-17)
In-place fit search (outline_fit_search.py, 4.32 lattice, non-overlap incl. 4.32 halo, all 4 hub instances):
| core | V1 | V2 | fit |
| qcore_r13 | 293.76x207.36 (in d16k) | 267.84x250.56 | both 0 um shift |
| sfustore_hw | 362.88x388.8 3x6 (in d16k) | 345.6x354.24 3x6, 10.8 gaps | both fit; B2n 561.6x276.48 NOFIT on NE (<302 um) |
| cxport_ij_q | 345.6x250.56, S 2115 pins -> 6.1/um, >=45 to W/E corners | 241.92x233.28, S on M5+M3 4.4/um/layer | <=9 um / 0 |
| vmdel, qctl, hcol_h0, lanes8_11, lane_exp0 | d16k tables (plan fix) | - | in d16k |
| programme_pslice_c5 | no build: 100 SRAM 389,385 um2 = 54.5% of 939.6x760.32; 1080x864 grow NOFIT; column-slice split = RTL partition change, estimate next | | |
cxport fill 0.061 / r2r 488 says the core is too large for its logic; the binding limit is the S face (2115 pins on
250.56 um = 8.4/um), so both variants shorten the core and fix the S face density.

## 3. RR_RT80 (DMA request->response budget 80 cycles) — estimate (inputs from Codex 09:0x, CHECKED there)
Deficits per DMA group [39,33,43,41,63,57,67,61] cycles; native bank intrinsic 7 cycles.
 (a) request padding: 6,868 FF bits, but shifts memory read sample dates -> needs a new qualified read/version calendar.
 (b) response padding: 103,828 bits total (~6.5 kb per group) -> one small 1R1W SRAM FIFO per group (16 macros),
     read dates unchanged, no calendar change. Area ~16 x 0.02 mm2 class (UNCHECKED).
 (c) raise the budget to the measured round trip (~150 cycles) with a credit/tag return: no padding, but the
     controller and the token model change (DMA latency +~70 cycles per round trip; tok/s effect UNCHECKED).
Recommendation: (b). DEFAULT: (b).

## 4. VM capacity — programme a122 live set 399,360 words > regular VM 262,144 (short 137,216, +52%) (Codex CHECKED)
 (A) grown VM (source on main d0b824a: 32 banks 3->4 SRAM, regular 524,288 words): +33% VM SRAM, 16 vms bank cores
     per hub grow (upper bound ~+0.6 mm2 per hub, hub core fill 55% -> ~57%, UNCHECKED), plus real 17-bit writers,
     multirow INDEX, re-kit of 32 bank cores and a hub re-pack -> delays the HBM plan freeze.
 (B) compiler finite phases for a122 (split the 4 disjoint live sets so <=262,144 are live): no physical change;
     price ~0.36% DS / 0.08% QW tok/s per added VM record (Codex conditional price, UNCHECKED), 1-2 records expected.
 (C) drop a122 from the HBM release scope.
Recommendation: (B). DEFAULT: (B); (A) only if more programmes exceed 262,144.

## 5. SPB G2 hotspot variants (epyc2, Codex live jobs adopted)
See section appended at collection.
