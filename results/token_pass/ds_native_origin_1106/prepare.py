from pathlib import Path
import re,json,shlex,hashlib
W=Path('/srv/opentallas-scratch2/claude/codex-ds-native-origin-1106');O=Path('/home/ubuntu/scratch-root/claude/tok-ds-2/build_v1c3/obj');SRC=Path('/srv/opentallas-scratch2/claude/tok-ds-2/v0copy/rtl');OLDTOP=Path('/home/ubuntu/scratch-root/claude/tok-ds-5-v1c3r/top_fresh2.f');P=W/'parents';P.mkdir(exist_ok=True)
receipt=json.loads(Path('/srv/opentallas-scratch2/claude/codex-ds-img2-service-1105/frozen_all_LP_epoch_receipts.json').read_text());pm={};rows=[]
for row in receipt['rows']:
 paths=[Path(x) for x in row['source_sha256'] if '_LP__' in x];assert len(paths)==1;old=paths[0];s=old.read_text();assert hashlib.sha256(s.encode()).hexdigest()==row['source_sha256'][str(old)]
 for ln in row['lanes']:
  a='#(.MUT(0)) '+ln['instance']+' (';b='#(.MUT(0), .KN_EPOCH_BIAS('+str(ln['KN_bias'])+'), .NK_EPOCH_BIAS('+str(ln['NK_bias'])+')) '+ln['instance']+' (';assert s.count(a)==1,(old,a);s=s.replace(a,b,1)
 new=P/old.name;new.write_text(s);pm[str(old)]=str(new);rows.append(dict(station=row['station'],source=str(old),candidate=str(new),KN=row['lanes'][0]['KN_bias'],NK=row['lanes'][0]['NK_bias'],lanes=len(row['lanes']),sha=hashlib.sha256(s.encode()).hexdigest()))
shared=['rtl/common/landed_parent/ot_pl_land.sv','rtl/common/landed_parent/ot_pl_land_reset_forest.sv','rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv','physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv']
repl={str(Path('/srv/opentallas-scratch2/claude/wt/tok-ds-2')/x):str(W/x) for x in shared};repl.update(pm)
childs=[]
for f in sorted(O.glob('Vs81p*LP*__hierMkArgs.f')):
 prefix=f.name.removesuffix('__hierMkArgs.f');assert (O/prefix).is_dir();s=f.read_text()
 for a,b in repl.items():s=s.replace(a,b)
 s=re.sub(r'-Mdir\s+\S+','-Mdir '+str(W/'obj'/prefix),s)
 dst=W/(prefix+'.f');dst.write_text(s);childs.append(dict(prefix=prefix,args=str(dst),archive='lib'+prefix[1:]+'.a',sv=prefix[1:]+'.sv'))
assert len(childs)==3
for n in ['tb_s81_die_native_ks.sv','native_ks_peer.sv']:(W/n).write_bytes((Path('/srv/opentallas-scratch2/claude/codex-ds-native-ks833-1106')/n).read_bytes())
tb=W/'tb_s81_die_native_ks.sv';ts=tb.read_text().replace('  bit native_ks_link = 0;', '  bit native_ks_link = 0; bit native_firstdispatch_done = 0;',1)
mark="    if (dut.seqhost.u_u_seqhost.u.u_u.cw_v === 1'b1)"
stop="""    // This owned candidate is the authorized first-dispatch diagnostic.
    // Stop one edge later through the existing summary/fault collector.
    if (native_ks_link && t_ks >= 0 && !native_firstdispatch_done &&
        ((dut.seqhost.u_u_seqhost.u.u_u.vo_s[0] === 1'b1) ||
         (dut.seqhost.u_u_seqhost.u.u_u.vo_n[0] === 1'b1))) begin
      native_firstdispatch_done = 1; NCYC = cyc + 1;
      $display("NATIVE_FIRST_DISPATCH_STOP first=%0d finish=%0d",cyc,NCYC);
    end
"""
assert ts.count(mark)==1;ts=ts.replace(mark,stop+mark,1);tb.write_text(ts)
s=OLDTOP.read_text()
for a,b in repl.items():s=s.replace(a,b)
s=s.replace('/srv/opentallas-scratch2/claude/tok-ds-2/v0copy/tb_s81_die_v1c.sv',str(W/'tb_s81_die_native_ks.sv'))
s=re.sub(r'(?<![/\w])wrap/',str(OLDTOP.parent/'wrap')+'/',s)
for c in childs:s=s.replace(str(OLDTOP.parent/'wrap'/c['sv']),str(W/'wrap'/c['sv']))
s=re.sub(r'-Mdir\s+\S+','-Mdir '+str(W/'top_obj'),s).replace('--binary','--main');assert '--main' in s
s+='\n'+str(W/'native_ks_peer.sv')+'\n';(W/'top.f').write_text(s)
plan=dict(scope='Root-authorized frozen11-01 LP reset-origin candidate; boundednativefirstdispatch only',rtl_source_capability='204f8dac0c9',original_cache_readonly=str(O),source_receipt='/srv/opentallas-scratch2/claude/codex-ds-img2-service-1105/frozen_all_LP_epoch_receipts.json',pin_cycles_added=0,parents=rows,children=childs,protected_libraries_reused=392,clock_fs=833000,top_inlined_parent='s_7N_LP',diagnostic_stop='First observed PROG VO after real native KS, then one edge for existing summary;11000 failbudget',candidate_tb_sha256=hashlib.sha256(ts.encode()).hexdigest(),current_main=False,physical_release_adopted=False)
(W/'proposal.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan,indent=2))
