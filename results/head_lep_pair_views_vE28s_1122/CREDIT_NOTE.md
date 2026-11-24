HEAD-CREDIT 11-23: registers the vE28s view on main so the release-tree count can read it (main_view_pins: pins.json beside source_signoff.json).
- source_signoff.json is the real SIGNED record (FABLE-FIX-HEAD-LEP0N 11-22, TT setup +13.98, DRC 0) of the vE28 routed DB + rst_n pin-move ECO; its DB dir was cleaned up.
- pins.json = the plan pin table lep_pair_pins_777s.json (2141 pins). Checked against this directory LEF: every non-PG pin centre of pins.json lies inside a same-layer pin rect of ot_s81hd_lep_pair.lef (0 misses, rst_n at the S face 399.372..399.396 x 0..0.192 M5).
