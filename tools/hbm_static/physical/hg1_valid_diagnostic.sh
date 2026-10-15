#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/hbm-att-hg1-167a/full_gate
out=/srv/opentallas-scratch/codex/ATT-HG1-valid-diagnostic
mkdir -p "$out"
cp -al "$base/obj" "$out/obj"
python3 - "$out/obj" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);f=p/'Vtb_hbm_attn_physical_calendar___024root__193.cpp'
s=f.read_text();needle='        if (vlSelfRef.tb_hbm_attn_physical_calendar__DOT__pv_v) {'
assert s.count(needle)==1
pre='vlSelfRef.tb_hbm_attn_physical_calendar__DOT__'
trace='''        if (PREmode == 1 && ((PREev & 64) || ((PREdut__DOT__u_tag__DOT__g_reg__DOT__r[64] >> 13) & 1) || PREpv_v)) {
            fprintf(stderr, "DIAG cyc=%u ev=%u iss_c=%u iss_blk=%u e_iv=%u e_pv=%u e_fin=%u e_c=%u tag_c=%u tag_fin=%u tag_pv=%u pv_v=%u pv_c=%u\\n", unsigned(PREcyc),unsigned(PREev),unsigned(PREdut__DOT__iss_c),unsigned(PREdut__DOT__iss_blk),unsigned(PREdut__DOT__e_iv),unsigned(PREdut__DOT__e_pv),unsigned(PREdut__DOT__e_fin),unsigned(PREdut__DOT__e_c),unsigned(PREdut__DOT__u_tag__DOT__g_reg__DOT__r[64] & 255),unsigned((PREdut__DOT__u_tag__DOT__g_reg__DOT__r[64] >> 13) & 1),unsigned((PREdut__DOT__u_tag__DOT__g_reg__DOT__r[64] >> 14) & 1),unsigned(PREpv_v),unsigned(PREpv_c));
        }
'''.replace('PRE',pre)
f.unlink();f.write_text(s.replace(needle,trace+needle))
for n in ('Vtb_hbm_attn_physical_calendar___024root__193.o','Vtb_hbm_attn_physical_calendar__ALL.a','sim'):
 (p/n).unlink(missing_ok=True)
PY
make -C "$out/obj" -f Vtb_hbm_attn_physical_calendar.mk -j4 sim > "$out/build.log" 2>&1
set +e
"$out/obj/sim" +DIR="$base/vectors" +MUT=0 > "$out/run.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/run.rc"
grep -q 'ATT_CALENDAR output accounting' "$out/run.log"
echo 'DIAGNOSTIC ONLY: original numerical failure reproduced with harness logging; no RTL/proof qualification' > "$out/STATUS"
