import json
from pathlib import Path
from core_infra_search import design_entry
p=Path('vmr');data=json.load(open(p/'input.json'));base=json.load(open(p/'candidate.json'));previous=json.load(open(p/'report.json'));candidate,report=design_entry(base,data['libraries'],data['points'],data['caps'],0,0,slew_limit=78.,input_slew_ps=0,routing_model=previous['routing_model']);report['qualification']=previous['qualification'];(p/'entry_report.json').write_text(json.dumps(report,indent=1));(p/'entry_candidate.json').write_text(json.dumps(candidate,indent=1));print(report['chosen'])
