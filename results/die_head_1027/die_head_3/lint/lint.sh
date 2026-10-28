#!/bin/bash
# DIE-HEAD-3: Verilator lint of the LAND-HEAD-BIND-1 gen2 landed top with BLACKBOXED hard cores (ot_s81hd_elem_cv_bb_native.v + *_bb.v macros)
cd /srv/opentallas-scratch2/claude/die-head-3/lint
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
G=/srv/opentallas-scratch2/claude/land-head-bind-1/gen2
inc=$(xargs -n1 dirname < gen2_lint_dh3.f | sort -u | sed "s/^/-I/" | tr "\n" " ")
verilator --version
/usr/bin/time -v verilator --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY --top-module s81_head_top -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF $inc -f gen2_lint_dh3.f $G/s81_head_top.sv > gen2_bb.lint.log 2>&1
echo "lint rc=$?" >> gen2_bb.lint.log
