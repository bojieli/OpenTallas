"""Compose source-qualified atomic control stages with current per-bit bound routes.

No bind9 tree, historical link table, seqhost latency or ring latency is read.
The origin is an actual seqhost output-register edge. Issuing-calendar timing and
leaf-store readiness remain separate until their local receipts are supplied.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import re

CTL_BITS=207  # valid + kind/hops/source + 186-bit CTL payload at bit21


class BoundControl:
    def __init__(self, die, timing, source_root, asbuilt_manifest=None):
        self.die=die
        self.timing=json.loads(Path(timing).read_text()) if not isinstance(timing,dict) else timing
        if self.timing.get('schema')!='opentallas.s81.bound_control_local.v1' or self.timing.get('verdict')!='PASS':
            raise ValueError('native control needs measured current local-stage receipts')
        self.source_root=Path(source_root)
        for name,wanted in self.timing['source_sha256'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('local-stage source paths must be repo-relative')
            path=self.source_root/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:
                raise ValueError('local-stage source changed: '+name)
        from layer_prog.slice_source import manifest_selection
        manifest=asbuilt_manifest or os.environ.get('OT_S81_SELECTED_ASBUILT_MANIFEST')
        if not manifest:
            raise ValueError('native control needs an explicit current as-built source manifest')
        self.selection=manifest_selection(self.source_root,manifest)
        self.cache={}

    def atomic(self, sl, suffix):
        hits=[n for n in self.die.units if n.startswith(sl+'.') and n.endswith('.'+suffix)]
        if len(hits)!=1:
            raise ValueError(f'{sl}: need one exact retained atomic {suffix}, found {hits}')
        return hits[0]

    def transport(self, source, sport, target, tport, source_bits=None, target_bits=None):
        sp=self.die.units[source]['ports'][sport];tp=self.die.units[target]['ports'][tport]
        si=list(range(len(sp['bits']))) if source_bits is None else list(source_bits)
        ti=list(range(len(tp['bits']))) if target_bits is None else list(target_bits)
        if len(si)!=len(ti) or not si or len(set(si))!=len(si) or len(set(ti))!=len(ti):
            raise ValueError('native transport needs explicit nonempty one-to-one bit views')
        if any(type(i) is not int or i<0 or i>=len(sp['bits']) for i in si) or any(type(i) is not int or i<0 or i>=len(tp['bits']) for i in ti):
            raise ValueError('native transport bit view outside current port')
        key=(source,sport,target,tport,tuple(si),tuple(ti))
        if key not in self.cache:
            # Query views retain exact source graph net IDs. They do not create
            # RTL ports, aliases, nets or transport; BoundDie proves each bit.
            view=copy.copy(self.die)
            view.units=dict(self.die.units)
            sn,tn='@native_source_view','@native_target_view'
            view.units[sn]=dict(ports={'p':dict(dir=sp['dir'],bits=[sp['bits'][i] for i in si])})
            view.units[tn]=dict(ports={'p':dict(dir=tp['dir'],bits=[tp['bits'][i] for i in ti])})
            r=view.route(sn,'p',tn,'p')
            self.die.sinks=view.sinks
            self.cache[key]=dict(r,source=source,source_port=sport,target=target,target_port=tport,
                                 source_bits=si,target_bits=ti)
        return self.cache[key]

    def group(self, label, requests):
        routes=[self.transport(*r) for r in requests]
        ages={r['age_edges'] for r in routes}
        if len(ages)!=1:
            raise ValueError(label+' control/payload bound ages disagree: '+str(sorted(ages)))
        return dict(kind='transport',label=label,edges=ages.pop(),routes=routes)

    @staticmethod
    def _integer(value):
        if type(value) is int:return value
        text=str(value).replace('_','').strip()
        if re.fullmatch(r'-?\d+',text):return int(text)
        m=re.fullmatch(r"(?:\d+)?'[sS]?([bBoOdDhH])([0-9a-fA-F]+)",text)
        if m:return int(m[2],{'b':2,'o':8,'d':10,'h':16}[m[1].lower()])
        raise ValueError('unsupported measured parameter constant '+text)

    def local(self, unit, transition):
        master=self.die.units[unit]['master']
        entry=self.timing['masters'].get(master)
        if not entry or transition not in entry['edges']:
            raise ValueError('unmeasured local control stage '+master+'.'+transition)
        # Every accepted wrapper has its own source hash in the receipt, plus
        # the measured underlying atomic ring/XRT source. No master-name alias.
        import bind_elab
        chosen,ambiguous=bind_elab.pick(self.selection[2],master,self.selection[3])
        expected=self.source_root/entry['source_path']
        if ambiguous or not chosen or Path(chosen).resolve()!=expected.resolve():
            raise ValueError('local timing is not for current preferred source: '+master)
        actual_defines=set(self.selection[1].get('defines',[]))
        if 'defines' in entry:
            scope=set(entry.get('define_scope',actual_defines|set(entry['defines'])))
            if actual_defines&scope!=set(entry['defines'])&scope:
                raise ValueError('local measured define set changed: '+master)
        body=bind_elab.module_body(expected,master)
        actual_params=self.die.units[unit].get('params',{})
        for name,wanted in entry.get('params',{}).items():
            value=actual_params.get(name)
            if value is None:
                # An omitted source parameter uses its declared literal default,
                # or this exact selected wrapper bakes the measured literal.
                default=re.search(r'\b'+re.escape(name)+r'\s*=\s*([^,)\n]+)',body)
                baked=re.findall(r'\.'+re.escape(name)+r'\(\s*([^()]+)\)',body)
                choices=[default[1]] if default else baked
                if len(choices)!=1:
                    raise ValueError('measured parameter has no unique current value: '+master+'.'+name)
                value=choices[0]
            if self._integer(value)!=self._integer(wanted):
                raise ValueError('local measured parameter changed: '+master+'.'+name)
        for name,wanted in entry.get('straps',{}).items():
            if self.die.strap(unit,name)!=self._integer(wanted):
                raise ValueError('local measured source strap changed: '+unit+'.'+name)
        if entry['source_path'] not in self.timing['source_sha256']:
            raise ValueError('local wrapper source missing from receipt: '+master)
        return dict(kind='local',unit=unit,master=master,transition=transition,edges=entry['edges'][transition])

    def delivery(self, sl, port):
        xg,xr=self.atomic(sl,'u_xg'),self.atomic(sl,'u_xr')
        if port=='vi': valid,data='dl_vv','dl_vb'
        elif port=='ri_e': valid,data='dl_wv','dl_w'
        elif port=='ri_w': valid,data='dl_ev','dl_e'
        else:raise ValueError('unsupported actual ring control input '+port)
        # XRT drops the redundant bit0 and unused high fields at its physical
        # input. Retain every live CTL field and its separate valid exactly.
        bus=self.group(sl+' '+port+' delivery',[(xg,valid,xr,valid),
             (xg,data,xr,data,range(1,CTL_BITS),range(CTL_BITS-1))])
        return [self.local(xg,port+'_to_delivery'),bus]

    def path(self, sl):
        slices=self.die.slices()
        if sl not in slices:raise ValueError('native target is not a current source slice: '+sl)
        sid=slices[sl]['sid'];tier='N' if sid&1 else 'S';col=sid//2
        by_sid={v['sid']:n for n,v in slices.items()}
        entry=by_sid[8+(sid&1)];xg=self.atomic(entry,'u_xg');xr=self.atomic(entry,'u_xr')
        parts=[]
        if tier=='N':
            parts.append(self.group('seqhost north egress', [('u_seqhost','vo_n',xg,'vi',range(CTL_BITS),range(CTL_BITS))]))
        else:
            parts.append(self.group('seqhost to bk selector', [('u_seqhost','vo_s','u_bk_sel','vi_n',range(CTL_BITS),range(CTL_BITS))]))
            parts.append(self.local('u_bk_sel','vi_n_to_vo_s'))
            parts.append(self.group('bk selector south egress', [('u_bk_sel','vo_s',xg,'vi',range(CTL_BITS),range(CTL_BITS))]))
        if col==4:
            parts+=self.delivery(entry,'vi');return self._result(sl,'vi',parts)
        # Only the V entry reinjects through XRT. Intermediate stops forward
        # the existing line packet; they do not reinject it a second time.
        parts+=self.delivery(entry,'vi')
        parts.append(self.local(xr,'dl_ctl_to_ci'))
        parts.append(self.group(entry+' ci injection',[(xr,'ci_dir',xg,'ci_dir'),
            (xr,'ci_b',xg,'ci_b',range(CTL_BITS),range(CTL_BITS))]))
        parts.append(self.local(xg,'ci_to_line'))
        direction=-1 if col<4 else 1;c=4;current=entry
        while c!=col:
            nxt=c+direction;other=by_sid[2*nxt+(sid&1)]
            src=self.atomic(current,'u_xg');dst=self.atomic(other,'u_xg')
            out_port,in_port=('ro_w','ri_e') if direction<0 else ('ro_e','ri_w')
            parts.append(self.group(current+' to '+other,[(src,out_port,dst,in_port,range(CTL_BITS),range(CTL_BITS))]))
            c=nxt;current=other
            if c==col:parts+=self.delivery(other,in_port)
            else:parts.append(self.local(dst,in_port+'_to_line'))
        return self._result(sl,in_port,parts)

    def _result(self,sl,port,parts):
        edge=0
        for p in parts:
            edge+=p['edges'];p['after_edge']=edge
        xr=self.atomic(sl,'u_xr')
        command=self.local(xr,'dl_ctl_to_command')
        return dict(slice=sl,entry_port=port,origin='actual u_seqhost vo output-register edge0',
                    xr_input_edge=edge,xr_command_pin_edge=edge+command['edges'],parts=parts,
                    command_stage=command,die_sha256=self.die.die_sha,
                    scope='current CTL transport to atomic XRT command pins; seqhost calendar and leaf-write readiness separate')


def compile_control(*, layer, out, bound, inventory, timing, source_root, asbuilt_manifest, entry_program=None):
    """Compile actual control transport and optional native command landing dates."""
    from layer_prog.bound_die import BoundDie
    out=Path(out)
    if out.exists():raise ValueError('preserve previous native compiler result; choose a fresh output')
    die=BoundDie(bound,inventory)
    control=BoundControl(die,timing,source_root,asbuilt_manifest)
    paths={}
    for sl in sorted(die.slices()):
        try:paths[sl]=dict(status='PASS',**control.path(sl))
        except (ValueError,KeyError) as exc:paths[sl]=dict(status='BLOCKED',slice=sl,reason=str(exc))
    commands=[]
    if entry_program is not None:
        entry=json.loads(Path(entry_program).read_text())
        if entry.get('die_sha256')!=die.die_sha:
            raise ValueError('entry commands belong to a different bound top')
        table={t['i']:t for t in entry['templates']}
        for command in entry['commands']:
            sl=command['slice'];p=paths.get(sl)
            rec=dict(command)
            if not p or p['status']!='PASS':
                rec.update(status='BLOCKED',reason='target has no complete measured control route')
            else:
                try:
                    sid=die.slices()[sl]['sid'];port='vo_n' if sid&1 else 'vo_s'
                    local=control.local('u_seqhost','calendar_command_to_'+port)
                    tx=command['issue']+local['edges']
                    rec.update(status='PARTIAL',payload186=table[command['template']]['payload186'],
                        seqhost_output_edge_from_age0_command=tx,
                        xr_input_edge_from_age0_command=tx+p['xr_input_edge'],
                        xr_command_pin_edge_from_age0_command=tx+p['xr_command_pin_edge'],
                        basis='exact current local command-to-output plus strict bound per-bit control transport',
                        leaf_store_commit_edge=None,
                        hold='actual XR output to leaf-store transport/commit, root boot phase and global exchange not sealed')
                except (KeyError,ValueError) as exc:rec.update(status='BLOCKED',reason=str(exc))
            commands.append(rec)
    blocked=sum(p['status']!='PASS' for p in paths.values())
    record=dict(schema='opentallas.s81.bound_control_compile.v1',layer=layer,
        verdict='PASS_CONTROL_TRANSPORT' if not blocked else 'BLOCKED',die_sha256=die.die_sha,
        paths=paths,commands=commands,blocked_paths=blocked,
        timing_origin='actual seqhost output-register edge0; optional command dates relative to observed age0-command event',
        legacy_geometry_used=False,legacy_local_latency_used=False,
        root_boot_phase_qualified=False,leaf_store_residency_qualified=False,
        native_job_sealed=False,full_token=False)
    out.mkdir(parents=True)
    (out/'bound_control.json').write_text(json.dumps(record,indent=1)+'\n')
    print(json.dumps(dict(verdict=record['verdict'],paths=len(paths),blocked=blocked,commands=len(commands))))
    return 2 if blocked or any(c['status']=='BLOCKED' for c in commands) else 0
