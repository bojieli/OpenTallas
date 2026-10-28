# QC A0 diagnostic source activity

These measurements use correctness-stress stimulus and the exact existing child CTS databases. They are not production programme power, routed signoff, parent closure, or a replacement for the full A0 activity inventory.

summary.json gives the resolved 833 ps clock, kit setRC_rcx placement-parasitic basis, power and coverage. Each pair of power reports uses the same database and clock capacitance; only register-output/input activity differs. Clock power is identical in each pair.

ROMleaf: existing 4096-address, two-column bench; selected RTL is byte-identical to the CTS kit. All 2200 register names and all 15 inputs match exactly. The ROM macro remains on the existing mean-activity fallback; its 8.944526 mW is listed separately and is identical in both reports.

Rawleaf: exact selected rst145 mapped provider RTL, existing LSL stress input pattern. Actual gate-instance QN maps cover 11646 of 11838 clocked FFs without suffix inference. The remaining 192 are physical input-anchor FFs with unconnected QN in the actual synthesis netlist. They retain explicit mean-activity fallback; all 391 inputs are measured. The ASRHQN simulation primitive follows the selected RVT TT Liberty contract, with eight independent clock/reset/set truth cases; the initial both-X provisional trace was retained in scratch and excluded.

VCDs, build objects and CTS databases remain at intel2:/srv/opentallas-scratch2/claude/codex-qc-a0-activity-0359. Source benches and launch commands are included; RTL sources come from codex/qc-a0-activity-0359-1028 at base2eb5e60188 and selected providers named by the summary. No physical build was launched. Node: existing N4096 shortened trace bench passed4144checks/3137nonzero results. All12102registers and1539inputs annotated after9explicit scalar/generate naming aliases; zero default registers. Node power source matches the selected CTS RTL byte for byte.

The existing power helper measures toggle rates but retains duty0.5 on register outputs and inputs. This duty assumption remains explicit. ROM macro pin CE duty/rate were separately recovered from the existing VCD; the selected Liberty has unconditional clock internal energy and no CE-dependent when condition, so no invented CE power scaling is applied.

Parent relevance: parent_power_model.json uses the QC-owner-confirmed fixed census and457.92x1157.76um outline. NK=8rawleaf+10ROMleaf+1node; NL omits node. Child Clock-group and assumed ROM macro terms are separate. Parent glue/clock/interconnect remain unknown; complete parent totals and densities are null. The census omits obsolete child pin coordinates.
