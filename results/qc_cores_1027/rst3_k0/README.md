# QC-CORES-1: qfd_dv_s5_su8_rst3 demote + fix (2026-10-27)

- **Demoted.** Row added to `~/coord/RETIRED_SIGNOFFS.tsv` (coord 4ba9426af). The routed LEC was KEEP FAIL: 16 of the 3254 declared kept bits, `g_xsl[0].g_sel[0..15]`, are missing from the netlist.
- **Root cause (CHECKED).** This was dead logic, not register merging. The synth flow's keep form was not the weak point.
  - Lane 0 instantiates `qfd_dv_su8_xlane #(.K(0))`.
  - `qfd_dv_su8_stride #(0)` is `y = 0`, so `xs_l[0]` can only ever load 0.
  - Yosys constant-folds `g_xsl[0].u.q`. That leaves the 16 `keep_hierarchy` kff select replicas of lane 0 with no load.
  - They are still present in `1_2_yosys.v` (16). ORFS `1_synth`, the OpenROAD read plus `eliminate_dead_logic`, then removes them: 0 remain in `1_synth.v` and `6_final.v`.
  - Lanes 1..7 keep 16 each, with the same keep form.
  - The LEC gold already proved the 112 lane-0 xlane bits constant.
- **Fix (RTL, structural).** Lane 0 becomes the constant it already was: `assign xs_l[0] = 0`, and the generate loop runs `for (gc = 1; ...) : g_xsl`. Names `g_xsl[1..7].*` are unchanged. The power-up X of a register that never loads a nonzero value is refined to 0, which synthesis and the LEC gold already did. Diff: `rtl/rst3_fix.diff`.
- **Synth proof (CHECKED, intel1 docker).**
  - face_guard PASS 1545/1545.
  - `1_synth.v` keeps 16 distinct `g_sel` flops on each of lanes 1..7 and has no lane-0 cells.
  - main lec.py, new RTL vs synth netlist: **EQUIVALENT**, 7234/7234 compare points, keep check passes (`lec/lec_newrtl_vs_synth.json`).
  - Original RTL vs new netlist: 7346/7346 proved, 0 differ. Only the 16 removed dead bits are missing, so the function is unchanged (`lec/lec_origrtl_vs_newsynth.json`).
- **Rebuild.** Same recipe as the retired view: the kits3 base kit with `run_kit.sh finish`, then warm hold ECO variant b (FF-only, margin 3, maxbuf 40), then `signoff.py` tt,ff, then main lec.py on the routed `6_final.v` (`chain.sh`).
  - The retired view was already in the 12.3 band (240.0/191.5), and the clock recipe is unchanged.
  - Job: ot-run unit oth-ubuntu-2693240-1793100007 on intel1, started 04:20 PDT.
  - Collect from `intel1:/srv/opentallas-scratch2/claude/qccores1-1027/rst3_k0/`: `chain.txt`, `hold_b/signoff/signoff.json`, `lec_routed/lec.json`, `hold_b/run/results/asap7/*/base/6_final.*`.
