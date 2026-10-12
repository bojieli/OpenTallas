#!/usr/bin/env python3
"""MARGIN 3 face plan for ot_dsrom_window_source_ctl and its hardened leaves (el1011-ds-misc 2026-10-11).
Prints one --pin-region argument per line.  usage: pinplan_m3.py top|land8|mirror DIE_X DIE_Y
top (540 x 540): W = clk (mid-face) + rst_n + config / prime / blk / start / stage / merge / status;
  S = acc_* / wl_req_* lanes 0-15; N = lanes 16-31 (each lane's issue + landing pins on one face); E = K-port request m_* (1.4k); the dead K-port response s_* (1.1k) on S.
  Measured edge capacity (PPL-0107 in flat-e29a7cacf / -a012105f0 / land8-670ed3c2a): ~2.55 pins/um on the W/E edges
  (M4+M6), ~12.2 pins/um on the N/S edges (M5+M7) -> die 620: S 6.3k / 7.3k, N 5.2k, E 1.36k / 1.53k, W 0.7k.
land8: acc inputs S, clk / rst_n / b / outputs N (140.4 x 43.224 um).
mirror: write command W, reads S, bad E, clk N."""
import sys
def rr(lo, hi):
    """regex alternation matching decimal integers lo..hi (no leading zeros)."""
    out=[]
    def rec(lo,hi):
        if lo>hi: return
        sl,sh=str(lo),str(hi)
        if len(sl)<len(sh):
            rec(lo,10**len(sl)-1); rec(10**len(sl),hi); return
        # same length
        n=len(sl)
        for k in range(n,0,-1):
            pass
        # split by common prefix
        i=0
        while i<n and sl[i]==sh[i]: i+=1
        if i==n: out.append(sl); return
        tail=n-i-1
        if sl[i+1:]=='0'*tail and sh[i+1:]=='9'*tail:
            out.append(sl[:i]+('[%s-%s]'%(sl[i],sh[i]) if sl[i]!=sh[i] else sl[i])+'[0-9]'*tail); return
        # lower partial
        if sl[i+1:]!='0'*tail:
            rec(lo,int(sl[:i+1]+'9'*tail)); lo=int(sl[:i]+str(int(sl[i])+1)+'0'*tail)
        if sh[i+1:]!='9'*tail:
            hi2=int(sh[:i]+str(int(sh[i])-1)+'9'*tail) if True else hi
            rec(lo,hi2); rec(int(sh[:i+1]+'0'*tail),hi); return
        rec(lo,hi)
    rec(lo,hi)
    return '('+'|'.join(out)+')'

def lanes(names_w, lo, hi):
    alts = []
    for n, w in names_w:
        alts.append(n + r'\[' + rr(lo * w, (hi + 1) * w - 1) + r'\]')
    return '^(' + '|'.join(alts) + ')$'
def main():
    kind, dx, dy = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    mx, my = dx / 2, dy / 2
    if kind == 'top':
        lane = [('acc_v', 1), ('acc_tag', 13), ('acc_beat', 4), ('acc_data', 256), ('wl_req_v', 1), ('wl_req_rdy', 1),
                ('wl_req_addr', 30), ('wl_req_len', 4), ('wl_req_tag', 13)]
        r = ['^clk$=left:%g-%g' % (mx - 1, mx + 1),
             lanes(lane, 0, 15)[:-2] + r'|s_[a-z_]*\[[0-9]+\])$=bottom:10-%g' % (dx - 10),
             lanes(lane, 16, 31) + '=top:10-%g' % (dx - 10),
             r'^m_[a-z_]*(\[[0-9]+\])?$=right:10-%g' % (dy - 10),
             r'^(rst_n|region_|prime_|blk_|start_|staged_v|stream_go|busy|done|fault|refill_cycles|sectors_|rows_|'
             r'blocks_written|stage_|merge_|la_load_cycles)=left:10-%g' % (dy - 10)]
    elif kind == 'land8':
        # all acc inputs on S (2,184 pins, ~16/um over 136 um, placed explicitly alternating M5 / M7 -> ~8/um per
        # layer); clk (mid), rst_n / b and the registered outputs on N.  In the controller the S-row leaves sit R0 and
        # the N-row leaves MX (H = 43.224 = 0.024 mod 0.048), so the input face always faces the die edge.
        r = ['^clk$=top:%g-%g' % (mx - 1, mx + 1), '^acc_=bottom:2-%g' % (dx - 2),
             r'^(rst_n|b\[)=top:2-%g' % (mx - 3), r'^(bad$|nb\[|sim_bad$)=top:%g-%g' % (mx + 3, dx - 2)]
    elif kind == 'mirror':
        r = ['^clk$=top:%g-%g' % (mx - 1, mx + 1), '^(wr_|rst_n)=left:2-%g' % (dy - 2),
             '^(rd_|j_user)=bottom:2-%g' % (dx - 2), r'^bad\[=right:2-%g' % (dy - 2)]
    else:
        raise SystemExit('unknown kind')
    print('\n'.join(r))
if __name__ == '__main__':
    main()
