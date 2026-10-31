#!/bin/bash
cd /srv/opentallas-scratch2/claude/s81ck7
python3 -I resign.py run --kit /srv/opentallas-scratch2/claude/s81ck5/kits/ot_s81c_attn_hcore_rt22m_hx2 --tag flow-20261030-e-s81 --repo /home/ubuntu/OpenTallas --tools /srv/opentallas-scratch2/claude/s81ck7/t_e-s81/tools/die_plan --out /srv/opentallas-scratch2/claude/s81ck7/attn_rt22m_hx2_resign_e-s81 --name s81ck7-attnhx2 --lane S81-CORES-KITS-7 --note "$1" --pincmp "$2"
