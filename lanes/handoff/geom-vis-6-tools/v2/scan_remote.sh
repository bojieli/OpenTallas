# runs on remote host: list layout_review stage dirs with PNGs newer than $1 minutes
M=${1:-480}
for d in $(find /srv/opentallas-scratch*/claude -mindepth 1 -maxdepth 1 -type d -mmin -$((M*3)) 2>/dev/null); do
  nice -n19 ionice -c3 timeout 120 find $d -path '*/layout_review/*' -name '*.png' -mmin -$M -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null
done
