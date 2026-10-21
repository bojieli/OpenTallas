#!/bin/bash
# TOK-FUNC2-S81-LX (10-21): TOK.DS.LAYER.5 LM head on the whole bound S81 head die (tb_s81hd_die.sv), Verilator 5.050.
#   run_head_die.sh SRC BIND IMG OUT [base|mut_slice|mut_img ...]
# SRC  = the head-die source root of the bind (rtl/, physical/; S81-HEAD H4: codex-s81-head-chain-1021/h4/src)
# BIND = the strict-bind dir (die.v + port_bind.json: its rtl_files / defines are the die's exact file set)
# IMG  = head_die_images.py output (2,530 ROM images, xb_beats.hex, golden.json)
# Cases: base (PASS expected); mut_slice = +define+OT_S81HD_CTL_MUT_SLICE (ctl x word select wrong) and mut_img = the
# tile holding the golden row reads another tile's ROM images: both must FAIL.  Writes OUT/<case>.log + OUT/result.json.
set -u
SRC=$(readlink -f $1); BIND=$(readlink -f $2); IMG=$(readlink -f $3); OUT=$4; shift 4
CASES=${*:-base mut_slice mut_img}
mkdir -p $OUT; OUT=$(readlink -f $OUT); H=$(cd "$(dirname "$0")" && pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $V ] || V=verilator
$V --version > $OUT/verilator_version.txt
python3 - "$BIND/port_bind.json" "$SRC" > $OUT/files.f <<'EOF'
import json, sys, os
d = json.load(open(sys.argv[1])); src = sys.argv[2]
seen, out = set(), []
for f in d["rtl_files"]:
    f = f if os.path.isabs(f) else os.path.join(src, f)
    b = os.path.basename(f)
    if b in seen:            # rtl_extra copies (listed first) win over the source-tree copy of the same file
        continue
    seen.add(b); out.append(f)
for f in ("rtl/dsrom_sys/s81_head/ot_s81hd_lep.sv",):   # the stage-circuit partner (not on the head die)
    p = os.path.join(src, f)
    if os.path.basename(p) not in seen:
        out.append(p)
dirs = sorted({os.path.dirname(f) for f in out})
print("\n".join(["+incdir+" + x for x in dirs] + out))
EOF
DEFS=$(python3 -c "import json,sys; print(' '.join('+define+'+x for x in json.load(open(sys.argv[1]))['defines']))" $BIND/port_bind.json)
PA=$(python3 - $IMG/golden.json <<'EOF'
import json, sys
g = json.load(open(sys.argv[1])); p = g["peers"]
a = [f"+LROW={g['local']['row']}", f"+LBITS={g['local']['bits']}", f"+TROW={g['token']['row']}", f"+TBITS={g['token']['bits']}"]
for i, q in enumerate(p, 1):
    a += [f"+P{i}ROW={q['row']}", f"+P{i}BITS={q['bits']}"]
print(" ".join(a))
EOF
)
build() { n=$1; shift
  [ -x $OUT/obj_$n/Vtb_s81hd_die ] && return 0
  /usr/bin/time -v -o $OUT/build_$n.time $V --binary --timing -O0 -fno-inline -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    -Wno-lint -Wno-style -Wno-MODDUP $DEFS "$@" --top-module tb_s81hd_die -Mdir $OUT/obj_$n -f $OUT/files.f $BIND/die.v \
    $H/tb_s81hd_die.sv --build-jobs ${J:-16} --output-split 20000 --output-split-cfuncs 2000 \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1" > $OUT/build_$n.log 2>&1 \
    || { echo "BUILD_FAILED $n"; grep -m20 %Error $OUT/build_$n.log; return 2; }
}
run() { n=$1 obj=$2 img=$3
  ( cd $OUT && /usr/bin/time -v -o $OUT/$n.time $OUT/obj_$obj/Vtb_s81hd_die +OT_ROM_DIR=$img +XB=$IMG/xb_beats.hex $PA > $OUT/$n.log 2>&1 )
  echo "$n: $(grep -m1 -E '^(PASS|FAIL) head_die' $OUT/$n.log)"
}
for c in $CASES; do
  case $c in
    base) build base && run base base $IMG ;;
    mut_slice) build mut_slice +define+OT_S81HD_CTL_MUT_SLICE && run mut_slice mut_slice $IMG ;;
    mut_img)
      M=$OUT/img_mut; rm -rf $M; mkdir -p $M
      for f in $IMG/*.viamap.hex; do ln -s $f $M/; done
      T=$(python3 -c "import json,sys;g=json.load(open(sys.argv[1]));print(g['token']['row']//128*128)" $IMG/golden.json)
      TI=$(awk -v r=$T '$2==r{print $1}' $IMG/../tiles.txt)
      for f in $M/${TI}*.viamap.hex; do b=$(basename $f); rm $f; ln -s $IMG/u_t_N00Wo0${b#$TI} $M/$b; done
      echo "mut_img: tile $TI (row0 $T) reads u_t_N00Wo0's images" > $OUT/mut_img.what
      build base && run mut_img base $M ;;
  esac
done
python3 - $OUT $IMG/golden.json <<'EOF'
import json, re, sys, os
o, g = sys.argv[1], json.load(open(sys.argv[2]))
res = dict(schema="opentallas.tokfunc_s81.head_die_run.v1", grade="RTL-functional (source assembly: bound head die H4)",
           golden=g, cases={})
for n in ("base", "mut_slice", "mut_img"):
    p = os.path.join(o, n + ".log")
    if not os.path.exists(p):
        continue
    t = open(p).read()
    v = re.search(r"^(PASS|FAIL) head_die.*$", t, re.M)
    cyc = {}
    for m in re.finditer(r"^CYC (.*)$", t, re.M):
        for k, val in re.findall(r"(\S+) (-?\d+)", m.group(1)):
            cyc[k] = int(val)
    res["cases"][n] = dict(verdict=v.group(1) if v else "NO_RESULT", line=v.group(0) if v else None, cycles=cyc,
                           expect="PASS" if n == "base" else "FAIL")
res["ok"] = all(c["verdict"] == c["expect"] for c in res["cases"].values()) and "base" in res["cases"]
json.dump(res, open(os.path.join(o, "result.json"), "w"), indent=1)
print("HEAD_DIE", "PASS" if res["ok"] else "FAIL", {k: v["verdict"] for k, v in res["cases"].items()})
EOF
