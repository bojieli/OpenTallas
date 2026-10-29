import glob,os,sys,re
D=sys.argv[1]
mods=open(D+"/mods.txt").read().split()
for m in mods:
    kits=[k for k in glob.glob(f"{D}/kits/{m}_*-_k12") if re.fullmatch(re.escape(m)+r"_[0-9a-f]{12}-_k12",os.path.basename(k))]
    cls=""
    for line in (l for f in glob.glob(D+"/mk_batch_*.log") for l in open(f)):
        if line.startswith(m+" | "): cls=re.search(r'"cls": "(\w+)"',line).group(1); break
    if kits:
        for k in kits:
            n=os.path.basename(k); t=f"{D}/preflight/{n}.txt"; s=open(t).read() if os.path.exists(t) else ""
            mm=re.findall(r"KIT_PREFLIGHT[^\n]*",s); pf=(mm[-1] if mm else (s.strip().splitlines() or ["NOPF"])[-1])[:200]
            print(f"{m}\t{cls}\t{n}\t{'FZ' if os.path.exists(k+'/freeze.json') else 'noFZ'}\t{pf}")
    else:
        lg=f"{D}/kits/gen_{m}_k12.log"; msg=""
        if os.path.exists(lg):
            L=[x for x in open(lg).read().splitlines() if x.strip() and not x.startswith("  ") and "Traceback" not in x and "CalledProcessError" not in x and not x.startswith("    ")]
            msg=L[-1][:220] if L else ""
        print(f"{m}\t{cls}\t-\t-\t{msg}")
