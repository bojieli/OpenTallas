#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/hbm-att-hg1-167a/full_gate
out=/srv/opentallas-scratch/codex/ATT-HG1-merge-diagnostic
mkdir -p "$out"
cp -al "$base/obj" "$out/obj"
python3 - "$out/obj" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);f=p/'Vtb_hbm_attn_physical_calendar___024root__193.cpp'
s=f.read_text();needle='        if (vlSelfRef.tb_hbm_attn_physical_calendar__DOT__pv_v) {'
assert s.count(needle)==1
pre='vlSelfRef.tb_hbm_attn_physical_calendar__DOT__'
trace='        if (PREmode == 1 && PREcyc >= PREt0 && PREcyc < PREt0 + 240) {\n            fprintf(stderr, "MERGEDIAG cyc=%u ev=%u e_c=%u efin=%u tag=%llu pv=%u pc=%u" " v0=%u t0=%u" " v1=%u t1=%u" " v2=%u t2=%u" " v3=%u t3=%u" " v4=%u t4=%u" "\\n", unsigned(PREcyc),unsigned(PREev),unsigned(PREdut__DOT__e_c),unsigned(PREdut__DOT__e_fin),static_cast<unsigned long long>(PREdut__DOT__u_tag__DOT__g_reg__DOT__r[64]),unsigned(PREpv_v),unsigned(PREpv_c),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__0__KET____DOT__u_dv__DOT__r),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__0__KET____DOT__u_dt__DOT__g_reg__DOT__r[5]),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__1__KET____DOT__u_dv__DOT__r),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__1__KET____DOT__u_dt__DOT__g_reg__DOT__r[5]),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__2__KET____DOT__u_dv__DOT__r),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__2__KET____DOT__u_dt__DOT__g_reg__DOT__r[5]),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__3__KET____DOT__u_dv__DOT__r),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__3__KET____DOT__u_dt__DOT__g_reg__DOT__r[5]),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__4__KET____DOT__u_dv__DOT__r),unsigned(PREdut__DOT__g_m__BRA__0__KET____DOT__g_real__DOT__g_s__DOT__u_m__DOT__g__BRA__4__KET____DOT__u_dt__DOT__g_reg__DOT__r[5]));\n        }\n'.replace('PRE',pre)
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
