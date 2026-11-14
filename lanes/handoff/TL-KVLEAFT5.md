# TL-KVLEAFT5 (s81/ot_s81sl_kv_leaf__t5) 11-14
- a14 FAIL GEN_LINT: wave src B3v/src ot_dp_clk_landing.sv lacks LOCAL param but bind emits .LOCAL(1) (same shared cause as TL-COLH9R0P5). a13 (src_pgL, bound without LOCAL) linted+placed-gen fine, died only at ot-run place (kit on epyc9 not in store of epyc2).
- Form A: a13 kit copy epyc9 /srv/opentallas-scratch2/claude/tl-kvleaft5/gen, ot-run pinned --hosts epyc9, log intel2 ~/tl-kvleaft5/gen.log.
- Form B: a14 kit (plan 4b7f1e087434) + main LOCAL-param ot_dp_clk_landing.sv overlay, epyc10 .../tl-kvleaft5/genB, log intel2 ~/tl-kvleaft5/genB.log.
- Next: when route done -> signoff, add AUTO-RESIGN row, post RESULT.
