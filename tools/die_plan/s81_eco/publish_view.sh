#!/bin/bash
# S81-ECO-1: publish a SIGNED + routed-LEC-EQUIVALENT ECO kit as a native core view
#   publish_view.sh HOST:KIT MODULE REPO_VIEWS_DIR
set -euo pipefail
HK=$1; M=$2; V=$3/$M; H=${HK%%:*}; K=${HK#*:}
ssh -o ControlPath=none $H "python3 -c \"import json,sys;d=json.load(open('$K/signoff/signoff.json'));sys.exit(d['verdict']!='SIGNED')\" && grep -q '\"verdict\": \"EQUIVALENT\"' $K/lec_routed/lec.json" \
  || { echo "publish_view: $M not SIGNED or routed LEC not EQUIVALENT"; exit 2; }
mkdir -p $V
B=$(ssh -o ControlPath=none $H "ls -d $K/run/results/asap7/*/base")
scp -o ControlPath=none -q $H:$B/$M.lef $V/$M.lef
scp -o ControlPath=none -q $H:$B/${M}_tc.lib $V/${M}_tt.lib
scp -o ControlPath=none -q $H:$B/${M}_bc.lib $V/${M}_ff.lib
for f in config.mk constraint.sdc pins.json ECO.json; do scp -o ControlPath=none -q $H:$K/$f $V/$f; done
scp -o ControlPath=none -q $H:$K/signoff/signoff.json $V/signoff.json
scp -o ControlPath=none -q $H:$K/lec_routed/lec.json $V/lec_routed.json
python3 - "$V" "$M" "$HK" "$B" <<'PY'
import hashlib, json, sys, pathlib
v, m, hk, b = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
s = json.loads((v / "signoff.json").read_text()); c = s["corners"]
files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(v.iterdir()) if p.name != "MANIFEST.json"}
man = dict(schema="opentallas.s81.native_core_view.v1", module=m, kit=hk, routed_db=b + "/6_final.odb", verdict=s["verdict"],
           modes="TT setup vclk 250 / FF hold vclk bound-ff 202.5 (METHODOLOGY 12.3; COORD RETIME-VIEWS-2 10:44)",
           tt_setup_ps=c["tt"]["std_wns_max"], ff_hold_ps=c["ff"]["std_wns_min"],
           eco="S81-ECO-1 FF-frame GRT hold repair (tools/die_plan/s81_eco/prep_eco.sh); stages 1-4 of the previously signed kit unchanged",
           files=files)
(v / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
print(m, s["verdict"], man["tt_setup_ps"], man["ff_hold_ps"])
PY
