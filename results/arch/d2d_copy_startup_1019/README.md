# D2D eight-copy startup check: HOLD

The exact analytical eight-FF cloning plan is unsafe under arbitrary initial Q. A constructive first-consumer witness is preserved in witness.json. This is an existential counterexample, not an equivalence PASS or a statistical qualification.

Canonical selected TT Liberty states DFFHQN and DFFASRHQN next_state = !D and QN = IQN. For the ASR master, RESETN low presets QN to 1; SETN low clears it to 0. The four q_sf_start/seg copies have no reset pin.

The witness redirects one true logical endpoint of q_sf_seg[0] to a hypothetical independent clone: _44236_/B. Both worlds share all 91 original cone boundary values. The 74-cell exact mapped cone reaches txcal.rep[0] through AND2, AO21, OA211 and AOI21. The original/clone QN before the first edge differ; consumer D is 1/0, so its QN after that edge is 0/1 with its RESETN/SETN held high. Parent and clone both sample the same cal_seg on that edge, but that convergence does not erase the consumer divergence caused by their old QNs. All combinational ancestors and reconvergence of this consumer are evaluated, rather than treating intermediate side inputs as independent cuts.

Fleet run: ot-epyc8, unit oth-ubuntu-1961277-1792445472, command python3 proof.py, exit 0. Source data and exact pins are in manifest.json and constructor_plan.json. cone.json retains the complete selected consumer cone and arbitrary shared boundary assignment. The witness shows a legal arbitrary-initial-state failure; a release reset/admission protocol might exclude it, but no such exclusion is proven here.

No source constructor, synthesis, physical run, or main edit was performed. Further clone construction is stopped. A correct successor must prove actual first-use reset/admission masking or preserve startup at every affected consumer; equal initialization and a guessed first-edge waiver are not valid repairs.
