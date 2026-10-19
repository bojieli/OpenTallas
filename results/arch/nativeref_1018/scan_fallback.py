import glob, re, json, os, sys
out = []
for d in sorted(glob.glob('/srv/*/claude/closure-loop/*/')):
    job = os.path.basename(d.rstrip('/'))
    for lg in glob.glob(d + 'routes/*/work/orfs/logs/asap7/*/base/5_1_grt.log'):
        try:
            t = open(lg, errors='replace').read()
        except OSError:
            continue
        refs = re.findall(r'QDM reference pin (\S+) clock arrival max (\S+)', t)
        if not refs:
            continue
        pf = re.findall(r'QDM PINFLOP reference: (\d+)', t)
        gl = re.findall(r'QDM REFGLOB (\S+) reference: (\d+)', t)
        ioref_nopf = 'OT_IOREF_PF no input pin flops' in t
        hb = [int(x) for x in re.findall(r'Inserted (\d+) hold buffers', t)]
        try:
            c = open(lg.replace('5_1_grt.log', '4_1_cts.log'), errors='replace').read()
        except OSError:
            c = ''
        cpf = re.findall(r'QDM PINFLOP reference: (\d+)', c)
        chb = [int(x) for x in re.findall(r'Inserted (\d+) hold buffers', c)]
        ref = refs[-1][0]
        fallback = not pf and not gl
        macro = not ref.endswith('/CLK')
        if fallback or macro or ioref_nopf:
            out.append(dict(job=job, ref=ref, arr=refs[-1][1], grt_pinflops=pf[-1] if pf else 0, refglob=gl[-1][0] if gl else None,
                            cts_pinflops=cpf[-1] if cpf else 0, grt_hold_bufs=sum(hb), cts_hold_bufs=sum(chb),
                            ioref_no_pf=ioref_nopf, lost_at_grt=bool(cpf) and not pf and not gl, macro_ref=macro,
                            mtime=int(os.path.getmtime(lg))))
json.dump(out, sys.stdout)
