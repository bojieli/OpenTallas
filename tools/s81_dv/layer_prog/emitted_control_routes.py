"""Selective actual native CTL paths; local ages require exact source receipts."""
import hashlib,json,re
from pathlib import Path
from layer_prog.emitted_leaf_routes import Wiring,_params
from layer_prog.emitted_norm_source import EmittedNormSource
from layer_prog.bound_control import BoundControl

class ControlView:
    def __init__(self,inventory,latency,timing=None,source_root=None,manifest=None):
        self.die=EmittedNormSource(inventory);self.top=Path(self.die.source_record['source_top']);self.text=self.top.read_text()
        self.lanes=json.loads(Path(latency).read_text())['buses'];self.units={};self.parts={};self.checked=[]
        for sl,row in self.die.rows.items():
            part=row['part'];self.part(part,Path(row['wrapper_file']))
            self.units[sl+'.xg']=self.atomic(part,r'ot_s81sl_xg\w*')
            self.units[sl+'.xr']=self.atomic(part,r'ot_s81sl_xrt[13]')
        for part,pattern,key in [('seqhost',r'dsdv_seq_host_mux','seqhost'),('bk_sel',r'dsdv_bk_sel_vmtx','bk')]:
            m=re.search(r'^\s*(\w+)(?:\s+#\((.*?)\))?\s+'+part+r'\s*\(',self.text,re.M)
            if not m:raise ValueError('actual selected part absent '+part)
            self.part(part,self.top.parent/(m[1]+'.sv'));self.units[key]=self.atomic(part,pattern)
        self.local_qualified=False;self.local_source_sha256={}
        if timing is not None:
            data=Path(timing).read_bytes();receipt=json.loads(data)
            if receipt.get('schema')!='opentallas.s81.bound_control_local.v1' or receipt.get('verdict')!='PASS':raise ValueError('actual passing local control receipt required')
            selected=json.loads(Path(manifest).read_text());defines=set(selected['defines'])
            for name,wanted in receipt['source_sha256'].items():
                if Path(name).is_absolute()or '..'in Path(name).parts:raise ValueError('local control source path differs')
                if hashlib.sha256((Path(source_root)/name).read_bytes()).hexdigest()!=wanted:raise ValueError('local control source body changed: '+name)
            self.local_source_sha256=receipt['source_sha256'];self.timing_sha256=hashlib.sha256(data).hexdigest()
            expected={'vi_to_delivery':2,'ri_e_to_delivery':2,'ri_w_to_delivery':2,'ri_e_to_line':2,'ri_w_to_line':2,'ci_to_line':2}
            for unit in self.units.values():
                if unit['master'].startswith('ot_s81sl_xg'):edges=expected
                elif unit['master'].startswith('ot_s81sl_xrt'):edges={'dl_ctl_to_ci':3,'dl_ctl_to_command':3}
                else:continue
                record=receipt['masters'][unit['master']]
                if record['edges']!=edges:raise ValueError('qualified selected local CTL ages changed')
                scope=set(record['define_scope'])
                if defines&scope!=set(record['defines'])&scope:raise ValueError('selected local control variant differs')
            if {k:BoundControl._integer(v)for k,v in self.units['seqhost']['params'].items()if k in ('SELR','STATIC_KS6')}!={'SELR':1,'STATIC_KS6':0}:raise ValueError('actual native seqhost active variant differs')
            bk=receipt['masters']['dsdv_bk_sel_vmtx']
            if bk['edges']['vi_n_to_vo_s']!=3:raise ValueError('qualified BK local age differs')
            if defines!=set(receipt['masters']['dsdv_hostb_seqhost_mux']['defines']):raise ValueError('selected native control source defines differ')
            seq=receipt['masters']['dsdv_hostb_seqhost_mux']['edges']
            self.seq_egress={0:seq['calendar_command_to_vo_s'],1:seq['calendar_command_to_vo_n']}
            if self.seq_egress!={0:8,1:7}:raise ValueError('actual selected issuer to VO local source age differs')
            source=self.atomic('seqhost',r'dsdv_hostb_source')
            if BoundControl._integer(source['params']['HOSTB_ENABLE'])!=0:raise ValueError('current HOSTB0 local source selection required')
            self.local_qualified=True
    def part(self,name,file):
        text=file.read_text();self.parts[name]=dict(text=text,wiring=Wiring(text),file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    def atomic(self,part,pattern):
        text=self.parts[part]['text'];hits=list(re.finditer(r'^\s*('+pattern+r')(?:\s+#\((.*?)\))?\s+(\w+)\s*\((.*?)^\s*\);',text,re.M|re.S))
        if len(hits)!=1:raise ValueError('one actual selected atomic '+pattern+' required')
        h=hits[0];canonical=re.findall(r'// as-built (\S+)',text[:h.start()])[-1]
        return dict(part=part,master=h[1],instance=h[3],canonical=canonical,params=_params(h[2]or''),ports=_params(h[4]))
    def local(self,source,sport,target,tport,si,ti):
        s=self.units[source];t=self.units[target]
        if s['part']!=t['part']:raise ValueError('local path crosses physical part')
        w=self.parts[s['part']]['wiring'];a=w.bits(s['ports'][sport]);b=w.bits(t['ports'][tport]);terminals={n for n,_ in a};ages=set()
        for i,j in zip(si,ti):
            name,index,age=w.trace(b[j],terminals)
            if (name,index)!=a[i]:raise ValueError('actual local CTL bit differs')
            ages.add(age)
        if len(ages)!=1:raise ValueError('actual local CTL field ages differ')
        return ages.pop()
    def cross(self,source,sport,target,tport,width=207):
        s=self.units[source];t=self.units[target];part=self.parts[t['part']];w=part['wiring'];targets=w.bits(t['ports'][tport]);ages=set();lanes=set()
        for bit in range(width):
            q,index,local=w.trace(targets[bit],set(w.inputs));expr,n=w.inputs[q];external=w.bits(expr)[index]
            if external[0]in w.landings:external=w.bits(w.landings[external[0]])[external[1]]
            hits=[b for b in self.lanes if b['dst']==t['part']and b['bus_in']==external[0]]
            if len(hits)!=1:raise ValueError('actual native CTL input lane absent/ambiguous')
            bus=hits[0]
            if n!=bus['width']or index>=n or external[1]!=index:raise ValueError('native CTL input active width differs')
            expected=['leaf',s['canonical'],sport,bit]
            if bus['source_bits'][index]!=expected:raise ValueError('actual CTL source bit differs: '+str((bus['source_bits'][index],expected)))
            header=re.search(r'^\s*input\s+wire\s+\[(\d+):0\]\s+'+re.escape(bus['bus_in'])+r'\s*,\s*//\s*(\d+) data \+ epoch \[(\d+)\]: lane '+re.escape(bus['lane'])+r', (\d+) cycles:',part['text'],re.M)
            if not header or [int(header[k])for k in (1,2,3)]!=[n]*3 or int(header[4])!=bus['bound_stages']:
                raise ValueError('selected native CTL lane/header identity differs')
            ages.add(bus['bound_stages']+local);lanes.add(bus['lane'])
        if len(ages)!=1:raise ValueError('selected CTL valid/payload ages differ')
        r=dict(source=source,source_port=sport,target=target,target_port=tport,bits=width,edges=ages.pop(),lanes=sorted(lanes));self.checked.append(r)
        return r['edges']
    def delivery(self,sl,port):
        data,valid={'vi':('dl_vb','dl_vv'),'ri_e':('dl_w','dl_wv'),'ri_w':('dl_e','dl_ev')}[port]
        a=self.local(sl+'.xg',data,sl+'.xr',data,range(1,207),range(206))
        b=self.local(sl+'.xg',valid,sl+'.xr',valid,range(1),range(1))
        if a!=b:raise ValueError('actual XG delivery valid/data age differs')
        return 2+a # exact-source qualified xg input->delivery
    def path(self,sid):
        if not self.local_qualified:raise ValueError('selected local control source/receipt identity required before composing ages')
        sl=next(n for n,r in self.die.slices().items()if r['sid']==sid);entry=next(n for n,r in self.die.slices().items()if r['sid']==8+(sid&1));col=sid//2
        parts=[]
        if sid&1:parts.append(self.cross('seqhost','vo_n',entry+'.xg','vi'))
        else:parts.extend([self.cross('seqhost','vo_s','bk','vi_n'),3,self.cross('bk','vo_s',entry+'.xg','vi')])
        parts.append(self.delivery(entry,'vi'))
        if col!=4:
            parts.append(3) # exact-source qualified XRT dl_ctl->ci
            a=self.local(entry+'.xr','ci_b',entry+'.xg','ci_b',range(207),range(207));b=self.local(entry+'.xr','ci_dir',entry+'.xg','ci_dir',range(3),range(3))
            if a!=b:raise ValueError('actual CTL injection valid/direction age differs')
            parts.extend([a,2]);direction=-1 if col<4 else 1;c=4;current=entry
            while c!=col:
                nxt=c+direction;other=next(n for n,r in self.die.slices().items()if r['sid']==2*nxt+(sid&1));outp,inp=('ro_w','ri_e')if direction<0 else('ro_e','ri_w')
                parts.append(self.cross(current+'.xg',outp,other+'.xg',inp));c=nxt;current=other
                parts.append(self.delivery(other,inp)if c==col else 2)
        parts.append(3) # exact-source qualified XRT dl_ctl->command output
        return dict(sid=sid,slice=sl,seqhost_vo_output_to_XR_command_edges=sum(parts),
            calendar_command_to_XR_command_edges=self.seq_egress[sid&1]+sum(parts),parts=parts,
            scope='relative to actual command register edge; no HOST/KS/reset/physical START date')
