# GEN19b GEN_COMPLETE (S-DIE r12, 2026-10-15)
Recipe s81_layer1_gen19b.opts on src19 @065f82f55 (--expect-manifest PASS): contract v23 (HC return columns + NORM NT strips,
hc_corridor 799.2), MIX4 option-C home reservation, v22_pq_cnt leaf pins, --hstn-posedge, hop-detour fix 0fed0e3ff.
Legality 80,646 instances, 0 overlap, 0 outside. pin_align FAIL 1 (jog spills past channel) / WARN 96,623 (pin_align.txt).
Strict port bind of the final die.v: FAIL 3 masters / 8 inputs / 3 widths, 0 unbound/stub/unknown/undriven:
BF xb x519 (S-BIND --bf-x2-pair), PQ ra2/xe/xw + f_iss (S-ELEM-B, x2 static PQ), VM f_mx x6 (MIX4 master binding, S-DIE + S-ELEM-C:
dsfd_engram_mix4_c has vector ck[132:0] and an f_inp with no static VM producer).
Old VM slot (1541.8 x 3952.8), NOT the 640-leaf VM body. Not a physical or native qualification.
