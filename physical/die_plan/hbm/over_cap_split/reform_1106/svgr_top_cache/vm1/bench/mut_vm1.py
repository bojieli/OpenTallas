# bench-only mutants of the vM1 WOH cache change; one exact replacement each
import sys,os
src=open(sys.argv[1]).read();out=sys.argv[2]
M={
 'O1_rot_by_4_always':("     if(WOH!=0)case(expected_sectors)","     if(WOH!=0)case(3'd4)"),
 'O2_no_reset_on_open':("     received<=0;wptr<=16'd1;","     received<=0;"),
 'O3_wsel_off_by_one':("assign wsel[wi]=(wptr<<wi)|(wptr>>(16-wi));","assign wsel[wi]=(wptr<<(wi+1))|(wptr>>(15-wi));"),
 'O4_no_present_check':("||(|(present&wsel[i])))sticky<=1;",")sticky<=1;"),
 'O5_rot3_as_2':("3'd3:wptr<={wptr[12:0],wptr[15:13]};","3'd3:wptr<={wptr[13:0],wptr[15:14]};"),
 'O6_present_not_set':("if(WDECOUPLE!=0)begin for(wk=0;wk<16;wk=wk+1)if(wsel[i][wk])begin words[wk]<=sector_data[i*256+:256];present[wk]<=1;end end",
                       "if(WDECOUPLE!=0)begin for(wk=0;wk<16;wk=wk+1)if(wsel[i][wk])begin words[wk]<=sector_data[i*256+:256];end end"),
}
os.makedirs(out,exist_ok=True)
for k,(a,b) in M.items():
    assert src.count(a)==1,(k,src.count(a))
    open(os.path.join(out,k+'.sv'),'w').write(src.replace(a,b))
print(' '.join(M))
