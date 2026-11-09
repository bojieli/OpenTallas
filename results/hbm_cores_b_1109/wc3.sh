set -e
W=/srv/opentallas-scratch2/claude/kw36/wt_w
cd $W/tools/autopilot
python3 -I - <<'PY'
p="test_kit_wave_source.py"
s=open(p).read()
old='''            a=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp1=json.loads((Path(a["dir"])/"spec.json").read_text())
            b=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp2=json.loads((Path(b["dir"])/"spec.json").read_text())
'''
new='''            a=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp1=json.loads((Path(a["dir"])/"spec.json").read_text())
            # a live producer is never replaced (LAUNCH-KEEP); attempt 2 follows a finished attempt
            self.assertIsNone(KW.launch(ap,c,st,"qwen_kvsys",r,"intel2"))
            self.assertEqual(len(st["items"]),1)
            for rec in st["items"].values():rec["status"]="FAIL"
            b=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp2=json.loads((Path(b["dir"])/"spec.json").read_text())
'''
assert s.count(old)==1
open(p,"w").write(s.replace(old,new))
PY
timeout 300 python3 -m unittest test_kit_wave_source test_wave_claims 2>&1 | tail -6 | cut -c1-200
git add test_kit_wave_source.py
git commit -q -m "wave-claims: second-attempt test follows a finished attempt, and covers LAUNCH-KEEP

ROOT-MERGE-53 held 5382e2a0ad0: LAUNCH-KEEP returns None on a second launch
of a RUNNING row, and this test launched twice with the first still active.
A real attempt 2 follows a finished attempt; the test now says so and also
asserts that a live producer is kept.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin claude/kw-fix-36-wave-claims-1108 2>&1 | tail -1
git log -2 --format='%h %s' | cut -c1-100; git rev-parse HEAD
