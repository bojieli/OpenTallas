set -e
W=/srv/opentallas-scratch2/claude/kw36/wt_g/tools/autopilot
cd $W
python3 -I - <<'PY'
p="kit_wave.py"
s=open(p).read()
old='''        f, floor = (free.get(h) or {}).get(die), (hard.get(h) or {}).get(die, GEN_SCRATCH_HARD_FLOOR_GB)
'''
new='''        f, floor = (free.get(h) or {}).get(die), (hard.get(h) or {}).get(die, GEN_SCRATCH_HARD_FLOOR_GB)
        f = ((cfg.get("_workroot_low") or {}).get(h) or {}).get(die) if f is None else f
'''
assert s.count(old)==1
open(p,"w").write(s.replace(old,new))
PY
cat kit_wave.py | ssh -o ControlPath=none epyc2 'rm -f /srv/opentallas-scratch3/claude/kw36/gtip/tools/autopilot/kit_wave.py; cat > /srv/opentallas-scratch3/claude/kw36/gtip/tools/autopilot/kit_wave.py'
