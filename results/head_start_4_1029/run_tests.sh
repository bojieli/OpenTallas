#!/bin/bash
# HEAD-START-4/DIE-HEAD-28: focused START/CA/STA tests on a tool tree ($1 = new|cx|main)
pip install -q pytest numpy >/dev/null 2>&1
cd /srv/opentallas-scratch2/claude/head-start-4/t_$1/tools/die_plan
python3 -m pytest -q -p no:cacheprovider test_count_align_datadelay.py test_count_align_plan.py test_count_align_bind.py test_count_align_depth16.py test_count_align_interval.py test_count_align_onemodel.py test_count_align_skewclean.py test_count_align_startprev.py test_count_align_starttree.py test_die_sta_related.py test_die_sta_core_insertion.py test_clk_cell_cal.py test_landing_start_tree.py test_origin_per_start.py 2>&1 | tail -15
