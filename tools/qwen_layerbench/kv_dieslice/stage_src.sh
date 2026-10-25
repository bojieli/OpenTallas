#!/bin/bash
# TOKj-KV 10-23: assemble a self-contained source tree for the KV die-slice vehicle on a BOUND KV top.
#   stage_src.sh BIND_DIR OUT [INCDIRS]
#   BIND_DIR = binder out dir (bind.f with absolute paths + rtl/); INCDIRS = ordered leaf dirs (default: the union of
#   BINDER3's per-partition lint -I lists, hub_C/hub_Wi/sys_c first = incdirs_order.txt).
# Leaves resolve exactly as in the binder's per-partition lints (same dir order), EXCEPT: the lint leaf stubs are never used
# (full RTL) and the PHY model dirs (bind/models, ucie bb) are left out: the bench compiles its own PHY models instead
# (owner 10-14: only PHY/off-chip modelled).  Every staged dir is a flat copy (files at that level only, as -y resolves).
set -eu
H=$(cd "$(dirname "$0")" && pwd)
B=$(readlink -f $1); O=$(mkdir -p $2 && readlink -f $2); INCF=${3:-}
if [ -z "$INCF" ]; then INCF=$O/incdirs_order.txt; python3 $H/lint_incdirs.py $B > $INCF; fi
rm -rf $O/src; mkdir -p $O/src
tag() { echo "$1" | sed -e "s#^$B#bind#" -e "s#^/home/ubuntu/##" -e 's#/#__#g'; }
: > $O/incdirs.f
stage_dir() { local d=$1 t; t=$O/src/$(tag $d); [ -d $t ] && return 0; mkdir -p $t; find $d -maxdepth 1 -type f \( -name '*.sv' -o -name '*.v' -o -name '*.svh' -o -name '*.vh' \) -exec cp -a {} $t/ \; ; }
# the bound rtl dir first (as the lints), then the ordered leaf dirs
stage_dir $B/rtl; echo "-y $O/src/$(tag $B/rtl)" >> $O/incdirs.f
while read -r d; do [ -z "$d" ] && continue; [ "$d" = $B/rtl ] && continue
  stage_dir $d; echo "-y $O/src/$(tag $d)" >> $O/incdirs.f; done < $INCF
# bind.f files (the bound top's file list, PHY black box removed)
: > $O/files.f
while read -r f; do [ -z "$f" ] && continue; case "$f" in *ot_qkvd_ucie_x64_phy_bb.v) continue;; esac
  d=$(dirname $f); stage_dir $d; echo "$O/src/$(tag $d)/$(basename $f)" >> $O/files.f; done < $B/bind.f
: > $O/hostside.f
# host board-side end of the SerDes link (real host link adapter + CDC RTL = the off-die host model's transport)
A=/home/ubuntu/scratch/binder2-1023/kv_src_e33504a6f
# the bind source root (leaf search roots for resolve_missing.py): the tree most bind.f entries come from
sed -n "s#/rtl/.*##p" $B/bind.f | sort | uniq -c | sort -rn | awk '{print $2}' > $O/src_roots.txt
for f in $A/rtl/test/qwen_host/qkd_host_board_port_fixture.sv $A/rtl/physical/ot_qfd_link_adp512_split.sv; do
  d=$(dirname $f); mkdir -p $O/src/$(tag $d); cp -a $f $O/src/$(tag $d)/; echo "$O/src/$(tag $d)/$(basename $f)" >> $O/hostside.f; done
for f in bind_latency.json param_regen.json bus_groups.json bus_groups.json.gz; do [ -f $B/$f ] && cp -a $B/$f $O/ || true; done
# The generated copy assertion is meaningful only after delivered reset.
python3 "$H/reset_selfcheck_guard.py" "$O/src"
sha256sum $B/rtl/qwen_kvsys_bound_top.sv | cut -c1-64 > $O/bound_top.sha256
echo "files $(grep -c . $O/files.f) incdirs $(grep -c . $O/incdirs.f) top_sha $(cut -c1-12 $O/bound_top.sha256) $(du -sh $O/src | cut -f1)"
