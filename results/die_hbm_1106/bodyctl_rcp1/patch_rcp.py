# Opt-in OT_Q3CTL_RCP1: replicated-copy registers _229667_ (19 x adv_x) and _229719_ (31 x take_x)
# become one 1-bit register each, fanned out by a wire.  Same value on every bit at every edge.
import re, sys
p = sys.argv[1]
L = open(p).read().split("\n")
def patch(name, width, sig):
    i = next(n for n, l in enumerate(L) if l.strip() == f"reg [{width-1}:0] {name};")
    # block: decl, always, [if reset, else] / plain, then assign
    j = i + 1
    assert L[j].strip().startswith("always @(posedge clk_issue")
    k = j + 1
    while not L[k].strip().startswith("assign "): k += 1
    body = "\n".join(L[j:k])
    toks = re.findall(r"\\u_body\.g_iss256\.u_issuer\.(\w+) ", body.split("<=")[-1])
    assert len(toks) == width and set(toks) == {sig}, (name, len(toks), set(toks))
    asg = L[k]
    assert asg.rstrip().endswith(f"}} = {name};"), asg[-60:]
    lhs = asg.rstrip()[: -len(f" = {name};")]
    new_always = [x.replace(f"{width}'h00000", "1'b0").replace(f"{width}'h0", "1'b0") for x in L[j:k]]
    new_always[-1] = re.sub(r"<= \{.*\};", rf"<= \\u_body.g_iss256.u_issuer.{sig} ;", new_always[-1])
    blk = ["`ifdef OT_Q3CTL_RCP1", f"  reg [0:0] {name};"] + new_always + [f"{lhs} = {{{width}{{{name}}}}};", "`else"] + L[i:k+1] + ["`endif"]
    L[i:k+1] = blk
patch("_229667_", 19, "adv_x")
patch("_229719_", 31, "take_x")
open(p, "w").write("\n".join(L))
print("ok")
