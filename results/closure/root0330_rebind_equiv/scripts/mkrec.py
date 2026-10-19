import json,os,shutil,hashlib,re
K='/home/ubuntu/wt/r0330_scratch/kits'; WT='/home/ubuntu/wt/root-0330-eqv'
R=f'{WT}/results/closure/root0330_rebind_equiv'; os.makedirs(R+'/logs',exist_ok=True)
idx=json.load(open(f'{K}/index.json')); summ={}
for t,rec in idx.items():
    L=f'{R}/logs/{t}'; os.makedirs(L,exist_ok=True)
    side={}
    for v in ('old','new'):
        o=f'{K}/{t}/out_{v}'
        for f in ('script.ys','yosys.log','modules.txt','stat.txt'):
            shutil.copy(f'{o}/{f}',f'{L}/{v}_{f}')
        mods=[l.strip() for l in open(f'{o}/modules.txt') if l.startswith('  ')]
        side[v]=dict(exit=open(f'{o}/status.txt').read().strip(), netlist_sha256=open(f'{o}/netlist.sha256').read().strip(),
                     netlist_rtlil_sha256=hashlib.sha256(open(f'{o}/netlist.il','rb').read()).hexdigest(), modules=mods)
    for f in ('equiv.ys','equiv.log'): shutil.copy(f'{K}/{t}/equiv/{f}',f'{L}/{f}')
    elog=open(f'{K}/{t}/equiv/equiv.log').read()
    proven='Equivalence successfully proven!' in elog and open(f'{K}/{t}/equiv/status.txt').read().strip()=='exit=0'
    ncell=re.search(r'Found (\d+) \$equiv cells in eq',elog)
    chmods={m for c in rec['changed'] for m in c['modules']}
    elab=sorted(m for v in side for m in side[v]['modules'] if any(m==c or m.endswith('\\'+c) for c in chmods))
    same=side['old']['netlist_sha256']==side['new']['netlist_sha256'] and side['old']['netlist_sha256']
    verdict='EQUAL_NOT_ELABORATED' if (same and proven and not elab) else ('EQUAL' if same and proven else 'DIFFERENT')
    out=dict(schema='opentallas.closure.rtl_rebind_equiv.v1', lane='ROOT-0330-EQV', tile=t, top=rec['top'], params=rec['params'],
        kit_env_gate_git_blob=rec['kit_env_blob'], change='ROOT-0300 merge f722b4bbe (from 73cf5c4d4)',
        gate_result=f'physical/ref_tile/{t}/gate_result.json',
        srcs=rec['srcs'], includes=rec.get('includes',[]),
        changed_files=[{k:c[k] for k in ('path','gate_git_blob','new_git_blob','in_srcs','included_by_srcs','modules','modules_named_in_srcs')} for c in rec['changed']],
        method=('flow yosys (docker openroad/orfs:asap7lock) on the fleet: read_verilog -defer -sv -DSYNTHESIS of the gate-bound '
                'kit SRCS (+`include files) then the changed file(s) at OLD (gate-bound blob) / NEW (f722b4bbe blob); '
                'hierarchy -top TOP -chparam <kit PARAMS>; proc; flatten; opt_clean -purge; rename -enumerate; '
                'write_verilog -noattr -> sha256; plus equiv_make/equiv_simple -seq 5/equiv_induct -seq 5/equiv_status -assert '
                '(after async2sync; memory_map) of OLD vs NEW flattened top'),
        old=side['old'], new=side['new'], netlist_hash_identical=bool(same), changed_modules_elaborated=elab,
        equiv=dict(proven=proven, equiv_cells=int(ncell.group(1)) if ncell else None, log=f'results/closure/root0330_rebind_equiv/logs/{t}/equiv.log'),
        logs=f'results/closure/root0330_rebind_equiv/logs/{t}/', verdict=verdict)
    json.dump(out,open(f'{R}/{t}.json','w'),indent=1); summ[t]=verdict
json.dump(dict(schema='opentallas.closure.rtl_rebind_equiv_summary.v1',lane='ROOT-0330-EQV',tiles=summ,
  counts={v:list(summ.values()).count(v) for v in set(summ.values())},
  closed_stands_note=('closed_stands.rtl_compare judges only kit SRCS blobs; no tile SRCS holds or includes a changed file, '
   'so CLOSED status is unaffected. source_binding.validate (pre_route_gate.kit_gate_evidence, consumed-closure) refuses any '
   'consumed RTL drift and has no RTL-equivalence evidence kind; these records are not read by it.')),open(f'{R}/summary.json','w'),indent=1)
print(summ)
