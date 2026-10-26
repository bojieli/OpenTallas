import json
from core_infra_sta import emit_model
report=emit_model(json.load(open('slice.json')),json.load(open('input.json')),'.');print('PLAN_EMIT',len(report['sinks']),len(report['nodes']),flush=True)
