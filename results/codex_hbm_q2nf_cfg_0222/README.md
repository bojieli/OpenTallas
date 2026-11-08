# Q2NF static-program configuration decode class

The geometry pilot's pre-placement wire-load timing shows setup -507.2ps /2757endpoints, with issuer_cfg[17] worst. It contains 6-bit step divided/modulo17 followed by a variable1536-bit word select. Geometry cannot remove this logic depth.

Opt-in `OT_Q2NF_CFG_CASE` replaces ONLY the37-bit issuer_cfg D cone with the constant-select combinational CFG_CASE form already used by HBM-HARD-5. Register set, reset, clocks and latency remain unchanged. PIN CYCLES0. Default off.

Production-shape proof: extract_cfg_cone.py follows the actual old flattened D net to1615free input bits (step6,row8,assembly1536,metadata64,draining1),20assignments, no unknown leaves. The extracted cone is byte-identical between the actual vA1 kit and main289149dea5 (SHA c92ca2833d020358a3231f718a7233dee523c4cd3a011aa2a29f612ee973470c). The helper miter proves equality over every defined input; a wrong-data-word mutant fails. Actual proof.rc good0/mutant1, Intel2 unit oth-ubuntu-825325-1794137229. The canonical helper differs from the proved helper only by its module name, a wiring bijection.

build_candidate.py stages the class on the reviewed periphery kit and adds the helper/define to the explicit source list. Fresh synthesis is required because RTL changed. The older geometry-only pilot continues as a diagnostic; no unchanged retry. Native kit LEC and actual physical review remain required before any sign-off/count claim. No plan-of-record or default change.
