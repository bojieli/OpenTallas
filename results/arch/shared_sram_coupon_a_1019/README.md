# Shared SRAM Stage A native union coupon

ROOT authorized Stage A only, via Qwen lead after method aeeb6dd65. No B/C,
production view, signal routing, PG/PDN, timing, or whole-master qualification.
This preparation has no native geometry verdict yet.

Inputs: exact Qwen5666def40 and SC2e91e03803, input hashes checked by prepare.py.
SC2 model supplies unchanged PG neighbor rectangles; native tech SHA7694bf4f.
Image openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29;
actual binary SHA21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846,
version26Q3-1510-g6cb3f2b704. Exact upstream checker source is retained in method
aeeb6dd65. Fixed-only RECTONLY can be suppressed and non-ORTH WIDTHTABLE is not
imported by DRT, so no zero-marker result establishes all PDK legality.

Preflight correction: neither exact source has an east read output. Actual
rd_out[0] is W and first actual E pin (wd_in[25]/wd_in[70]) is a separate case.
Source joins and actual distant r_ce via columns get independent crops. All
same-net/cross-net shapes including PG intersecting +/-500nm halo retained;
only inner +/-200nm ROI is scored. Native VIA45 cut and both metal enclosures
are preserved and compared against actual loaded tech shapes. Translations are
multiples of48nm, preserving source phase. Explicit M4/M5 TRACKS and GCELLGRID.
Every metal rectangle is emitted as an actual REGULAR dbWire segment or patch;
all-fixed case is the explicit visibility negative. No repair command exists.

17 cases,195 rectangles,19 complete vias including neighbors. Seven controls:
aligned rectangle,9nm shifted join,fixed equivalent,23nm cross-net gap,
disconnected contact,old track phase,33nm width. Disconnected contact has two
components in an independent layer/rectangle/via geometry graph; source target
crops each have one. Integer DBU=1nm manufacturing grid makes subgrid control
unsupported, not fabricated. Old phase/33nm are coverage probes, not presumed
DRC failures. Initial container PATH failure is preserved with corrected
absolute binary preflight. Requested admission1CPU/4GB/2GB, unpinned ot-run.
Actual RSS/disk/runtime and complete original markers to follow execution.
