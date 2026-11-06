# Bank128 safe-form review — 2026-11-06

Images are drawn from generated kit macro-placement coordinates, exact current pin table, and the B ingress-guide rectangle. They are pre-build geometry reviews, not placed-logic or routed evidence.

Draft: `bank128_wface_plan.png` — FAIL geometry. The inherited X SRAM at y108.012 leaves only1.032um between its halo and upper W0 halo; lower channel is much wider. No candidate was routed from this draft.

Revision: `bank128_wface_revised.png` — PASS-COND for A/B physical trials. X moved to y96.252; both halo-clear channels are12.792um. Neither outline nor pins change. A and B now share the corrected geometry, M6 signal ceiling and single-root CTS; B adds the proved525bit write ingress and north-face guide. Actual config PLACE_DENSITY0.40, MAX_ROUTING_LAYERM6; no density tap OT_DTAP settings. Clock entry125.304,133.92 is outside macro halo, east of X. Existing power hooks retained; final routed PG/DRC remains to be measured.

N-face write bus terminates in the adjacent north register guide; stage-to-bottom SRAM span remains below~270um, within405um guidance. M6 supplies horizontal over-macro escape where M1-M4 SRAM obstructions forced M5 detours. Clear side channels and balanced horizontal corridors avoid the old near-touching macro wall. No pins move or face-order changes. Placement and post-CTS images must be inspected when available.

Conditions before adoption: parent must reserve the actual M6 hard-core obstruction/resource; sign-off and routed LEC must pass; WFACE+1 write programming/read-go guard must be composed by the native HC projection owner. No setup/hold/clock constraint was changed. This record authorizes diagnostic physical trials only.

Weight_E variant: `bank128_weightE_revised.png` viewed PASS-COND. Actual pin table leaves512data bits on north but moves10address+3enables to east aroundy64.8-66.7. Separate disjoint guides retain512data flops north and13control flops in east corridor x226.8-246.24,y43.2-86.4, near their actual pins and clear of lower SRAM halo. Same balanced macrochannels/singleclock/M6/0.40 and all earlier adoptionconditions apply. Sourceview9bf80cdae38d kit hashb549fad338678913.

Actual canonical B placed ODB review: `bank128_actual_placed.png` viewed PASS-COND. All525write-stage cells present;512data pin-to-flop Manhattan p90/max7.65/9.65um, address10 p90/max7.50/8.00um. Data/address were first fixed by face placement and then released for detailed placement; explicit region guidance is needed only for3reset-gated write enables. Balanced SRAM corridors remain open; stdcells occupy side channels and the free X-east region, with local dense clusters that need routed congestion review. Actual GPLstdcell area14624.4um² over34177.1freecore area=0.4279. Clock entry still central; actual CTS367ps is later than250target and remains a real-view parent obligation, not a passed clock band. No physical sign-off claim.
