import odb,re,sys,json
D=odb.dbDatabase.create();odb.read_db(D,sys.argv[1]);b=D.getChip().getBlock()
out={}
for f in ["/work/control_local.tcl","/work/phase_dag_local.tcl"]:
    t=open(f).read()
    out[f]={"nets":[n for n in sorted(set(re.findall(r"findNet \{(_\d+_)\}",t))) if b.findNet(n) is None],
            "insts":[n for n in sorted(set(re.findall(r"\[list \{(_\d+_)\} \{\w+\}\]",t))) if b.findInst(n) is None]}
json.dump(out,open("/work/probe_missing.json","w"),indent=1)
print({f:(len(v["nets"]),len(v["insts"])) for f,v in out.items()})
