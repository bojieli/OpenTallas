# Actual SC-v1 failed placement

Old immutable source5346b95c915, type sle_sc_v1__cl115da35f, block5427411c3fe2; not current d90 source.
Native1_synth:562603 logic standard cells,0macros,0physical-only. Failed placement:657268 logic cells (+94665),69016 CORE_WELLTAP physical-only excluded. Tie cells remain included.159231 logic FIRM,498037 PLACED.
Legalizer4431 negotiation violations; final1010 overlap/padding pairs, DPL0033 at detail_place.tcl39. Actual FIRM cland logic overlaps PLACED bin FF/buffer, shown in failure.png. This is real capacity plus constrained placement debt. No placement retry launched.

Classification uses actual OpenDB master-type strings: CORE/CORE_TIEHIGH/CORE_TIELOW included; CORE_WELLTAP excluded. No other physical-only type occurs in this database.

Original failed ODB/log preserved intel1:/srv/opentallas-scratch2/claude/kit-wave/qwen_compute/5346b95c915/items/sle_sc_v1__cl115da35f/gen/sle_sc_v1__cl115da35f . Readonly diagnosis intel1:/srv/opentallas-scratch2/claude/codex-qc-sc-v1-dpl-1101 . Unit oth-ubuntu-3679877-1793570822 exit0.

KIT/FLOW owns actual pre-floorplan400k guard and later actual growth visibility; no duplicate generic flow change here. Standalone SC hard-leaf candidate/source event is separately held; this old failure does not qualify a new cut.
