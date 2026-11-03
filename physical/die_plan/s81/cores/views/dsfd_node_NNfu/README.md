Native dsfd_node_NNfu view (S81 network node, 43.2x77.76 um, 8.3k cells). Uniform SIGNED: TT setup 18.88 ps, FF hold 3.96 ps; DRV/DRC/antenna PASS; sdc_lint/face_guard PASS (raw netlist, no hook); pin audit PASS. Clock insertion balanced to 250 ps. Reset: timed synchronous rst_n input (pre OWNER DECISION 13). Source staged in source/. Routed abstract + TT/FF timing models.

UPDATE 2026-11-02 (DIE-S81-48 plan pin event, 12.8a centre clock entry): this dir now holds the q-s81 SIGNED rebuild
(Codex QBS centre-clock kit gen11_allpg_sdc, routed by DIE-S81-48 with the normal ORFS stage resume from the saved GRT DB):
TT +9.62 / FF +4.03 / DRC 0 / antenna 0, post-route LEC EQUIVALENT 2066, pin_audit 202/202. clk[0] is an M5 centre pin
(21.612, 38.892); dsfd_node_NNfu_tt.lib / _ff.lib = ORFS generate_abstract tc / BC models of 6_final. The text above
describes the retired 10-24 view (routed DB lost; retired by name 10-30).
