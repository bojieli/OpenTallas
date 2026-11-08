import sys,shutil
d=sys.argv[1]
shutil.copy(d+'/../../../lc_new.py', d+'/landing_collector.py')
p=d+'/clock_landings.py'; s=open(p).read()
old='''    generated_grid = (not taps and ("tap_um" in ck or "tap_mode" in ck)) or ck.get("tap_mode") in ("grid", "grid+explicit")'''
new='''    generated_grid = (not taps and ("tap_um" in ck or "tap_mode" in ck)) or \\
        ck.get("tap_mode") in ("grid", "grid+explicit", "density")'''
if old in s: s=s.replace(old,new); print('ring_taps: patched (d95ec has the ringtap form)')
else:
    old2='''    generated_grid = not taps and ("tap_um" in ck or "tap_mode" in ck)'''
    assert old2 in s, 'ring_taps form unknown'
    s=s.replace(old2,'''    generated_grid = (not taps and ("tap_um" in ck or "tap_mode" in ck)) or ck.get("tap_mode") == "density"''')
    print('ring_taps: patched (pre-ringtap form: density only)')
open(p,'w').write(s)
