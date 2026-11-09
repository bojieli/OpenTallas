cd /
B=$HOME/coord/autopilot/kit_wave
for t in t15_beb7c04bf1ff6/a2 t59_b3c4b67545ab1/a2 t40__clf8bbdae1_b417a5bd46b10/a10; do
 a=$B/s81_ot_s81sl_leaf__$t
 python3 -I -c "
import json
s=json.load(open('$a/spec.json'));print('work',s['work'],'root',s['root'],'pinslot',s['cland_pinslot'],'gen_env',str(s.get('gen_env'))[:900])
r=json.load(open('$a/result.json'));print({k:(str(v)[:200]) for k,v in r.items()})
p=json.load(open('$a/place_service.json'));print({k:(str(v)[:200]) for k,v in p.items()})
"
 grep -n "OT_CLAND" $a/place.log | grep -vE "ring_place=ff|chunked" | head -20 | cut -c1-420
 grep -c "OT_CLAND" $a/place.log
done
