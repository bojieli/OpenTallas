#!/bin/bash
cd /srv/opentallas-scratch2/claude/s81ck7
python3 -I resign.py run --kit /srv/opentallas-scratch2/claude/s81ck5/kits/ot_s81sl_vq_rt6e_hx3 --tag flow-20261030-e-s81 --repo /home/ubuntu/OpenTallas --tools /srv/opentallas-scratch2/claude/s81ck7/t_e-s81/tools/die_plan --out /srv/opentallas-scratch2/claude/s81ck7/vq_rt6e_hx3_resign_e-s81 --name s81ck7-vqhx3 --lane S81-CORES-KITS-7 --note "$1" --pincmp "$2"
