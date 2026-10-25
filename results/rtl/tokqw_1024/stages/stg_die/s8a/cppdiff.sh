#!/bin/bash
# compare generated Verilator C++ (fix tree vs wf3 what-if tree), comments + '#line' + path strings normalised
A=/srv/opentallas-scratch2/claude/tok-qw/s8a/v12/obj_n12; X=/srv/opentallas-scratch2/claude/tok-qw/s8exp_wf3/die/build/obj_n12
norm(){ sed -E -e 's#//.*$##' -e 's#s8exp_wf3/tree|s8a/tree#TREE#g' -e 's#s8exp_wf3/die/build/obj_n12|s8a/v12/obj_n12#OBJ#g' -e 's/[[:space:]]+$//' "$1" | grep -v '^$'; }
cd $A; fa=$(ls *.cpp *.h *.mk 2>/dev/null | sort); fx=$(cd $X && ls *.cpp *.h *.mk 2>/dev/null | sort)
[ "$fa" = "$fx" ] && echo "FILESET same ($(echo "$fa" | wc -l) files)" || { echo "FILESET differs"; diff <(echo "$fa") <(echo "$fx") | head; }
nd=0; for f in $fa; do if ! cmp -s $f $X/$f; then if ! diff -q <(norm $f) <(norm $X/$f) >/dev/null; then nd=$((nd+1)); echo "DIFF $f"; diff <(norm $f) <(norm $X/$f) | head -6; fi; fi; done
echo "SEMANTIC_DIFF_FILES $nd"; grep -c . /dev/null >/dev/null
