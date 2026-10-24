#!/bin/bash
# TOK-QW xdie_bound: LITERAL bound-partition carve of the D2D mechanism on both dies + elaboration (Verilator 5.050 lint).
#   compute: bound_r8 qwen_compute_bound_top {glue (d2d_rom + sys_face calendar producer), ucie_kv (PHY), native59}
#   KV:      bound_pv qwen_kvsys_bound_top {sys_c (d2d_kv master + dcal bc4 sequencer + ucie_rom PHY)}
# usage (repo root): carve_elab.sh OUTDIR    -> OUTDIR/{qc,kv}_* + ELAB.txt; also checks every staged closure file is
# byte-identical to the same path in this checkout (so the co-sim's main-path sources ARE the bound closure).
set -u
O=$1; mkdir -p "$O"
X=tools/qwen_tokfunc/xdie_bound
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
REV=$(git rev-parse HEAD)
QB=physical/die_plan/qwen_compute/bind/bound_r8; KB=physical/die_plan/qwen_kvsys/bind/bound_pv
python3 $X/bound_carve.py --top $QB/rtl/qwen_compute_bound_top.sv --seeds glue,ucie_kv,native59 --name qc_d2d_carve --out "$O" || exit 2
python3 $X/bound_carve.py --top $KB/rtl/qwen_kvsys_bound_top.sv --seeds sys_c --name kv_d2d_carve --out "$O" || exit 2
export CAL_SMOKE_CACHE_ROOT=$O/srccache
python3 $X/stage_closure.py --die qc --bound $QB --asbuilt physical/die_plan/qwen_compute/bind/asbuilt_tie.json --rev $REV --carve "$O/qc_d2d_carve.json" --work "$O" || exit 2
python3 $X/stage_closure.py --die kv --bound $KB --asbuilt physical/die_plan/qwen_kvsys/bind/asbuilt_v36e.json --rev $REV --carve "$O/kv_d2d_carve.json" --work "$O" || exit 2
: > "$O/ELAB.txt"
for d in qc kv; do
  n=0; bad=0
  while read -r f; do
    case "$f" in src/$d/bound/*) continue;; esac
    p=${f#src/$d/}; n=$((n+1))
    cmp -s "$O/$f" "$p" || { bad=$((bad+1)); echo "  closure file differs from checkout: $p" >> "$O/ELAB.txt"; }
  done < "$O/${d}_files.f"
  echo "$d closure: $n non-bound files, $bad differ from checkout $REV" >> "$O/ELAB.txt"
done
# KV hard models: the bound recipe's own (bound_pv/kv_hard_models.sv) + the PHY model inside ot_qkvd_ucie_x64_phy
EXTRA_kv="$KB/kv_hard_models.sv physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
EXTRA_qc=""
for d in qc kv; do
  t=${d}_d2d_carve; ex=EXTRA_$d
  (cd "$O" && $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN $(cat ${d}_defines.f) \
     $(sed 's|^|+incdir+|' ${d}_inc.f) $(cat ${d}_files.f) $(for e in ${!ex}; do echo "$OLDPWD/$e"; done) $t.v --top-module $t) > "$O/elab_$d.log" 2>&1
  rc=$?
  echo "$d elaboration rc=$rc errors=$(grep -c '%Error' "$O/elab_$d.log")" >> "$O/ELAB.txt"
  grep '%Error' "$O/elab_$d.log" | grep -v 'Exiting due' | sed 's/^/    /' >> "$O/ELAB.txt"
done
rm -rf "$O/srccache"
cat "$O/ELAB.txt"
