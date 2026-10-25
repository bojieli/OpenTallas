#!/usr/bin/env bash
# HBM-HC (2026-10-24): B2 die top with the HC half-hub fragment (tools/hbm_b2/hc_half_items.py) vs without, strict port bind.
#   tools/hbm_b2/run_hc_half_bind.sh OUT BUNDLE [BASE]   (repo root of the branch; BUNDLE = r18h5 source bundle with files.f)
# The overlay = every rtl file changed in the working tree vs BASE (default d13ff7c78 = the bind branch point, as gate_b2_bind.sh) + the canonical terminal bank (replaces scoped hcbt.sv).
# PASS = fragment checks 0 fail, b2_top with the fragment has no CUT_UNRESOLVED / UNDRIVEN, and the port-bind FAIL lines with
# the fragment are the baseline FAIL lines minus every HC line (no new FAIL; hc_eng / hc_* / hcb_* clean).
set -uo pipefail
OUT=$(realpath -m "${1:?out}"); BUNDLE=$(realpath "${2:?bundle}"); BASE=${3:-d13ff7c78}
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT"; mkdir -p "$OUT/ovl"
DIE=physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz; AB=physical/die_plan/hbm/bind/asbuilt.json
python3 tools/hbm_b2/hc_half_items.py --die $DIE --asbuilt $AB --out "$OUT/hc_items.json" > "$OUT/items.log" 2>&1 || { cat "$OUT/items.log"; echo "HC_HALF_BIND FAIL items"; exit 1; }
git diff --name-only $BASE -- rtl | grep -Ev '/(tb_|run_)' > "$OUT/ovl.lst"
git ls-files --others --exclude-standard -- rtl | grep -Ev '/(tb_|run_)' >> "$OUT/ovl.lst"
# the NQ 2 root is the canonical ot_hbm_hc_root_static (the bundle carries a scoped die copy whose children are renamed):
# its canonical child closure joins the overlay (unchanged files)
H=rtl/hbm_accel/generic/peers/static_hc
RC="$H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_tail_unit_static.sv $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv
 rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv"
for f in $(sort -u "$OUT/ovl.lst") $H/ot_hbm_hc_bankq_term_static.sv $RC; do
  [ -f "$f" ] && mkdir -p "$OUT/ovl/$(dirname $f)" && cp "$f" "$OUT/ovl/$f"; done
X=""; for f in $(find "$OUT/ovl" -name '*.sv' -o -name '*.v' | sort); do X="$X --rtl-file $f --prefer $f"; done
while read rel; do [ "$rel" = rtl/hbm_accel/die_glue/scoped_d4g/hcbt.sv ] && continue
  if [ -f "$OUT/ovl/$rel" ]; then echo "$OUT/ovl/$rel"; else echo "$BUNDLE/$rel"; fi; done < "$BUNDLE/files.f" > "$OUT/files_abs.f"
# overlay files LAST: a later preferred definition wins over the bundle's scoped copies (scoped_d4g/hc*.sv)
find "$OUT/ovl" -name '*.sv' -o -name '*.v' | sort >> "$OUT/files_abs.f"
for v in base hc; do
  it=(); [ $v = hc ] && it=(--rtl-items "$OUT/hc_items.json")
  python3 tools/hbm_b2/make_wiring.py --die $DIE --asbuilt $AB "${it[@]}" --out "$OUT/wiring_$v.json" > "$OUT/mw_$v.log" 2>&1
  python3 tools/hbm_b2/b2_top.py --die $DIE --asbuilt $AB --delta "$OUT/wiring_$v.json" --out "$OUT/top_$v" > "$OUT/b2_$v.log" 2>&1; echo "b2_top $v rc=$?"
  python3 tools/die_port_bind.py "$OUT/top_$v/die_b2.v" --top hbm_b2_die --rtl-root "$BUNDLE/rtl" --rtl-root "$BUNDLE/physical" \
    -f "$OUT/files_abs.f" $X --out "$OUT/pb_$v.json" > "$OUT/pb_$v.log" 2>&1
  grep -E '^FAIL' "$OUT/pb_$v.log" | sort > "$OUT/pbfail_$v.txt"; echo "port-bind $v: $(wc -l < "$OUT/pbfail_$v.txt") FAIL lines; $(tail -1 "$OUT/pb_$v.log" | cut -c1-300)"
done
hcre='(^| )(hc_eng|hc_NW|hc_NE|hcb_N[WE][0-7])( |$)|ot_hbm_hc_(root|qhub|bankq)'
comm -13 "$OUT/pbfail_base.txt" "$OUT/pbfail_hc.txt" | grep -Ev '^FAIL \S+ +x[0-9]+ +INPUT_TIED ' > "$OUT/pb_new.txt"
grep -E "$hcre" "$OUT/pbfail_hc.txt" | grep -Ev '^FAIL \S+ +x[0-9]+ +INPUT_TIED ' > "$OUT/pb_hc_left.txt"
cut=$(python3 - "$OUT/top_base/b2_top_report.json" "$OUT/top_hc/b2_top_report.json" <<'PY'
import json, re, sys
b, h = (json.load(open(f))['detail'] for f in sys.argv[1:3])
hcre = re.compile(r'^(hc_eng|hc_NW|hc_NE|hcb_N[WE][0-7])\.')
n = 0
for k in ('CUT_UNRESOLVED', 'UNDRIVEN'):
    n += len([x for x in h.get(k, []) if hcre.match(x) or x not in set(b.get(k, []))])
print(n)
PY
)
echo "new FAIL lines with the fragment: $(wc -l < "$OUT/pb_new.txt"); HC FAIL lines left: $(wc -l < "$OUT/pb_hc_left.txt"); b2_top cut/undriven: $cut"
[ ! -s "$OUT/pb_new.txt" ] && [ ! -s "$OUT/pb_hc_left.txt" ] && [ "$cut" = 0 ] && echo "HC_HALF_BIND PASS" || { head -20 "$OUT/pb_new.txt" "$OUT/pb_hc_left.txt"; echo "HC_HALF_BIND FAIL"; exit 1; }
