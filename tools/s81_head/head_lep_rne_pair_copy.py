#!/usr/bin/env python3
"""HEAD-EAST-REPLAN RNE-PAIR-COPY (11-24): zero-cycle consumer-local copy of the pair partner's nonempty flag.

r6 post-CTS worst -158.99 ps: g_rx[2].g_nonempty_regions.addr_nz -> (~300 ps wire) -> g_rx[3] u_rx_mem read-pointer
advance -> local hit compare -> prev_q.  Each lane's SRAM read pointer advances on BOTH pair flags (advance_a/b); one
of them is the partner lane's addr_nz, registered in the partner's region.  A pipeline stage on advance would put the
SRAM read pointer one pop behind rp (functional break), so the structural fix is register duplication: every lane
keeps its own addr_pz = the partner's n_nx != 0 (same D as the partner's addr_nz, same partner reset net), placed by
its loads.  Cycle-exact (no LATCHECK change); the cross-region leg now ends at a flop with a full cycle.
Usage: rne_pair_copy.py IN OUT  (fails closed if any anchor is missing or found more than expected)."""
import sys


def sub(text, old, new, n=1):
    c = text.count(old)
    if c != n:
        raise SystemExit(f"RNE-PAIR-COPY anchor count {c} != {n}: {old[:80]!r}")
    return text.replace(old, new)


def apply(src):
    # 1. partner copy beside the lane's own region flags (SAFE_CONTROL); shared mode reads the partner rne directly.
    src = sub(src,
      "          assign rne_addr[t]=addr_nz;assign rne_meta[t]=meta_nz;assign rne_return[t]=return_nz;\n",
      "          assign rne_addr[t]=addr_nz;assign rne_meta[t]=meta_nz;assign rne_return[t]=return_nz;\n"
      "          // RNE-PAIR-COPY: this lane's own copy of the pair partner's addr_nz (same D rnex[t^1], same partner reset)\n"
      "          (* keep=1 *) reg addr_pz;\n"
      "          wire reset_p=rr[NATIVE32_RXRSTBASE+(t^1)];\n"
      "          always @(posedge clk or negedge reset_p)\n"
      "            if(!reset_p) addr_pz<=0; else addr_pz<=rnex[t^1];\n"
      "          assign adv_pair=addr_pz;\n"
      "          (* keep=1 *) reg meta_pz;   // RNE-PAIR-COPY: same for the partner's meta_nz (meta read pointers)\n"
      "          always @(posedge clk or negedge reset_p)\n"
      "            if(!reset_p) meta_pz<=0; else meta_pz<=rnex[t^1];\n"
      "          assign adv_meta_pair=meta_pz;\n")
    src = sub(src,
      "          assign rne_addr[t]=rne[t];assign rne_meta[t]=rne[t];assign rne_return[t]=rne[t];\n",
      "          assign rne_addr[t]=rne[t];assign rne_meta[t]=rne[t];assign rne_return[t]=rne[t];\n"
      "          assign adv_pair=rne[t^1];\n"
      "          assign adv_meta_pair=rne[t^1];\n")
    src = sub(src,
      "        if(SAFE_CONTROL) begin:g_nonempty_regions\n",
      "        wire adv_pair, adv_meta_pair;   // RNE-PAIR-COPY: the pair partner's nonempty flags as seen by this lane's pointers\n"
      "        if(SAFE_CONTROL) begin:g_nonempty_regions\n")
    # 2. the lane SRAM pointer: own flag from its own register, partner flag from the local copy.
    src = sub(src,
      ".advance_a(rne_addr[2*(t/2)]),",
      ".advance_a(((t%2)==0)?rne_addr[t]:adv_pair),")
    src = sub(src,
      ".advance_b((t==0)?1'b1:rne_addr[2*(t/2)+1]));",
      ".advance_b((t==0)?1'b1:(((t%2)==1)?rne_addr[t]:adv_pair)));")
    src = sub(src,
      ".advance_b(rne_addr[2*(t/2)+1]));",
      ".advance_b(((t%2)==1)?rne_addr[t]:adv_pair));")
    # 3. the lane meta read pointers (host / ring / land), same class.
    src = sub(src,
      "                wire mb=(t==0)?1'b1:rne_meta[2*(t/2)+1];\n",
      "                wire mb=(t==0)?1'b1:(((t%2)==1)?rne_meta[t]:adv_meta_pair);\n")
    src = sub(src,
      "                wire mb=rne_meta[2*(t/2)+1];\n",
      "                wire mb=((t%2)==1)?rne_meta[t]:adv_meta_pair;\n")
    src = sub(src,
      ".advance_a(rne_meta[2*(t/2)]),.advance_b(mb),",
      ".advance_a(((t%2)==0)?rne_meta[t]:adv_meta_pair),.advance_b(mb),")
    return src


if __name__ == "__main__":
    open(sys.argv[2], "w").write(apply(open(sys.argv[1]).read()))
    print("RNE-PAIR-COPY applied")
