#!/usr/bin/env python3
"""Collect actual Q source/forwarded/native clock pin arrivals, without fabricating a phase.

plan derives all pins from one GEN. measure runs inside OpenROAD on a completed
physical clock ODB, one library corner at a time. join preserves source hashes,
assumed-view and GEN mismatch blockers. This receipt alone never admits prefetch.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

LANES = {'dvw_dd_wo': ('dvs_W5', 'dd_wo', 'dd_i'),
         'sf_q_slot': ('sys_face', 'q_slot', 'q_slot'),
         'sf_q_slot_beat': ('sys_face', 'q_slot_beat', 'q_slot_beat')}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=1)+'\n')


def make_plan(die_v, lanes, source_commit, qready=None):
    inst={}
    for line in Path(die_v).read_text().splitlines():
        m=re.match(r'\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$',line)
        if m:inst[m[2]]=dict(master=m[1],ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3])))
    rows={r['bid']:r for r in load(lanes)['lanes']}
    pins=set();records={};blockers=[]
    for bid,(src,sp,dp) in LANES.items():
        row=rows.get(bid)
        if not row or src not in inst or 'native59' not in inst:
            raise ValueError('missing Q lane/endpoints: '+bid)
        source=inst[src]['ports'].get(sp);sink=inst['native59']['ports'].get(dp)
        if (row.get('src'),row.get('dst'))!=(src,'native59') or not source or not sink:
            raise ValueError('Q lane GEN endpoint mismatch: '+bid)
        chain=(row.get('stations') or [])+[row['landing']]
        at=source
        for name in chain:
            if name not in inst or inst[name]['ports'].get('a')!=at:
                raise ValueError('broken Q lane chain: '+name)
            at=inst[name]['ports'].get('b')
        if at!=sink or len(chain)!=row['n']:
            raise ValueError('wrong Q lane sink/frame count: '+bid)
        land=chain[-1];ports=inst[land]['ports']
        k=sum((ports.get('k'+str(b))==ports.get('tie_hi'))<<b for b in range(3))
        if any(ports.get('k'+str(b)) not in (ports.get('tie_hi'),ports.get('tie_lo')) for b in range(3)) or k!=row['K']:
            raise ValueError('Q landing straps differ from GEN: '+bid)
        clkports={}
        for name in [src]+chain+['native59']:
            have=inst[name]['ports']
            cp=[n for n in ('ck','ck_s','ckf','ck_o','ck_core','ck_fmt','ck_qbuf') if n in have]
            clkports[name]=dict(master=inst[name]['master'],pins={n:f'{name}/{n}' for n in cp})
            pins.update(f'{name}/{n}' for n in cp)
        for needed in ('ck_fmt','ck_qbuf'):
            if needed not in inst['native59']['ports']:
                blockers.append('SAFE2 native clock port absent from GEN: native59/'+needed)
        g=row.get('G_reset_tree');r0=row.get('R0_reset_tree')
        if type(g) is not int or type(r0) is not int or (row['E']+g-r0)%8!=k:
            blockers.append('fixed reset/landing epoch not source-bound: '+bid)
        records[bid]=dict(source=src+'.'+sp,consumer='native59.'+dp,frames=row['n'],
                         E=row['E'],K=k,planned_age_edges=row['E']+1,G_effective=g,R0=r0,
                         source_reset_raw=None if g is None else g-1,clock_ports=clkports,
                         note='G includes HOP0_EN_REG=1; measured source/forwarded/read phases must realize the planned age')
    identity=dict(source_commit=source_commit,die_v_sha256=sha(die_v),fwd_lanes_sha256=sha(lanes))
    if qready:
        q=load(qready)
        if q.get('inputs',{}).get('die_v_sha256')!=identity['die_v_sha256'] or q.get('inputs',{}).get('fwd_lanes_sha256')!=identity['fwd_lanes_sha256']:
            blockers.append('Q readiness certificate belongs to a different GEN')
        identity['qready_sha256']=sha(qready)
    return dict(schema='opentallas.qwen.q_phase_pin_plan.v1',identity=identity,lanes=records,pins=sorted(pins),
                blockers=sorted(set(blockers)),phase_qualified=False,advance_admitted=False)


def read_arrivals(path):
    out={}
    for line in Path(path).read_text().splitlines():
        f=line.split('\t')
        if len(f)!=4:continue
        try:late,early,slew=map(float,f[1:])
        except ValueError:continue
        if not all(math.isfinite(n) and abs(n)<1e20 for n in (late,early,slew)):continue
        pin=f[0][:-3] if f[0].endswith('[0]') else f[0]
        if pin in out:raise ValueError('duplicate clock pin arrival: '+pin)
        out[pin]=dict(late_ps=late,early_ps=early,slew_ps=slew)
    return out


def join(plan, targets, measurements):
    """measurements={corner:(arrival.tsv, measurement_receipt.json)}; no cross-corner early/late mixing."""
    p=load(plan);t=load(targets)['masters'];blockers=list(p['blockers']);corners={};sources={}
    for corner in ('tt','ff','ss'):
        if corner not in measurements:
            blockers.append('missing actual clock pin measurement: '+corner);continue
        path,receipt_path=measurements[corner];receipt=load(receipt_path)
        if receipt.get('corner')!=corner or receipt.get('plan_sha256')!=sha(plan) or receipt.get('arrivals_sha256')!=sha(path):
            raise ValueError('phase measurement identity/corner mismatch: '+corner)
        a=read_arrivals(path);missing=sorted(set(p['pins'])-set(a))
        clocked=set(receipt.get('pins_with_propagated_clocks',[]))
        unclocked=sorted(set(p['pins'])-clocked)
        if unclocked:blockers.append(f'{corner}: no propagated clock identity ({len(unclocked)})')
        if missing:blockers.append(f'{corner}: missing/nonfinite pin arrivals ({len(missing)})')
        corners[corner]=dict(arrivals={pin:a.get(pin) for pin in p['pins']},missing=missing)
        sources[corner]=receipt
    refs={}
    for lane in p['lanes'].values():
        for inst,desc in lane['clock_ports'].items():
            # Input root/capture clocks owe their actual hardened pin->flop insertion.
            # ck_o is an output; forwarded ckf remains a measured arrival, not a guessed root.
            master=desc['master'];m=t.get(master,{})
            for port,pin in desc['pins'].items():
                if port=='ck_o':continue
                mm=m.get('insertion_per_clock_pin_ps',{});v=mm.get(port,mm.get(port+'[0]'))
                real=m.get('view')=='real'
                if not real or v is None:
                    blockers.append('unqualified hard-child clock reference: '+pin+' master '+master)
                refs[pin]=dict(master=master,view=m.get('view'),insertion_ss_ff_tt_ps=v)
    return dict(schema='opentallas.qwen.q_phase_receipt.v1',plan_sha256=sha(plan),targets_sha256=sha(targets),
                identity=p['identity'],lanes=p['lanes'],corners=corners,measurement_sources=sources,
                hard_child_clock_references=refs,blockers=sorted(set(blockers)),
                pin_evidence_complete=not blockers,phase_qualified=False,advance_admitted=False,
                remaining_proof='Run all512 production Q writes and32 requests on these actual phases with the bound programme; '
                                'prove landing epoch, planned age, native SRAM readiness and unchanged CMD/Q output slots')


def measure(a):
    # Run inside fleet OpenROAD. build.Die uses only the supplied single corner lib set here.
    import types
    import build
    p=load(a.plan);m=load(a.manifest)
    if not Path(a.odb).is_file():raise ValueError('completed physical clock ODB missing')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    d=build.Die(types.SimpleNamespace(odb=a.odb,libs=a.libs,libs_ff=None))
    d.setup_sta([tuple(c) for c in m['clocks']],m['spec'].get('rc_layer','M8'))
    dest=out/f'qphase_{a.corner}.tsv';d.measure(p['pins'],dest)
    clock_file=out/f'qphase_{a.corner}_clocks.tsv'
    d.tcl(f'''set fi [open {{{dest}.pins}}]; set fo [open {{{clock_file}}} w]
while {{[gets $fi n] >= 0}} {{
 set p [get_pins -quiet [string map {{[ \\[ ] \\]}} $n]]
 # Native pin property includes generated/gated clock families. Unsupported
 # or missing tags remain empty; numeric arrivals alone never qualify them.
 set cs {{}}; catch {{set cs [get_property $p clocks]}}
 set names {{}}; foreach c $cs {{lappend names [get_full_name $c]}}
 puts $fo "$n\\t[llength $cs]\\t$names"
}}
close $fi; close $fo''')
    clocked=[];owners={}
    for line in clock_file.read_text().splitlines():
        f=line.split('\t')
        if len(f)>=3:
            pin=f[0][:-3] if f[0].endswith('[0]') else f[0]
            owners[pin]=dict(count=int(f[1]),clock_names_tcl=f[2])
            if int(f[1])==1:clocked.append(pin)
    d.tcl(f'report_check_types -max_slew -max_capacitance -violators > {out}/drv_{a.corner}.rpt')
    write(out/f'qphase_{a.corner}.json',dict(schema='opentallas.qwen.q_phase_measure.v1',corner=a.corner,
          plan_sha256=sha(a.plan),manifest_sha256=sha(a.manifest),odb_sha256=sha(a.odb),
          libraries={s:sha(s) for s in Path(a.libs).read_text().split()},arrivals_sha256=sha(dest),
          pins_with_propagated_clocks=clocked,clock_identity_sha256=sha(clock_file),
          clock_pin_owners=owners,
          clock_identity_status='native get_property pin clocks; empty/missing tags block qualification',
          parasitics='placement estimate on completed physical clock ODB',
          scope='actual die clock pin arrivals; single-corner early/late; not native flop or production admission'))


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True)
    pl=sub.add_parser('plan');pl.add_argument('--die-v',required=True);pl.add_argument('--lanes',required=True)
    pl.add_argument('--source-commit',required=True);pl.add_argument('--qready');pl.add_argument('--out',required=True)
    me=sub.add_parser('measure')
    for arg in ('plan','manifest','odb','libs','corner','out'):me.add_argument('--'+arg,required=True)
    jo=sub.add_parser('join');jo.add_argument('--plan',required=True);jo.add_argument('--targets',required=True);jo.add_argument('--out',required=True)
    for c in ('tt','ff','ss'):jo.add_argument('--'+c+'-arrivals');jo.add_argument('--'+c+'-receipt')
    a=ap.parse_args()
    if a.mode=='plan':write(a.out,make_plan(a.die_v,a.lanes,a.source_commit,a.qready))
    elif a.mode=='measure':measure(a)
    else:
        pairs={c:(getattr(a,c+'_arrivals'),getattr(a,c+'_receipt')) for c in ('tt','ff','ss') if getattr(a,c+'_arrivals') and getattr(a,c+'_receipt')}
        write(a.out,join(a.plan,a.targets,pairs))


if __name__=='__main__':main()
