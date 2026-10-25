#!/usr/bin/env bash
# Logical native B2 bind; no P&R/STA. Existing failed records stay untouched.
set -euo pipefail
OUT=$(realpath -m "${1:?out}");BUNDLE=$(realpath "${2:?source bundle}")
PL=$(realpath "${3:?extracted plan lanes}");CM=$(realpath "${4:?census map}")
BASE=${5:-d13ff7c78};ROOT=$(git rev-parse --show-toplevel);cd "$ROOT";mkdir -p "$OUT/ovl"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
bash tools/hbm_b2/regen_b2.sh "$OUT/raw" "$PL" "$CM" > "$OUT/regen.log" 2>&1
python3 tools/hbm_b2/native_clock_items.py "$OUT/raw/wiring.json" --out "$OUT/clock_wiring.json"
python3 tools/hbm_b2/native_root_items.py "$OUT/clock_wiring.json" --out "$OUT/native_wiring.json"
python3 tools/hbm_b2/b2_top.py --die physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz --asbuilt physical/die_plan/hbm/bind/asbuilt.json --delta "$OUT/native_wiring.json" --out "$OUT/top" > "$OUT/b2.log" 2>&1
python3 tools/hbm_b2/clock_gate.py "$OUT/top/die_b2.v" --out "$OUT/clock_gate.json"
python3 tools/hbm_b2/start_alignment.py --die "$OUT/top/die_b2.v" --plan "$PL" --census-map "$CM" --out "$OUT/start_alignment.json"
# Canonical HC child closure replaces scoped old default-width definitions.
H=rtl/hbm_accel/generic/peers/static_hc
RC="$H/ot_hbm_hc_bankq_term_static.sv $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_tail_unit_static.sv $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv
 rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
 rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv"
{ git diff --name-only "$BASE" -- rtl;git ls-files --others --exclude-standard -- rtl; } | grep -Ev '/(tb_|run_)' | sort -u > "$OUT/ovl.lst"
for f in $(cat "$OUT/ovl.lst") $RC;do
 [ -f "$f" ] && mkdir -p "$OUT/ovl/$(dirname "$f")" && cp "$f" "$OUT/ovl/$f"
done
X=();while read -r f;do X+=(--rtl-file "$f" --prefer "$f");done < <(find "$OUT/ovl" -name '*.sv' -o -name '*.v' | sort)
# Make the tested f12_l4 canonical qadd choice explicit after every other preference.
X+=(--prefer "$OUT/ovl/rtl/hdc/ot_hdc_fastfp_lat_c12.sv")
while read -r f;do
 [ "$f" = rtl/hbm_accel/die_glue/scoped_d4g/hcbt.sv ] && continue
 if [ -f "$OUT/ovl/$f" ];then echo "$OUT/ovl/$f";else echo "$BUNDLE/$f";fi
done < "$BUNDLE/files.f" > "$OUT/files_abs.f"
find "$OUT/ovl" -name '*.sv' -o -name '*.v' | sort >> "$OUT/files_abs.f"
python3 tools/die_port_bind.py "$OUT/top/die_b2.v" --top hbm_b2_die --rtl-root "$BUNDLE/rtl" --rtl-root "$BUNDLE/physical" -f "$OUT/files_abs.f" "${X[@]}" --out "$OUT/port_bind.json" > "$OUT/port_bind.log" 2>&1 || true
python3 - "$OUT/port_bind.json" <<'PY_CHECK'
import json,sys
r=json.load(open(sys.argv[1]));assert r.get('schema') and isinstance(r.get('summary'),dict),r
s=r['summary'];assert s.get('instances',0)>300,s
PY_CHECK
grep -E '^FAIL' "$OUT/port_bind.log" | grep -Ev '^FAIL \S+ +x[0-9]+ +INPUT_TIED |ot_hbm3e_phy_rc_e8p5 .*STUB|child ot_hbm_accel_smh_fc_' > "$OUT/new_fail.txt" || true
tail -1 "$OUT/port_bind.log"
if [ -s "$OUT/new_fail.txt" ];then cat "$OUT/new_fail.txt";echo 'B2_NATIVE_BIND FAIL';exit 1;fi
echo 'B2_NATIVE_BIND PASS'
echo 'Physical capacity, per-cut SU binding, W128 HC views, reset wavefront and L74 multi-beat schedule remain separate gates.'
