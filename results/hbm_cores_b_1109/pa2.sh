#!/usr/bin/env bash
# DIE-HBM-96 DRT-0073 candidate view, one signed master: exact-ODB detail abstract + M5 pin clear, then pin_access probe.
set -u
P=/srv/opentallas-scratch2/claude/die-hbm-96/pa_probe2; R=/srv/opentallas-scratch3/claude/die-hbm-85/eco/b128_e1_resign_dq
V=/srv/opentallas-scratch3/claude/kw32-views/hbm/3cee1eada0f6/ot_hbm_hc_bank128_pair_core
M=ot_hbm_hc_bank128_pair_core; IMG=openroad/orfs:asap7lock; OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
cd $P; mkdir -p src
O=$(find $R -path '*results*' -name 6_final.odb | head -1); echo ODB $O; ls -la $O | cut -c25-
ln -f $O src/6_final.odb 2>/dev/null || cp $O src/6_final.odb
cp -f $V/$M.lef base.lef; sha256sum base.lef | cut -c1-16
for BF in 1 0; do
  python3 -I abstract_detail.py tcl --odb /p/src/6_final.odb --out /p/detail$BF.lef --bloat-factor $BF > detail$BF.tcl
  timeout 240 docker run --rm --name h96_d$BF --memory=16g --cpus=4 -v $P:/p $IMG bash -c "$OR -no_init -threads 4 -exit /p/detail$BF.tcl" > log_d$BF.txt 2>&1; echo detail $BF rc $?
  python3 -I abstract_detail.py splice --base base.lef --detail detail$BF.lef --out new$BF.lef --layers M5,M6 --pin-clear-um 0.048 --pin-clear-layers M5 > splice$BF.json 2>splice$BF.err; echo splice $BF rc $?
  python3 -I -c "
import json;d=json.load(open('splice$BF.json'));print({k:d.get(k) for k in ('rects','pin_clear','detail_pins_equal_base','check_ok','problems')})"
  python3 -I abstract_detail.py check --base base.lef --new new$BF.lef > check$BF.json; echo check $BF rc $?; cut -c1-200 check$BF.json
  mkdir -p n$BF; cp -f new$BF.lef n$BF/$M.lef
  sed "s#/p/ot_hbm_hc_bank128_pair_core.lef#/p/n$BF/$M.lef#" pa.tcl > pa$BF.tcl
  for p in clk go; do timeout 110 docker run --rm --name h96_p${BF}_$p --memory=16g --cpus=4 -e PIN=$p -v $P:/p $IMG bash -c "$OR -no_init -threads 4 -exit /p/pa$BF.tcl" > lp${BF}_$p.txt 2>&1; echo "== bf$BF $p rc $?"; grep -E 'DRT-0073|PA_OK|^\[ERROR' lp${BF}_$p.txt | cut -c1-160; done
  python3 -I -c "
import json;d=json.load(open('splice$BF.json'));ok=d.get('check_ok');print('ok',ok)
raise SystemExit(0 if ok else 1)" && grep -q PA_OK lp${BF}_clk.txt && { echo SELECT bf$BF; break; }
done
