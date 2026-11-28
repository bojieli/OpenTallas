import sys
p, permit, holds, allowed = sys.argv[1:5]
s = open(p).read()
s = s.replace('"$P/permit/candidate.json"', '"$P/%s/candidate.json"' % permit)
g = ('python3 -I -B "$C/autopilot/head-form-r3/w13_launch_guard.py" "$P/%s/candidate.json" "$P/%s" %s '
     '|| { echo "launch guard refused" >&2; exit 66; }\n') % (permit, holds, allowed)
anchor = 'exec python3 -I -B "$R/tools/autopilot/publish_apply.py"'
assert anchor in s
s = s.replace(anchor, g + anchor)
a2 = 'assert len(cfg["only_items"])=='
assert a2 in s
s = s.replace(a2, 'assert "CREDITED-UNVERSIONED" in cfg["take_states"]\n' + a2)
open(p, "w").write(s)
