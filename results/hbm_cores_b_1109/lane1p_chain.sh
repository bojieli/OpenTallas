#!/bin/bash
cd /
L=hbm-open-a
ssh -n -o ControlPath=none epyc6 "cd /srv/opentallas-scratch3/claude/hbm-hard-7 && tar -cf - --exclude=run/objects kit_lane1p_C2mw80_resume" | ssh -o ControlPath=none intel1 "mkdir -p /srv/opentallas-scratch2/claude/$L/kit_lane1p_C2 && tar -xf - --strip-components=1 -C /srv/opentallas-scratch2/claude/$L/kit_lane1p_C2"
ssh -n -o ControlPath=none intel1 "cat > /srv/opentallas-scratch2/claude/$L/lane1p_eco_chain.sh <<'E'
#!/bin/bash
cd /tmp
export OT_HOLD_REPAIR_SCOPE=nonport
T=/srv/opentallas-scratch3/claude/auto-resign/tools/flow-20261108-fs-hbm
K=/srv/opentallas-scratch2/claude/hbm-open-a/kit_lane1p_C2
python3 -I \$T/tools/die_plan/resign.py run --auto --kit \$K --tag flow-20261108-fs-hbm --repo \$T/tag_manifest.json --tools \$T/tools/die_plan --out /srv/opentallas-scratch2/claude/hbm-open-a/lane1p_C2_so --lane HBM-OPEN-A --name l1pC2 --lec-mem 40g --note 'lane1p C2mw80 copied from epyc6 for ECO base record; fs re-sign'
python3 -I \$T/tools/die_plan/eco_loop.py run --kit \$K --signoff /srv/opentallas-scratch2/claude/hbm-open-a/lane1p_C2_so/signoff/signoff.json --runner \$K/run_kit_hbm.sh --out /srv/opentallas-scratch2/claude/hbm-open-a/lane1p_C2_eco --max-iter 1 --strict-one-pass --lec --lec-tool \$T/tools/die_plan/lec.py --owner-override --mem 48 --cpus 8
E
chmod +x /srv/opentallas-scratch2/claude/$L/lane1p_eco_chain.sh; du -sh /srv/opentallas-scratch2/claude/$L/kit_lane1p_C2"
ssh -n -o ControlPath=none intel2 "cd / && nohup bash -lc 'ot-run --crit --mem 48 --threads 8 --hosts intel1 --dir /srv/opentallas-scratch2/claude/$L --disk 8 -- bash /srv/opentallas-scratch2/claude/$L/lane1p_eco_chain.sh </dev/null' > ~/hbm-open-a-logs/lane1p_eco_chain.otrun.log 2>&1 < /dev/null &"
echo chain-launched
