"""Widen the vJ SRAM-to-program-macro corridor without changing RTL or pins."""
from pathlib import Path
import re,json,hashlib,sys
p=Path(sys.argv[1]);f=p/'macro_place.tcl';old=f.read_text();changed=[]
def move(m):
 name,x,y=m.group(1),float(m.group(2)),float(m.group(3))
 if not name.startswith('u_program.g_pm'):return m.group(0)
 changed.append({'macro':name,'old_y_um':y,'new_y_um':round(y+11.52,3)})
 return f'place_macro -macro_name {{{name}}} -location {{{x:.3f} {y+11.52:.3f}}}'
new=re.sub(r'place_macro -macro_name \{([^}]+)\} -location \{([\d.]+) ([\d.]+)\}',move,old)
assert len(changed)==4
new+='\n# CODEX J2 CHANNEL: program SRAM rows +11.52um (240 M4 tracks); big SRAM gap 5.496 ->17.016um, 8.376um after 4.32um halos.\n'
f.write_text(new)
with (p/'config.mk').open('a') as o:o.write('\n# REDESIGN vJ2: widen SRAM/program macro corridor by11.52um; same RTL/pins, inherited read PIN CYCLES +1, reset release +3. Placement pilot first.\n')
r={'schema':'opentallas.prompt_channel_redesign.v1','variant':'vJ2','class':'CHANNEL','changed':changed,'old_macro_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_macro_sha256':hashlib.sha256(new.encode()).hexdigest(),'RTL':'unchanged from vJ','added_pin_cycles_vs_vJ':0,'inherited_read_pin_cycles':1,'inherited_reset_release_cycles':3}
(p/'CHANNEL_REDESIGN.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
