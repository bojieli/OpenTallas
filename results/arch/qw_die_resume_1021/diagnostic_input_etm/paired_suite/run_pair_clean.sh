#!/bin/bash
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
cd "$B/src"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$B/pytest_env"
test ! -e tools || { echo "tools must be absent before exact published extraction"; exit 3; }
tar -xzf "$B/baseline_tools.tar.gz"
for tag in baseline final; do
 if [ "$tag" = final ]; then tar -xzf "$B/candidate.tar.gz"; fi
 python3 -m pytest -q tools/qwen_split --junitxml="$B/$tag.xml" > "$B/$tag.log" 2>&1
 printf '%s\n' "$?" > "$B/$tag.rc"
done
python3 - "$B" <<'PY'
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as E,json,sys
b=Path(sys.argv[1]); rows={}; counters={}
for tag in ('baseline','final'):
 t=E.parse(b/(tag+'.xml')); cases=list(t.iter('testcase')); c=Counter((x.get('classname',''),x.get('name',''),y.tag,y.get('type',''),y.get('message',''),y.text or '') for x in cases for y in x if y.tag in ('failure','error'))
 counters[tag]=c;rows[tag]={'cases':len(cases),'failure_elements':sum(c.values()),'rc':int((b/(tag+'.rc')).read_text()),'failure_counter':[{'key':list(k),'count':v}for k,v in sorted(c.items())]}
new=counters['final']-counters['baseline']; resolved=counters['baseline']-counters['final']
rows.update(new_failure_elements=sum(new.values()),resolved_failure_elements=sum(resolved.values()),same_failure_element_multiset=counters['baseline']==counters['final'])
rows['verdict']='NEW0' if rows['baseline']['cases'] and rows['final']['cases'] and not new else 'FAIL'
(b/'paired_result.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:v for k,v in rows.items()if k not in ('baseline','final')}));print('CASE_CENSUS',rows['baseline']['cases'],rows['final']['cases']);sys.exit(0 if rows['verdict']=='NEW0' else 1)
PY
