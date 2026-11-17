"""Opt-in physical minimum delay before a synchronous reset/START entry.

Every chain has explicit input-to-capture cell sites and its priced maximum hop.
The function is an identity, with no added FF or whole-cycle latency. Timing and
boot/count-window qualification remain on the actual routed type/phase class.
"""
import copy,math

CELL='BUFx4_ASAP7_75t_R'
CELL_RTL='''(* keep_hierarchy, keep *)
module ot_dp_rrelay_delay #(parameter integer N=1) (input wire clk,input wire d,output reg q);
    (* keep *) wire [N:0] p;
    assign p[0]=d;
    generate for(genvar i=0;i<N;i=i+1) begin:g_delay
`ifdef SYNTHESIS
        (* keep, dont_touch *) BUFx4_ASAP7_75t_R u_delay(.A(p[i]),.Y(p[i+1]));
`else
        assign p[i+1]=p[i];
`endif
    end endgenerate
    always @(posedge clk) q<=p[N];
endmodule
'''


def uses(raw):
    return any(isinstance(s,dict) and (s.get('reset',0) or s.get('start',0))
               for t in (raw.get('partition_types') or {}).values()
               for s in [t.get('reset',{}).get('pin_entry_delay')])


def configure(P,tn,T,error=ValueError):
    spec=P.types[tn].get('reset',{}).get('pin_entry_delay')
    if spec is None:return T
    keys={'cell','reset','start','reset_sites_um','start_sites_um','max_hop_um'}
    if not isinstance(spec,dict) or set(spec)!=keys or spec.get('cell')!=CELL:
        raise error(f'type {tn}: pin_entry_delay requires exact BUFx4 counts, sites and max_hop_um')
    if T.get('entry')!='relayed':raise error('pin_entry_delay needs a synchronous relayed entry')
    if T.get('pin_entry_fall'):raise error('pin_entry_delay plus falling entry has no composed phase model')
    if T.get('pin_root_copies') or T.get('pin_start_copies'):
        raise error('pin_entry_delay copies need their own measured input paths')
    bound=spec['max_hop_um']
    if isinstance(bound,bool) or not isinstance(bound,(int,float)) or not math.isfinite(bound) or bound<=0:
        raise error('pin_entry_delay max_hop_um must be finite positive')
    w,h=P.types[tn]['outline_um']
    for sig in ['reset','start']:
        n=spec[sig];sites=spec[sig+'_sites_um']
        if type(n)is not int or n<0 or not isinstance(sites,list) or len(sites)!=n:
            raise error(f'pin_entry_delay {sig} count/sites disagree')
        if sig=='start' and n and not T.get('start'):raise error('pin_entry_delay START needs a broadcast input')
        for xy in sites:
            if (not isinstance(xy,(list,tuple)) or len(xy)!=2 or
                any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in xy) or
                not (0<=xy[0]<=w and 0<=xy[1]<=h)):
                raise error('pin_entry_delay sites must be finite in-outline input-to-capture coordinates')
        if any(abs(a[0]-b[0])+abs(a[1]-b[1])>bound+1e-8 for a,b in zip(sites,sites[1:])):
            raise error('pin_entry_delay declared site hop exceeds its priced bound')
    return dict(T,pin_entry_delay=copy.deepcopy(spec))


def entry_cell(T,signal):
    if T.get('pin_entry_handoff'):return 'ot_dp_rrelay_handoff'
    n=(T.get('pin_entry_delay') or {}).get(signal,0)
    if n:return f'ot_dp_rrelay_delay #(.N({n}))'
    return 'ot_dp_rrelay_fn' if T.get('pin_entry_fall') else 'ot_dp_rrelay'


def summary(T):
    s=T.get('pin_entry_delay')
    return {} if not s else dict(pin_entry_delay=dict(cell=CELL,buffers=s['reset']+s['start'],
                         added_flops=0,added_whole_cycles=0,area_um2=(s['reset']+s['start'])*.10206,
                         sites_order='input_to_capture',max_hop_um=s['max_hop_um']))


PLACE_TCL=r'''
# Explicit technology-buffer sites, in data-flow order. Never let a placement
# heuristic permute a minimum-delay chain or silently exceed its priced pitch.
proc ot_pin_entry_delay_xy {it} {
    set xy [$it getAvgXY]
    if {[llength $xy]==3 && [lindex $xy 0]} {return [lrange $xy 1 2]}
    if {[llength $xy]==2} {return $xy}
    error "PIN_ENTRY_DELAY no exact pin centre"
}
proc ot_pin_entry_delay_place {entry count sites maxhop boxes_um} {
    global ff_blk ff_dbu
    set cells [dict create];set captures {}
    foreach i [$ff_blk getInsts] {
        set nm [string map {\\[ [ \\] ]} [$i getName]]
        set pattern [format {(^|[/.])%s[/.]} $entry]
        if {![regexp $pattern $nm]} continue
        if {[string match *DFF* [[$i getMaster] getName]]} {lappend captures $i}
        if {[regexp {g_delay\[([0-9]+)\][/.]u_delay$} $nm -> k]} {
            if {[[$i getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "PIN_ENTRY_DELAY wrong technology master"}
            if {[dict exists $cells $k]} {error "PIN_ENTRY_DELAY duplicated stage $k"}
            dict set cells $k $i
        }
    }
    if {[dict size $cells]!=$count || [llength $captures]!=1 || [llength $sites]!=$count} {
        error "PIN_ENTRY_DELAY missing cells/capture/site: $entry $count [dict size $cells] [llength $captures]"
    }
    set own [dict create]
    dict for {k i} $cells {dict set own [$i getName] 1}
    set boxes {};set placements {}
    for {set k 0} {$k<$count} {incr k} {
        if {![dict exists $cells $k]} {error "PIN_ENTRY_DELAY missing index $k"}
        set i [dict get $cells $k];set master [$i getMaster]
        lassign [lindex $sites $k] x y;set x [expr {round($x*$ff_dbu)}];set y [expr {round($y*$ff_dbu)}]
        set w [$master getWidth];set h [$master getHeight];set legal 0;set orient R0
        foreach row [$ff_blk getRows] {
            lassign [$row getOrigin] rx ry
            set site [$row getSite];set sw [$site getWidth];set sh [$site getHeight];set bb [$row getBBox]
            if {$y==$ry && $x>=[$bb xMin] && $x+$w<=[$bb xMax] && $h<=$sh && ($x-$rx)%$sw==0} {
                set legal 1;set orient [$row getOrient];break
            }
        }
        if {!$legal} {error "PIN_ENTRY_DELAY site not on a legal row: $entry $k"}
        set box [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
        foreach other $boxes {
            lassign $other a b c d
            if {$x<$c && $x+$w>$a && $y<$d && $y+$h>$b} {error "PIN_ENTRY_DELAY overlapping planned chain sites"}
        }
        lappend boxes $box
        foreach obstacle $boxes_um {
            lassign $obstacle a b c d
            set a [expr {$a*$ff_dbu}];set b [expr {$b*$ff_dbu}];set c [expr {$c*$ff_dbu}];set d [expr {$d*$ff_dbu}]
            if {$x<$c && $x+$w>$a && $y<$d && $y+$h>$b} {error "PIN_ENTRY_DELAY site intrudes macro halo"}
        }
        foreach other [$ff_blk getInsts] {
            if {[dict exists $own [$other getName]]} continue
            if {[$other getPlacementStatus] ni {FIRM LOCKED} && [[$other getMaster] getType] ne "BLOCK"} continue
            set q [$other getBBox]
            if {$x<[$q xMax] && $x+$w>[$q xMin] && $y<[$q yMax] && $y+$h>[$q yMin]} {
                error "PIN_ENTRY_DELAY site overlaps fixed instance [$other getName]"
            }
        }
        lappend placements [list $i $x $y $orient]
    }
    foreach row $placements {
        lassign $row i x y orient;$i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus FIRM
    }
    set tail [lindex $captures 0];lassign [$tail getLocation] tx ty
    set worst 0.0;set total 0.0
    for {set k 0} {$k<$count} {incr k} {
        set i [dict get $cells $k];lassign [ot_pin_entry_delay_xy [$i findITerm Y]] x y
        if {$k+1<$count} {
            set next [dict get $cells [expr {$k+1}]]
            lassign [ot_pin_entry_delay_xy [$next findITerm A]] nx ny
        } else {lassign [ot_pin_entry_delay_xy [$tail findITerm D]] nx ny}
        set hop [expr {(abs($nx-$x)+abs($ny-$y))/double($ff_dbu)}]
        set total [expr {$total+$hop}];set worst [expr {max($worst,$hop)}]
        if {$hop>$maxhop+1e-6} {error "PIN_ENTRY_DELAY actual ordered hop $hop exceeds $maxhop at $entry/$k"}
    }
    puts "PIN_ENTRY_DELAY $entry count $count master BUFx4_ASAP7_75t_R ordered_max_hop_um $worst total_um $total flops_added 0 cycles_added 0"
}
'''


def placement_tcl(T):
    s=T.get('pin_entry_delay')
    if not s:return ''
    out=[PLACE_TCL]
    for sig,entry in [('reset','u_rst_in'),('start','u_run_in')]:
        if not s[sig]:continue
        sites=' '.join('{'+f'{x:.9g} {y:.9g}'+'}' for x,y in s[sig+'_sites_um'])
        boxes=' '.join('{'+ ' '.join(f'{v:.9g}' for v in b)+'}' for b in T.get('pin_entry_delay_blockages',[]))
        out.append(f'ot_pin_entry_delay_place {entry} {s[sig]} {{{sites}}} {s["max_hop_um"]:.9g} {{{boxes}}}')
    return '\n'.join(out)+'\n'
