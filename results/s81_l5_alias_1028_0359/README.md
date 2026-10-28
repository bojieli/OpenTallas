# L5 n32 checked register aliases

The inherited actual L5 hint job finished EQUIVALENT:98,941/98,941 compare points,27,603 kept registers all present,0missing. All16 explicit gate x_z[k] to gold g_x[k].xz_q register aliases were accepted and independently checked by the existing induction machinery. The negative control shifts k to k+1 and remains UNPROVEN, with all27,603 kept registers present. Runtime is epyc2:/srv/opentallas-scratch2/claude/die-s81-2b/l5/{hint,mut}/out.

Both names arise from the same source unreset flop in the Sinkhorn tail: `reg xz_q; always @(posedge clk) xz_q <= nz[0]; assign x_z[k] = xz_q`. This is a source naming/correspondence repair, with no loaded-valid or constant-lane assumption, reset duration change, data edge, or KEEP exemption. The original actual kit freeze selects ref_tile `physical/ref_tile/dsdv_gunit_l5_n32`, matching the sole recipe updated here. The unrelated l5f recipe remains unchanged.

Current gen_core_kit_legacy.py already copies a recipe's lec_hints file into KIT/lec_hints.json for its modern LEC flow. This change supplies the actual passed16-pair file for the n32 recipe, so fresh kits carry the fix. The checker treats these hints as untrusted and re-proves them for every actual generated netlist. This receipt does not transfer any physical view or bypass current kit/source/timing gates.
