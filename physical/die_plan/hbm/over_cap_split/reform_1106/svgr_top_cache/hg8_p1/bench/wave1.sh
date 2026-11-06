#!/bin/bash
cd /srv/opentallas-scratch3/claude/hbm-gaps-8/bench
mk(){ n=$1; shift; bash mkbench_hg8.sh $n "$@" > out_mk_$n.log 2>&1 && bash one_hg8.sh $n L00:0 smoke; }
mkdir -p out
mk k0 /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k0 "" &
mk k0il /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k0 ".OPEN_IL(1)" &
mk k1 /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k1 ".P1(1)" &
mk k1il /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k1 ".P1(1),.OPEN_IL(1)" &
mk m_odly /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k1 ".P1(1)" /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/m_odly.sed &
mk m_wa /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k1 ".P1(1)" /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/m_wa.sed &
mk m_mid /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k1 ".P1(1)" /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/m_mid.sed &
mk m_match /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/rtl_k1 ".P1(1)" /srv/opentallas-scratch3/claude/hbm-gaps-8/bench/m_match.sed &
wait; echo ALLDONE >> out/rc.txt
