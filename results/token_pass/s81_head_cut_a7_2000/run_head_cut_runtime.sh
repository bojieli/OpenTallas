#!/bin/bash
# RTLGAP2-HEADTB (10-21): G-HEAD-DIE-TB -- per-tile hierarchical head-die token TB on the CURRENT bound head die
# (S81-HEAD H10b strict bind), Verilator 5.050.  Replaces the whole-die elaboration (H4: >166 GB, exit 143) by two cuts:
#   CUT-A  tb_s81hd_tilecut: one ot_s81hd_tile (die parameters, full RTL incl. bundle + 10 ROMs) built ONCE and run once per
#          die tile (253 runs, its rank-0 ROM images + die strap row0): every formed logit bit-exact vs the golden logits,
#          tile best = golden argmax of its 128 rows; records the bundle output face (lat, row, bits, fault) -> rec.hex.
#   CUT-B  tb_s81hd_diecut: the whole bound dv_die in RTL with ot_s81hd_bundle = ot_s81hd_bundle_replay.sv (input face
#          bit-checked vs the golden bus-B stream, output face = CUT-A's record): XB in on the lep, own BEST on the mesh,
#          peers' BEST in, merged token on the ring (K_TOK) + host RESULT = golden token 21946 / 4173a558.
#   run_head_cut.sh SRC BIND IMG TILES REF OUT [cases]
# SRC   head-die source root of the bind (H10b: stw-s81-head-h10/h10bm/src)   BIND  strict-bind dir (die.v, port_bind.json)
# IMG   head_die_images.py output (2,530 ROM images, xa/xb.hex, xb_beats.hex, golden.json)   TILES tiles.txt  REF golden npz
# cases (default all): a (CUT-A 253 tiles) a_mut (golden tile reads u_t_N00Wo0's images: must FAIL)
#                      b (CUT-B base: must PASS) b_mut_rec (golden tile's record bits -> second best: must FAIL)
#                      b_mut_slice (+define+OT_S81HD_CTL_MUT_SLICE in the bound ctl: must FAIL)
# Writes OUT/result.json (verdict HEAD_CUT PASS iff every case meets its expectation), build_*.time (peak RSS).
set -u
SRC=$(readlink -f $1); BIND=$(readlink -f $2); IMG=$(readlink -f $3); TILES=$(readlink -f $4); REF=$(readlink -f $5); OUT=$6; shift 6
CASES=${*:-a a_mut b b_mut_rec b_mut_slice}
mkdir -p $OUT; OUT=$(readlink -f $OUT); H=$(cd "$(dirname "$0")" && pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $V ] || V=verilator
$V --version > $OUT/verilator_version.txt
J=${J:-32}
python3 $H/head_cut_gold.py --ref $REF --tiles $TILES --golden $IMG/golden.json --out $OUT/gold > $OUT/gold.log 2>&1 \
  || { echo "GOLD_FAILED"; cat $OUT/gold.log; exit 2; }
# the die's exact file set (port_bind rtl_files, rtl_extra copies first) + the stage partner; CUT-B swaps the bundle
python3 - "$BIND/port_bind.json" "$SRC" "$H/ot_s81hd_bundle_replay.sv" $OUT <<'EOF'
import json, sys, os
d = json.load(open(sys.argv[1])); src = sys.argv[2]; shim = sys.argv[3]; out = sys.argv[4]
seen, fs = set(), []
for f in d["rtl_files"]:
    f = f if os.path.isabs(f) else os.path.join(src, f)
    b = os.path.basename(f)
    if b in seen:
        continue
    seen.add(b); fs.append(f)
p = os.path.join(src, "rtl/dsrom_sys/s81_head/ot_s81hd_lep.sv")
if os.path.basename(p) not in seen:
    fs.append(p)
assert any(os.path.basename(f) == "ot_s81hd_bundle.sv" for f in fs)
def w(name, files):
    dirs = sorted({os.path.dirname(f) for f in files})
    open(os.path.join(out, name), "w").write("\n".join(["+incdir+" + x for x in dirs] + files) + "\n")
w("files_a.f", fs)
w("files_b.f", [shim if os.path.basename(f) == "ot_s81hd_bundle.sv" else f for f in fs])
EOF
DEFS=$(python3 -c "import json,sys; print(' '.join('+define+'+x for x in json.load(open(sys.argv[1]))['defines']))" $BIND/port_bind.json)
sha256sum $BIND/die.v $BIND/port_bind.json $H/*.sv $H/*.py $H/*.sh > $OUT/inputs.sha256
# the masters' file list lacks their children (SerDes column, SRAM models, ...): resolve them from SRC (logged choices)
if [[ " $CASES " == *" b"* ]] && [ ! -s $OUT/files_b_full.f ]; then
  python3 $H/resolve_files.py --src $SRC --filelist $OUT/files_b.f --out $OUT/files_b_full.f.tmp --top tb_s81hd_diecut \
    --verilator $V --log $OUT/resolve_b.json --extra $BIND/die.v $H/tb_s81hd_diecut.sv -- $DEFS > $OUT/resolve_b.log 2>&1 \
    && mv $OUT/files_b_full.f.tmp $OUT/files_b_full.f || { echo "RESOLVE_FAILED b"; tail -5 $OUT/resolve_b.log; }
fi
VF="-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-MODDUP -Wno-WIDTHCONCAT"
build_a() {
  [ -x $OUT/obj_a/Vtb_s81hd_tilecut ] && return 0
  /usr/bin/time -v -o $OUT/build_a.time $V --binary --timing -O1 $VF $DEFS --top-module tb_s81hd_tilecut -Mdir $OUT/obj_a \
    -f $OUT/files_a.f $H/tb_s81hd_tilecut.sv --build-jobs $J -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $OUT/build_a.log 2>&1 || { echo "BUILD_FAILED a"; grep -m20 %Error $OUT/build_a.log; return 2; }
}
build_b() { n=$1; shift
  [ -x $OUT/obj_$n/Vtb_s81hd_diecut ] && return 0
  /usr/bin/time -v -o $OUT/build_$n.time $V --binary --timing -O0 -fno-inline $VF $DEFS "$@" --top-module tb_s81hd_diecut \
    -Mdir $OUT/obj_$n -f $OUT/files_b_full.f $BIND/die.v $H/tb_s81hd_diecut.sv --build-jobs $J --output-split 20000 \
    --output-split-cfuncs 2000 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1" > $OUT/build_$n.log 2>&1 \
    || { echo "BUILD_FAILED $n"; grep -m20 %Error $OUT/build_$n.log; return 2; }
}
run_head_binary() {
  if [ -n "${HEAD_BINARY_RUNNER:-}" ]; then
    "$HEAD_BINARY_RUNNER" "$@"
  else
    "$@"
  fi
}
export -f run_head_binary

run_tile() {   # run_tile CASEDIR INST IMGINST
  local d=$1/$2 i=$2 s=$3; mkdir -p $d
  for e in a0 a1 a2 a3 b; do for k in 0 1; do ln -sf $IMG/${s}${e}_$k.viamap.hex $d/t${e}_$k.viamap.hex; done; done
  read -r _ r0 er eb < <(awk -v t=$i '$1==t' $OUT/gold/tiles_gold.txt)
  ( cd $d && run_head_binary $OUT/obj_a/Vtb_s81hd_tilecut +DIR=$IMG +LG=$OUT/gold/lg/$i.hex +ROW0=$r0 +EXP_ROW=$er +EXP_BITS=$eb \
      +OT_ROM_DIR=$d > $d/run.log 2>&1 )
  rm -f $d/*.viamap.hex
}
export -f run_tile; export OUT IMG
GT=$(awk -v r=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['token']['row'])" $IMG/golden.json) \
     '$3==r{print $1}' $OUT/gold/tiles_gold.txt)
for c in $CASES; do
  case $c in
    a) build_a || continue
       awk '{print $1}' $TILES | xargs -P $J -I{} bash -c "run_tile $OUT/a {} {}"
       python3 - $OUT <<'EOF'
import re, sys, os, json
o = sys.argv[1]; res = {}; lines = []
for ln in open(os.path.join(o, "gold/tiles_gold.txt")):
    inst, r0, er, eb = ln.split()
    t = open(os.path.join(o, "a", inst, "run.log")).read()
    ok = bool(re.search(r"^PASS tilecut", t, re.M))
    m = re.search(r"^REC (\d+) (\d+) ([0-9a-f]{8}) (\d)", t, re.M)
    lg = re.search(r"^LOGITS (\d+)/(\d+)", t, re.M)
    res[inst] = dict(row0=int(r0), ok=ok, rec=m.groups() if m else None, logits=lg.group(0) if lg else None)
    if ok and m:
        lat, row, bits, flt = int(m.group(1)), int(m.group(2)), int(m.group(3), 16), int(m.group(4))
        v = (int(r0) << 66) | (lat << 50) | (row << 33) | (bits << 1) | flt
        lines.append(f"{v:021x}")
n_ok = sum(r["ok"] for r in res.values())
open(os.path.join(o, "rec.hex"), "w").write("\n".join(lines) + "\n")
lats = sorted({int(r["rec"][0]) for r in res.values() if r["rec"]})
json.dump(dict(tiles=len(res), pass_=n_ok, lats=lats, tiles_detail=res), open(os.path.join(o, "a.json"), "w"), indent=1)
print(f"CUT_A {n_ok}/{len(res)} tiles PASS, bundle lat {lats}")
EOF
       ;;
    a_mut) build_a || continue
       rm -rf $OUT/a_mut; run_tile $OUT/a_mut $GT u_t_N00Wo0
       echo "a_mut: golden tile $GT reads u_t_N00Wo0's images: $(grep -m1 -E '^(PASS|FAIL) tilecut' $OUT/a_mut/$GT/run.log)" ;;
    b) build_b b && ( cd $OUT && /usr/bin/time -v -o b.time obj_b/Vtb_s81hd_diecut +XB=$IMG/xb_beats.hex +HC_REC=$OUT/rec.hex \
         +DIR=$IMG $(python3 $H/head_cut_pa.py $IMG/golden.json) > b.log 2>&1 ); echo "b: $(grep -m1 -E '^(PASS|FAIL) head_die' $OUT/b.log)" ;;
    b_mut_rec)
       build_b b || continue
       # the golden tile's recorded bundle result -> the tile's second-best logit (row + bits): the die must lose the token
       python3 - $OUT $GT <<'EOF'
import sys, os
o, gt = sys.argv[1], sys.argv[2]
r0 = [int(l.split()[1]) for l in open(os.path.join(o, "gold/tiles_gold.txt")) if l.split()[0] == gt][0]
lg = [int(x, 16) for x in open(os.path.join(o, "gold/lg", gt + ".hex")).read().split()]
import struct
f = [struct.unpack(">f", struct.pack(">I", x))[0] for x in lg]
best = max(range(128), key=lambda k: (f[k], -k)); sec = max((k for k in range(128) if k != best), key=lambda k: (f[k], -k))
out = []
for ln in open(os.path.join(o, "rec.hex")).read().split():
    v = int(ln, 16)
    if v >> 66 == r0:
        v = (v & ~(((1 << 49) - 1) << 1)) | ((r0 + sec) << 33) | (lg[sec] << 1)
    out.append(f"{v:021x}")
open(os.path.join(o, "rec_mut.hex"), "w").write("\n".join(out) + "\n")
print(f"mut_rec: {gt} row0 {r0}: best {r0 + best} -> second {r0 + sec} {lg[sec]:08x}")
EOF
       ( cd $OUT && obj_b/Vtb_s81hd_diecut +XB=$IMG/xb_beats.hex +HC_REC=$OUT/rec_mut.hex +DIR=$IMG \
           $(python3 $H/head_cut_pa.py $IMG/golden.json) > b_mut_rec.log 2>&1 ); echo "b_mut_rec: $(grep -m1 -E '^(PASS|FAIL) head_die' $OUT/b_mut_rec.log)" ;;
    b_mut_slice)
       build_b b_mut_slice +define+OT_S81HD_CTL_MUT_SLICE && ( cd $OUT && obj_b_mut_slice/Vtb_s81hd_diecut +XB=$IMG/xb_beats.hex \
         +HC_REC=$OUT/rec.hex +DIR=$IMG $(python3 $H/head_cut_pa.py $IMG/golden.json) > b_mut_slice.log 2>&1 )
       echo "b_mut_slice: $(grep -m1 -E '^(PASS|FAIL) head_die' $OUT/b_mut_slice.log)" ;;
  esac
done
python3 $H/head_cut_report.py --out $OUT --img $IMG --bind $BIND
