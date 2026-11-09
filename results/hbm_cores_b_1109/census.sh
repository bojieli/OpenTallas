# list signoff.json and recent key logs for 9 target cores
P='hnx_fused_lane_c|lanec|hnx_rp3h_xs|rp3h|lane1p|lane_full_x|fullx|cfg_h9b|rootctl|topk|n4ext|n4_|n4rf|rx_bm3|rxbm3'
for r in /srv/opentallas-scratch2/claude /srv/opentallas-scratch3/claude; do
  [ -d $r ] || continue
  for top in $(ls -d $r/hbm-* $r/die-hbm-* $r/codex-hbm-* 2>/dev/null); do
    timeout 90 find $top -maxdepth 5 -type f \( -name signoff.json -o -name eco_loop.json -o -name 6_final.odb \) -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' 2>/dev/null
  done
done | grep -E "$P" | sort
