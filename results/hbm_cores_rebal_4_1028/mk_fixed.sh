#!/bin/bash
# HBM-CORES-REBAL-4: plan-fixed macro placement kits (COORD 07:23 (1)): lanes__canon (= A RTLMP result, 0 moves),
# hnx_rp3lp3h_n/_s (= baseline RTLMP + 4/3 nearest-legal moves). Plan c20e_k2, slices with island ft pins 1.08.
set -eu
W=/srv/opentallas-scratch2/claude/wt/hbm-cores-rebal-4; B=/srv/opentallas-scratch2/claude/die-hbm-1027
P=$B/c20e_k2; V=$B/kits/c20e_k2/views.json; R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-4
F=$B/kits/fixes; G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
cd $R
# 1) plan-fixed placement JSON in gen --macro-placement form (k = instance path below u_fcore)
python3 - <<PY
import json
for src, dst in (("legalA_lc", "mp_lanes__canon"), ("legal2_hn", "mp_hnx_n"), ("legal2_hs", "mp_hnx_s")):
    d = json.load(open(f"keep/{src}.json"))
    assert d["overlaps_left"] == 0 and not d["fail"]
    mp = [dict(k=m["inst"][len("u_fcore."):], origin_um=m["xy_um"], orient=m["orient"],
               macro="ot_sram_1r1w_128x256_m1_r2c2") for m in d["macro_placement"]]
    assert all(m["inst"].startswith("u_fcore.") for m in d["macro_placement"])
    json.dump(dict(source=f"HBM-CORES-REBAL-3 keep/{src}.json (bbox lower-left from RTLMP 2_2 odb; moved " + str(d.get("moved")) + ")",
                   macro_placement=mp), open(f"{dst}.json", "w"), indent=1)
    print(dst, len(mp))
PY
# 2) slices with island ft pins at cx+-1.08 (islands-only; rects unchanged)
python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $V $R/slices $R/kits $W \
  ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77,hnx_rp3lp3h_n,hnx_rp3lp3h_s --islands-only --ft-pin-dx-um 1.08 > $R/mk_slices.log 2>&1
view() { python3 -c "import json;print([v[\"view\"] for v in json.load(open(\"$V\"))[\"view_list\"] if v[\"module\"]==\"$1\"][0])"; }
cd $W/physical/die_plan/hbm_arch_cores
m=ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77
python3 $F/run_canon_kit.py $W $F --views $V --view $(view $m) --out $R/kits --master-slice $R/slices --trial --tag _c20ek2m \
  --macro-placement $R/mp3_lanes__canon.json --macro-inst-fmt "{k}" > $R/kits/gen_$m.log 2>&1; echo "$m rc=$?"
for h in n s; do m=hnx_rp3lp3h_$h
python3 $G --views $V --view $(view $m) --out $R/kits --master-slice $R/slices --trial --tag _c20ek2m \
  --macro-placement $R/mp3_hnx_$h.json --macro-inst-fmt "{k}" > $R/kits/gen_$m.log 2>&1; echo "$m rc=$?"
done
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $R/kits $R/preflight $W
