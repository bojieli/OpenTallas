#!/bin/bash
# QXPQ-FIX/FSTA: run every frame-region STA case in one ORFS container (OpenSTA from openroad/orfs:asap7lock).
# Layout under $PWD: net/<case>/{netlist.v,wire.spef}, views/{q,qbn,qbs_s,qbs_t,seq}/, fsta.tcl; outputs out/<run>.{log,slk}
set -u
D=$(pwd)
mkdir -p out
cat > out/cases.txt <<'EOF'
h9 qbs_s
h10 qbs_s
h9t qbs_t
h10t qbs_t
EOF
# run: corner spef trunk tag
cat > out/runs.txt <<'EOF'
tt 1 445.0 nom
tt 0 445.0 nom
ff 1 355.5 nom
ff 0 355.5 nom
ff 0 373.275 p5
ff 0 337.725 m5
ff 1 373.275 p5
ff 1 337.725 m5
tt 1 467.25 p5
tt 1 422.75 m5
EOF
docker run --rm -u $(id -u):$(id -g) -v "$D":/w -w /w openroad/orfs:asap7lock bash -c '
STA=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta
while read net qbs; do
  while read c s t tag; do
    r=${net}_${c}_w${s}_${tag}
    CORNER=$c NETDIR=/w/net/$net SPEF=$s TRUNK=$t OUT=/w/out/$r.slk QV=/w/views/q QBN=/w/views/qbn QBS=/w/views/$qbs SEQ=/w/views/seq \
      $STA -no_init -no_splash -exit /w/fsta.tcl < /dev/null > /w/out/$r.log 2>&1
    echo "$r rc=$? $(grep -h FSTA_DUMP /w/out/$r.log)"
  done < /w/out/runs.txt
done < /w/out/cases.txt
'
echo FSTA_ALL_DONE
