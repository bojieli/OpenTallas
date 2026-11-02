from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text();allowed={'2_1_floorplan','2_2_floorplan_macro','2_3_floorplan_tapcell','2_4_floorplan_pdn','2_floorplan','2_floorplan.sdc'}
stages=re.findall(r'flow\.sh\s+(\S+)',s);targets=re.findall(r'\bdo-([A-Za-z0-9_.-]+)',s)
assert (stages or targets) and set(stages+targets)<=allowed,(stages,targets)
if not stages:assert set(targets)==allowed,targets
assert not re.search(r'(?m)^\s*(?:\S*/)?yosys(?:\s|$)',s)
print('DRY_TARGET_FP_ONLY_PASS',sorted(set(stages+targets)))
