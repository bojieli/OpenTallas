import re,sys
s=open('/out/original_iop.def').read()
for sec in ('COMPONENTS','NETS'):
 s=re.sub(r'^'+sec+r' \d+ ;.*?^END '+sec+r'\n','',s,flags=re.M|re.S)
s=re.sub(r'\(\s+[^()\s]+\s+(?:VDD|VSS)\s+\)','',s)
open('/out/floorplan_only.def','w').write(s)
