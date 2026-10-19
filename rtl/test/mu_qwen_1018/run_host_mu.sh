#!/bin/bash
# MU-QWEN-HOST 10-19: host-plane benches on Verilator 5.050 (the closure daemon's version).
#   usage: run_host_mu.sh ROOT OUT CASE
#   ROOT: a tree holding rtl/ (the worktree, or a copy with the pre-MU files for the MU 0 identity runs)
#   CASE: a bench name from lists/ (tb_*), or a mutant id below (applied to a copy of one RTL file; must FAIL)
# Prints the bench's last PASS/FAIL line; exit 0 on PASS.  Every file a bench reads is in lists/<tb>.f.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
P=rtl/qwen_sys/host_integrated_20261014/ot_host_if_pb2_observed.sv
K=rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv
C=rtl/physical/ot_qwen_host_ctl.sv
I=rtl/qwen_sys/host_integrated_20261014/qkd_host_if_pins_observed.sv
R=rtl/qwen_sys/mu_qwen_20261018/qkd_kv_mu_rowoff.sv
TB=$CASE; MF=""; FROM=""; TO=""
case "$CASE" in
 # pkgctl MU: retire when ANY die reported (not all 8)
 cm1) TB=tb_qkd_host_ctl_mu; MF=$K; FROM='(fault_any || &m_seen[m_old])'; TO='(fault_any || |m_seen[m_old])';;
 # pkgctl MU: no in-order generation check per die
 cm2) TB=tb_qkd_host_ctl_mu; MF=$K; FROM='if (!m_v[gk] || gk != m_last[d*2 +: 2] + 2'"'"'d1) f_die'; TO='if (!m_v[gk]) f_die';;
 # qkd_host_ctl MU: the user is not put on hc pos[17:16]
 cm3) TB=tb_qkd_host_ctl_mu; MF=$C; FROM='{kv_base[11:10],pos[15:0]}'; TO='{2'"'"'b00,pos[15:0]}';;
 # pkgctl MU: eng_done is not a one-edge pulse (held)
 cm4) TB=tb_qkd_host_ctl_mu; MF=$K; FROM='d_start <= 1'"'"'b0; eng_done <= 1'"'"'b0; m_now'; TO='d_start <= 1'"'"'b0; m_now';;
 # host MU_OUT: a retired step is attributed to the last issued slot, not the in-flight FIFO head
 hm1) TB=tb_qkd_host_mu_out; MF=$P; FROM='wire [SB-1:0] d_slot = (MU_OUT != 0) ? mq_head : eng_slot;'; TO='wire [SB-1:0] d_slot = (MU_OUT != 0) ? eng_slot : eng_slot;';;
 # host MU_OUT: a slot with a step outstanding may be picked again
 hm2) TB=tb_qkd_host_mu_out; MF=$P; FROM='if (sl_st[cand] == SL_RUN && !(MU_OUT != 0 && sl_inf[cand]))'; TO='if (sl_st[cand] == SL_RUN)';;
 # host: no per-user KV base (every user on kv_base 0)
 hm3) TB=tb_qkd_host_mu_out; MF=$P; FROM='kv_base <= (ENG_CTX == 1) ? {AW{1'"'"'b0}} : pick * KVW;'; TO='kv_base <= {AW{1'"'"'b0}};';;
 # host pins MU_OUT: completion guard kept (drops a done that follows a start)
 hm4) TB=tb_qkd_host_mu_out; MF=$I; FROM='(MU_OUT!=0) ? pin_eng_done :'; TO='(MU_OUT!=0) ? completion_armed \&\& pin_eng_done :';;
 # KV write leaf: user not inserted into row[9:8] (users alias)
 rm1) TB=tb_qkd_kv_mu_rowoff; MF=$R; FROM='es_i[q*288+265 +: 2] | u;'; TO='es_i[q*288+265 +: 2];';;
 # KV read leaf: offsets embedding rows too
 rm2) TB=tb_qkd_kv_mu_rowoff; MF=$R; FROM='&& row[18:8] == 0;'; TO=';';;
esac
[ -f "$L/$TB.f" ] || { echo "HOST_MU $CASE: no list $TB"; exit 2; }
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then
  python3 - "$W/$MF" "$FROM" "$TO" <<'EOF' || { echo "HOST_MU $CASE: mutation did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3].replace("\\&", "&")
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
EOF
fi
cd "$W"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 8 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "HOST_MU $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | tail -1)
echo "HOST_MU $CASE rc=$rc $(basename "$ROOT"): $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
