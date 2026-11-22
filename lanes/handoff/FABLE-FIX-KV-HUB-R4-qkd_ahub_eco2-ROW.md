# qkd_ahub access view row for kv3_hub_C (FABLE-FIX-KV-HUB-R4, 2026-11-21) -> KV-PLAN-R6, D27/D28

Row: LEF-only swap of the kvgeom7q qkd_ahub view, base sha256 f357274f6d49 -> 83f8a1e66e4d
(file next to this one: FABLE-FIX-KV-HUB-R4-qkd_ahub_eco2.lef; staged view dir epyc7
/srv/opentallas-scratch2/claude/fable-fix-kv-hub/r4/ahub/view_eco2/ with libs, signoff.json, provenance.json, splice.json, probe/).
Carry it as an overlay: a lef_override row keyed on the base LEF sha (form of main 417f6ceadf) or a declared view overlay.
Never write it into a sealed tree (kvgeom7q_views is in the src_manifest).

What changes
- ck[5] gains a second M5 rect 579.984 109.56 580.032 109.76 (extension below the signed box, same track and width, under no M6 strap).
  ECO DB sha 36f134bda9bd, base signed DB 7351e075fc29 (dkv71/ahub/h1). 0 nets ripped, 0 wires changed, netlist 6_final.v byte-identical
  (e46648cacd58).
- M6/M7 OBS opened 1.0 um round ck[0..6] and rst_n, exact signed metal put back.
- Libs byte-identical (tt a04e3c039488, ff afbe8f606a40): signed_view_sha_kv.json, core latency and tap rows stay. No pin row: every
  signed rect keeps its place.

Evidence
- TritonRoute pin_access probe of the view alone: 0 DRT-0073 for ck[0..6] and rst_n (view_eco2/probe).
- DRC report identical to the signed base; pin audit 631/631.
- Sign-off rt tools, tag flow-20261104-l-kv: SIGNED (minimal profile) TT +14.85, FF +7.12, DRC 0.
- Re-sign with routed LEC at tag flow-20261117-je-kv: epyc7 unit oth-ubuntu-889231-1795314793, out .../r4/ahub/eco2/resign_je
  (PROVENANCE.json kind resign when it passes). RUNNING at the time of writing; do not count the view as re-signed before it.

Parent pin tooling with two M5 rects on ck[5] (plan LEF vs this LEF through rt 7b6af7dd0449 parsers)
- cores.lef_pins, gen_phys._lef_macro_pins, _lef_signal_pin_layers, lef_face_pins: identical output.
- core_ft_physical._lef_pins: carries the pin block text, both rects kept.
- gen_phys.lef_interior_pins: returns two entries for ck[5]; its only user pg_island_cuts makes one more cut window that abuts the
  first (a 0.2 um longer cut on the same track).
- kit_contract.lef_pin_contract raises "no boundary rectangle: ck[0]" on the plan LEF and on this one alike (interior pins; existing
  behaviour, not a change).
- NOT yet proven: a kv3_hub_C kit gen + route with this view.

Known false flag
- splice.json check_ok false, "signal pins without access up to M7: ck[3], ck[4]": abstract_detail.access_report asks for an
  OBS-free 0.1 um box centred on the pin on M6; over ck[3]/ck[4] the free M6 gap between the signed wires is narrower than that
  box but wide enough for the V5 landing the router uses. The gate is the TritonRoute probe, which passes. The static rule is left
  as is (it is the conservative side for every other view).
