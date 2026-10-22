import sys,json,subprocess,os
from pathlib import Path
sys.path[:0]=['tools','tools/hbm_layer_vehicle']
from hbm_layer_vehicle import layer_images as LI
from native_su_calendar import compile_calendar
root=Path('.')
words=[int(x,16)for x in Path('record23_profile/native18/quarter.mem').read_text().split()]
calwords=[(x&~(((1<<180)-1)<<(440+60)))&~(((1<<234)-1)<<(128+78)) for x in words]
c,m=compile_calendar(calwords,first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160,request_lane_edges_by_bank=[4,5,0,0,0,0,0,0],write_lane_edges_by_bank=[3,3,0,0,0,0,0,0])
Path('calendar.mem').write_text(''.join(f'{x:064x}\n'for x in c));Path('calendar_model.json').write_text(json.dumps(m,indent=2))
old=[int(x,16)for x in Path('record23_profile/legacy/quarter.mem').read_text().split()]
mut=[(x&((1<<680)-1))|((old[i]>>680)<<680 if i<len(old)else 0)for i,x in enumerate(words)]
LI.column_image(mut,Path('record23_profile/old_fill_mutant'))
