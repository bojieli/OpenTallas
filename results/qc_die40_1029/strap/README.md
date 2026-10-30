# DIE-QC-40 QC count-strap pin sites (COORD 20:2x item 2)

Plan of record for kits = results/qc_die33_1029/bind/plan.json (sha256 00ebe12b...). Tool UNCHANGED from main: tools/s81_head/head_count_strap_sites.py (HEAD form: M5 interior sites, 4.32 pitch, 4.32+1.08 macro halo, clock reserved sites +1.08 clear, existing plan pins +-2.16 clear, nearest to landing-ring/tap anchor). It is already die-agnostic (schema + gen_phys only); no code change needed.

    python3 tools/s81_head/head_count_strap_sites.py results/qc_die33_1029/bind/plan.json --out plan_straps.json

Result [CHECKED]: 114/114 strap types placed, 7,224 strap pins, layer M5 (QC kits MAX_ROUTING_LAYER M7), max anchor hop 56.16 um; schema validate PASS; plan diff = count_straps layer/sites_um ONLY (all other keys identical); rerun byte-identical (sha256 6d5b996f...); gen_phys.strap_pin_sites emits 7,224 pins on all 119 types, 0 errors. Full plan (19 MB) not committed: intel2:/srv/opentallas-scratch2/claude/die-qc40/strap/plan_straps.json; count_strap_sites_delta.json = the per-type count_straps after the delta.
Not run here: kit regen/PLACE (QC-KITS-U), die-top tie (12.15a bind follow-up).
