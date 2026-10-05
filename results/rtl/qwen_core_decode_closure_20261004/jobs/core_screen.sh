#!/bin/bash
# Core decode screen: Yosys 0.68 synth of a screen copy of the emitted core (Yosys 0.68 workarounds of
# qwen_dspark_closure_20261004/jobs/fix_scr*.py; logic identical), spine / vstream / stream black-boxed, then the
# repaired register-to-register SS screen (tools/risk_clock_loops_screen.py's script without I/O constraints).
# usage: core_screen.sh LABEL VPOS DEC_LA
R=/srv/opentallas-scratch/claude/qwen-core-decode; OLD=/srv/opentallas-scratch/claude/qwen-dspark-closure
L=$1; V=$2; D=$3; W=$R/runs/$L; mkdir -p $W/named
cd $R/src
cp gen/ot_qwen_rom_core.sv gen/ot_qwen_rom_core_scr_$L.sv
sed "s#gen_dsc/ot_qwen_rom_core_scr.sv#gen/ot_qwen_rom_core_scr_$L.sv#" $OLD/jobs/fix_scr.py > $W/fix1.py
sed "s#gen_dsc/ot_qwen_rom_core_scr.sv#gen/ot_qwen_rom_core_scr_$L.sv#" $OLD/jobs/fix_scr2.py > $W/fix2.py
python3 - gen/ot_qwen_rom_core_scr_$L.sv <<'PY' || exit 1
import sys
p = sys.argv[1]; t = open(p).read()
a = "    generate if (VPOS != 0) begin : g_vpos_tiles\n        genvar vpt;\n"
assert t.count(a) == 1
open(p, "w").write(t.replace(a, "    genvar vpt;\n    generate if (VPOS != 0) begin : g_vpos_tiles\n"))
PY
python3 $W/fix1.py && python3 $W/fix2.py || exit 1
sed -e "s#$OLD/src/gen_dsc/ot_qwen_rom_core_scr.sv#$R/src/gen/ot_qwen_rom_core_scr_$L.sv#" \
    -e "s#$OLD/src/gen_dsc/ot_hdc_vstream_rt.sv#$R/src/gen/ot_hdc_vstream_rt.sv#" \
    -e "s#$OLD/src/#$R/src/#g" \
    -e "s#-chparam VPOS 1#-chparam VPOS $V -chparam DEC_LA $D#" \
    -e "s#$OLD/runs/core_vpos1s_0833#$W#g" $OLD/runs/core_vpos1s_0833/named/synth.ys > $W/named/synth.ys
grep -q "DEC_LA $D" $W/named/synth.ys || { echo "chparam patch failed"; exit 2; }
# the kept prefix adders of the DEC_LA predecode
sed -i "0,/^read_verilog .*ot_hdc_stream.sv/s##&\nread_verilog -sv -I$R/src/rtl/hdc $R/src/rtl/hdc/ot_hdc_prefix.sv#" $W/named/synth.ys
grep -q ot_hdc_prefix.sv $W/named/synth.ys || { echo "prefix read patch failed"; exit 2; }
/srv/opentallas-scratch/admit.sh 12 -- $HOME/.local/opentallas-tools/yosys-0.68/bin/yosys -q -s $W/named/synth.ys > $W/named/yosys.log 2>&1
[ -f $W/named/mapped.v ] || { echo "synth failed"; exit 3; }
python3 - $W/named/mapped.v <<'PY'
import re, sys
p = sys.argv[1]; t = open(p).read(); bb = ["ot_qwen_me_spine_w12", "ot_hdc_vstream_rt", "ot_hdc_stream"]
out, i = [], 0
pat = re.compile(r"\b(" + "|".join(bb) + r")\s*#\(")
while True:
    m = pat.search(t, i)
    if not m:
        out.append(t[i:]); break
    out.append(t[i:m.start()] + m.group(1) + " "); d, j = 1, m.end()
    while d:
        d += {"(": 1, ")": -1}.get(t[j], 0); j += 1
    i = j
open(p, "w").write("".join(out))
PY
python3 - $OLD/runs/core_vpos1s_0833/rep2.tcl $W/rep2.tcl <<'PY'
import sys
t = open(sys.argv[1]).read().splitlines()
focus = (r"set ::ot_focus [list fsm {(^|\.)(st|state|pc|fpc)(\[|\$)} "
         r"issue {(^|\.)(fq_n|fq_rd|fq_wr|pend1|nx_v|d_wait_me|d_wait_su|waited|progress|d_chase_n)(\[|\$)} "
         r"decode {(^|\.)(me_nout|me_tiles|me_k|me_wbase|me_xbase|me_obase|su_nin|a_base|b_base|c_base|d_base)\[} "
         r"fqd {(^|\.)fqd_} tables {(^|\.)(la_|dyn\[|dynp\[)}]")
t = [focus if l.startswith("set ::ot_focus") else l for l in t]
open(sys.argv[2], "w").write("\n".join(t) + "\n")
PY
docker run --rm -v $W/named:/w:ro -v $W:/o openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /o/rep2.tcl" > $W/rep2.log 2>&1
grep -E "^OT_REP_" $W/rep2.log | grep -v -E "BEGIN|END" > $W/summary.txt
