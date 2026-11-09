#!/bin/bash
# private cp -al overlay of the wave src on the SAME filesystem as its realpath (scratch3 on epyc4/epyc2)
set -e; D=/srv/opentallas-scratch2/claude/qct10/ctlm; KS=$(readlink -f /srv/opentallas-scratch2/claude/kw35/src_c303p)
FS=$(df --output=target $KS | tail -1); D3=$FS/claude/qct10/ctlm; mkdir -p $D3
S=$D3/src_ctlmfq
[ -e $S/AGENTS.md ] || cp -al $KS/. $S/
for f in $(tar -tf $D/changed.tar); do
  r=$(readlink -f $S/$(dirname $f)); case "$r" in $S/*) ;; *) echo "ABORT: $f parent resolves outside ($r)"; exit 9;; esac
  [ ! -L $S/$f ] || { echo "ABORT symlink file $f"; exit 9; }
done
before=$(cd $KS && sha256sum $(tar -tf $D/changed.tar) | md5sum)
cd $S; for f in $(tar -tf $D/changed.tar); do chmod u+w $(dirname $f); rm -f $f; done; tar -xf $D/changed.tar
after=$(cd $KS && sha256sum $(tar -tf $D/changed.tar) | md5sum)
[ "$before" = "$after" ] || { echo "ABORT: original changed"; exit 9; }
[ -e $D/src_ctlmfq ] || ln -s $S $D/src_ctlmfq
echo "OK $S mine=$(sha256sum $S/rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv | cut -c1-12) orig=$(sha256sum $KS/rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv | cut -c1-12)"
