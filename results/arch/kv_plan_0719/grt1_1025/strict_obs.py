"""PATH-KV-GRT1 what-if: abstract LEF planned-core OBS M4/M5 -> also M6/M7 (strict model: head cores harden with
sigmax M7, as g2.probe_blockages).  Only hg/hgi types (the head-eighth cores).  usage: strict_obs.py LEF..."""
import re, sys
for f in sys.argv[1:]:
    s = open(f).read()
    m = re.search(r"    LAYER M5 ;\n((?:      RECT [^\n]*\n)+)", s[s.index("\n  OBS"):])
    if not m:
        print("no M5 OBS", f); continue
    rects = m.group(1)
    i = s.index("\n  OBS") + m.end()
    s = s[:i] + "    LAYER M6 ;\n" + rects + "    LAYER M7 ;\n" + rects + s[i:]
    open(f, "w").write(s)
    print(f, rects.count("RECT"), "core rects -> M6/M7")
