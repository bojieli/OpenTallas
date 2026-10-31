#!/bin/bash
cd /srv/opentallas-scratch2/claude/s81ck7
python3 -I resign.py run --kit /srv/opentallas-scratch2/claude/s81ck5/kits/ot_s81sl_ve_m_rt22m_hx --tag flow-20261030-e-s81 --repo /home/ubuntu/OpenTallas --tools /srv/opentallas-scratch2/claude/s81ck7/t_e-s81/tools/die_plan --out /srv/opentallas-scratch2/claude/s81ck7/ve_m_rt22m_hx_resign_e-s81 --name s81ck7-vemhx --lane S81-CORES-KITS-7 --note "$1" --pincmp "$2"
