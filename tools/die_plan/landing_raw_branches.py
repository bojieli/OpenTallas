"""Default-off literal same-depth raw-reset branches for placed START transport.

No new reset equation is inferred. Every copied stage names its original Q;
final emission checks the exact original clk/D chain and every consumer.
"""
import math
import re

class RawBranchError(ValueError):
    pass

class RelayIndex(dict):
    """Keep the legacy connectivity API and the independently checked relay kinds."""
    def __init__(self):
        super().__init__()
        self.modules = {}

class RawBranches:
    def __init__(self, tn, cfg, body, outline_um=None, *, hard_entry_um=None):
        self.tn=tn;self.rows=[];self.rtl=[];self.roles={};self.used={};self.names=set()
        self.hard_prefixes = []
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
            prefix = branch.get("hard_boot_prefix_um")
            if prefix is not None:
                if hard_entry_um is None or base != "rst_n" or not re.search(r"\brst_n = arst_n;", body):
                    raise RawBranchError(f"{tn}.{name}: boot prefix requires the hard wrapper delivered reset")
                if not isinstance(prefix, list) or not prefix:
                    raise RawBranchError(f"{tn}.{name}: explicit nonempty boot prefix required")
                if set(consumers) & {"origin"} or any(not role.startswith(("writer:", "fstart:")) for role in consumers):
                    raise RawBranchError(f"{tn}.{name}: hard boot prefix applies only to outgoing START")
                points = [hard_entry_um, *prefix, stages[0].get("xy_um")]
                for point in points:
                    if not isinstance(point, list) or len(point) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in point):
                        raise RawBranchError(f"{tn}.{name}: finite hard prefix point required")
                    if outline_um and not all(0 <= v <= bound for v, bound in zip(point, outline_um)):
                        raise RawBranchError(f"{tn}.{name}: boot prefix point outside outline")
                hops = [sum(abs(x-y) for x,y in zip(a,b)) for a,b in zip(points, points[1:])]
                import cbc_rules
                reach = cbc_rules.reset_hop_cap_um()
                if max(hops) > reach + 1e-6:
                    raise RawBranchError(f"{tn}.{name}: hard boot prefix {max(hops):.3f}um exceeds R4 {reach}um")
                for index, xy in enumerate(prefix):
                    net = f"cland_hard_raw_{name}_{index}"
                    inst = f"u_cland_hard_raw_{name}_{index}"
                    self.rtl.extend([f"    wire {net};",
                        f'    (* keep = "true" *) ot_dp_rrelay {inst} (.clk(clk), .d({prev}), .q({net}));'])
                    self.hard_prefixes.append(dict(name=f"{name}_boot_{index}", instance=inst, net=net,
                        raw=prev, xy_um=xy, added_flops=1, added_cycles=1, kind="hard_wrapper_boot_raw_prefix"))
                    prev = net
            for i,stage in enumerate(stages):
                original=stage.get('original');xy=stage.get('xy_um')
                if not isinstance(original,str) or not re.fullmatch(r'[A-Za-z_]\w*',original):raise RawBranchError(f"{tn}.{name}: original stage Q required")
                if not isinstance(xy,list) or len(xy)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in xy):raise RawBranchError(f"{tn}.{name}: finite stage xy required")
                if outline_um is not None and not (0 <= xy[0] <= outline_um[0] and 0 <= xy[1] <= outline_um[1]):raise RawBranchError(f"{tn}.{name}: stage xy outside outline")
                net=f'cland_raw_{name}_{i}';inst=f'u_cland_raw_{name}_{i}'
                # A default landing ring relay can be registered after construction;
                # those default relays are plain. validate() rejects any other kind.
                modules=original_index.modules.get(original, ['ot_dp_rrelay'])
                module=modules[0] if len(modules)==1 else 'ot_dp_rrelay'
                self.rtl += [f'    wire {net};',f'    (* keep = "true" *) {module} {inst} (.clk(clk), .d({prev}), .q({net}));']
                rec=dict(name=f'{name}_{i}',instance=inst,net=net,raw=prev,original=original,original_parent=original_parent,base=base,stage=i,xy_um=list(xy),module=module,added_flops=2 if module=='ot_dp_rrelay_nl' else 1,added_cycles=0,kind='literal_same_depth_raw_branch')
                records.append(rec);self.rows.append(rec);prev=net;original_parent=original
            for c in consumers:
                if c in self.roles:raise RawBranchError(f"{tn}: duplicate raw consumer {c}")
                self.roles[c]=dict(net=prev,original=original_parent,branch=name)
    @staticmethod
    def driver_index(text):
        """Index one immutable connectivity epoch, retaining every driver for uniqueness checks."""
        drivers = RelayIndex()
        for m in re.finditer(r"\b(ot_dp_rrelay(?:_nl)?)\s+(\w+)\s*\(([^;]*?)\);",text,re.S):
            pins=dict(re.findall(r"\.(clk|d|q)\(\s*(\w+)\s*\)",m.group(3)))
            if 'q' in pins:
                drivers.setdefault(pins['q'], []).append((m.group(2),pins))
                drivers.modules.setdefault(pins['q'], []).append(m.group(1))
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
        for prefix in self.hard_prefixes:
            inst, pins = self.driver(None, prefix["net"], emitted_index)
            if inst != prefix["instance"] or pins["d"] != prefix["raw"] or emitted_index.modules[prefix["net"]] != ["ot_dp_rrelay"]:
                raise RawBranchError(f"{self.tn}: hard boot prefix {prefix['net']} lost its exact relay equation")
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
            module=original_index.modules[row['original']]
            if module!=[row['module']] or emitted_index.modules[row['original']]!=module or emitted_index.modules[row['net']]!=module:
                raise RawBranchError(f"{self.tn}: raw relay module/clock phase changed for {row['original']}")
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
        report = dict(branches=len(self.names), flops=sum(r["added_flops"] for r in self.rows),
                      consumers=dict(self.roles), status="literal source chains and relay clock phases verified; cold admission still requires actual mechanism proof")
        if self.hard_prefixes:
            depth = {}
            for prefix in self.hard_prefixes:
                depth[prefix["net"]] = 1 + depth.get(prefix["raw"], 0)
            for row in self.rows:
                depth[row["net"]] = depth.get(row["raw"], 0)
            report["hard_boot_prefix"] = dict(
                stages=self.hard_prefixes, added_data_cycles=0,
                added_boot_cycles_by_role={role: depth.get(rec["net"], 0) for role, rec in self.roles.items()})
            report["flops"] += len(self.hard_prefixes)
        return report
