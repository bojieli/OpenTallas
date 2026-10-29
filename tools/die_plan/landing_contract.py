"""Physical pin/window contracts for the opt-in regional landing infrastructure.

Like reset wavefront pins and die clock taps, these scalar endpoints are not
functional R8 buses. Ordinary port alignment/layer rules remain unchanged.
"""
import math


def check(P):
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
    for pn,p in P.parts.items():
        for name in pinmap[p["type"]]:
            n=uses.get((pn,name),0)
            if n!=1:errors.append(f"{pn}.{name}: infrastructure pin used {n} times (no absent-child ties)")
    obs=net.get("root_observer",{})
    if obs.get("part") not in P.parts or not all(obs.get(k) for k in ("module","fault_port","ready_port")):
        errors.append("real local controller observer is required (no new external status ports)")
    return dict(errors=errors,pins=count,edges=len(net.get("edges",[])),max_hop_um=maxhop,
                physical_qualified=False,observer=obs)


def io_tcl(P,tn):
    t=P.types[tn];c=t.get("clock",{}).get("landing_contract",{})
    input_clocks={e["port"] for e in t.get("clock",{}).get("edge_clocks",[])}
    out=[]
    for p in c.get("pins",[]):
        if p["name"] in input_clocks:continue # existing edge_clock_pins handles these
        x,y=p["xy_um"]
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
    window=float(P.die["period_ps"])/2-60
    for p in c["pins"]:
        if p["kind"]!="clock" or p["dir"]!="in":continue
        n=p["name"]
        for a,b in ((n,"clk"),("clk",n)):
            text+=f"set_max_delay -ignore_clock_latency {window:.4f} -from [get_clocks {a}] -to [get_clocks {b}]\n"
            text+=f"set_min_delay -ignore_clock_latency 0 -from [get_clocks {a}] -to [get_clocks {b}]\n"
    return text


def export_tcl(P,tn):
    """Attach a forwarded output to its declared real tap BEFORE CTS.

    The receiver builds the same local clock-latency contract under this
    forwarded root; data source and receiver write trees are measured in the
    physical gate. No fictional wire latency is added to STA.
    """
    pins=P.types[tn].get("clock",{}).get("landing_contract",{}).get("pins",[])
    if export_form(P,tn)=="fwd_buffer":return export_tcl_fwd(P,tn)
    out=["set cland_block [ord::get_db_block]"]
    for p in pins:
        if p["kind"]!="clock" or p["dir"]!="out":continue
        out += [f"set cland_dst [$cland_block findBTerm {{{p['name']}}}]",
                f"set cland_src [$cland_block findBTerm {{{p['source_clock_port']}}}]",
                'if {$cland_dst eq "NULL" || $cland_src eq "NULL"} { error "clock landing export endpoint missing" }',
                "set cland_net [$cland_src getNet]",
                'if {$cland_net eq "NULL"} { error "clock landing source tap has no physical net" }',
                "$cland_dst disconnect", "$cland_dst connect $cland_net", "$cland_net setSigType CLOCK",
                f"puts {{OT_CLAND_EXPORT {p['name']} <- {p['source_clock_port']}}}"]
    return "\n".join(out)+"\n"


FWD_BUFFER_MASTER="BUFx24_ASAP7_75t_R"


def export_form(P,tn):
    """clock.landing_export_form: "tie" (default, legacy: the forwarded output BTerm joins the source tap net) or
    "fwd_buffer" (FLOW-GEN-2 CTS-0114, opt-in)."""
    form=P.types[tn].get("clock",{}).get("landing_export_form","tie")
    if form not in ("tie","fwd_buffer"):raise ValueError(f"{tn}: clock.landing_export_form {form!r}")
    return form


def export_tcl_fwd(P,tn):
    """FLOW-GEN-2 CTS-0114 (opt-in clock.landing_export_form = "fwd_buffer").

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
        out += [f"set cland_dst [$cland_block findBTerm {{{n}}}]",
                f"set cland_src [$cland_block findBTerm {{{s}}}]",
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
