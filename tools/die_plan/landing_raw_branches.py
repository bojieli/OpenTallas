"""Default-off literal same-depth raw-reset branches for placed START transport.

No new reset equation is inferred. Every copied stage names its original Q;
final emission checks the exact original clk/D chain and every consumer.
"""
import math
import re

class RawBranchError(ValueError):
    pass

class RawBranches:
    def __init__(self, tn, cfg, body, outline_um=None):
        self.tn=tn;self.rows=[];self.rtl=[];self.roles={};self.used={};self.names=set()
        # ORIGINAL module body (before any generated landing logic): every literal stage must name a relay that already
        # exists here, so a generated Q can never stand in for an original chain node (FLOW 10-30 finding).
        self.original_body=body
        original_index = self.driver_index(body)
        # Default landing hardware emitted independently of this option (the ring reset relays u_cland_rst_<bus>, a
        # same-depth copy of the wrapper's own gate relay) is registered by the emitter via baseline_relay(): it is
        # pre-existing landed state in the default-off RTL, so a literal chain may continue through it.
        self.baseline=[]
        if not isinstance(cfg,list) or not cfg:raise RawBranchError(f"{tn}: literal raw branches must be a nonempty list")
        for branch in cfg:
            name=branch.get('name');base=branch.get('base');stages=branch.get('stages');consumers=branch.get('consumers')
            if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z_]\w*',name) or name in self.names:raise RawBranchError(f"{tn}: bad/duplicate raw branch {name!r}")
            self.names.add(name)
            if not isinstance(base,str) or not re.fullmatch(r'[A-Za-z_]\w*',base):raise RawBranchError(f"{tn}.{name}: registered base required")
            # DIE-KV-60 11-01: a hard wrapper's delivered reset (wire rst_n = arst_n, depth 0: the ring reset relay
            # u_cland_rst_<bus> takes it on D) is a legal base, so a literal copy of that relay can sit elsewhere
            if not (base=='rst_n' and re.search(r'\bwire rst_n = arst_n;',body)):self.driver(body,base,original_index)
            if not isinstance(stages,list) or not stages:raise RawBranchError(f"{tn}.{name}: literal stages required")
            if not isinstance(consumers,list) or not consumers or any(not isinstance(c,str) or not c for c in consumers):raise RawBranchError(f"{tn}.{name}: consumers required")
            prev=base;original_parent=base;records=[]
            for i,stage in enumerate(stages):
                original=stage.get('original');xy=stage.get('xy_um')
                if not isinstance(original,str) or not re.fullmatch(r'[A-Za-z_]\w*',original):raise RawBranchError(f"{tn}.{name}: original stage Q required")
                if not isinstance(xy,list) or len(xy)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in xy):raise RawBranchError(f"{tn}.{name}: finite stage xy required")
                if outline_um is not None and not (0 <= xy[0] <= outline_um[0] and 0 <= xy[1] <= outline_um[1]):raise RawBranchError(f"{tn}.{name}: stage xy outside outline")
                net=f'cland_raw_{name}_{i}';inst=f'u_cland_raw_{name}_{i}'
                self.rtl += [f'    wire {net};',f'    (* keep = "true" *) ot_dp_rrelay {inst} (.clk(clk), .d({prev}), .q({net}));']
                rec=dict(name=f'{name}_{i}',instance=inst,net=net,raw=prev,original=original,original_parent=original_parent,base=base,stage=i,xy_um=list(xy),added_flops=1,added_cycles=0,kind='literal_same_depth_raw_branch')
                records.append(rec);self.rows.append(rec);prev=net;original_parent=original
            for c in consumers:
                if c in self.roles:raise RawBranchError(f"{tn}: duplicate raw consumer {c}")
                self.roles[c]=dict(net=prev,original=original_parent,branch=name)
    @staticmethod
    def driver_index(text):
        """Index one immutable connectivity epoch, retaining every driver for uniqueness checks."""
        drivers = {}
        for m in re.finditer(r"\bot_dp_rrelay(?:_nl)?\s+(\w+)\s*\(([^;]*?)\);",text,re.S):
            pins=dict(re.findall(r"\.(clk|d|q)\(\s*(\w+)\s*\)",m.group(2)))
            if 'q' in pins:
                drivers.setdefault(pins['q'], []).append((m.group(1),pins))
        return drivers
    @staticmethod
    def driver(text,net,index=None):
        if index is None:
            index = RawBranches.driver_index(text)
        matches = index.get(net, [])
        if len(matches)!=1 or matches[0][1].get('clk')!='clk' or not matches[0][1].get('d'):raise RawBranchError(f"raw Q {net}: exactly one same-clk plain relay required")
        return matches[0]
    def baseline_relay(self,line):
        if not isinstance(line,str) or 'ot_dp_rrelay' not in line or 'u_cland_raw_' in line:raise RawBranchError(f"{self.tn}: baseline relay must be a default landing ot_dp_rrelay line")
        self.baseline.append(line)
    def raw_for(self,role,default):
        if role not in self.roles:return default
        if role in self.used:raise RawBranchError(f"{self.tn}: raw consumer emitted twice: {role}")
        self.used[role]=default
        return self.roles[role]['net']
    def validate(self,text):
        if set(self.roles)!=set(self.used):raise RawBranchError(f"{self.tn}: unused raw consumers {sorted(set(self.roles)-set(self.used))}")
        # Rebuild after all baseline relays and generated text are complete; no stale/global cache.
        original_index = self.driver_index(self.original_body+"\n"+"\n".join(self.baseline))
        emitted_index = self.driver_index(text)
        generated={r['net'] for r in self.rows}
        for row in self.rows:
            if row['original'] in generated:raise RawBranchError(f"{self.tn}: {row['original']} is a generated raw branch net, not an original chain node")
            # resolve uniquely in the ORIGINAL body (+ registered default landing relays) only, exact predecessor on D
            inst0,pins0=self.driver(None,row['original'],original_index)
            if pins0['d']!=row['original_parent']:raise RawBranchError(f"{self.tn}: original {row['original']} D={pins0['d']} != literal predecessor {row['original_parent']}")
            # the same single original relay must survive unchanged in the emitted text (no added or changed driver)
            inst,pins=self.driver(None,row['original'],emitted_index)
            if inst!=inst0 or pins!=pins0:raise RawBranchError(f"{self.tn}: original relay of {row['original']} changed or duplicated in the emitted text")
            _,copy=self.driver(None,row['net'],emitted_index)
            if copy['d']!=row['raw']:raise RawBranchError(f"{self.tn}: copied raw D changed for {row['net']}")
        # Consumer defaults may be an alias of another equivalent copied branch.
        original_for={r['net']:r['original'] for r in self.rows}
        for role,old in self.used.items():
            if not isinstance(old,str) or not old:raise RawBranchError(f"{self.tn}: {role} lacks an original raw equation")
            seen=set()
            while old not in original_for and old!=self.roles[role]['original']:
                if old in seen:raise RawBranchError(f"{self.tn}: reset alias loop {old}")
                seen.add(old);a=re.search(r'\bassign\s+'+re.escape(old)+r'\s*=\s*(\w+)\s*;',text)
                if not a:break
                old=a.group(1)
            original=original_for.get(old,old)
            if original!=self.roles[role]['original']:raise RawBranchError(f"{self.tn}: {role} reset phase/equation differs: {original} != {self.roles[role]['original']}")
        return dict(branches=len(self.names),flops=len(self.rows),consumers=dict(self.roles),status='literal source chains verified; cold admission still requires actual mechanism proof')
