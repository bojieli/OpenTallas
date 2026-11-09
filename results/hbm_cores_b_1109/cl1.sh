cd /
B=$HOME/coord/autopilot/kit_wave
for t in t15_beb7c04bf1ff6 t59_b3c4b67545ab1 t40__clf8bbdae1_b417a5bd46b10; do
 d=$B/s81_ot_s81sl_leaf__$t
 [ -d "$d" ] || { echo MISSING $d; continue; }
 a=$(ls -d $d/a* | sort -V | tail -1)
 echo "== $a"; ls $a | tr "\n" " "; echo
 python3 -I -c "
import json,sys
s=json.load(open('$a/spec.json'))
print(sorted(s)[:60])
for k in ('host','hosts','work_root','workroot','src','attempt','wave','outdir'):
    if k in s: print(k,s[k])
e=s.get('item_env') or s.get('env') or {}
print({k:(v[:400] if isinstance(v,str) else v) for k,v in e.items()} if isinstance(e,dict) else e)
"
 grep -lE "CLAND" $a/* 2>/dev/null | head
 grep -hE "OT_CLAND|landing band|too small|blocked" $a/*.log 2>/dev/null | tail -14 | cut -c1-500
done
