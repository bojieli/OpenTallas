#!/bin/bash
set -euo pipefail
R=$PWD
exec 9> "$R/out/.b_resume.lock"
flock -n 9 || { echo "duplicate continuation writer" >&2; exit 73; }
python3 "$R/verify_retained.py" > "$R/out/retained_integrity.log"
O=$R/out
H=$R/tools
B=$R/bind
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > "$O/verilator_version.txt"
mapfile -t defs < <(python3 -c 'import json,sys;print("\n".join("+define+"+x for x in json.load(open(sys.argv[1]))["defines"]))' "$B/port_bind.json")
VF=(-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-MODDUP -Wno-WIDTHCONCAT)
python3 - <<'VERIFY'
from pathlib import Path
import hashlib,json
for e in json.loads(Path('source_identity.json').read_text())['files']:
 assert hashlib.sha256(Path(e['staged']).read_bytes()).hexdigest()==e['sha256'],e
print('all staged source, header and input hashes verified')
VERIFY
build_b() {
 n=$1;shift
 [ -x "$O/obj_$n/Vtb_s81hd_diecut" ] && return 0
 if [ "$n" = b ]; then
  /usr/bin/time -v -o "$O/build_b_resume.time" make -C "$O/obj_b" -f Vtb_s81hd_diecut.mk -j2 OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1 > "$O/build_b_resume.log" 2>&1
 else
 /usr/bin/time -v -o "$O/build_$n.time" "$V" --binary --timing -O0 -fno-inline "${VF[@]}" "${defs[@]}" "$@" --top-module tb_s81hd_diecut   -Mdir "$O/obj_$n" -f "$R/files_b_full.f" "$B/die.v" "$H/tb_s81hd_diecut.sv" --build-jobs 2 --output-split 20000   --output-split-cfuncs 2000 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1' > "$O/build_$n.log" 2>&1
 fi
 sha256sum "$O/obj_$n/Vtb_s81hd_diecut" > "$O/binary_$n.sha256"
}
mapfile -t plus < <(python3 "$H/head_cut_pa.py" "$R/img/golden.json" | tr ' ' '\n')
build_b b
python3 "$R/record_link_identity.py" > "$O/link_identity_b.json"
set +e
(cd "$O" && /usr/bin/time -v -o b.time obj_b/Vtb_s81hd_diecut +XB="$R/img/xb_beats.hex" +HC_REC="$O/rec.hex" +DIR="$R/img" "${plus[@]}" > b.log 2>&1)
rc=$?
set -e
printf '%s\n' "$rc" > "$O/b.exit"
if ! grep -q '^PASS head_die' "$O/b.log"; then
 python3 "$H/head_cut_report.py" --out "$O" --img "$R/img" --bind "$B"
 exit 2
fi
GT=$(python3 - <<'GT'
import json
r=json.load(open('img/golden.json'))['token']['row']
for l in open('out/gold/tiles_gold.txt'):
 s=l.split()
 if int(s[2])==r: print(s[0]);break
GT
)
python3 mutate_record.py "$O" "$GT" > "$O/mutate_record.log"
set +e
(cd "$O" && obj_b/Vtb_s81hd_diecut +XB="$R/img/xb_beats.hex" +HC_REC="$O/rec_mut.hex" +DIR="$R/img" "${plus[@]}" > b_mut_rec.log 2>&1)
rc=$?
set -e
printf '%s\n' "$rc" > "$O/b_mut_rec.exit"
build_b b_mut_slice +define+OT_S81HD_CTL_MUT_SLICE
python3 "$R/record_link_identity.py" b_mut_slice > "$O/link_identity_b_mut_slice.json"
set +e
(cd "$O" && obj_b_mut_slice/Vtb_s81hd_diecut +XB="$R/img/xb_beats.hex" +HC_REC="$O/rec.hex" +DIR="$R/img" "${plus[@]}" > b_mut_slice.log 2>&1)
rc=$?
set -e
printf '%s\n' "$rc" > "$O/b_mut_slice.exit"
python3 "$H/head_cut_report.py" --out "$O" --img "$R/img" --bind "$B"
