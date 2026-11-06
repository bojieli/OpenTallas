WBQ MAIN wider form proposal, candidate only

Old86.4x544.32 MAIN failed detailed placement:301overlaps,2874edge-spacing,205padding; preDPL128134standard/tapcells17367.6um2/41654.5=41.6945%. Actual failed ODB image personallyviewed: densehourglass y170..340 and unusedupperroom. Existing heads guide3001cells827.6um2=25.3%; send guides54movablecells11.4um2+fixed84..86um2=20.2..20.6%. No overreservedguidecause. Data g_d2288bits were allE y1.944..221.496 while outputW16packets span50.76..493.176.

A103.68 and B120.96 expandWEST keeping EASTabsoluteX fixed; parent movesOUT51 west by17.28/34.56 respectively and ownsAQHI/neighbors/stations/clocks. Target fill estimates34.3%/29.1% from actualoldarea, cells<150k; newGENactualstillrequired.

Revised draft ABI7352pins preservesW16sendpackets/N/S pins. Actual four ROOT432x129.6 tiles begin at MAINY+138.24*r in both hubs/q0/q1. E g_d[g,bit] nowmatchesROOTwest exactly: y138.24*(g//2)+1.368+27.456*(g%2)+.096*bit. g_v=138.24*r+56.28+.096*k; g_credit=138.24*r+1.176+.096*k; root_id=138.24*r+56.568+.096*k; root_ready=138.24*r+56.76. AllROOTpinABI unchanged. HBM/streamclocklocalA51.864/52.248 orB60.504/60.888, y272.16. Olduniform55.08group draft65c9 was rejected after actualROOTpinreview; do notbuildthatdraft.

Four paired queue regions now place g_q[2r]/g_q[2r+1] at theirROOT-facing input bands: xwidth-56.16..width-4.32,ymax(5.4,138.24*r-4.032)..138.24*r+62.256. Each pair measured2978cells860.7um2; firstregionmovable29.2%, laterregions25.1%; ~35%/30%withfixed572bitinputbank. Sharedhead/controlx24..width-60.48,y240..304 isdisjointfromE/Wregions. Existing16Wsendregionsretained. Actualcandidateimage personallyreviewed: fourROOT-facingqueuehomesdistributedfullheight, disjointregions, centralclock, macrofreecorridors. PASS-COND proposal; parentfit/station/clockevent+typednativefamilyqualification BEFOREGEN/P&R.

Source unchanged, protocolcycles0. TypedWIPe13d6d04eab NOTqualified: oldbareOUTfullclockhandshake passes but capturedphysicalKsharetupleFAILbad10; newFULLCLOCKstrictsameparentreciprocal INTERNAL_CORE Kseam API/profile andactualfamilyproof stillpending (typed85445e4c075 supersedeshalfcycleWIP). Do notblindlyactivate oldprofile.
