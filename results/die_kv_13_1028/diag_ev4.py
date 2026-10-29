import json,sys
src=open("/srv/opentallas-scratch2/claude/wt/die-kv-6/results/die_kv_13_1028/kv13_event.py").read().split("\n")
head="\n".join(src[:24])
head=head.replace("return _bind(plan, *a, **k)","json.dump(plan, open(str(O/\"plan_doc_fail.json\"),\"w\")); return _bind(plan, *a, **k)")
exec(compile(head+"\nrc = CB.main(argv)\n","kv13_event_head","exec"))
