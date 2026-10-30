"""Apply complete actual QC PG access; preserve every non-PG clock/signal object."""
import argparse,sys,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--helper',required=True);p.add_argument('--source',required=True);p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--cells',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path[:0]=[a.tools,a.helper]
import odb
from mixed_apply_access import apply_access
d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();m=json.load(open(a.cells));result=apply_access(b,a.plan,a.grid,198762,m);o=Path(a.out);o.mkdir(parents=True,exist_ok=True);odb.write_db(d,str(o/'provider.odb'));result.update(source=a.source,plan=a.plan,scope='Actual complete clock/provider PG access import. Physical DRC/IR/STA and die GRT pending.');json.dump(result,open(o/'receipt.json','w'),indent=2);print(json.dumps(result),flush=True)
