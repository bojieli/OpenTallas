import json,os; print(json.dumps({k:v for k,v in os.environ.items() if k.startswith("OT_PIN_REGS")}))
