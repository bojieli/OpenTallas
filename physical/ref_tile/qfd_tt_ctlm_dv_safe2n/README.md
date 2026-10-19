# qfd_tt_ctlm_dv_safe2n — PARALLEL fallback of safe2 (QW-CTLM 10-19)

Identical to ../qfd_tt_ctlm_dv_safe2 (same RTL, standard D4/K2 landing MCP SDC, native_cmd E-face pins, macros) except: NO placement
regions. Two unfenced regional CTS roots (ck_core, ck_hr) built over their own sinks; the tile is 778 x 432 um (< 1 mm). Cones place by
connectivity, so repair-created cells never meet a fenced/negative free area. Checklist: see ../qfd_tt_ctlm_dv_safe2/README.md
(items identical; item 7 spread is what this variant tests without fences). Bind whichever variant closes first under the checklist.
