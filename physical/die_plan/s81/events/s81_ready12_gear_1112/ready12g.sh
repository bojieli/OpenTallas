#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111
B=b5faa1bacc5f6e80c6167856ee1597a7a775ea81dad9305424a3c47de0786d7b
E=$R/repo/physical/die_plan/s81/events/compose_cleanslate_1111
M=$R/deltas; V3=/srv/opentallas-scratch3/claude/cpl-s81-slice-2/slice_v3; X=$R/s87
cd $R/repo
exec nice -n 19 python3 -I physical/die_plan/s81/compose_cleanslate_1111_r6.py compose $R/out/v_fb2b/plan.json $R/out/s87_ready12g \
  --base-sha $B --no-g0 --g0-base $R/out/g0_base_1200 \
  --pos $M/misc_1031/delta_cpl_s81_misc_bk_sel_1111.json::$M/misc_1031/intent_BK_SEL.json --derived $M/misc_1031/derived_cpl_s81_misc_bk_sel_1111.json \
  --pos $M/misc_1018/delta_cpl_s81_misc_serdes_1111.json --derived $M/misc_1018/derived_cpl_s81_misc_serdes_1111.json \
  --pos $V3/delta_SLICE-C_v3_b5faa1ba.json::$V3/INTENT_index.json --derived $V3/companion_SLICE-C_v3.json \
  --window-tap $X/window_tap_lepw_eface.json --stage-script $X/stage_a_leaf.json --stage-script $E/stage_e_station_dir.json --stage-script $E/stage_x_s4n_ftlane.json \
  --stage-script $X/stage_f_ftregs.json --stage-script $X/stage_l_lepw_eface.json --stage-script $X/stage_r_svcrs_por.json \
  --stage-script $X/stage_i_iqf_cland.json --stage-script $X/stage_d1_dielayout_svc.json --stage-script $X/stage_d2_pvso_f1r.json --stage-script $X/stage_q_leaf_cyc2.json --stage-script $X/stage_y_relay.json --stage-script $X/stage_c2_ctapw.json --stage-script $X/stage_z_dead.json --stage-script $X/stage_w_window.json --stage-script $X/stage_g_gear.json
