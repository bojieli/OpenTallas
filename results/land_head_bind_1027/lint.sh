#!/bin/bash
# Verilator lint (5.050) of a generated HEAD die top.  usage: lint.sh GEN
set -u
R=/srv/opentallas-scratch2/claude/land-head-bind-1
g=$1
cd "$R"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
inc=$(xargs -n1 dirname < ${g}_lintsim.f | sort -u | sed 's/^/-I/' | tr '\n' ' ')
verilator --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY --top-module s81_head_top \
    $inc -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -f ${g}_lintsim.f $g/s81_head_top.sv > $g.lint.log 2>&1
echo "lint rc=$?" >> $g.lint.log
grep -c "^%Error" $g.lint.log >> $g.lint.log
grep -o "^%Warning-[A-Z0-9_]*" $g.lint.log | sort | uniq -c >> $g.lint.log
