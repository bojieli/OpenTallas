Read-only current-main clock-family replay

Main59835e962ec617f79ad2ca57daf58cf479ac8487 introduced shared clock_family ownership/active-edge normalization after the exact xstn submission. The current ck_insertion.py+clock_family.tcl were replayed against the immutable detailed6_finalODB/SDC/SPEF, raw-sourcezero latency, at nativeTT/FF/SS. No reroute, repair or constraint edit occurred. Exact inputs/tool hashes are in current_family_sources.json.

qfd_c_xstn_safe: TTmean140.3ps/spread36.6ps; FFmean118.7ps/spread35.9ps;699owned core_clk sinks, no errors

qfd_c_xstnw_safe: TTmean136.2ps/spread33.4ps; FFmean115.0ps/spread33.6ps;699owned core_clk sinks, no errors

TT/FF boundary mean,min,max,count exactly match the routed-insertion references used by the CLOSED native re-STA. Thus this current-family measurement introduces no reference delta into the reported TT/FF verdicts. It does not constitute a new source-bound route/gate, approve parent clock phases, or replace any unrelated updated runtime rule.
