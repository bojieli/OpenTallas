    wire win_su_match = FULL_SHAPE && KV_HBM && d_unit == 3'd2 &&
                        dst == 2'd3 && a_src == 2'd0 &&
                        su_nout == NW'(1) && su_nin == NW'(512) &&
                        a_base == win_cap_src_base;
    wire win_admit = !FULL_SHAPE || win_idle || (win_su_match && win_issue_ready);
    wire kv_gate = ((KV_HBM == 0) || !(d_unit == 3'd1 && me_cls == MC_A) || (kv_ok && !kvd_v)) &&
                   (!FULL_SHAPE || win_idle);
