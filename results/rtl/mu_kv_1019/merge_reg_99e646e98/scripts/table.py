import re, os, sys
R = sys.argv[1]; os.chdir(R)
rows = []
def rd(p):
    try: return open(p, errors='replace').read()
    except FileNotFoundError: return None
def summ(path, key):
    for l in open(path):
        if key in l: return l.strip()
    return None
# positive + identity legs
pos = [("host", "host/runs/summary.txt", t, "HOST_MU %s rc=0 src: PASS" % t) for t in ["tb_qkd_host_ctl_mu","tb_qkd_host_mu_out","tb_qkd_kv_mu_rowoff"]]
pos += [("kv", "kv/runs/summary.txt", t, k) for t, k in [("tb_mu_kv_writer_rows","MU_KV tb_mu_kv_writer_rows rc=0: PASS"),("tb_mu_kv_pc_path_rows","MU_KV tb_mu_kv_pc_path_rows rc=0: PASS"),("lint_mu_kv_tiles","MU_KV lint_mu_kv_tiles: PASS"),("ex tb_qkd_kv_mu_rowoff (MU0)","HOST_MU tb_qkd_kv_mu_rowoff rc=0 src: PASS"),("ex kvplan_ci_nc_gate (MU0)","MU0 kvplan_ci_nc_gate rc=0: PASS")]]
pos += [("hroot", "hroot/runs/summary.txt", t, "MU_HROOT %s rc=0: PASS" % t) for t in ["tb_mu_hroot_e2e","tb_mu_hroot_collide","tb_mu_lprg_lockstep","tb_mu_lprg_lockstep_s2","ex_endpoint","ex_endpoint_mu0","ex_lifecycle","ex_lifecycle_mu0"]]
pos += [("hroot","hroot/runs/summary.txt","lint_guard_mu","MU_HROOT lint_guard_mu: PASS")]
for g, f, t, k in pos:
    l = summ(f, k); rows.append((g, t, "PASS", "PASS" if l else "NOT PASS", (l or "")[len(k)-4:][:110]))
hs = open("host.out").read()
for t in re.findall(r"^  (tb_\S+) (identical|DIFFERS)", hs, re.M):
    rows.append(("host", "MU0 identity %s (MU tree vs pre-MU tree)" % t[0], "identical", t[1], ""))
mut = {
 "host/runs/mut": {"cm1":r"ERR retire 0 at","cm2":r"ERR fault mode 1 bit 87 first 0001","cm3":r"ERR start 1 gen .* user 0/1","cm4":r"ERR retire 1 at","hm1":r"ERR retire slot","hm2":r"ERR start user 0 pos 0/0 busy 1","hm3":r"ERR start user 0 .* busy 1","hm4":r"ERR retire slot 2","rm1":r"FAIL user0 layer0 pos0 .* nalias8","rm2":r"FAIL non-KV command changed"},
 "kv/runs/mut": {"mw1":r"FAIL user. layer0 pos0 errors272 nalias8","mw2":r"FAIL user1 layer0 pos0 errors8","mw3":r"FAIL user. layer0 pos0 errors272","mk1":r"FAIL MU_KV_READ_ROWS act_bad=144 disjoint_bad=288","mk2":r"FAIL MU_KV_READ_ROWS act_bad=96","mk3":r"FAIL MU_KV_READ_ROWS act_bad=96 disjoint_bad=64"},
 "hroot/runs/mut": {"ep1":r"ERR cyc \d+ endpoint protocol_fault","ep2":r"retire late \(waited for global drains","al1":r"allocator epoch != \{seq14\[user\], user\}","al2":r"allocator never ready for this user","kp1":r"ERR cyc \d+ KV programme fault","kp2":r"user token without 36 writer stages","kp3":r"FAIL MU_HROOT_COLLIDE: no collision fault"},
}
for d, ms in mut.items():
    g = d.split("/")[0]
    for m, rx in ms.items():
        s = rd(f"{d}/{m}.log") or ""
        hit = re.search(rx, s); pas = re.search(r"^PASS", s, re.M)
        got = "FAIL (regex hit)" if hit and not pas else ("PASS (mutant survived)" if pas else "FAIL (regex MISS)")
        rows.append((g, f"mutant {m}  /{rx}/", "FAIL", got, (hit.group(0) if hit else "")[:110]))
for l in open("bootage/summary.txt"):
    m = re.match(r"\[(pass|fail)\] (\S+) (\S+)(.*?) :: rc=(\d+) :: (.*)", l.strip())
    e, b, mt, par, rc, v = m.groups()
    rx = r"^KVBA_%s %s " % (b.upper(), "PASS" if e == "pass" else "FAIL")
    tag = "_".join([b, mt] + par.split()); tag = re.sub(r"[^A-Za-z0-9_]", "_", tag) + "_"
    s = rd(f"bootage/runs/sim_{tag}.log") or ""
    ok = re.search(rx, s, re.M)
    got = ("PASS" if (rc == "0" and ok) else "NOT PASS") if e == "pass" else ("FAIL (regex hit)" if (rc != "0" and ok) else "UNEXPECTED")
    rows.append(("bootage", f"{b} mut={mt}{par}" + ("" if e=="pass" else f"  /{rx}/"), e.upper(), got, v[:110]))
ok = lambda r: (r[2] == "PASS" and r[3] == "PASS") or (r[2] == "FAIL" and r[3] == "FAIL (regex hit)") or (r[2] == "identical" and r[3] == "identical")
bad = [r for r in rows if not ok(r)]
out = ["# KV-die MU merge regression, claude/mu-die-kv-1019 @99e646e98 (REFILL-1330/MUKVREG, 10-19)", "",
 "Verilator 5.050 (~/.local/opentallas-tools/verilator-5.050) on ot-epyc5 via ot-run; source = git archive 99e646e98 (rtl tools results/rtl/mu_qwen_1018 results/rtl/kv_bootage_1019 ...);",
 "MU0 identity head tree = pre-MU tree (~/scratch/mu-qwen-adopt/head, as REFILL-0730/MUQWREG). Merged on this commit: HKV-DIE 0c8616105, KV-BOOTAGE c99be3fd2.",
 "NOT merged at 99e646e98 (so NOT covered): KV-PVFST claude/kv-pvfst-1019 bccc561e3, MU-KV-HCTL2 claude/mu-kv-hctl2-1019 (cm5 / runs_hctl2), KV-CTL mu2, MU-KV-CTL3, MU-KV-CTX, MU-KV-TOKLIST, MU-KV-PROG, MU-KV-PEER.",
 "Excluded by brief: qwk_slice_attn attention vehicle (MU-TOK-KV / MU-TOK-KV2).",
 "Legs: host = rtl/test/mu_qwen_1018/run_all.sh; kv = run_all_kv.sh; hroot = run_all_hroot.sh; bootage = the 24 cases of results/rtl/kv_bootage_1019/run_all_benches.sh (tools/qwen_kv_die/kv_bootage_bench.sh).",
 "Mutant regexes: results/rtl/mu_qwen_1018/{host,kv,hroot}/README.md; bootage: verdict line KVBA_<BENCH> FAIL with exit != 0.", "",
 f"**Result: {len(rows)} legs, {len(rows)-len(bad)} as expected, {len(bad)} unexpected.**", "",
 "| group | leg | expect | got | evidence |", "|---|---|---|---|---|"]
out += ["| %s | %s | %s | %s | %s |" % (r[0], r[1].replace("|", "\\|"), r[2], r[3], r[4].replace("|", "\\|")) for r in rows]
open("TABLE.md", "w").write("\n".join(out) + "\n")
print(len(rows), "rows,", len(bad), "unexpected"); [print(b) for b in bad]
