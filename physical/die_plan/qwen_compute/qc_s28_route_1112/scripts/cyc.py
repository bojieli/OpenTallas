import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/qc-s28-route/tools/die_plan")
import schema as S
raw = json.load(open(sys.argv[1])); P = S.Plan(raw); T = raw["latency"]["lanes"]
print("column\tx_fw_ctl\tp1\tp2\tgroup_max(plan)\tgroup_max(table)\tsu_l1_ctl\tsu_l0_ctl\tsu_vmw_max(plan)\tsu_vmw_max(table)\te1_est_x_fw_ctl_group\tchosen(a)_delta")
for c in [f"{s}{i}" for s in "EW" for i in range(6)]:
    ids = [f"sl_{c}_fw__x_fw_ctl", f"sl_{c}_fw__x_fw_ctl_p1", f"sl_{c}_fw__x_fw_ctl_p2"]
    su = [f"sl_{c}_su_l1__x_su_l1_ctl", f"sl_{c}_su_l0__x_su_l0_ctl"]
    L = {l: P.lane_latency(l)["cycles"] for l in ids + su}
    print(f"{c}\t" + "\t".join(str(L[l]) for l in ids) + f"\t{max(L[l] for l in ids)}\t{max(T[l]['cycles'] for l in ids)}\t"
          + "\t".join(str(L[l]) for l in su) + f"\t{max(L[l] for l in su)}\t{max(T[l]['cycles'] for l in su)}\t"
          + f"{max(L[ids[0]], L[ids[1]])}\t0")
