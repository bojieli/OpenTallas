#!/bin/bash
# xdie_bound on ARBITRARY bind dirs (FABLE-FIX-QC-CBGLUE 11-16): the compute <-> KV D2D exchange co-sim with the seam
# stages of two strict binds given as arguments, instead of the binds checked into the repo (bound_r8 / bound_pv).
#   run_binds.sh QC_BIND_DIR KV_BIND_DIR OUTDIR [CONFIG ...]        (run from the root of the source tree under test)
# QC_BIND_DIR / KV_BIND_DIR = tools/die_plan/bind.py --out dirs (bus_groups.json[.gz] inside).  Seam stages:
#   compute half  XDIE_SEAM_C of tools/die_plan/regen_constants.py --die qwen_compute --bound QC_BIND_DIR (must be status OK:
#                 one Delta per seam bundle), and its D2D_TXDP_C must equal the TXDP the bound glue u_d2d_rom carries;
#   KV half       physical/die_plan/qwen_kvsys/boot_v36/kst.py KV_BIND_DIR/bus_groups.json (the pair-image recipe's own reader).
# XB_C_STAGES / XB_K_STAGES override either half (a predicted seam before its bind exists).
# Then run_xdie_bound.sh with XB_STAGES=C/K.  Default configs = the ones that do not hardcode old TXDP bytes: the pair on
# source and bound compute masters, layer 0, and one +1 seam mutant per direction + payload mutants (each must FAIL).
set -u
QC=$1; KV=$2; OUT=$(realpath -m "$3"); shift 3
X=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
C=${XB_C_STAGES:-}; K=${XB_K_STAGES:-}
if [ -z "$C" ]; then
  python3 -I tools/die_plan/regen_constants.py --die qwen_compute --bound "$QC" --src-root . --out-json "$OUT/regen_qc.json" > "$OUT/regen_qc.log" 2>&1
  C=$(python3 -I - "$OUT/regen_qc.json" "$QC" <<'PY'
import json, re, sys, glob
c = json.load(open(sys.argv[1]))["constants"]
s, t = c.get("XDIE_SEAM_C") or {}, c.get("D2D_TXDP_C") or {}
if s.get("status") != "OK" or t.get("status") != "OK":
    sys.exit("XDIE_SEAM_C / D2D_TXDP_C not OK on this bind: %s / %s" % (s.get("status"), t.get("status")))
g = [f for f in glob.glob(sys.argv[2] + "/rtl/*glue*.sv")]
b = [m for f in g for m in re.findall(r"\.TXDP\(32'h([0-9a-fA-F]+)\)", open(f).read())]
want = re.search(r"'h([0-9a-fA-F]+)", t["sv_literal"]).group(1).lower()
if not b or {x.lower() for x in b} != {want}:
    sys.exit("bound glue TXDP %s != regenerated D2D_TXDP_C %s" % (sorted(set(b)), want))
print(s["value"])
PY
  ) || { echo "run_binds: compute seam: $C"; tail -3 "$OUT/regen_qc.log"; exit 2; }
fi
if [ -z "$K" ]; then
  BG=$KV/bus_groups.json; [ -f "$BG" ] || { zcat "$KV/bus_groups.json.gz" > "$OUT/kv_bus_groups.json"; BG=$OUT/kv_bus_groups.json; }
  K=$(python3 physical/die_plan/qwen_kvsys/boot_v36/kst.py "$BG") || { echo "run_binds: kst.py failed on $KV"; exit 2; }
fi
echo "$C" | grep -Eq '^[0-9]+(,[0-9]+){5}$' && echo "$K" | grep -Eq '^[0-9]+(,[0-9]+){6}$' || { echo "run_binds: bad stages C=$C K=$K"; exit 2; }
echo "qc_bind $QC" > "$OUT/BINDS.txt"; echo "kv_bind $KV" >> "$OUT/BINDS.txt"; echo "stages $C/$K" >> "$OUT/BINDS.txt"
[ $# -gt 0 ] || set -- src_pair src_pair_l0 compat_pair src_mut_seam_cs_txs_p1 src_mut_seam_ks_rxv_p1 src_mut_seam_sk_txp_p1 \
  src_mut_result_bit src_mut_status_done
XB_STAGES="$C/$K" bash "$X/run_xdie_bound.sh" "$OUT/cosim" "$@"; rc=$?
echo "RESULT stages=$C/$K cosim_all_expected=$([ $rc = 0 ] && echo YES || echo NO)" | tee -a "$OUT/BINDS.txt"
exit $rc
