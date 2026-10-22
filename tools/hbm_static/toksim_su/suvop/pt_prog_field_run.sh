#!/usr/bin/env bash
# HBM-PRETREE3 10-20: die form of the pre-tree command (H.STA.BLK.16.6 item 3, option A).  The 48-b per-quarter tree_cmd
# ({v,max,cntB5,cntA5} x 4 slices, su_pretree_lower.tree_cmd_word) rides in the SU programme command word as bits
# [2422 +: 48] of pgp_<q> = ot_hbm_su_programme_pslice_c5 #(.SB(2470)).  SB 2470 keeps NC = 10 columns (column 9 =
# bits 2304..2559 already exists, its pgcol leaf outputs 256 b, only the parent's truncation moves), so NO leaf / head
# master changes: every leaf stays the closed pgcol_s / pgcol_l master.  This bench lowers REAL pre-tree production
# records (prog.mem quarter k [2422 b] | tree.mem quarter k [48 b] << 2422) with su_programme_compile.py --columns
# --line-bits 2470 and runs the existing lockstep/golden bench tb_hbm_su_programme_pgcol (cluster vs r4 reference,
# every command line == golden incl. the tree field, directed fault cases).  Mutant (must FAIL): +MUT_CFG with the
# column-9 (tree-field column) index one edge off and its first dictionary word flipped.
# Usage: OUT=dir RECS="dir1 dir2 ..." $0      (each rec dir has prog.mem + tree.mem as written by prod_compile --pretree)
set -euo pipefail
ulimit -c 0
OUT=$(mkdir -p "${OUT:?OUT required}" && realpath "$OUT")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=rtl/hbm_accel/generic/adapters/static_su/programme
R=rtl/lib/ot_rst_relay.sv
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SB=2470
"$vl" --version > "$OUT/verilator.txt"
ok=1
for rec in ${RECS:?RECS required}; do
  n=$(basename "$rec")
  # quarters whose tree field is active (others carry tree word 0 = the as-built image; quarter 0 always run)
  qs=$(python3 - "$rec" "$OUT/$n" "$SB" <<'PY'
import sys; from pathlib import Path
rec,o,sb=Path(sys.argv[1]),Path(sys.argv[2]),int(sys.argv[3]); o.mkdir(parents=True,exist_ok=True)
P=[int(t,16) for t in (rec/'prog.mem').read_text().split()]
T=[int(t,16) for t in (rec/'tree.mem').read_text().split()]
T+= [0]*(len(P)-len(T)); assert len(T)==len(P), (len(T),len(P))
# the pgcol leaves are built for the resident 7111-edge producer (EDGES default, 4 packed index banks): the record is
# placed at edge 0 of a resident image and the remaining edges are all-zero (no command), as in the production image
assert len(P)<=7111; P+= [0]*(7111-len(P)); T+= [0]*(7111-len(T))
act=[]
for k in range(4):
    rows=[((p>>(2422*k))&((1<<2422)-1)) | (((t>>(48*k))&((1<<48)-1))<<2422) for p,t in zip(P,T)]
    nz=sum(1 for t in T if (t>>(48*k))&((1<<48)-1))
    if nz or k==0: act.append(k)
    d=o/f'q{k}'; d.mkdir(exist_ok=True)
    (d/'source.mem').write_text(''.join(f'{r:0{(sb+3)//4}x}\n' for r in rows))
    (d/'tree_active_edges.txt').write_text(f'{nz}\n')
print(' '.join(map(str,act)))
PY
)
  for k in $qs; do
    d="$OUT/$n/q$k"
    python3 tools/hbm_static/su_programme_compile.py "$d/source.mem" "$d" --columns --line-bits $SB \
      --mut-pc-col 9 --mut-tpl-col 9 > "$d/cols.log"
    for m in 0; do
      "$vl" --binary --timing -O1 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND --top-module tb_hbm_su_programme_pgcol \
        -I"$d" -GMUT=$m --Mdir "$d/obj$m" "$R" "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_part.sv" \
        "$s/ot_hbm_su_programme_pgcol.sv" "$s/tb_hbm_su_programme_pgcol.sv" "$M" > "$d/build$m.log" 2>&1 \
        || { tail -20 "$d/build$m.log"; echo "PT_PROG_FIELD BUILD_FAIL $n q$k"; exit 2; }
    done
    set +e
    "$d/obj0/Vtb_hbm_su_programme_pgcol" +DIR="$d" > "$d/run_positive.log" 2>&1; rp=$?
    "$d/obj0/Vtb_hbm_su_programme_pgcol" +DIR="$d" +MUT_CFG > "$d/run_mut_cfg9.log" 2>&1; rm_=$?
    set -e
    pv=$(grep -h "SU_PROGRAMME_PGCOL" "$d/run_positive.log" | tail -1)
    mv=$(grep -h "SU_PROGRAMME_PGCOL" "$d/run_mut_cfg9.log" | tail -1)
    ta=$(cat "$d/tree_active_edges.txt"); c9=$(python3 -c "import json;m=json.load(open('$d/cols_manifest.json'));c=m['columns'][9];print(c['leaf'],c['dictionary_entries'],c['dictionary_banks'])")
    echo "[$n q$k] tree_active_edges=$ta col9(leaf,entries,banks)=$c9 positive rc=$rp: $pv"
    echo "[$n q$k] mut_cfg9 rc=$rm_: $mv"
    grep -q "SU_PROGRAMME_PGCOL PASS" "$d/run_positive.log" || ok=0
    grep -q "SU_PROGRAMME_PGCOL FAIL" "$d/run_mut_cfg9.log" || { ok=0; echo "[$n q$k] MUTANT ESCAPED"; }
  done
done
[ $ok = 1 ] && { echo "PT_PROG_FIELD_GATE PASS SB=$SB"; exit 0; }
echo "PT_PROG_FIELD_GATE FAIL"; exit 1
