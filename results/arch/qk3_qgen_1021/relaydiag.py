import sys
p2, p3 = sys.argv[1:]
s = open(p2).read()
old = "\nexit $rc\n"
assert s.endswith(old), repr(s[-40:])
s = s[:-len(old)] + """
# QK3-QGEN 10-21: a DIAGNOSTIC chain (strict bind output-open only) whose relay check FAILS keeps the FAIL on record and
# continues to the physical chain for GRT / STA / CLK numbers only (compiled schedule present; never a qualification)
if [ $rc -ne 0 ] && [ -e $S/DIAGNOSTIC_BIND_OPEN ] && ls $P/compiled_L1/relay_schedule/compute_compiled.json* > /dev/null 2>&1 && [ -s $P/compiled_L1/manifest.json ]; then
  echo "RELAY_CHECK FAIL rc=$rc kept (relay_check.json); DIAGNOSTIC physical chain continues, no qualification" > $S/DIAGNOSTIC_RELAY_CHECK_FAIL
  echo "$(date '+%F %T %Z') QK3 relay check FAIL -> DIAGNOSTIC_RELAY_CHECK_FAIL, physical chain continues (diagnostic)" >> $S/PILOT.log; exit 0
fi
exit $rc
"""
open(p2, 'w').write(s)
t = open(p3).read()
old3 = """grep -q '"pass": true\\|PASS' $P/relay_check.json || { echo "relay check not PASS"; exit 9; }"""
assert t.count(old3) == 1, 'p3'
t = t.replace(old3, """[ -e $S/DIAGNOSTIC_RELAY_CHECK_FAIL ] || grep -q '"pass": true\\|PASS' $P/relay_check.json || { echo "relay check not PASS"; exit 9; }""")
open(p3, 'w').write(t)
