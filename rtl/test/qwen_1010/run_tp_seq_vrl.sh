#!/bin/bash
# qwen-1010/a: the stationed all-reduce VM read bench (tb_tp_seq_vrl.sv).  usage: run_tp_seq_vrl.sh <work dir>  (from the repo)
# PASS lines expected for the base unstationed and every VRL = round trip; FAIL (as required) for the base stationed and
# every VRL = round trip - 1 mutant.  Exit 0 only when every case matches its expectation.
set -u; W=$1; mkdir -p $W
python3 -c "import sys;sys.path.insert(0,'tools/redesign_qwen');import split_ctrl as S;open('$W/vrl.sv','w').write(S.tp_seq_vrl(cred=True))" || exit 2
rc=0
# VRL OS IS RLY CRDY CST CRED IB expect
while read v o i r c cs cr ib e; do
  iverilog -g2012 -o $W/tb -P tb_tp_seq_vrl.VRL=$v -P tb_tp_seq_vrl.OS=$o -P tb_tp_seq_vrl.IS=$i -P tb_tp_seq_vrl.RLY=$r -P tb_tp_seq_vrl.CRDY=$c -P tb_tp_seq_vrl.CST=$cs -P tb_tp_seq_vrl.CRED=$cr -P tb_tp_seq_vrl.IB=$ib \
    rtl/test/qwen_1010/tb_tp_seq_vrl.sv rtl/rom/ot_qwen_tp_seq_w12.sv $W/vrl.sv rtl/hdc/ot_hdc_delay.sv || exit 2
  out=$(vvp -n $W/tb | grep -E "^(PASS|FAIL)"); echo "expect=$e $out"
  case "$e:$out" in pass:PASS*|fail:FAIL*) ;; *) rc=1;; esac
done <<CASES
0 0 0 0 0 0 0 0 pass
0 1 1 0 0 0 0 0 fail
3 1 1 0 0 0 0 0 pass
2 1 1 0 0 0 0 0 fail
3 1 1 0 1 0 0 0 pass
9 1 1 3 1 0 0 0 pass
8 1 1 3 0 0 0 0 fail
23 1 1 10 0 0 0 0 pass
22 1 1 10 0 0 0 0 fail
3 1 1 0 1 1 4 4 pass
3 1 1 0 1 1 0 0 fail
3 1 1 0 1 1 8 4 fail
9 1 1 3 1 1 12 12 pass
9 1 1 3 1 1 13 12 fail
CASES
exit $rc
