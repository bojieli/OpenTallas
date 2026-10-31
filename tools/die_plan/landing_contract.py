"""Physical pin/window contracts for the opt-in regional landing infrastructure.

Like reset wavefront pins and die clock taps, these scalar endpoints are not
functional R8 buses. Ordinary port alignment/layer rules remain unchanged.
"""
import math
import re


def check(P,sidecar=None):
    """sidecar: optional compose sidecar; with it a declared START tree must equal the sidecar's (see _start_tree_check)."""
    net=P.clock.get("landing_network")
    if not net:return dict(errors=[],pins=0,edges=0,max_hop_um=0)
    errors=[];pinmap={};count=0
    for tn,t in P.types.items():
        c=t.get("clock",{}).get("landing_contract",{})
        ps={}
        for p in c.get("pins",[]):
            name=p.get("name");x,y=p.get("xy_um",[float("nan"),float("nan")]);w,h=t["outline_um"]
            if name in ps:errors.append(f"{tn}: duplicate infrastructure pin {name}")
            ps[name]=p;count+=1
            if p.get("dir") not in ("in","out") or p.get("kind") not in ("clock","ctl") or p.get("epoch") is not False:
                errors.append(f"{tn}.{name}: scalar clock/control pin without epoch required")
            if not all(math.isfinite(v) for v in (x,y)) or not (0<=x<=w and 0<=y<=h):
                errors.append(f"{tn}.{name}: pin outside its unchanged type outline")
            if p.get("layer") not in P.layers or int(p.get("layer","M99")[1:])>7:
                errors.append(f"{tn}.{name}: partition infrastructure pin must be on M7 or below")
            if p.get("kind")=="clock" and p.get("dir")=="in":
                ec=[e for e in t.get("clock",{}).get("edge_clocks",[]) if e["port"]==name]
                if len(ec)!=1 or ec[0].get("period_mult",1)!=1:errors.append(f"{tn}.{name}: declared same-frequency clock required")
        pinmap[tn]=ps
    uses={};maxhop=0
    for edge in net.get("edges",[]):
        points=[]
        if edge.get("width")!=1 or edge.get("epoch") is not False or edge.get("kind") not in ("ctl","clock"):
            errors.append(f"{edge.get('id')}: scalar clock/control infrastructure edge required")
        if edge.get("kind")=="ctl" and not (edge.get("source_registered") and edge.get("capture_registered")):
            errors.append(f"{edge.get('id')}: status hop must have registered ends")
        for side,d in (("src","out"),("dst","in")):
            e=edge[side];pn=e["part"];name=e["bus"]
            if pn not in P.parts:errors.append(f"{edge.get('id')}: real partition endpoint required");continue
            p=pinmap[P.parts[pn]["type"]].get(name)
            if not p:errors.append(f"{edge.get('id')}: missing physical {pn}.{name}");continue
            if p["dir"]!=d or p["kind"]!=edge["kind"]:errors.append(f"{edge.get('id')}: endpoint role mismatch {pn}.{name}")
            points.append(P.to_die(pn,p["xy_um"]));uses[(pn,name)]=uses.get((pn,name),0)+1
        if len(points)==2:
            hop=sum(abs(a-b) for a,b in zip(*points));maxhop=max(maxhop,hop)
            limit=float(edge.get("max_hop_um",405))
            if limit>405 or hop>limit+1e-6:errors.append(f"{edge.get('id')}: actual endpoint hop {hop:.3f}um exceeds405")
    st=net.get("start_tree")
    st_sum=None;opened=set()
    if st is not None:
        st_sum,opened=_start_tree_check(P,st,pinmap,uses,errors,sidecar)
    elif sidecar is not None and ((sidecar.get("count_aligned") or {}).get("start_pins") or {}).get("ports"):
        errors.append("start tree: sidecar count_aligned.start_pins present but the plan declares no landing_network.start_tree")
    for pn,p in P.parts.items():
        for name in pinmap[p["type"]]:
            n=uses.get((pn,name),0)
            if (pn,name) in opened:continue          # declared open START launch output (proved in _start_tree_check)
            if st is not None and name==START_PIN_OUT and n>=1:continue   # one launch pin, fanned out at the die top
            if n!=1:errors.append(f"{pn}.{name}: infrastructure pin used {n} times (no absent-child ties)")
    obs=net.get("root_observer",{})
    if obs.get("part") not in P.parts or not all(obs.get(k) for k in ("module","fault_port","ready_port")):
        errors.append("real local controller observer is required (no new external status ports)")
    return dict(errors=errors,pins=count,edges=len(net.get("edges",[])),max_hop_um=maxhop,
                physical_qualified=False,observer=obs,**({"start_tree":st_sum} if st_sum is not None else {}))


# ---- external START tree (DIE-HEAD-11 start_ports; COORD 10-28 22:37 TOK-HEAD-LAND-1 ASK2 -> DIE-HEAD-21) ----------
# A count-aligned bind with start_tree="clock" gives each region origin ONE cland_tstart_in and each launch partition ONE
# cland_tstart_out (clock_landing_plan._ca_start_pins).  Real -> real start ports are plan ports and become ordinary
# landing_network edges.  Ends at a virtual region are die-level start stages (start_stage_emit.py ot_die_start_stages:
# rs_<region> read / pst_<region> driven), wired by clock_landings.top_rtl from the sidecar count_aligned.start_pins -- NOT
# network edges, so before this declaration every such pin read "used 0 times".  They are now DECLARED in the plan
# (landing_network.start_tree, written by compose from the same start_pins) and PROVED here, in the same declare-and-prove
# form as the fstart START inputs (face_guard land_slots "starts"):
#   use  {part, pin, net}: pin is a START pin of that part's type contract (ctl, scalar, right dir); an input reads exactly
#        one pst_<region> stage net, an output drives rs_<region> stage net(s); each pst_ net lands on one origin, each
#        rs_ net has one launch partition; a pin is used once by the start tree and never also by a network edge.
#   open {part, pin}: ONLY a cland_tstart_out of a type-shared copy that launches nothing (left unconnected at the die
#        top; an unused output is not a tie).  A START INPUT is never open: an unread start input would be a tied
#        absent child, so it keeps the "used 0 times" error.
#   side: with the compose sidecar, the declaration must equal the sidecar start tree that top_rtl wires (every
#        die_inputs / die_outputs entry declared, nothing else), and every START pin of every partition is accounted for.
# An undeclared START pin with no edge still fails "used 0 times"; any error here is a landing-contract error (the
# compose report and die check FAIL on any error).
START_PIN_IN="cland_tstart_in"     # == clock_landings.START_PIN_IN == count_align_bind.START_PIN_IN
START_PIN_OUT="cland_tstart_out"   # == clock_landings.START_PIN_OUT
RAW_RESET_PIN_OUT="cland_raw_reset_out"
START_FORM="die_start_stages"
_NET={START_PIN_IN:re.compile(r"^pst_\w+$"),START_PIN_OUT:re.compile(r"^rs_\w+$"), RAW_RESET_PIN_OUT:re.compile(r"^rraw_\w+$")}


def start_declaration(start_pins,part_types,type_pins,edge_uses,raw_outputs=None):
    """landing_network.start_tree for a compose: start_pins = sidecar count_aligned.start_pins (clock_landings.start_pins),
    part_types {part: type}, type_pins {type: {pin: dir}} (landing contract pins), edge_uses {(part, pin)} already used by
    network edges.  Uses = the die-level stage ends; open = launch outputs of copies that launch nothing."""
    uses=[]
    for e in start_pins.get("die_inputs",[]):
        u=dict(part=e["src_part"],pin=START_PIN_OUT,net=e["net"])
        if u not in uses:uses.append(u)
    for e in start_pins.get("die_outputs",[]):
        uses.append(dict(part=e["dst_part"],pin=START_PIN_IN,net=e["net"]))
    uses += [dict(part=e["src_part"],pin=e.get("src_port",RAW_RESET_PIN_OUT),net=e["net"]) for e in start_pins.get("reset_inputs",[])]
    used={(u["part"],u["pin"]) for u in uses}|set(edge_uses)
    opened=[dict(part=pn,pin=START_PIN_OUT) for pn,tn in sorted(part_types.items())
            if type_pins.get(tn,{}).get(START_PIN_OUT)=="out" and (pn,START_PIN_OUT) not in used]
    opened += [dict(part=pn,pin=RAW_RESET_PIN_OUT) for pn,tn in sorted(part_types.items())
               if type_pins.get(tn,{}).get(RAW_RESET_PIN_OUT)=="out" and (pn,RAW_RESET_PIN_OUT) not in used]
    opened += [dict(part=pn,pin=pin) for pn,tn in sorted(part_types.items())
               for pin in sorted((raw_outputs or {}).get(tn,()))
               if type_pins.get(tn,{}).get(pin)=="out" and (pn,pin) not in used]
    return dict(form=START_FORM,pins=dict(input=START_PIN_IN,output=START_PIN_OUT),
                source="sidecar count_aligned.start_pins (clock_landings.top_rtl wires it)",
                uses=sorted(uses,key=lambda u:(u["part"],u["pin"],u["net"])),open=opened)


def _typed_raw_reset_output(P,tn,name,pinmap,cache):
    """Actual registered raw-wavefront producer, never a prefix-based exception."""
    if tn not in cache:
        import reset_tree as RT
        try:
            tree=RT.for_type(P,tn)
            relays=RT.start_relays(tree) if tree.get("start") else tree["relays"]
            cache[tn]={r["name"]:r for r in relays if not tree.get("start") or
                       r.get("role") in ("raw","boot","bootstrap_transport")}
        except (RT.ResetError,KeyError,ValueError,TypeError) as ex:
            cache[tn]=str(ex)
    sources=cache[tn]
    if not isinstance(sources,dict):return False,f"raw reset tree invalid: {sources}"
    rows=[r for r in P.types[tn].get("reset_start_raw_exports",[]) if r.get("port")==name and not r.get("existing_port")]
    if len(rows)!=1:return False,"not one declared raw reset export"
    row=rows[0];pin=pinmap.get(tn,{}).get(name,{})
    if (pin.get("dir"),pin.get("kind"),pin.get("source_registered"))!=("out","ctl",True):
        return False,"raw reset export requires a registered control OUTPUT"
    source=sources.get(row.get("instance"))
    def same_xy(a,b):
        return len(a or ())==len(b or ())==2 and all(abs(x-y)<=1e-6 for x,y in zip(a,b))
    if source is None or source.get("q")!=row.get("net") or not same_xy(source.get("xy"),row.get("xy_um")):
        return False,"raw reset export source instance/net/xy differs from actual reset tree"
    # The physical output pin is track-snapped and may be de-duplicated beside
    # this raw FF. Source coordinates stay exact above; ordinary pin/GEOM gates
    # continue to judge the separate pin location and pin-to-register distance.
    if pin.get("source_instance")!=row["instance"]:
        return False,"raw reset export pin source differs from declaration"
    if P.types[tn].get("private_reset_start_exports"):
        if (pin.get("source_net"),pin.get("source_copy_from_net"),pin.get("source_output_pin"))!=(name,row["net"],"export_q"):
            return False,"raw reset private output does not copy the declared raw source"
    elif pin.get("source_net")!=row["net"]:
        return False,"raw reset export pin net differs from actual source"
    return True,None


def _start_tree_check(P,st,pinmap,uses,errors,side):
    """prove the declared START tree; adds its uses into `uses`; -> (summary, {(part, pin)} declared open)."""
    def bad(m):errors.append("start tree: "+m)
    if not isinstance(st,dict) or st.get("form")!=START_FORM:
        bad(f"form {st.get('form') if isinstance(st,dict) else st!r} (want {START_FORM})");return dict(uses=0,open=0),set()
    if set(st)-{"form","pins","source","uses","open","provider","reset_source"}:bad(f"unknown keys {sorted(set(st)-{'form','pins','source','uses','open','provider','reset_source'})}")
    if st.get("pins",dict(input=START_PIN_IN,output=START_PIN_OUT))!=dict(input=START_PIN_IN,output=START_PIN_OUT):
        bad(f"pins {st.get('pins')} (want input {START_PIN_IN}, output {START_PIN_OUT})")
    provider_summary=None
    if "provider" in st:
        import start_provider_plan as SP
        try:
            proof=SP.check(P,st["provider"])
            provider_summary={k:v for k,v in proof.items() if k!="errors"}
            for message in proof["errors"]:bad(message)
        except (KeyError,ValueError,TypeError,StopIteration) as ex:
            bad(f"invalid physical provider contract: {ex}")
    reset_summary=None
    if "reset_source" in st:
        import reset_route as RR
        reset_summary=RR.check_provider_root(P,st["reset_source"],st.get("provider"))
        for message in reset_summary["errors"]:bad(message)
    want={START_PIN_IN:"in",START_PIN_OUT:"out",RAW_RESET_PIN_OUT:"out"}
    edge_used={k for k,v in uses.items() if v}
    raw_cache={};raw_outputs={}
    seen=set();declared=set();net_parts={};n_ok=0

    def pin_ok(pn,pin,what):
        if pn not in P.parts:
            bad(f"{what} {pn}.{pin}: not a plan partition");return False
        if pin not in want:
            tn=P.parts[pn]["type"]
            if not any(r.get("port")==pin for r in P.types[tn].get("reset_start_raw_exports",[])):
                bad(f"{what} {pn}.{pin}: only {START_PIN_IN}/{START_PIN_OUT} or declared raw outputs are START-tree pins");return False
            good,why=_typed_raw_reset_output(P,tn,pin,pinmap,raw_cache)
            if not good:bad(f"{what} {pn}.{pin}: {why}");return False
            raw_outputs.setdefault(tn,set()).add(pin)
        p=pinmap[P.parts[pn]["type"]].get(pin)
        if not p:
            bad(f"{what} {pn}.{pin}: type {P.parts[pn]['type']} has no such landing-contract pin");return False
        if p.get("dir")!=want.get(pin,"out") or p.get("kind")!="ctl":
            bad(f"{what} {pn}.{pin}: dir/kind {p.get('dir')}/{p.get('kind')} (want {want.get(pin,'out')}/ctl)");return False
        # A real registered launch may fan out to a direct real child and
        # to virtual START stages. A capture input still has exactly one source;
        # an open output cannot simultaneously drive any edge.
        if (pn,pin) in edge_used and not (what == "use" and pin == START_PIN_OUT):
            bad(f"{what} {pn}.{pin}: also used by a landing_network edge");return False
        return True
    for u in st.get("uses") or []:
        pn,pin,nt=u.get("part"),u.get("pin"),u.get("net")
        if (pn,pin,nt) in seen:bad(f"use {pn}.{pin} -> {nt}: declared twice");continue
        seen.add((pn,pin,nt))
        if not pin_ok(pn,pin,"use"):continue
        raw_net="wr_"+re.sub(r"[^A-Za-z0-9_]","_",pn)+"__"+str(pin)
        if not isinstance(nt,str) or (not _NET[pin].match(nt) if pin in _NET else nt!=raw_net):
            bad(f"use {pn}.{pin}: net {nt!r} is not a die start-stage {'pst_' if pin==START_PIN_IN else 'rs_'}<region> net");continue
        if (pn,pin) in declared:
            bad(f"use {pn}.{pin}: on more than one stage net (one start wire per pin)");continue
        net_parts.setdefault(nt,set()).add(pn)
        declared.add((pn,pin));uses[(pn,pin)]=uses.get((pn,pin),0)+1
        n_ok+=1
    for nt,ps in sorted(net_parts.items()):
        if len(ps)!=1:bad(f"stage net {nt} on {len(ps)} partitions {sorted(ps)[:3]} (want one {'origin' if nt.startswith('pst_') else 'launch partition'})")
    opened=set()
    for o in st.get("open") or []:
        pn,pin=o.get("part"),o.get("pin")
        if pin==START_PIN_IN:
            bad(f"open {pn}.{pin}: a START input cannot be open (unread start = tied absent child)");continue
        if not pin_ok(pn,pin,"open"):continue
        if (pn,pin) in declared or (pn,pin) in opened:
            bad(f"open {pn}.{pin}: also declared used / open twice");continue
        opened.add((pn,pin))
    if side is not None:
        sp=(side.get("count_aligned") or {}).get("start_pins")
        if not sp:
            bad("sidecar has no count_aligned.start_pins to prove the declaration against")
        else:
            for tn,t in P.types.items():
                for row in t.get("reset_start_raw_exports",[]):
                    if row.get("existing_port"):continue
                    good,why=_typed_raw_reset_output(P,tn,row.get("port"),pinmap,raw_cache)
                    if good:raw_outputs.setdefault(tn,set()).add(row["port"])
                    else:bad(f"{tn}.{row.get('port')}: {why}")
            exp=start_declaration(sp,{pn:p["type"] for pn,p in P.parts.items()},
                                  {tn:{n:q.get("dir") for n,q in ps.items()} for tn,ps in pinmap.items()},edge_used,raw_outputs)
            got_u={(u.get("part"),u.get("pin"),u.get("net")) for u in st.get("uses") or []}
            exp_u={(u["part"],u["pin"],u["net"]) for u in exp["uses"]}
            for x in sorted(exp_u-got_u)[:20]:bad(f"sidecar start-tree end {x[0]}.{x[1]} -> {x[2]} not declared")
            for x in sorted(got_u-exp_u)[:20]:bad(f"declared use {x[0]}.{x[1]} -> {x[2]} not in the sidecar start tree")
            got_o={(o.get("part"),o.get("pin")) for o in st.get("open") or []}
            exp_o={(o["part"],o["pin"]) for o in exp["open"]}
            for x in sorted(got_o^exp_o)[:20]:bad(f"open {x[0]}.{x[1]}: declaration != sidecar start tree")
    return dict(uses=n_ok,open=len(opened),stage_nets=len(net_parts),
                **({"physical_provider":provider_summary} if provider_summary is not None else {}),
                **({"local_root_reset":{k:v for k,v in reset_summary.items() if k!="errors"}} if reset_summary is not None else {})),opened


def on_track(P,layer,x,y):
    """FLOW-KITFAIL-2 10-29 (DIE-HEAD-34: hd_mesh_e rst_start_raw_0/1 DRT-0255 twice at x 558.72 = half an M7 pitch
    off the plan track 558.752): a landing pin is drawn as a narrow rectangle on its layer, so its crossing coordinate
    (x of a vertical layer, y of a horizontal one) must sit on a plan track (offset + k * pitch, make_tracks.tcl).
    Snap it to the nearest track; a pin already on a track keeps its exact coordinate (byte-identical io.tcl)."""
    L=getattr(P,"layers",{}).get(layer)
    if not L or not L.get("pitch_um"):return x,y
    def snap(v):
        k=round((v-L["offset_um"])/L["pitch_um"])
        q=round(L["offset_um"]+k*L["pitch_um"],4)
        return v if abs(q-v)<5e-5 else q
    return (snap(x),y) if L.get("dir")=="V" else (x,snap(y))


def io_tcl(P,tn):
    t=P.types[tn];c=t.get("clock",{}).get("landing_contract",{})
    input_clocks={e["port"] for e in t.get("clock",{}).get("edge_clocks",[])}
    out=[]
    for p in c.get("pins",[]):
        if p["name"] in input_clocks:continue # existing edge_clock_pins handles these
        x,y=on_track(P,p["layer"],*p["xy_um"])
        out.append(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{x:.4f} {y:.4f}}} "
                   "-pin_size {0.0800 0.4320} ;# real scalar landing infrastructure pin")
    return "\n".join(out)+("\n" if out else "")


def data_output_selectors(P,tn):
    """Actual non-clock output ports, including landed status/start wires.

    Explicit collections work in OpenSTA; Synopsys collection operators do not.
    """
    import gen_phys
    import gen_rtl
    t=P.types[tn]
    out=[gen_rtl.sv_id(b['name'])+'[*]' for b in t.get('buses',[]) if b['dir']=='out']
    out += [gen_rtl.sv_id(sl['name']+'_o')+'[*]' for sl in t.get('ft_slots',[])]
    out += [p['name']+('[*]' if int(p.get('width',1))>1 else '') for p in t.get('pads',[])
            if p.get('dir')=='out' and not p.get('clock',False)]
    out += [name for name,_x,_y in gen_phys.reset_out_pins(P,tn)]
    out += [p['name'] for p in t.get('clock',{}).get('landing_contract',{}).get('pins',[])
            if p['dir']=='out' and p['kind']!='clock']
    return list(dict.fromkeys(out))


def sdc(P,tn,text):
    c=P.types[tn].get("clock",{}).get("landing_contract",{})
    if not c:return text
    exports=[p for p in c["pins"] if p["kind"]=="clock" and p["dir"]=="out"]
    if exports:
        selectors=" ".join(data_output_selectors(P,tn))
        text=text.replace("[all_outputs]","$cland_data_outputs")
        text=f"set cland_data_outputs [get_ports {{{selectors}}}]\n"+text
        for p in exports:
            text+=f"create_generated_clock -name {p['name']} -master_clock clk -source [get_ports {p['source_clock_port']}] -divide_by 1 [get_ports {p['name']}]\n"
    # Same existing meso ring phase-window law, at exactly833ps. No clock
    # groups, false paths or clock relaxation. Physical clock/export/RC gates
    # still qualify the actual ring; these are its timing constraints.
    # COORD 10-31 (OWNER 12.24c follow-up): full half-period window; OT_MARGIN_POLICY=legacy keeps T/2-60 (A/B),
    # same law as sdc_lint.landing_window_setup_ps()
    import os
    window=float(P.die["period_ps"])/2-(60.0 if os.environ.get("OT_MARGIN_POLICY","nominal").strip().lower()=="legacy" else 0.0)
    for p in c["pins"]:
        if p["kind"]!="clock" or p["dir"]!="in":continue
        n=p["name"]
        for a,b in ((n,"clk"),("clk",n)):
            text+=f"set_max_delay -ignore_clock_latency {window:.4f} -from [get_clocks {a}] -to [get_clocks {b}]\n"
            text+=f"set_min_delay -ignore_clock_latency 0 -from [get_clocks {a}] -to [get_clocks {b}]\n"
    return text+ring_input_sdc(P,tn)


RING_INPUTS_TAG="# OT_FWD_RING_INPUTS"


def ring_input_ports(P,tn):
    """[(forwarded clock, [input port selectors])]: the inputs a landing ring writes on its forwarded clock.

    clock_landings.py emits u_cland_<b> with .fclk(fclk_in_<b>) and .d(<b>) (dataflow form: .d({cland_dn_fault_<b>,
    cland_dn_ready_<b>, <b>})), so these ports are captured by fclk_in_<b>, never by the local clk.  A band whose
    bus is not an input port of the type fails closed.  Empty when the type has no forwarded input ring."""
    import gen_rtl
    t=P.types[tn];c=t.get("clock",{}).get("landing_contract",{})
    pins={p["name"]:p for p in c.get("pins",[])}
    widths={gen_rtl.sv_id(b["name"]):int(b.get("width",1)) for b in t.get("buses",[]) if b["dir"]=="in"}
    widths.update({gen_rtl.sv_id(sl["name"]+"_i"):2 for sl in t.get("ft_slots",[])})   # ft slots are vectors
    out=[]
    for b in sorted(c.get("bands",{})):
        ck=f"fclk_in_{b}"
        if pins.get(ck,{}).get("kind")!="clock" or pins[ck].get("dir")!="in":continue
        if b not in widths:raise ValueError(f"{tn}: landing band {b} has forwarded clock {ck} but no input port {b}")
        sel=[b+("[*]" if widths[b]>1 else "")]
        sel+=[n for n in (f"cland_dn_ready_{b}",f"cland_dn_fault_{b}") if pins.get(n,{}).get("dir")=="in"]
        out.append((ck,sel))
    return out


def ring_input_sdc(P,tn):
    """DIE-HEAD-36 (COORD 10-29 21:11 ruling (3)): source-synchronous ring inputs are timed against the forwarded
    write clock that captures them, not the local virtual IO clock vclk.  The sender's fclk_out leaves from its clk
    leaf net beside the launching flops, so the sender insertion cancels; the same IO budget values (max: ft hop /
    IO budget + tap-window shift; min: the plan's seam-hold input min) are re-referenced to fclk_in_<b>.  OpenSTA
    replaces a port's input delays when set_input_delay names another clock without -add_delay, so these lines must
    come last.  The die STA prices the crossing itself (die_sta_related ca_ring writer clock)."""
    rows=ring_input_ports(P,tn)
    if not rows:return ""
    import gen_phys as G
    import gen_rtl
    per=G.t_lib(P.die["period_ps"]);tw_in,_=G.tap_window_io_shift(P, tn)
    ft={gen_rtl.sv_id(sl["name"]+"_i") for sl in P.types[tn].get("ft_slots",[])}
    A=G.input_hold_min(P,tn)
    dd=G.die_sta_hold_demand(P,tn) or {}
    out=[]
    for ck,sel in rows:
        if any(s.split("[")[0] in (dd.get("inputs") or {}) for s in sel):
            raise ValueError(f"{tn}: forwarded ring input with die_sta per-bit hold demand (unsupported, fail closed)")
        out.append(f"{RING_INPUTS_TAG} {ck} {' '.join(sel)}")
        for s in sel:
            bus=s.split("[")[0]
            mx=((1-G.ft_hop_in_share(P))*per if bus in ft else G.IO_BUDGET*per)+G.t_lib(tw_in)
            mn=A[bus]["in_min_ps"] if bus in A else G.hold_in_min_ps(P)
            out.append(f"set_input_delay -max {mx:.4f} -clock {ck} [get_ports {{{s}}}]")
            out.append(f"set_input_delay -min {G.t_lib(mn):.4f} -clock {ck} [get_ports {{{s}}}]")
    return ("# source-synchronous ring inputs (COORD 10-29 21:11): timed against their forwarded write clock, "
            "not vclk (landing_contract.ring_input_sdc)\n"+"\n".join(out)+"\n")


_VEC1=re.compile(r"^\s*(?:input|output|inout)\s+(?:wire\s+|logic\s+)?\[0:0\]\s+(\w+)",re.M)


def bit0_ports(wrapper_text):
    """Ports a kit wrapper declares as a one-bit VECTOR [0:0] (bind.py kit-rtl bound-only pins, e.g. kv3_sys_SD
    fclk_out_o_serdes_W_rx_flit): OpenROAD names their BTerm "<port>[0]", not "<port>" (KV-022 CTS 'clock landing
    export endpoint missing').  Scalar ports are not listed, so their findBTerm text stays byte-identical."""
    return frozenset(_VEC1.findall(wrapper_text))


def _bterm(n,bit0):
    return f"{n}[0]" if n in bit0 else n


def export_tcl(P,tn,bit0=frozenset()):
    """Attach a forwarded output to its declared real tap BEFORE CTS.

    The receiver builds the same local clock-latency contract under this
    forwarded root; data source and receiver write trees are measured in the
    physical gate. No fictional wire latency is added to STA.
    """
    pins=P.types[tn].get("clock",{}).get("landing_contract",{}).get("pins",[])
    if export_form(P,tn)=="fwd_buffer":return export_tcl_fwd(P,tn,bit0)
    out=["set cland_block [ord::get_db_block]"]
    for p in pins:
        if p["kind"]!="clock" or p["dir"]!="out":continue
        out += [f"set cland_dst [$cland_block findBTerm {{{_bterm(p['name'],bit0)}}}]",
                f"set cland_src [$cland_block findBTerm {{{_bterm(p['source_clock_port'],bit0)}}}]",
                'if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }',
                "set cland_net [$cland_src getNet]",
                'if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }',
                "$cland_dst disconnect", "$cland_dst connect $cland_net", "$cland_net setSigType CLOCK",
                f"puts {{OT_CLAND_EXPORT {p['name']} <- {p['source_clock_port']}}}"]
    return "\n".join(out)+"\n"


FWD_BUFFER_MASTER="BUFx24_ASAP7_75t_R"


def export_form(P,tn):
    """clock.landing_export_form: "fwd_buffer" (DEFAULT since AUTOBUILD-PIPE-3 10-31, FLOW-GEN-2 CTS-0114 form) or
    "tie" (explicit legacy: the forwarded output BTerm joins the source tap net).

    Why the default moved: kit sdc() always declares a divide_by 1 generated clock on every exported port, and with
    the port tied onto the source tap net TritonCTS stops with CTS-0114 "overlaps a previous clock" on EVERY such kit
    (DIE-HEAD-14 hd_tile, DIE-KV-49 kv3_sys_SD, and all 3 S81 station wave kits that reached CTS 10-31: t23,
    t30__clcedefe91, t24__cleece78ec). 187/188 S81 plan types with a forwarded clock output did not set the opt-in, so
    the automatic wave could not reach route. A plan that really wants the tie text sets "tie" explicitly."""
    form=P.types[tn].get("clock",{}).get("landing_export_form","fwd_buffer")
    if form not in ("tie","fwd_buffer"):raise ValueError(f"{tn}: clock.landing_export_form {form!r}")
    return form


def export_tcl_fwd(P,tn,bit0=frozenset()):
    """FLOW-GEN-2 CTS-0114 (clock.landing_export_form = "fwd_buffer", the default; see export_form).

    The legacy form ties the forwarded output BTerm onto the source tap net. TritonCTS then sees the port's divide_by 1
    generated clock on the clk root net (CTS-0114 "overlaps a previous clock"), and the root net stretches to the far
    export pin: repair buffers it as a wire and tree roots / sinks along it (DIE-HEAD-15: 8 reset relay flops at
    290 ps, DIE-HEAD-17: the eB core branch root) end up outside the balanced tree. Here the output gets its OWN net,
    driven by one buffer placed at the source tap (clamped into the core; CTS DPL legalises it). Its input is a
    non-register load of the source net, which TritonCTS keeps at the root, so the source net stays local. The
    synthesized forward driver (assign fclk_out = clk -> BUF, ORFS output buffer) that drives nothing after the move is
    removed; a non-buffer driver fails closed. The SDC generated clock on the port is unchanged."""
    pins=P.types[tn].get("clock",{}).get("landing_contract",{}).get("pins",[])
    out=["set cland_block [ord::get_db_block]",
         "proc ot_cland_drop_orphan {net} {",
         "  while {$net ne \"NULL\" && ![llength [$net getBTerms]]} {",
         "    set loads 0; set drv {}",
         "    foreach it [$net getITerms] { if {[$it isOutputSignal]} {lappend drv $it} elseif {[$it isInputSignal]} {incr loads} }",
         "    if {$loads || [llength $drv] != 1} return",
         "    set inst [[lindex $drv 0] getInst]",
         "    if {![string match \"BUF*\" [[$inst getMaster] getName]]} { error \"OT_CLAND_EXPORT forwarded driver [$inst getName] is not a buffer\" }",
         "    set up \"NULL\"; foreach it [$inst getITerms] { if {[$it isInputSignal]} {set up [$it getNet]} }",
         "    puts \"OT_CLAND_EXPORT drop orphan forward driver [$inst getName] ([[$inst getMaster] getName])\"",
         "    odb::dbInst_destroy $inst; odb::dbNet_destroy $net",
         "    set net $up",
         "  }",
         "}",
         f"set cland_m [[ord::get_db] findMaster {{{FWD_BUFFER_MASTER}}}]",
         'if {$cland_m eq "NULL"} { error "OT_CLAND_EXPORT forward buffer master missing" }',
         "set cland_ca [$cland_block getCoreArea]"]
    for p in pins:
        if p["kind"]!="clock" or p["dir"]!="out":continue
        n,s=p["name"],p["source_clock_port"];fw="cland_fwd_"+n
        out += [f"set cland_dst [$cland_block findBTerm {{{_bterm(n,bit0)}}}]",
                f"set cland_src [$cland_block findBTerm {{{_bterm(s,bit0)}}}]",
                'if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }',
                "set cland_net [$cland_src getNet]",
                'if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }',
                f'if {{[$cland_block findInst {{{fw}}}] ne "NULL"}} {{ error "OT_CLAND_EXPORT {fw} exists" }}',
                "set cland_old [$cland_dst getNet]",
                "$cland_dst disconnect",
                'if {$cland_old ne "NULL" && $cland_old ne $cland_net} { ot_cland_drop_orphan $cland_old }',
                f"set cland_i [odb::dbInst_create $cland_block $cland_m {{{fw}}}]",
                "set cland_bb [$cland_src getBBox]",
                "set cland_x [expr {min(max(([$cland_bb xMin] + [$cland_bb xMax]) / 2, [$cland_ca xMin]), [$cland_ca xMax] - [$cland_m getWidth])}]",
                "set cland_y [expr {min(max(([$cland_bb yMin] + [$cland_bb yMax]) / 2, [$cland_ca yMin]), [$cland_ca yMax] - [$cland_m getHeight])}]",
                "$cland_i setLocation $cland_x $cland_y; $cland_i setPlacementStatus PLACED",
                "[$cland_i findITerm A] connect $cland_net",
                f"set cland_fn [odb::dbNet_create $cland_block {{{fw}}}]",
                "[$cland_i findITerm Y] connect $cland_fn",
                "$cland_dst connect $cland_fn",
                "$cland_net setSigType CLOCK; $cland_fn setSigType CLOCK",
                f"puts {{OT_CLAND_EXPORT {n} <- {s} via {fw} ({FWD_BUFFER_MASTER} at the source)}}"]
    return "\n".join(out)+"\n"
