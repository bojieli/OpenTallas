# AHUB current plan: source proof next, physical export dependencies explicit

Status: bounded read-only pickup complete; source-proof proposal only. No RTL, simulation, synthesis, gate, route or binding was changed. Source checkout is frozen `5f2ce19bc`; `identity.json` records 14 exact paths. Existing model `b0efcc85b` and returned gate packets `648281887` / `f03b0a06f` remain authoritative historical evidence.

## Reconciled source identity

The actual selected generator at `kv_static_die.py:1492` binds `qkd_ahub_static_dw`, not the optional safe-face native module. Its selected source SHA is `15c402899c814a44f48e54cf4bd562419a831357f21d1078b6b3abf64e450a6b`, byte-identical to the baseline source preserved by the structural model. Both safe source and fixed `safe_gen7` wrapper are absent from this selected commit. Therefore the 3,420 FF / 1,611.14832 um2 safe-face census and sfa/sfb physical failures characterize that separate candidate, not the selected baseline implementation.

All six selected child LEF/TT/FF files match the failed-gate model hashes exactly. This confirms the access defect remains relevant to the selected child views. It does not prove that a new parent source has the same arithmetic or calendar as either vehicle.

| Contract | Selected baseline | Failed safe-face profile |
|---|---|---|
| Module | qkd_ahub_static_dw | safe native/face emitted source |
| ZW / ZR relay edges | 0 / 0 defaults | 0 / 0 fixed |
| RX / RY relay edges | 1 / 1 defaults | 1 / 2 fixed |
| RS / WF relay parameters | absent | 1 / 1 fixed |
| Reciprocal return | issue +67+RX+RY =69 default | issue +67+RS+RX+RY =71 |
| AP / FR constants | default +2 /0; binding may override | [-40,-40,-38,-39] /-7 fixed |
| Export target | PV_START+R+FR_OFS | PV_START+R+FR_OFS-WF_RLY |

The selected generator can bind Z_IN_STRIDE from ASTK and AP/FR from `OT_KV_AHUB_OFS`; defaults must never be substituted for the actual expanded manifest. This pickup does not claim a value for the live v4 expanded `bind` parameters or loaded regional reset ancestry. The existing generator formula is AP_s=2+L_s+D(ap_s)-D(hs), FR=D(pvfst)-PV_LEAD-D(fr)-D(hs)-1; original am lag is D(hs)+1+D(am_s)-L_s. Any new channel latency must enter those equations explicitly.

## Smallest actionable private source-proof proposal

Request ROOT authorization for a source-only opt-in primitive plus component harness, default/public files byte-identical. No full 21-channel shell or physical submission. Start with one real 268-bit ZH command bundle and 68-bit return bundle, banked at <=32 bits, plus the actual baseline and safe-profile interface adapters. Use the original bit ordering (`start,zs_we,sid,ziv,zg,zp`; return `root,zerr`), no dummy child, tied fault, or substitute arithmetic. An eventual arithmetic comparison must compile the exact child source with its historical ZH snapshot overlay; primitive transport can first compare accepted input words against delayed output words without claiming child equivalence.

The primitive must emit real four-slot storage, not a four-deep shift register. Prove exact producer-to-consumer latency from nonblocking edge semantics before choosing a three-edge setting. Write/read pointer, registered one-hot phase, capture FF, and all banks must use a single explicitly defined phase/age. Assert no overwrite and no bank or valid/control skew at one word per edge, continuous traffic, wraparound, reset assertion, independently delayed legal reset release, immediate first command, command collision, and back-to-back passes. No stall or backpressure repair is allowed. The 80-bank /11,290 added FF figure remains a full-model allocation, not a mapped source or minimum implementation claim.

Initialize payload slots and cloned unreset FF arbitrarily and independently. Require a source-derived reset/occupancy/valid frontier showing exactly when each first consumer becomes meaningful; compare all meaningful outputs and real fault predicates from that edge onward. A failure from unequal old Q is a failure, not a license for equal initialization, an ignored startup interval, or quiet-window input constraints. Reset landing is two registered stages per face; actual nested `ot_rst_pipe` release and ring phase must be derived, not guessed from four elapsed wall-clock edges. Preserve coherent epoch/layer/context/calendar with start; no valid may outrun its payload.

Required causal negative controls: one bank reads the wrong slot; one valid/control bank shifts by one edge; one reset phase releases early; return fault/epoch belongs to the wrong pass; retained fault is cleared at a new start. Each must fail at the first authoritative consumer, with committed witness. Transport success alone cannot waive old arithmetic/error lifetime. The original AHUB start clears pass histories and fault state; a new delayed channel must preserve owned errors across restart and carry them into real downstream health/STATUS retirement. The correct retained-health implementation is coordinated with the active retained-commit owner, not invented by this transport test.

Only after this proof: generate a distinct candidate profile, rederive Z-level gap / reciprocal issue-return-publish / AP / AM / FR first-use ages from the selected actual schedules, compile the legal T-dependent calendar, price SU and MU delay, then map the combined full-copy Boolean/reset graph and clocks. The earlier +42 edges/layer illustration and 21-channel geometry are not a compiled token price. Whole-token simulation is not the next component test.

## Exact physical dependency: two repaired child exports

AHUB physical shell stays WAITS on real `ot_nhb_zh` (four replicas, current151.2-square) and `ot_qkh_recip_leaf` (current216-square) terminal-access/PG exports. Both actual local contact pitch is .096 um (10.4167 contacts/um); whole-face averages do not satisfy <=6/window. ZH also has2,158 own-layer OBS pockets. Fix the routed child connectivity/access before re-export; moving only LEF coordinates or adding parent halo cannot establish access.

ZH spec `ot_nhb_zh_m5/spec.json` pins three historical source overlays from closed commit `2b693766fd23423df955e568ba2a41a5706b9019`; job source is e5e8e058b, not current nearhbm source by implication. Reciprocal spec uses native leaf reset `rr[0]`; its job metadata still says COMMIT. These are exact provenance gaps to resolve with original source/export receipts before compiling a successor. Both specs params are empty, so source defaults and descendant parameters must also be recorded. Shared LEAD-QW A2 coupon work is not a ZH or reciprocal source/export qualification.

The child owner must return source and param closure (including snapshot overlay and descendants), actual routed database/netlist hashes, LEF signal shapes and own-layer OBS/via/escape audit, real local <=6 contacts/window, connected PG contact/route proof with every master PG MTerm bound to its ITerm net, full-face connected cell region, and native TT/FF Liberty with exact input/output/valid/reset latency. Do not infer PG from net membership or old CLOSED labels. New dimensions or latencies force parent geometry/calendar rederivation. No new PG census was performed here.

Preserve the existing loaded-library interpretation: sfb overrides WC=TC and actual read_liberty loads TT child and stdcell into raw ss/WC mode. TT CTS setup -420.07 ps; GRT -344.34 ps; FF CTS hold -152.20 ps and GRT -24.01 ps. sfa spreads86.5/97.3 and sfb116.3/123.2 ps TT/FF fail. Zero GRT overflow and old source functional roots<=24 /743 one-sink ties do not close these defects. No new SS failure label, timing waiver, or inherited native qualification is introduced.

Next owner: private boundary proof if ROOT grants; child physical exports require dedicated ZH/reciprocal repair ownership. No live job owned by this pickup.
