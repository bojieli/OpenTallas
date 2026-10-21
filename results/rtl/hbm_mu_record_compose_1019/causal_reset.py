from pathlib import Path
s=Path('causal_requests.py').read_text().split('args=')[0].replace("'event_controls'","'event_controls_reset'")
exec(s)
args=[f'+CFG={R}/production/cols/config.mem',f'+GOLD={R}/production/quarter.mem','+N=73','+W=70','+REQMUT=6','+CONTROL=6']
with (O/'reset_pulse_without_reinstall.log').open('w')as f:r=subprocess.run([str(O/'event_controls_reset'),*args],stdout=f,stderr=subprocess.STDOUT)
text=(O/'reset_pulse_without_reinstall.log').read_text();assert r.returncode!=0 and 'RESET_NEW_EPOCH' in text and '%Fatal' in text
print('RESET_PULSE_WITHOUT_REINSTALL',r.returncode,next(x for x in text.splitlines()if '%Fatal' in x))
(O/'reset_pulse_summary.json').write_text(json.dumps(dict(returncode=r.returncode,expected_fail=True,matched=True,por_low_ps=1668,source='top-level POR stimulus; no internal-state force',first_fatal=next(x for x in text.splitlines()if '%Fatal' in x)),indent=2))
