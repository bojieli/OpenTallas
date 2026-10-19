import json
from pathlib import Path
m=json.loads(Path('ctlm_metadata_source.json').read_text())
for name in ('original','compact_duplicate','clone24'):
    words=[]
    for r in m['xpf_records']:
        pc=r['producer_pc'];unit=r['producer_unit']
        if name!='original':
            pc={1:3,12:11,16:3,20:10}[r['consumer_pc']];unit=2
            if name=='clone24' and r['consumer_pc']==16:pc=24
        word=int(r['xpf72'],16)|(pc<<72)|(unit<<84)|(m['stage_label']<<86)|(r['arm_cycle']<<92)|(r['issue_cycle']<<124)|(r['first_write_cycle']<<156)
        words.append(word)
    Path(f'xpf_{name}.hex').write_text(''.join(f'{x:047x}\n' for x in words))
