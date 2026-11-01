# RED five-level actual-sink balancing model

MODEL ONLY, no physical/source/native-profile/view/parent+1 adoption. Same five-level geometry as preserved2245cell near-miss;4103 actual sinks reassigned only between existing sibling leaf tips to equalize local actual counts,0blockedgroups, maximum permitted35um. Actual resulting leafspread20.6um. Same2245nodes/7stages, no added/deleted/dummy sinks, no dummy loads, no padding, no per-driver sizing. OneBUFx8 pernonleaflevel, oneBUFx24 leafmaster. Exact34225typedHQN/ASRHQNcaps and20psTT/FFwindow/60psleafslew/80psinput gates unchanged.

PASS model TT276.36/window18.29/slew26.7, FF218.42/window16.61/slew22.5. ConverterPGclearancePASS/0.999ummaxdriverdisplacement. CapTT3.339pF/FF3.695pF, about20.56/20.69% above nativeDFFCLKcap;642.62808um2clockarea; actualold217427nonclocklogic plus2245tree gives219672cells/39.151%corefill. Clockwire/internalpower not measured; root input slew0 and absolute parent clock frame remain hypotheses, regardless proximity to common250/202.5 reference.

Personally LOOKED qfd_dv_s5_red2_leaf_r13.png: symmetric full-region branches, centerentry, fewerdriverswith bounded20.6umactualleafreach, no macros/walls. Requires independent exactbody/TAP/selfcollision review then a separately approved freshPLACE-only scope. Actualnewplacement/sinks/root-slew/frame/NLDM required beforeCTS.

Approved exactsixlevelkit66a42afd81f4c8f0 remains ONE submitted normal16GB4TPLACE diagnostic(client2244431); this model does not swap that scope orlaunch a second PLACE. This is a concrete lowerpower nextcandidate for coordinator review.

Runtime epyc2:/srv/opentallas-scratch2/claude/codex-qc-red-balance-1101/model_balanced/qfd_dv_s5_red2_leaf; normal4GB1T unit1463923-1793575328 exit0. EarliermissingR7/R8helper import failed beforemodel, preservedmodel_NOTRUN_missing_helpers.log; exactexistinghelperdirs restored and one retry.
