cd /
R=$1; shift
for it in "$@"; do
 n=${it%:*}; a=${it#*:}; A=$R/items/$n/attempt_$a
 echo "== $n a$a"; ls $A | tr '\n' ' ' | cut -c1-200; echo; ls $A/gen/$n | tr '\n' ' ' | cut -c1-300; echo
 find $A -maxdepth 5 \( -name 'kit_rtl*' -o -name 'kit_manifest*' -o -name 'bind_report.json' \) 2>/dev/null | head -5 | cut -c1-200
 timeout 60 grep -rIl --include='*.json' --include='*.f' --include='*.mk' --include='*.tcl' --include='*.sh' --include='*.txt' -E 'bind_kvcls|kv_sys_phy|codex-wave-bind-1106' $A/gen/$n 2>/dev/null | head -8 | cut -c1-220
 timeout 60 grep -rIhoE -m3 --include='*.json' --include='*.f' '/srv/[A-Za-z0-9_./-]*(bind_kvcls|kv_sys_phy|codex-wave-bind-1106)[A-Za-z0-9_./-]*' $A/gen/$n 2>/dev/null | sort -u | head -6 | while read p; do [ -e "$p" ] && echo "EXISTS $p" || echo "MISSING $p"; done | cut -c1-220
done
