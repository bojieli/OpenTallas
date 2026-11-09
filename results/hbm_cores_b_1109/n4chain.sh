#!/bin/bash
cd /
L=hbm-open-a
for i in $(seq 1 120); do
  n=$(ssh -n -o ControlPath=none intel1 'ps aux | grep "[t]ar -xf - --strip-components=1 -C /srv/opentallas-scratch2/claude/hbm-open-a/kit_n4_vRF1b" | wc -l')
  [ "$n" = 0 ] && break
  sleep 15
done
ssh -n -o ControlPath=none intel1 "cat > /srv/opentallas-scratch2/claude/$L/n4_eco_chain.sh <<'E'
#!/bin/bash
cd /tmp
export OT_HOLD_REPAIR_SCOPE=nonport
T=/srv/opentallas-scratch3/claude/auto-resign/tools/flow-20261108-fs-hbm
K=/srv/opentallas-scratch2/claude/hbm-open-a/kit_n4_vRF1b
python3 -I \$T/tools/die_plan/resign.py run --auto --kit \$K --tag flow-20261108-fs-hbm --repo \$T/tag_manifest.json --tools \$T/tools/die_plan --out /srv/opentallas-scratch2/claude/hbm-open-a/n4_vRF1b_so --lane HBM-OPEN-A --name n4rf1b --lec-mem 40g --note 'n4 vRF1b kit copied from epyc4 die-hbm-89/n4rf/kits/n4_vRF1b for ECO; first fs re-sign for the record'
python3 -I \$T/tools/die_plan/eco_loop.py run --kit \$K --signoff /srv/opentallas-scratch2/claude/hbm-open-a/n4_vRF1b_so/signoff/signoff.json --runner \$K/run_kit_hbm.sh --out /srv/opentallas-scratch2/claude/hbm-open-a/n4_vRF1b_eco --max-iter 1 --strict-one-pass --lec --lec-tool \$T/tools/die_plan/lec.py --mem 48 --cpus 8
E
chmod +x /srv/opentallas-scratch2/claude/$L/n4_eco_chain.sh; du -sh /srv/opentallas-scratch2/claude/$L/kit_n4_vRF1b"
ssh -n -o ControlPath=none intel2 "cd / && nohup bash -lc 'ot-run --crit --mem 48 --threads 8 --hosts intel1 --dir /srv/opentallas-scratch2/claude/$L --disk 8 -- bash /srv/opentallas-scratch2/claude/$L/n4_eco_chain.sh </dev/null' > ~/hbm-open-a-logs/n4_eco_chain.otrun.log 2>&1 < /dev/null &"
echo chain-launched
