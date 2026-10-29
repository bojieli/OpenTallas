#!/usr/bin/env python3
"""Fleet wrapper for one disjoint partition group; persistent stdout/exit record."""
import json,pathlib,subprocess,sys
p=pathlib.Path.cwd();group=sys.argv[1];groups=json.loads((p/'street_groups.json').read_text());parts=groups[group];logs=p/'street_logs';logs.mkdir(exist_ok=True)
cmd=[sys.executable,'-u','allocate.py','geometry_street50','street_alloc_'+group,'--parts',','.join(parts),'--keep-going','--tools','tools/die_plan']
with (logs/(group+'.log')).open('x') as stream:
    result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
(logs/(group+'.exit.json')).write_text(json.dumps({'group':group,'parts':parts,'exit':result.returncode,'command':cmd},indent=1)+'\n')
raise SystemExit(result.returncode)
