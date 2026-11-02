# HBM compact native Tnode — actual GEN review

Verdict: PASS-COND for one PLACE diagnostic from geometry. No route, proof or parent release.

Personally viewed `/home/ubuntu/coord/tmp/codex-hbm-tnode-compact-kit-1101/actual_review/actual_gen_geometry.png` and read actual_gen_model.json from the generated R3 kit. The actual125.28×95.04um outline preserves1341 native pins. SRAM data macro(94.824×41.064) starts at(15.168,8.796); control macro(31.992×17.304) starts at(15.168,69.372). The4.32um halos leave10.848/10.968um W/E channels and10.872um between the halo bands. The large lower macro is not a wall: both side channels continue to the top region. Upper-right standard-cell/clock space is open, and actual M5 clock entry(64.776,64.8) clears both halos. The full-outline Manhattan span is220.32um<405; actual pin-flop and logic reach are still unmeasured.

Conditions: preserve the full native pin ABI; measure actual row legality, standard-cell fill/empty bins, pin-flop locality and macro-edge congestion at PLACE, then PG/CTS/GRT and real timing normally. The30-instance parent tap/data shifts and source/current-view binding still need qualification. The GEN freeze's historical64-edge reset scaffolding grants no native4-edge proof credit; do not alias prior component proof or outside face-shell evidence to this new physical candidate.
