"""QC rp1-clock: copy the vclk source latency of the kit SDC (= the core's measured I, ruling 9.7) into a stage SDC."""
import re, sys
stage, kit = sys.argv[1], sys.argv[2]
m = re.search(r"set_clock_latency\s+-source\s+([0-9.]+)\s+\[get_clocks\s+\{?vclk\}?\]", open(kit).read())
if not m:
    sys.exit("set_vclk: no vclk source latency in kit SDC")
lat = m.group(1)
s = open(stage).read()
pat = re.compile(r"(set_clock_latency\s+-source\s+)([0-9.]+)(\s+\[get_clocks\s+\{?vclk\}?\])")
s2, n = pat.subn(lambda x: x.group(1) + lat + x.group(3), s)
if n != 1:
    sys.exit(f"set_vclk: {n} vclk latency lines in {stage}")
open(stage, "w").write(s2)
print(f"set_vclk: {stage} vclk source latency := {lat}")
