#!/usr/bin/env bash
# x-store commit tracker gate: ot_hbm_b2_xcommit + the real PIPE1 sink + the real native SM (ot_hbm_accel_smh, production
# defines, no parameter overrides).  One Verilator build, five runs (+SEL = tracker MUT 0..4).
#   ot-heavy --mem 24 -- bash rtl/hbm_accel/generic/adapters/native_b2/run_xcommit.sh <out dir> [build jobs]
# Run from the root of a source snapshot (git archive of the commit under test).
set -euo pipefail
out=$1
jobs=${2:-32}
here=rtl/hbm_accel/generic/adapters/native_b2
mkdir -p "$out"
if [[ -e $out/source.sha256 ]]; then echo refuse_overwriting_receipt; exit 2; fi
VER=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}   # VERILATOR=<path> overrides
[[ -x $VER ]] || VER=$(command -v verilator)
mapfile -t src < <(python3 - <<'P'
import os, sys
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
sys.path.insert(0, "tools")
import dshbm_sm_pq_seq as P
for s in [s for s in P.SRC if not s.startswith("rtl/test/")] + P.SMH_SRC + ["rtl/hdc/ot_hdc_cg.sv", "rtl/hbm_accel/cg/ot_cg_tile.sv"]:
    print(s)
P
)
src+=("$here/ot_hbm_b2_vm8_sm_sink.sv" "$here/ot_hbm_b2_xcommit.sv" "$here/tb_hbm_b2_xcommit.sv")
defs=(-DOT_SMH -DOT_SMH_CG -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_FC_HIER -DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST
      -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_MEM_NO_INIT)
sha256sum "${src[@]}" "$here/tb_hbm_b2_xcommit_vec.py" "$here/run_xcommit.sh" tools/dshbm_sm_pq_seq.py \
    tools/dshbm_matched_sm_seq.py tools/rtl_gpu_sm_exact.py > "$out/source.sha256"
{ hostname; date -Is; "$VER" --version; echo "defines: ${defs[*]}"; echo "top: tb_hbm_b2_xcommit (ot_hbm_accel_smh without parameter overrides)"; } > "$out/environment.txt"
python3 "$here/tb_hbm_b2_xcommit_vec.py" gen --dir "$out/vec" | tee "$out/gen.log"
nops=$(awk '/^NOPS/{print $2}' "$out/gen.log")
set +e
/usr/bin/time -v "$VER" --binary --timing -O2 -Wno-fatal --top-module tb_hbm_b2_xcommit --Mdir "$out/build" -j "$jobs" \
    "${defs[@]}" "${src[@]}" > "$out/build.log" 2>&1
rc=$?
set -e
echo $rc > "$out/build.rc"
if [[ $rc -ne 0 ]]; then tail -40 "$out/build.log"; exit 3; fi
bad=0
for sel in 0 1 2 3 4; do
    d=$out/mut$sel
    mkdir -p "$d"
    for f in seq.hex lines.hex x.hex xc.hex gold.json; do ln -f "$out/vec/$f" "$d/$f"; done
    set +e
    /usr/bin/time -v "$out/build/Vtb_hbm_b2_xcommit" +DIR="$d" +NOPS="$nops" +SEL=$sel > "$d/run.log" 2>&1
    echo $? > "$d/sim.rc"
    python3 "$here/tb_hbm_b2_xcommit_vec.py" check --dir "$d" --sel $sel --out "$d/result.json" > "$d/check.log" 2>&1
    rc=$?
    set -e
    echo $rc > "$d/rc"
    echo "== mut$sel rc $rc"; cat "$d/check.log"
    if [[ $sel == 0 && $rc -ne 0 ]]; then bad=1; fi
    if [[ $sel != 0 && $rc -ne 1 ]]; then bad=1; fi     # a mutant must be REJECTED by the verdict (rc 1), not crash
done
echo $bad > "$out/gate.rc"
exit $bad
