`timescale 1ps/1ps
// WIP actual primary enrollment. No runtime/build/bridge admission.
// All current-word status is wired from the actual frozen sealed decoders.
module ot_w2_nc6_protected_completion #(
 parameter integer OPT_EXACT=0, NC=6, MAX_OUT=16, AW=34,
 parameter integer CTAGW=32, GENW=4, SIDW=3, PTAGW=35,
 parameter logic [6:0] PC_ID=0
)(
 input wire clk,rst_n,admission_stop,rearm_v,provider_fenced,reset_fenced,
 output wire rearm_rdy,idle,
 input wire [NC-1:0] c_req_v,c_req_we,
 output reg [NC-1:0] c_req_rdy,
 input wire [NC*AW-1:0] c_req_addr,
 input wire [NC*CTAGW-1:0] c_req_tag,
 input wire [NC*GENW-1:0] c_req_gen,
 input wire [NC*256-1:0] c_req_data,
 output reg [NC-1:0] c_rsp_v,c_wr_done_v,
 input wire [NC-1:0] c_rsp_rdy,c_wr_done_rdy,
 output reg [NC*CTAGW-1:0] c_rsp_tag,c_wr_done_tag,
 output reg [NC*GENW-1:0] c_rsp_gen,c_wr_done_gen,
 output reg [NC*256-1:0] c_rsp_data,
 output reg p_req_v,p_req_we,
 input wire p_req_rdy,
 output reg [AW-1:0] p_req_addr,
 output reg [PTAGW-1:0] p_req_tag,
 output reg [GENW-1:0] p_req_gen,
 output reg [255:0] p_req_data,
 input wire p_rsp_v,p_wr_done_v,
 output reg p_rsp_rdy,p_wr_done_ready,
 input wire [PTAGW-1:0] p_rsp_tag,p_wr_done_tag,
 input wire [GENW-1:0] p_rsp_gen,p_wr_done_gen,
 input wire [255:0] p_rsp_data,
 output wire fault,repair_busy,
 input wire reverse_fenced
);
 localparam integer NW=182;
 (* keep="true" *) logic [71:0] cw[0:NW-1];
 wire [43:0] P[0:218]; wire [71:0] raw[0:218],fixed_word[0:218];
 wire [218:0] clean,ce,invalid;
 logic [43:0] D[0:NW-1]; logic [NW-1:0] WE;
 wire [71:0] encoded[0:NW-1];
 wire [2663:0] secondary_raw,secondary_fixed;
 wire [1627:0] secondary_payload;
 wire [36:0] secondary_clean,secondary_ce,secondary_bad;
 wire [191:0] table_state;
 wire [95:0] table_clean,table_bad;
 logic [5:0] count_pending,offer_drained,cancel_request,reopen_epoch;
 logic [17:0] reserve_roles,intents;
 wire [17:0] committed;
 wire [5:0] request_open,completion_open;
 wire permit,secondary_idle,secondary_rearm;
 logic all_core_clean,any_core_bad,core_bad,plan_bad,core_idle,context_live;
 integer fault_i,fault_j,fault_k,fault_c,fault_a,fault_n,fault_slot;
 logic [43:0] fault_row,fault_target;logic [38:0] fault_key;logic [15:0] fault_mask;logic fault_busy;
 logic [351:0] H,Hn,RQ,RQn,RD,RDn;
 logic [40:0] WQ,WQn;
 logic [4:0] S[0:5],Sn[0:5];
 logic [78:0] C,Cn;
 logic [86:0] J[0:8],Jn[0:8];
 logic [64:0] Q[0:5],Qn[0:5];
 logic [95:0] X[0:7],Xn[0:7];
 logic [7:0] context_clean,context_changed,peer_repaired;
 logic [1:0] scrub_v;
 logic [19:0] scrub_index;
 logic [143:0] scrub_original,scrub_repaired;
 wire [1:0] scrub_ready;
 wire [15767:0] controller_raw,controller_fixed;
 wire [9635:0] controller_payload;
 wire [767:0] context_current,context_next;
 wire [7:0] repair_context_we,repair_scrub_v;
 wire [79:0] repair_index;
 wire [575:0] repair_original,repair_candidate;
 wire [7:0] repair_retire_ready;
 logic [7:0] primary_retire_offer,secondary_retire_offer;
 wire correction_busy,correction_error;
 logic [2:0] rr,rrn;
 logic [2:0] phase[0:2];
 logic [43:0] row,target;
 logic [38:0] key;
 logic [15:0] mask;
 logic req_offer,read_offer;
 logic [5:0] wr_offer;
 logic [17:0] candidate_intents;
 integer i,j,k,c,a,n,slot,hits,choice,rc,wc,bank,offset,eng,owner;
 integer view_i,view_j,retire_e,retire_a;
 integer offer_i,offer_k,offer_c,offer_a;logic [43:0] offer_target;logic offer_found;
 integer count_i,count_k,count_c,count_a;logic [43:0] count_target;logic count_found;
 logic found,busy;

 function automatic integer global_index(input integer x);
 begin case(x)
0:global_index=0;
1:global_index=1;
2:global_index=2;
3:global_index=3;
4:global_index=4;
5:global_index=5;
6:global_index=6;
7:global_index=7;
8:global_index=8;
9:global_index=9;
10:global_index=10;
11:global_index=11;
12:global_index=12;
13:global_index=13;
14:global_index=14;
15:global_index=15;
16:global_index=16;
17:global_index=17;
18:global_index=18;
19:global_index=19;
20:global_index=20;
21:global_index=21;
22:global_index=22;
23:global_index=23;
24:global_index=24;
25:global_index=25;
26:global_index=26;
27:global_index=27;
28:global_index=28;
29:global_index=29;
30:global_index=30;
31:global_index=31;
32:global_index=32;
33:global_index=33;
34:global_index=34;
35:global_index=35;
36:global_index=36;
37:global_index=37;
38:global_index=38;
39:global_index=39;
40:global_index=40;
41:global_index=41;
42:global_index=42;
43:global_index=43;
44:global_index=44;
45:global_index=45;
46:global_index=46;
47:global_index=47;
48:global_index=48;
49:global_index=49;
50:global_index=50;
51:global_index=51;
52:global_index=52;
53:global_index=53;
54:global_index=54;
55:global_index=55;
56:global_index=56;
57:global_index=57;
58:global_index=58;
59:global_index=59;
60:global_index=60;
61:global_index=61;
62:global_index=62;
63:global_index=63;
64:global_index=64;
65:global_index=65;
66:global_index=66;
67:global_index=67;
68:global_index=68;
69:global_index=69;
70:global_index=70;
71:global_index=71;
72:global_index=72;
73:global_index=73;
74:global_index=74;
75:global_index=75;
76:global_index=76;
77:global_index=77;
78:global_index=78;
79:global_index=79;
80:global_index=80;
81:global_index=81;
82:global_index=82;
83:global_index=83;
84:global_index=84;
85:global_index=85;
86:global_index=86;
87:global_index=87;
88:global_index=88;
89:global_index=89;
90:global_index=90;
91:global_index=91;
92:global_index=92;
93:global_index=93;
94:global_index=94;
95:global_index=95;
96:global_index=96;
97:global_index=97;
98:global_index=98;
99:global_index=99;
100:global_index=100;
101:global_index=101;
102:global_index=102;
103:global_index=103;
104:global_index=104;
105:global_index=105;
106:global_index=106;
107:global_index=107;
108:global_index=108;
109:global_index=109;
110:global_index=110;
111:global_index=111;
112:global_index=112;
113:global_index=113;
114:global_index=114;
115:global_index=115;
116:global_index=116;
117:global_index=117;
118:global_index=118;
119:global_index=119;
120:global_index=120;
121:global_index=121;
122:global_index=122;
123:global_index=123;
124:global_index=124;
125:global_index=131;
126:global_index=133;
127:global_index=134;
128:global_index=135;
129:global_index=136;
130:global_index=137;
131:global_index=138;
132:global_index=139;
133:global_index=140;
134:global_index=141;
135:global_index=142;
136:global_index=143;
137:global_index=144;
138:global_index=145;
139:global_index=146;
140:global_index=147;
141:global_index=148;
142:global_index=149;
143:global_index=150;
144:global_index=151;
145:global_index=152;
146:global_index=153;
147:global_index=154;
148:global_index=155;
149:global_index=156;
150:global_index=157;
151:global_index=158;
152:global_index=159;
153:global_index=160;
154:global_index=161;
155:global_index=162;
156:global_index=163;
157:global_index=164;
158:global_index=165;
159:global_index=166;
160:global_index=167;
161:global_index=168;
162:global_index=169;
163:global_index=170;
164:global_index=171;
165:global_index=172;
166:global_index=173;
167:global_index=174;
168:global_index=175;
169:global_index=176;
170:global_index=177;
171:global_index=178;
172:global_index=179;
173:global_index=180;
174:global_index=181;
175:global_index=182;
176:global_index=183;
177:global_index=184;
178:global_index=185;
179:global_index=186;
180:global_index=187;
181:global_index=188;
 default:global_index=-1;endcase end
 endfunction
 function automatic integer local_index(input integer x);
 begin case(x)
0:local_index=0;
1:local_index=1;
2:local_index=2;
3:local_index=3;
4:local_index=4;
5:local_index=5;
6:local_index=6;
7:local_index=7;
8:local_index=8;
9:local_index=9;
10:local_index=10;
11:local_index=11;
12:local_index=12;
13:local_index=13;
14:local_index=14;
15:local_index=15;
16:local_index=16;
17:local_index=17;
18:local_index=18;
19:local_index=19;
20:local_index=20;
21:local_index=21;
22:local_index=22;
23:local_index=23;
24:local_index=24;
25:local_index=25;
26:local_index=26;
27:local_index=27;
28:local_index=28;
29:local_index=29;
30:local_index=30;
31:local_index=31;
32:local_index=32;
33:local_index=33;
34:local_index=34;
35:local_index=35;
36:local_index=36;
37:local_index=37;
38:local_index=38;
39:local_index=39;
40:local_index=40;
41:local_index=41;
42:local_index=42;
43:local_index=43;
44:local_index=44;
45:local_index=45;
46:local_index=46;
47:local_index=47;
48:local_index=48;
49:local_index=49;
50:local_index=50;
51:local_index=51;
52:local_index=52;
53:local_index=53;
54:local_index=54;
55:local_index=55;
56:local_index=56;
57:local_index=57;
58:local_index=58;
59:local_index=59;
60:local_index=60;
61:local_index=61;
62:local_index=62;
63:local_index=63;
64:local_index=64;
65:local_index=65;
66:local_index=66;
67:local_index=67;
68:local_index=68;
69:local_index=69;
70:local_index=70;
71:local_index=71;
72:local_index=72;
73:local_index=73;
74:local_index=74;
75:local_index=75;
76:local_index=76;
77:local_index=77;
78:local_index=78;
79:local_index=79;
80:local_index=80;
81:local_index=81;
82:local_index=82;
83:local_index=83;
84:local_index=84;
85:local_index=85;
86:local_index=86;
87:local_index=87;
88:local_index=88;
89:local_index=89;
90:local_index=90;
91:local_index=91;
92:local_index=92;
93:local_index=93;
94:local_index=94;
95:local_index=95;
96:local_index=96;
97:local_index=97;
98:local_index=98;
99:local_index=99;
100:local_index=100;
101:local_index=101;
102:local_index=102;
103:local_index=103;
104:local_index=104;
105:local_index=105;
106:local_index=106;
107:local_index=107;
108:local_index=108;
109:local_index=109;
110:local_index=110;
111:local_index=111;
112:local_index=112;
113:local_index=113;
114:local_index=114;
115:local_index=115;
116:local_index=116;
117:local_index=117;
118:local_index=118;
119:local_index=119;
120:local_index=120;
121:local_index=121;
122:local_index=122;
123:local_index=123;
124:local_index=124;
131:local_index=125;
133:local_index=126;
134:local_index=127;
135:local_index=128;
136:local_index=129;
137:local_index=130;
138:local_index=131;
139:local_index=132;
140:local_index=133;
141:local_index=134;
142:local_index=135;
143:local_index=136;
144:local_index=137;
145:local_index=138;
146:local_index=139;
147:local_index=140;
148:local_index=141;
149:local_index=142;
150:local_index=143;
151:local_index=144;
152:local_index=145;
153:local_index=146;
154:local_index=147;
155:local_index=148;
156:local_index=149;
157:local_index=150;
158:local_index=151;
159:local_index=152;
160:local_index=153;
161:local_index=154;
162:local_index=155;
163:local_index=156;
164:local_index=157;
165:local_index=158;
166:local_index=159;
167:local_index=160;
168:local_index=161;
169:local_index=162;
170:local_index=163;
171:local_index=164;
172:local_index=165;
173:local_index=166;
174:local_index=167;
175:local_index=168;
176:local_index=169;
177:local_index=170;
178:local_index=171;
179:local_index=172;
180:local_index=173;
181:local_index=174;
182:local_index=175;
183:local_index=176;
184:local_index=177;
185:local_index=178;
186:local_index=179;
187:local_index=180;
188:local_index=181;
 default:local_index=-1;endcase end
 endfunction
 function automatic integer payload_bits(input integer x);
 begin case(x)
0:payload_bits=44;
1:payload_bits=44;
2:payload_bits=44;
3:payload_bits=44;
4:payload_bits=44;
5:payload_bits=44;
6:payload_bits=44;
7:payload_bits=44;
8:payload_bits=44;
9:payload_bits=44;
10:payload_bits=44;
11:payload_bits=44;
12:payload_bits=44;
13:payload_bits=44;
14:payload_bits=44;
15:payload_bits=44;
16:payload_bits=44;
17:payload_bits=44;
18:payload_bits=44;
19:payload_bits=44;
20:payload_bits=44;
21:payload_bits=44;
22:payload_bits=44;
23:payload_bits=44;
24:payload_bits=44;
25:payload_bits=44;
26:payload_bits=44;
27:payload_bits=44;
28:payload_bits=44;
29:payload_bits=44;
30:payload_bits=44;
31:payload_bits=44;
32:payload_bits=44;
33:payload_bits=44;
34:payload_bits=44;
35:payload_bits=44;
36:payload_bits=44;
37:payload_bits=44;
38:payload_bits=44;
39:payload_bits=44;
40:payload_bits=44;
41:payload_bits=44;
42:payload_bits=44;
43:payload_bits=44;
44:payload_bits=44;
45:payload_bits=44;
46:payload_bits=44;
47:payload_bits=44;
48:payload_bits=44;
49:payload_bits=44;
50:payload_bits=44;
51:payload_bits=44;
52:payload_bits=44;
53:payload_bits=44;
54:payload_bits=44;
55:payload_bits=44;
56:payload_bits=44;
57:payload_bits=44;
58:payload_bits=44;
59:payload_bits=44;
60:payload_bits=44;
61:payload_bits=44;
62:payload_bits=44;
63:payload_bits=44;
64:payload_bits=44;
65:payload_bits=44;
66:payload_bits=44;
67:payload_bits=44;
68:payload_bits=44;
69:payload_bits=44;
70:payload_bits=44;
71:payload_bits=44;
72:payload_bits=44;
73:payload_bits=44;
74:payload_bits=44;
75:payload_bits=44;
76:payload_bits=44;
77:payload_bits=44;
78:payload_bits=44;
79:payload_bits=44;
80:payload_bits=44;
81:payload_bits=44;
82:payload_bits=44;
83:payload_bits=44;
84:payload_bits=44;
85:payload_bits=44;
86:payload_bits=44;
87:payload_bits=44;
88:payload_bits=44;
89:payload_bits=44;
90:payload_bits=44;
91:payload_bits=44;
92:payload_bits=44;
93:payload_bits=44;
94:payload_bits=44;
95:payload_bits=44;
96:payload_bits=44;
97:payload_bits=44;
98:payload_bits=44;
99:payload_bits=44;
100:payload_bits=44;
101:payload_bits=44;
102:payload_bits=44;
103:payload_bits=27;
104:payload_bits=44;
105:payload_bits=44;
106:payload_bits=44;
107:payload_bits=44;
108:payload_bits=44;
109:payload_bits=44;
110:payload_bits=33;
111:payload_bits=41;
112:payload_bits=44;
113:payload_bits=44;
114:payload_bits=44;
115:payload_bits=44;
116:payload_bits=44;
117:payload_bits=44;
118:payload_bits=36;
119:payload_bits=5;
120:payload_bits=5;
121:payload_bits=5;
122:payload_bits=5;
123:payload_bits=5;
124:payload_bits=5;
125:payload_bits=9;
126:payload_bits=9;
127:payload_bits=9;
128:payload_bits=9;
129:payload_bits=9;
130:payload_bits=9;
131:payload_bits=3;
132:payload_bits=1;
133:payload_bits=44;
134:payload_bits=21;
135:payload_bits=44;
136:payload_bits=21;
137:payload_bits=44;
138:payload_bits=21;
139:payload_bits=44;
140:payload_bits=21;
141:payload_bits=44;
142:payload_bits=21;
143:payload_bits=44;
144:payload_bits=21;
145:payload_bits=44;
146:payload_bits=44;
147:payload_bits=8;
148:payload_bits=44;
149:payload_bits=44;
150:payload_bits=8;
151:payload_bits=44;
152:payload_bits=44;
153:payload_bits=8;
154:payload_bits=44;
155:payload_bits=44;
156:payload_bits=8;
157:payload_bits=44;
158:payload_bits=44;
159:payload_bits=8;
160:payload_bits=44;
161:payload_bits=44;
162:payload_bits=8;
163:payload_bits=44;
164:payload_bits=44;
165:payload_bits=8;
166:payload_bits=44;
167:payload_bits=44;
168:payload_bits=8;
169:payload_bits=44;
170:payload_bits=43;
171:payload_bits=44;
172:payload_bits=43;
173:payload_bits=44;
174:payload_bits=43;
175:payload_bits=44;
176:payload_bits=43;
177:payload_bits=44;
178:payload_bits=43;
179:payload_bits=44;
180:payload_bits=43;
181:payload_bits=44;
182:payload_bits=43;
183:payload_bits=44;
184:payload_bits=43;
185:payload_bits=44;
186:payload_bits=43;
187:payload_bits=44;
188:payload_bits=35;
189:payload_bits=44;
190:payload_bits=44;
191:payload_bits=10;
192:payload_bits=44;
193:payload_bits=44;
194:payload_bits=10;
195:payload_bits=44;
196:payload_bits=44;
197:payload_bits=10;
198:payload_bits=44;
199:payload_bits=44;
200:payload_bits=10;
201:payload_bits=44;
202:payload_bits=44;
203:payload_bits=10;
204:payload_bits=44;
205:payload_bits=44;
206:payload_bits=10;
207:payload_bits=5;
208:payload_bits=5;
209:payload_bits=5;
210:payload_bits=5;
211:payload_bits=5;
212:payload_bits=5;
213:payload_bits=8;
214:payload_bits=8;
215:payload_bits=8;
216:payload_bits=8;
217:payload_bits=8;
218:payload_bits=8;
 default:payload_bits=0;endcase end
 endfunction
 function automatic integer kind(input integer x);
 begin case(x)
0:kind=0;
1:kind=0;
2:kind=0;
3:kind=0;
4:kind=0;
5:kind=0;
6:kind=0;
7:kind=0;
8:kind=0;
9:kind=0;
10:kind=0;
11:kind=0;
12:kind=0;
13:kind=0;
14:kind=0;
15:kind=0;
16:kind=0;
17:kind=0;
18:kind=0;
19:kind=0;
20:kind=0;
21:kind=0;
22:kind=0;
23:kind=0;
24:kind=0;
25:kind=0;
26:kind=0;
27:kind=0;
28:kind=0;
29:kind=0;
30:kind=0;
31:kind=0;
32:kind=0;
33:kind=0;
34:kind=0;
35:kind=0;
36:kind=0;
37:kind=0;
38:kind=0;
39:kind=0;
40:kind=0;
41:kind=0;
42:kind=0;
43:kind=0;
44:kind=0;
45:kind=0;
46:kind=0;
47:kind=0;
48:kind=0;
49:kind=0;
50:kind=0;
51:kind=0;
52:kind=0;
53:kind=0;
54:kind=0;
55:kind=0;
56:kind=0;
57:kind=0;
58:kind=0;
59:kind=0;
60:kind=0;
61:kind=0;
62:kind=0;
63:kind=0;
64:kind=0;
65:kind=0;
66:kind=0;
67:kind=0;
68:kind=0;
69:kind=0;
70:kind=0;
71:kind=0;
72:kind=0;
73:kind=0;
74:kind=0;
75:kind=0;
76:kind=0;
77:kind=0;
78:kind=0;
79:kind=0;
80:kind=0;
81:kind=0;
82:kind=0;
83:kind=0;
84:kind=0;
85:kind=0;
86:kind=0;
87:kind=0;
88:kind=0;
89:kind=0;
90:kind=0;
91:kind=0;
92:kind=0;
93:kind=0;
94:kind=0;
95:kind=0;
96:kind=1;
97:kind=1;
98:kind=1;
99:kind=1;
100:kind=1;
101:kind=1;
102:kind=1;
103:kind=1;
104:kind=1;
105:kind=1;
106:kind=1;
107:kind=1;
108:kind=1;
109:kind=1;
110:kind=1;
111:kind=1;
112:kind=2;
113:kind=2;
114:kind=2;
115:kind=2;
116:kind=2;
117:kind=2;
118:kind=2;
119:kind=3;
120:kind=3;
121:kind=3;
122:kind=3;
123:kind=3;
124:kind=3;
125:kind=4;
126:kind=4;
127:kind=4;
128:kind=4;
129:kind=4;
130:kind=4;
131:kind=4;
132:kind=4;
133:kind=5;
134:kind=5;
135:kind=5;
136:kind=5;
137:kind=5;
138:kind=5;
139:kind=5;
140:kind=5;
141:kind=5;
142:kind=5;
143:kind=5;
144:kind=5;
145:kind=6;
146:kind=6;
147:kind=6;
148:kind=6;
149:kind=6;
150:kind=6;
151:kind=6;
152:kind=6;
153:kind=6;
154:kind=6;
155:kind=6;
156:kind=6;
157:kind=6;
158:kind=6;
159:kind=6;
160:kind=6;
161:kind=6;
162:kind=6;
163:kind=6;
164:kind=6;
165:kind=6;
166:kind=6;
167:kind=6;
168:kind=6;
169:kind=7;
170:kind=7;
171:kind=7;
172:kind=7;
173:kind=7;
174:kind=7;
175:kind=7;
176:kind=7;
177:kind=7;
178:kind=7;
179:kind=7;
180:kind=7;
181:kind=7;
182:kind=7;
183:kind=7;
184:kind=7;
185:kind=7;
186:kind=7;
187:kind=4;
188:kind=4;
189:kind=7;
190:kind=7;
191:kind=7;
192:kind=7;
193:kind=7;
194:kind=7;
195:kind=7;
196:kind=7;
197:kind=7;
198:kind=7;
199:kind=7;
200:kind=7;
201:kind=7;
202:kind=7;
203:kind=7;
204:kind=7;
205:kind=7;
206:kind=7;
207:kind=4;
208:kind=4;
209:kind=4;
210:kind=4;
211:kind=4;
212:kind=4;
213:kind=4;
214:kind=4;
215:kind=4;
216:kind=4;
217:kind=4;
218:kind=4;
 default:kind=0;endcase end
 endfunction
 function automatic [71:0] seal(input [43:0] p,input integer wi);
 reg [63:0] data64;reg [71:0] code;reg parity;integer pos,b,t;
 begin
 data64={3'(kind(wi)),10'(wi),PC_ID,p};code=0;t=0;
 for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin code[pos-1]=data64[t];t=t+1;end
 for(b=0;b<7;b=b+1)begin parity=0;
 for(pos=1;pos<=71;pos=pos+1)if((pos&(1<<b))!=0)parity=parity^code[pos-1];
 code[(1<<b)-1]=parity;end
 code[71]=^code[70:0];seal=code;
 end endfunction
 function automatic [351:0] get_record(input integer base,input integer chunks);
 integer t;begin get_record=0;for(t=0;t<chunks;t=t+1)get_record[44*t+:44]=P[base+t];end
 endfunction
 task automatic put_record(input integer base,input integer chunks,input [351:0] value);
 integer t,l;begin for(t=0;t<chunks;t=t+1)begin l=local_index(base+t);if(l>=0)begin D[l]=value[44*t+:44];WE[l]=1;end end end
 endtask
 task automatic prepare(input integer role,input integer address,input [43:0] value);
 begin
 if(J[role][86])plan_bad=1;
 else begin
 Jn[role]=0;Jn[role][71:0]=seal(value,address);
 Jn[role][81:72]=10'(address);Jn[role][85:82]=P[address][42:39];Jn[role][86]=1;
 Cn[9+2*role+:2]=0;
 end
 end
 endtask
 function automatic [63:0] decode_data(input [71:0] value);
 integer pos,t;begin decode_data=0;t=0;
 for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin decode_data[t]=value[pos-1];t=t+1;end
 end endfunction
 function automatic [6:0] syndrome(input [71:0] value);
 integer pos,b;begin syndrome=0;
 for(b=0;b<7;b=b+1)for(pos=1;pos<=71;pos=pos+1)if((pos&(1<<b))!=0)syndrome[b]=syndrome[b]^value[pos-1];
 end endfunction
 function automatic integer popcount16(input [15:0] value);
 integer t;begin popcount16=0;for(t=0;t<16;t=t+1)popcount16=popcount16+integer'(value[t]);end
 endfunction
 function automatic qualified(input [43:0] oldrow,newrow,input [3:0] version,input integer role);
 begin
 qualified=oldrow[42:39]==version;
 if(role==0)begin
 if(newrow[1:0]==0&&newrow[43])qualified=qualified&&oldrow[1:0]==0&&!oldrow[43]&&newrow[42:39]==version;
 else if(newrow[1:0]==1)qualified=qualified&&oldrow[1:0]==0&&oldrow[43]&&!newrow[43]&&newrow[38:2]==oldrow[38:2]&&newrow[42:39]==version;
 else qualified=qualified&&newrow[1:0]==0&&oldrow[1:0]==0&&oldrow[43]&&!newrow[43]&&newrow[38:2]==oldrow[38:2]&&newrow[42:39]==4'(version+1);
 end else begin
 qualified=qualified&&!oldrow[43]&&!newrow[43]&&oldrow[38:2]==newrow[38:2];
 if(role==1&&newrow[1:0]==2)qualified=qualified&&oldrow[1:0]==1&&!oldrow[38]&&newrow[42:39]==version;
 else if(role==2)qualified=qualified&&oldrow[1:0]==1&&newrow[1:0]==3&&oldrow[38]&&newrow[42:39]==version;
 else qualified=qualified&&oldrow[1:0]==(role==1?2:3)&&newrow[1:0]==0&&oldrow[38]==(role!=1)&&newrow[42:39]==4'(version+1);
 end
 end endfunction
 generate for(genvar l=0;l<NW;l=l+1)begin:primary_word
 localparam integer G=global_index(l),PB=payload_bits(G);
 wire uncorrectable,seal_ok,padding_ok;
 wire [43:0] bounded={{(44-PB){1'b0}},D[l][PB-1:0]};
 ot_w2_sealed_secded72 #(.PC_ID(PC_ID),.WORD_INDEX(10'(G)),.WORD_KIND(3'(kind(G))),.PAYLOAD_BITS(PB)) decoder(
 .payload(44'b0),.current_word(cw[l]),.encoded_word(),.syndrome(),.overall_odd(),.clean(),
 .correctable(ce[G]),.uncorrectable(uncorrectable),.seal_ok(seal_ok),.padding_ok(padding_ok),
 .release_clean(clean[G]),.repaired_payload(P[G]),.repaired_word(fixed_word[G]));
 ot_w2_sealed_secded72 #(.PC_ID(PC_ID),.WORD_INDEX(10'(G)),.WORD_KIND(3'(kind(G))),.PAYLOAD_BITS(PB)) encoder(
 .payload(bounded),.current_word(72'b0),.encoded_word(encoded[l]),.syndrome(),.overall_odd(),.clean(),
 .correctable(),.uncorrectable(),.seal_ok(),.padding_ok(),.release_clean(),.repaired_payload(),.repaired_word());
 assign raw[G]=cw[l];assign invalid[G]=uncorrectable||!seal_ok||!padding_ok;
 end
assign raw[125]=secondary_raw[0+:72];assign fixed_word[125]=secondary_fixed[0+:72];assign P[125]=secondary_payload[0+:44];assign clean[125]=secondary_clean[0];assign ce[125]=secondary_ce[0];assign invalid[125]=secondary_bad[0];
assign raw[126]=secondary_raw[72+:72];assign fixed_word[126]=secondary_fixed[72+:72];assign P[126]=secondary_payload[44+:44];assign clean[126]=secondary_clean[1];assign ce[126]=secondary_ce[1];assign invalid[126]=secondary_bad[1];
assign raw[127]=secondary_raw[144+:72];assign fixed_word[127]=secondary_fixed[144+:72];assign P[127]=secondary_payload[88+:44];assign clean[127]=secondary_clean[2];assign ce[127]=secondary_ce[2];assign invalid[127]=secondary_bad[2];
assign raw[128]=secondary_raw[216+:72];assign fixed_word[128]=secondary_fixed[216+:72];assign P[128]=secondary_payload[132+:44];assign clean[128]=secondary_clean[3];assign ce[128]=secondary_ce[3];assign invalid[128]=secondary_bad[3];
assign raw[129]=secondary_raw[288+:72];assign fixed_word[129]=secondary_fixed[288+:72];assign P[129]=secondary_payload[176+:44];assign clean[129]=secondary_clean[4];assign ce[129]=secondary_ce[4];assign invalid[129]=secondary_bad[4];
assign raw[130]=secondary_raw[360+:72];assign fixed_word[130]=secondary_fixed[360+:72];assign P[130]=secondary_payload[220+:44];assign clean[130]=secondary_clean[5];assign ce[130]=secondary_ce[5];assign invalid[130]=secondary_bad[5];
assign raw[189]=secondary_raw[432+:72];assign fixed_word[189]=secondary_fixed[432+:72];assign P[189]=secondary_payload[264+:44];assign clean[189]=secondary_clean[6];assign ce[189]=secondary_ce[6];assign invalid[189]=secondary_bad[6];
assign raw[190]=secondary_raw[504+:72];assign fixed_word[190]=secondary_fixed[504+:72];assign P[190]=secondary_payload[308+:44];assign clean[190]=secondary_clean[7];assign ce[190]=secondary_ce[7];assign invalid[190]=secondary_bad[7];
assign raw[191]=secondary_raw[576+:72];assign fixed_word[191]=secondary_fixed[576+:72];assign P[191]=secondary_payload[352+:44];assign clean[191]=secondary_clean[8];assign ce[191]=secondary_ce[8];assign invalid[191]=secondary_bad[8];
assign raw[192]=secondary_raw[648+:72];assign fixed_word[192]=secondary_fixed[648+:72];assign P[192]=secondary_payload[396+:44];assign clean[192]=secondary_clean[9];assign ce[192]=secondary_ce[9];assign invalid[192]=secondary_bad[9];
assign raw[193]=secondary_raw[720+:72];assign fixed_word[193]=secondary_fixed[720+:72];assign P[193]=secondary_payload[440+:44];assign clean[193]=secondary_clean[10];assign ce[193]=secondary_ce[10];assign invalid[193]=secondary_bad[10];
assign raw[194]=secondary_raw[792+:72];assign fixed_word[194]=secondary_fixed[792+:72];assign P[194]=secondary_payload[484+:44];assign clean[194]=secondary_clean[11];assign ce[194]=secondary_ce[11];assign invalid[194]=secondary_bad[11];
assign raw[195]=secondary_raw[864+:72];assign fixed_word[195]=secondary_fixed[864+:72];assign P[195]=secondary_payload[528+:44];assign clean[195]=secondary_clean[12];assign ce[195]=secondary_ce[12];assign invalid[195]=secondary_bad[12];
assign raw[196]=secondary_raw[936+:72];assign fixed_word[196]=secondary_fixed[936+:72];assign P[196]=secondary_payload[572+:44];assign clean[196]=secondary_clean[13];assign ce[196]=secondary_ce[13];assign invalid[196]=secondary_bad[13];
assign raw[197]=secondary_raw[1008+:72];assign fixed_word[197]=secondary_fixed[1008+:72];assign P[197]=secondary_payload[616+:44];assign clean[197]=secondary_clean[14];assign ce[197]=secondary_ce[14];assign invalid[197]=secondary_bad[14];
assign raw[198]=secondary_raw[1080+:72];assign fixed_word[198]=secondary_fixed[1080+:72];assign P[198]=secondary_payload[660+:44];assign clean[198]=secondary_clean[15];assign ce[198]=secondary_ce[15];assign invalid[198]=secondary_bad[15];
assign raw[199]=secondary_raw[1152+:72];assign fixed_word[199]=secondary_fixed[1152+:72];assign P[199]=secondary_payload[704+:44];assign clean[199]=secondary_clean[16];assign ce[199]=secondary_ce[16];assign invalid[199]=secondary_bad[16];
assign raw[200]=secondary_raw[1224+:72];assign fixed_word[200]=secondary_fixed[1224+:72];assign P[200]=secondary_payload[748+:44];assign clean[200]=secondary_clean[17];assign ce[200]=secondary_ce[17];assign invalid[200]=secondary_bad[17];
assign raw[201]=secondary_raw[1296+:72];assign fixed_word[201]=secondary_fixed[1296+:72];assign P[201]=secondary_payload[792+:44];assign clean[201]=secondary_clean[18];assign ce[201]=secondary_ce[18];assign invalid[201]=secondary_bad[18];
assign raw[202]=secondary_raw[1368+:72];assign fixed_word[202]=secondary_fixed[1368+:72];assign P[202]=secondary_payload[836+:44];assign clean[202]=secondary_clean[19];assign ce[202]=secondary_ce[19];assign invalid[202]=secondary_bad[19];
assign raw[203]=secondary_raw[1440+:72];assign fixed_word[203]=secondary_fixed[1440+:72];assign P[203]=secondary_payload[880+:44];assign clean[203]=secondary_clean[20];assign ce[203]=secondary_ce[20];assign invalid[203]=secondary_bad[20];
assign raw[204]=secondary_raw[1512+:72];assign fixed_word[204]=secondary_fixed[1512+:72];assign P[204]=secondary_payload[924+:44];assign clean[204]=secondary_clean[21];assign ce[204]=secondary_ce[21];assign invalid[204]=secondary_bad[21];
assign raw[205]=secondary_raw[1584+:72];assign fixed_word[205]=secondary_fixed[1584+:72];assign P[205]=secondary_payload[968+:44];assign clean[205]=secondary_clean[22];assign ce[205]=secondary_ce[22];assign invalid[205]=secondary_bad[22];
assign raw[206]=secondary_raw[1656+:72];assign fixed_word[206]=secondary_fixed[1656+:72];assign P[206]=secondary_payload[1012+:44];assign clean[206]=secondary_clean[23];assign ce[206]=secondary_ce[23];assign invalid[206]=secondary_bad[23];
assign raw[207]=secondary_raw[1728+:72];assign fixed_word[207]=secondary_fixed[1728+:72];assign P[207]=secondary_payload[1056+:44];assign clean[207]=secondary_clean[24];assign ce[207]=secondary_ce[24];assign invalid[207]=secondary_bad[24];
assign raw[208]=secondary_raw[1800+:72];assign fixed_word[208]=secondary_fixed[1800+:72];assign P[208]=secondary_payload[1100+:44];assign clean[208]=secondary_clean[25];assign ce[208]=secondary_ce[25];assign invalid[208]=secondary_bad[25];
assign raw[209]=secondary_raw[1872+:72];assign fixed_word[209]=secondary_fixed[1872+:72];assign P[209]=secondary_payload[1144+:44];assign clean[209]=secondary_clean[26];assign ce[209]=secondary_ce[26];assign invalid[209]=secondary_bad[26];
assign raw[210]=secondary_raw[1944+:72];assign fixed_word[210]=secondary_fixed[1944+:72];assign P[210]=secondary_payload[1188+:44];assign clean[210]=secondary_clean[27];assign ce[210]=secondary_ce[27];assign invalid[210]=secondary_bad[27];
assign raw[211]=secondary_raw[2016+:72];assign fixed_word[211]=secondary_fixed[2016+:72];assign P[211]=secondary_payload[1232+:44];assign clean[211]=secondary_clean[28];assign ce[211]=secondary_ce[28];assign invalid[211]=secondary_bad[28];
assign raw[212]=secondary_raw[2088+:72];assign fixed_word[212]=secondary_fixed[2088+:72];assign P[212]=secondary_payload[1276+:44];assign clean[212]=secondary_clean[29];assign ce[212]=secondary_ce[29];assign invalid[212]=secondary_bad[29];
assign raw[213]=secondary_raw[2160+:72];assign fixed_word[213]=secondary_fixed[2160+:72];assign P[213]=secondary_payload[1320+:44];assign clean[213]=secondary_clean[30];assign ce[213]=secondary_ce[30];assign invalid[213]=secondary_bad[30];
assign raw[214]=secondary_raw[2232+:72];assign fixed_word[214]=secondary_fixed[2232+:72];assign P[214]=secondary_payload[1364+:44];assign clean[214]=secondary_clean[31];assign ce[214]=secondary_ce[31];assign invalid[214]=secondary_bad[31];
assign raw[215]=secondary_raw[2304+:72];assign fixed_word[215]=secondary_fixed[2304+:72];assign P[215]=secondary_payload[1408+:44];assign clean[215]=secondary_clean[32];assign ce[215]=secondary_ce[32];assign invalid[215]=secondary_bad[32];
assign raw[216]=secondary_raw[2376+:72];assign fixed_word[216]=secondary_fixed[2376+:72];assign P[216]=secondary_payload[1452+:44];assign clean[216]=secondary_clean[33];assign ce[216]=secondary_ce[33];assign invalid[216]=secondary_bad[33];
assign raw[217]=secondary_raw[2448+:72];assign fixed_word[217]=secondary_fixed[2448+:72];assign P[217]=secondary_payload[1496+:44];assign clean[217]=secondary_clean[34];assign ce[217]=secondary_ce[34];assign invalid[217]=secondary_bad[34];
assign raw[218]=secondary_raw[2520+:72];assign fixed_word[218]=secondary_fixed[2520+:72];assign P[218]=secondary_payload[1540+:44];assign clean[218]=secondary_clean[35];assign ce[218]=secondary_ce[35];assign invalid[218]=secondary_bad[35];
assign raw[132]=secondary_raw[2592+:72];assign fixed_word[132]=secondary_fixed[2592+:72];assign P[132]=secondary_payload[1584+:44];assign clean[132]=secondary_clean[36];assign ce[132]=secondary_ce[36];assign invalid[132]=secondary_bad[36];
 for(genvar r=0;r<96;r=r+1)begin:table_view
 assign table_state[2*r+:2]=P[r][1:0];assign table_clean[r]=clean[r];assign table_bad[r]=invalid[r];
 end endgenerate
 generate for(genvar g=0;g<219;g=g+1)begin:repair_view
 assign controller_raw[72*g+:72]=raw[g];assign controller_fixed[72*g+:72]=fixed_word[g];
 assign controller_payload[44*g+:44]=P[g];
 end
 for(genvar e=0;e<8;e=e+1)begin:context_view
 assign context_current[96*e+:96]={P[147+3*e][7:0],P[146+3*e],P[145+3*e]};
 end endgenerate
 ot_w2_nc6_correction_control correction(
 .enable(OPT_EXACT!=0&&rst_n),.context_current(context_current),.context_clean(context_clean),
 .current_raw(controller_raw),.current_fixed(controller_fixed),.current_payload(controller_payload),
 .current_clean(clean),.current_ce(ce),.current_bad(invalid),
 .context_next(context_next),.context_we(repair_context_we),
 .scrub_v(repair_scrub_v),.scrub_index(repair_index),.scrub_original(repair_original),.scrub_candidate(repair_candidate),
 .retire_ready(repair_retire_ready),.busy(correction_busy),.error(correction_error));
 ot_w2_nc6_coded_secondary_acyclic #(.OPT_PROTECTION(OPT_EXACT),.PC_ID(PC_ID)) secondary(
 .clk(clk),.rst_n(rst_n),.admission_stop(admission_stop),.table_state(table_state),
 .table_clean(table_clean),.table_bad(table_bad),.table_pending(count_pending),.offer_copies_drained(offer_drained),
 .other_clean(all_core_clean&&!context_live),.other_bad(any_core_bad),.logic_fault(core_bad),
 .reserve_roles(reserve_roles),.accept_intent(intents),.cancel_request(cancel_request),.reopen_epoch(reopen_epoch),
 .commit_roles(committed),.request_bank_open(request_open),.completion_bank_open(completion_open),
 .normal_permit(permit),.repair_busy(repair_busy),.fault(fault),
 .rearm_v(rearm_v),.provider_fenced(provider_fenced),.reverse_fenced(reverse_fenced),.reset_fenced(reset_fenced),
 .local_other_idle(core_idle),.rearm_ready(secondary_rearm),.local_idle(secondary_idle),
 .scrub_v(scrub_v),.scrub_index(scrub_index),.scrub_original(scrub_original),.scrub_repaired(scrub_repaired),.scrub_ready(scrub_ready),
 .inspect_original(secondary_raw),.inspect_corrected(secondary_fixed),.inspect_payload(secondary_payload),
 .inspect_clean(secondary_clean),.inspect_ce(secondary_ce),.inspect_bad(secondary_bad));
 assign idle=core_idle&&secondary_idle;
 assign rearm_rdy=secondary_rearm;
 initial if(NC!=6||MAX_OUT!=16||AW!=34||CTAGW!=32||GENW!=4||SIDW!=3||PTAGW!=35)
 $fatal(1,"full protected NC6/MAX16/AW34/customer32/gen4 required");

 // CURRENT-only views: never depend on permit, retirement or next-context.
 always_comb begin
 all_core_clean=1;any_core_bad=0;context_live=0;core_idle=1;
 for(view_i=0;view_i<NW;view_i=view_i+1)begin
 all_core_clean=all_core_clean&&clean[global_index(view_i)];
 any_core_bad=any_core_bad||invalid[global_index(view_i)];end
 for(view_i=0;view_i<8;view_i=view_i+1)begin
 X[view_i]=96'(get_record(145+3*view_i,3));
 context_clean[view_i]=clean[145+3*view_i]&&clean[146+3*view_i]&&clean[147+3*view_i];
 if(X[view_i][95]||!context_clean[view_i])context_live=1;
 end
 H=get_record(96,8);RQ=get_record(104,7);RD=get_record(112,7);WQ=41'(get_record(111,1));
 C=79'(get_record(187,2));rr=P[131][2:0];
 for(view_i=0;view_i<3;view_i=view_i+1)phase[view_i]=C[3*view_i+:3];
 for(view_i=0;view_i<9;view_i=view_i+1)J[view_i]=87'(get_record(169+2*view_i,2));
 for(view_i=0;view_i<6;view_i=view_i+1)begin Q[view_i]=65'(get_record(133+2*view_i,2));S[view_i]=P[119+view_i][4:0];end
 for(view_i=0;view_i<96;view_i=view_i+1)if(P[view_i][1:0]!=0||P[view_i][43])core_idle=0;
 if(H[0]||RQ[0]||RD[0]||WQ[0]||context_live)core_idle=0;
 for(view_i=0;view_i<9;view_i=view_i+1)if(J[view_i][86])core_idle=0;
 for(view_i=0;view_i<6;view_i=view_i+1)if(S[view_i][0]||Q[view_i][63])core_idle=0;
 end
 generate for(genvar re=0;re<8;re=re+1)begin:retirement_feedback
 if(re<6)assign repair_retire_ready[re]=primary_retire_offer[re];
 else assign repair_retire_ready[re]=primary_retire_offer[re]||(secondary_retire_offer[re]&&scrub_ready[re-6]);
 end endgenerate
 // Retirement eligibility does not consume next-context writeback.
 always_comb begin
 scrub_v=0;scrub_index=0;scrub_original=0;scrub_repaired=0;primary_retire_offer=0;secondary_retire_offer=0;
 retire_a=0;
 if(OPT_EXACT&&rst_n&&!any_core_bad&&!correction_error&&!core_bad)begin
 for(retire_e=0;retire_e<8;retire_e=retire_e+1)if(repair_scrub_v[retire_e])begin
 retire_a=integer'(repair_index[10*retire_e+:10]);
 if(retire_a<219&&ce[retire_a]&&!invalid[retire_a]&&raw[retire_a]==repair_original[72*retire_e+:72]&&fixed_word[retire_a]==repair_candidate[72*retire_e+:72])begin
 if(local_index(retire_a)>=0)primary_retire_offer[retire_e]=1;
 else if(retire_e>=6)begin
 scrub_v[retire_e-6]=1;scrub_index[10*(retire_e-6)+:10]=10'(retire_a);
 scrub_original[72*(retire_e-6)+:72]=repair_original[72*retire_e+:72];
 scrub_repaired[72*(retire_e-6)+:72]=repair_candidate[72*retire_e+:72];
 secondary_retire_offer[retire_e]=1;end
 end end end
 end
 // Semantic fault is independent of permit, bank eligibility and next state.
 always_comb begin
 core_bad=0;fault_i=0;fault_j=0;fault_k=0;fault_c=0;fault_a=0;fault_n=0;fault_slot=0;
 fault_row=0;fault_target=0;fault_key=0;fault_mask=0;fault_busy=0;
 if(rr>=6||phase[0]>5||phase[1]>4||phase[2]>4)core_bad=1;
 if(H[0]&&H[4:2]>=6||RQ[0]&&RQ[4:2]>=6||RD[0]&&RD[3:1]>=6||WQ[0]&&WQ[4:2]>=6)core_bad=1;
 if(H[0]&&!admission_stop&&H[4:2]<6)begin fault_c=integer'(H[4:2]);
 if(!c_req_v[fault_c]||c_req_we[fault_c]!=H[1]||c_req_addr[fault_c*34+:34]!=H[42:9]||
 c_req_tag[fault_c*32+:32]!=H[74:43]||c_req_gen[fault_c*4+:4]!=H[78:75]||c_req_data[fault_c*256+:256]!=H[334:79])core_bad=1;end
 if(all_core_clean)begin
 if((phase[0]!=0)!=H[0]||(phase[1]!=0)!=RQ[0]||(phase[2]!=0)!=WQ[0])core_bad=1;
 for(fault_n=0;fault_n<3;fault_n=fault_n+1)begin
 if(Q[2*fault_n][63]!=(phase[fault_n]>=2)||Q[2*fault_n+1][63]!=(phase[fault_n]>=3))core_bad=1;
 end
 end
 for(fault_i=0;fault_i<9;fault_i=fault_i+1)if(J[fault_i][86])begin
 fault_a=integer'(J[fault_i][81:72]);if(fault_a>=96)core_bad=1;
 else begin
 fault_target=44'(decode_data(J[fault_i][71:0]));
 if(J[fault_i][71:0]!=seal(fault_target,fault_a)||!qualified(P[fault_a],fault_target,J[fault_i][85:82],fault_i))core_bad=1;
 if(fault_i>=3&&fault_a/16!=fault_i-3)core_bad=1;
 if(fault_i==0&&fault_target[43]&&(!H[0]||fault_a!=16*integer'(H[4:2])+integer'(H[8:5])||fault_target[33:2]!=H[74:43]||fault_target[37:34]!=H[78:75]||fault_target[38]!=H[1]))core_bad=1;
 if(fault_i==1&&fault_target[1:0]==2&&(!RQ[0]||fault_a!=16*integer'(RQ[4:2])+integer'(Q[3][58:55])||fault_target[33:2]!=RQ[36:5]||fault_target[37:34]!=RQ[40:37]))core_bad=1;
 if(fault_i==1&&fault_target[1:0]==0&&(fault_a!=16*integer'(RD[3:1])+integer'(RD[7:4])||fault_target[33:2]!=RD[39:8]||fault_target[37:34]!=RD[43:40]))core_bad=1;
 if(fault_i==2&&(!WQ[0]||fault_a!=16*integer'(WQ[4:2])+integer'(Q[5][58:55])||fault_target[33:2]!=WQ[36:5]||fault_target[37:34]!=WQ[40:37]))core_bad=1;
 if(fault_i>=3&&fault_a!=16*(fault_i-3)+integer'(S[fault_i-3][4:1]))core_bad=1;
 end end
 if(all_core_clean)begin
 if(H[0]&&phase[0]==5&&H[4:2]<6)begin fault_a=16*integer'(H[4:2])+integer'(H[8:5]);fault_row=P[fault_a];
 if(fault_row[1:0]!=0||!fault_row[43]||fault_row[38]!=H[1]||fault_row[33:2]!=H[74:43]||fault_row[37:34]!=H[78:75])core_bad=1;end
 if(RD[0]&&RD[3:1]<6)begin fault_a=16*integer'(RD[3:1])+integer'(RD[7:4]);fault_row=P[fault_a];
 if(fault_row[1:0]!=2||fault_row[43]||fault_row[38]||fault_row[33:2]!=RD[39:8]||fault_row[37:34]!=RD[43:40])core_bad=1;end
 for(fault_i=0;fault_i<6;fault_i=fault_i+1)if(S[fault_i][0])begin fault_a=16*fault_i+integer'(S[fault_i][4:1]);
 if(P[fault_a][1:0]!=3||P[fault_a][43]||!P[fault_a][38])core_bad=1;end
 end
 if(all_core_clean&&!context_live&&OPT_EXACT&&rst_n)begin
 if(RQ[0]&&RQ[1]||WQ[0]&&WQ[1])core_bad=1;
 for(fault_n=0;fault_n<3;fault_n=fault_n+1)begin
 fault_c=(fault_n==0)?integer'(H[4:2]):(fault_n==1)?integer'(RQ[4:2]):integer'(WQ[4:2]);
 fault_key=(fault_n==0)?{H[4:2],H[74:43],H[78:75]}:(fault_n==1)?{RQ[4:2],RQ[36:5],RQ[40:37]}:{WQ[4:2],WQ[36:5],WQ[40:37]};
 if(phase[fault_n]!=0&&fault_c>=6)core_bad=1;
 if(fault_c<6&&!(fault_n==0&&admission_stop))begin
 if(phase[fault_n]==1&&fault_n==0)begin
 fault_busy=0;for(fault_j=0;fault_j<9;fault_j=fault_j+1)if(J[fault_j][86]&&integer'(J[fault_j][81:72])/16==fault_c)fault_busy=1;
 if(!fault_busy)for(fault_k=0;fault_k<16;fault_k=fault_k+1)begin fault_row=P[16*fault_c+fault_k];
 if((fault_row[1:0]!=0||fault_row[43])&&fault_row[33:2]==H[74:43]&&fault_row[37:34]==H[78:75]&&fault_row[38]==H[1])core_bad=1;
 end end
 if(phase[fault_n]==2)begin
 fault_mask=0;fault_slot=0;
 for(fault_k=15;fault_k>=0;fault_k=fault_k-1)begin fault_row=P[16*fault_c+fault_k];
 if(fault_n==0&&fault_row[1:0]==0&&!fault_row[43]||fault_n!=0&&fault_row[1:0]==1&&!fault_row[43]&&fault_row[38]==(fault_n==2)&&fault_row[33:2]==fault_key[35:4]&&fault_row[37:34]==fault_key[3:0])begin fault_mask[fault_k]=1;fault_slot=fault_k;end
 end
 if(!Q[2*fault_n][63]||Q[2*fault_n][64]||Q[2*fault_n][54:16]!=fault_key||Q[2*fault_n][15:0]!=fault_mask||Q[2*fault_n][58:55]!=4'(fault_slot)||
 (fault_n!=0&&popcount16(fault_mask)!=1)||fault_n==0&&fault_mask==0)core_bad=1;
 end
 if(phase[fault_n]==3)begin
 if(!Q[2*fault_n+1][63]||Q[2*fault_n+1][64]||Q[2*fault_n+1][54:16]!=fault_key)core_bad=1;
 else begin
 fault_a=16*fault_c+integer'(Q[2*fault_n+1][58:55]);fault_row=P[fault_a];
 if(fault_row[42:39]!=Q[2*fault_n+1][62:59])core_bad=1;
 if(fault_n==0)begin if(fault_row[1:0]!=0||fault_row[43])core_bad=1;end
 else if(fault_row[1:0]!=1||fault_row[43]||fault_row[38]!=(fault_n==2)||fault_row[33:2]!=fault_key[35:4]||fault_row[37:34]!=fault_key[3:0])core_bad=1;
 if(J[fault_n][86])core_bad=1;
 end end
 end end
 // Journal availability is checked from OLD state, before any handshake.
 if((H[0]&&phase[0]==5&&!admission_stop&&H[4:2]<6)&&p_req_rdy&&J[0][86])core_bad=1;
 if((RD[0]&&RD[3:1]<6)&&c_rsp_rdy[integer'(RD[3:1])]&&J[1][86])core_bad=1;
 for(fault_c=0;fault_c<6;fault_c=fault_c+1)if(S[fault_c][0]&&c_wr_done_rdy[fault_c]&&J[fault_c+3][86])core_bad=1;
 if(admission_stop&&H[0]&&H[4:2]<6&&(phase[0]==5||phase[0]==4&&!J[0][86])&&J[0][86])core_bad=1;
 end
 if(correction_error)core_bad=1;
 end
 // Pre-permit intents/status, isolated from state writeback and retire ready.
 always_comb begin
 count_pending=0;offer_drained=0;reopen_epoch=0;
 count_i=0;count_k=0;count_c=0;count_a=0;count_target=0;count_found=0;
 // Pending role0 contributes only when its count_target is ISSUED; role1 retirement
 // is identified by old RD_HELD, and local WR retire roles3..8 always count.
 count_target=44'(decode_data(J[0][71:0]));
 if(J[0][86]&&J[0][81:72]<96&&count_target[1:0]==1)count_pending[integer'(J[0][81:72])/16]=1;
 if(J[1][86]&&J[1][81:72]<96&&P[integer'(J[1][81:72])][1:0]==2)count_pending[integer'(J[1][81:72])/16]=1;
 for(count_i=3;count_i<9;count_i=count_i+1)if(J[count_i][86])count_pending[count_i-3]=1;
 for(count_i=0;count_i<6;count_i=count_i+1)begin
 offer_drained[count_i]=(!P[213+count_i][3]||((!H[0]||H[4:2]!=3'(count_i))&&(!Q[0][63]||Q[0][54:52]!=3'(count_i))&&
 (!Q[1][63]||Q[1][54:52]!=3'(count_i))&&(!J[0][86]||integer'(J[0][81:72])/16!=count_i)))&&
 (!P[213+count_i][4]||((!RD[0]||RD[3:1]!=3'(count_i))&&(!J[1][86]||integer'(J[1][81:72])/16!=count_i)))&&
 (!P[213+count_i][5]||(!S[count_i][0]&&!J[count_i+3][86]));
 if(P[213+count_i][7]&&P[213+count_i][2:0]==P[213+count_i][5:3]&&offer_drained[count_i]&&!count_pending[count_i]&&
 !P[207+count_i][3]&&!P[191+3*count_i][4])reopen_epoch[count_i]=1;
 end
 end
 // CURRENT pre-permit request and completion intents.
 always_comb begin
 cancel_request=0;reserve_roles=0;intents=0;req_offer=0;read_offer=0;wr_offer=0;candidate_intents=0;
 offer_i=0;offer_k=0;offer_c=0;offer_a=0;offer_target=0;offer_found=0;
 req_offer=H[0]&&phase[0]==5&&!admission_stop&&H[4:2]<6;
 read_offer=RD[0]&&RD[3:1]<6;
 for(offer_i=0;offer_i<6;offer_i=offer_i+1)wr_offer[offer_i]=S[offer_i][0];
 if(req_offer&&p_req_rdy)candidate_intents[3*integer'(H[4:2])]=1;
 if(read_offer&&c_rsp_rdy[integer'(RD[3:1])])candidate_intents[3*integer'(RD[3:1])+1]=1;
 for(offer_i=0;offer_i<6;offer_i=offer_i+1)if(wr_offer[offer_i]&&c_wr_done_rdy[offer_i])candidate_intents[3*offer_i+2]=1;
 intents=candidate_intents;
 // Reserve intent is offer_a CURRENT offer; only common permit commits it.
 offer_target=44'(decode_data(J[0][71:0]));
 if(all_core_clean&&!context_live&&OPT_EXACT&&rst_n)begin
 if(!H[0]&&phase[0]==0&&!admission_stop&&(!J[0][86]||(offer_target[1:0]==1&&C[9+:2]>=1)))begin
 offer_found=0;for(offer_k=0;offer_k<6;offer_k=offer_k+1)begin offer_c=integer'(rr)+offer_k;if(offer_c>=6)offer_c=offer_c-6;
 if(!offer_found&&c_req_v[offer_c]&&request_open[offer_c])begin offer_found=1;reserve_roles[3*offer_c]=1;end end end
 if(phase[1]==4&&RQ[0]&&!RD[0]&&RQ[4:2]<6)begin
 offer_c=integer'(RQ[4:2]);offer_a=16*offer_c+integer'(Q[3][58:55]);
 if((!J[1][86]&&P[offer_a][1:0]==2||J[1][86]&&C[11+:2]==3)&&completion_open[offer_c])reserve_roles[3*offer_c+1]=1;
 end
 for(offer_c=0;offer_c<6;offer_c=offer_c+1)if(!S[offer_c][0]&&completion_open[offer_c])begin
 offer_found=0;for(offer_k=0;offer_k<16;offer_k=offer_k+1)if(P[16*offer_c+offer_k][1:0]==3&&!P[16*offer_c+offer_k][43])offer_found=1;
 if(offer_found)reserve_roles[3*offer_c+2]=1;end
 if(admission_stop&&H[0]&&H[4:2]<6)begin offer_c=integer'(H[4:2]);
 if(P[213+offer_c][0]&&!P[213+offer_c][3])cancel_request[offer_c]=1;end
 end
 end
 always_comb begin
 WE=0;plan_bad=0;
 for(i=0;i<NW;i=i+1)D[i]=P[global_index(i)];
 context_changed=0;peer_repaired=0;
 for(i=0;i<8;i=i+1)Xn[i]=X[i];
 Hn=H;RQn=RQ;RDn=RD;WQn=WQ;Cn=C;rrn=rr;
 for(i=0;i<9;i=i+1)Jn[i]=J[i];
 for(i=0;i<6;i=i+1)begin Qn[i]=Q[i];Sn[i]=S[i];end
 row=0;target=0;key=0;mask=0;found=0;busy=0;
 j=0;k=0;c=0;a=0;n=0;slot=0;hits=0;choice=0;rc=0;wc=0;bank=0;offset=0;eng=0;owner=0;
 if(rr>=6||phase[0]>5||phase[1]>4||phase[2]>4)plan_bad=1;
 if(H[0]&&H[4:2]>=6||RQ[0]&&RQ[4:2]>=6||RD[0]&&RD[3:1]>=6||WQ[0]&&WQ[4:2]>=6)plan_bad=1;
 if(H[0]&&!admission_stop&&H[4:2]<6)begin c=integer'(H[4:2]);
 if(!c_req_v[c]||c_req_we[c]!=H[1]||c_req_addr[c*34+:34]!=H[42:9]||
 c_req_tag[c*32+:32]!=H[74:43]||c_req_gen[c*4+:4]!=H[78:75]||c_req_data[c*256+:256]!=H[334:79])plan_bad=1;end
 if(all_core_clean)begin
 if((phase[0]!=0)!=H[0]||(phase[1]!=0)!=RQ[0]||(phase[2]!=0)!=WQ[0])plan_bad=1;
 for(n=0;n<3;n=n+1)begin
 if(Q[2*n][63]!=(phase[n]>=2)||Q[2*n+1][63]!=(phase[n]>=3))plan_bad=1;
 end
 end
 for(i=0;i<9;i=i+1)if(J[i][86])begin
 a=integer'(J[i][81:72]);if(a>=96)plan_bad=1;
 else begin
 target=44'(decode_data(J[i][71:0]));
 if(J[i][71:0]!=seal(target,a)||!qualified(P[a],target,J[i][85:82],i))plan_bad=1;
 if(i>=3&&a/16!=i-3)plan_bad=1;
 if(i==0&&target[43]&&(!H[0]||a!=16*integer'(H[4:2])+integer'(H[8:5])||target[33:2]!=H[74:43]||target[37:34]!=H[78:75]||target[38]!=H[1]))plan_bad=1;
 if(i==1&&target[1:0]==2&&(!RQ[0]||a!=16*integer'(RQ[4:2])+integer'(Q[3][58:55])||target[33:2]!=RQ[36:5]||target[37:34]!=RQ[40:37]))plan_bad=1;
 if(i==1&&target[1:0]==0&&(a!=16*integer'(RD[3:1])+integer'(RD[7:4])||target[33:2]!=RD[39:8]||target[37:34]!=RD[43:40]))plan_bad=1;
 if(i==2&&(!WQ[0]||a!=16*integer'(WQ[4:2])+integer'(Q[5][58:55])||target[33:2]!=WQ[36:5]||target[37:34]!=WQ[40:37]))plan_bad=1;
 if(i>=3&&a!=16*(i-3)+integer'(S[i-3][4:1]))plan_bad=1;
 end end
 // Outputs are frozen tuples from coded records, never the live input bus.
 c_req_rdy=0;c_rsp_v=0;c_wr_done_v=0;c_rsp_tag=0;c_rsp_gen=0;c_rsp_data=0;c_wr_done_tag=0;c_wr_done_gen=0;
 p_req_v=0;p_req_we=H[1];p_req_addr=H[42:9];p_req_tag={H[4:2],H[74:43]};p_req_gen=H[78:75];p_req_data=H[334:79];
 p_rsp_rdy=0;p_wr_done_ready=0;
 if(all_core_clean)begin
 if(H[0]&&phase[0]==5&&H[4:2]<6)begin a=16*integer'(H[4:2])+integer'(H[8:5]);row=P[a];
 if(row[1:0]!=0||!row[43]||row[38]!=H[1]||row[33:2]!=H[74:43]||row[37:34]!=H[78:75])plan_bad=1;end
 if(RD[0]&&RD[3:1]<6)begin a=16*integer'(RD[3:1])+integer'(RD[7:4]);row=P[a];
 if(row[1:0]!=2||row[43]||row[38]||row[33:2]!=RD[39:8]||row[37:34]!=RD[43:40])plan_bad=1;end
 for(i=0;i<6;i=i+1)if(S[i][0])begin a=16*i+integer'(S[i][4:1]);
 if(P[a][1:0]!=3||P[a][43]||!P[a][38])plan_bad=1;end
 end
 if(permit&&!core_bad&&OPT_EXACT&&rst_n)begin
 p_req_v=req_offer;if(req_offer)c_req_rdy[integer'(H[4:2])]=p_req_rdy;
 p_rsp_rdy=!RQ[0]&&phase[1]==0&&!RD[0]&&!J[1][86];
 p_wr_done_ready=!WQ[0]&&phase[2]==0&&!J[2][86];
 if(read_offer)begin c=integer'(RD[3:1]);c_rsp_v[c]=1;c_rsp_tag[c*32+:32]=RD[39:8];c_rsp_gen[c*4+:4]=RD[43:40];c_rsp_data[c*256+:256]=RD[299:44];end
 for(i=0;i<6;i=i+1)if(wr_offer[i])begin a=16*i+integer'(S[i][4:1]);
 c_wr_done_v[i]=1;c_wr_done_tag[i*32+:32]=P[a][33:2];c_wr_done_gen[i*4+:4]=P[a][37:34];end
 end
 if(all_core_clean&&!context_live&&OPT_EXACT&&rst_n)begin
 // Plan from OLD records/intents; the common permit gates every write below.
 // Matching faults are independent of permit, avoiding a ready/fault loop.
 if(RQ[0]&&RQ[1]||WQ[0]&&WQ[1])plan_bad=1;
 target=44'(decode_data(J[0][71:0]));
 if(!H[0]&&phase[0]==0&&!admission_stop&&(!J[0][86]||(target[1:0]==1&&C[9+:2]>=1)))begin
 found=0;
 for(k=0;k<6;k=k+1)begin c=integer'(rr)+k;if(c>=6)c=c-6;
 if(!found&&c_req_v[c]&&request_open[c])begin
 found=1;Hn=0;Hn[0]=1;Hn[1]=c_req_we[c];Hn[4:2]=3'(c);
 Hn[42:9]=c_req_addr[34*c+:34];Hn[74:43]=c_req_tag[32*c+:32];
 Hn[78:75]=c_req_gen[4*c+:4];Hn[334:79]=c_req_data[256*c+:256];
 Cn[2:0]=1;
 end end end
 if(p_rsp_v&&p_rsp_rdy)begin
 RQn=0;RQn[0]=1;RQn[4:2]=p_rsp_tag[34:32];RQn[36:5]=p_rsp_tag[31:0];RQn[40:37]=p_rsp_gen;RQn[296:41]=p_rsp_data;
 RQn[1]=req_offer&&p_req_rdy&&!H[1]&&p_rsp_tag=={H[4:2],H[74:43]}&&p_rsp_gen==H[78:75];Cn[5:3]=1;
 end
 if(p_wr_done_v&&p_wr_done_ready)begin
 WQn=0;WQn[0]=1;WQn[4:2]=p_wr_done_tag[34:32];WQn[36:5]=p_wr_done_tag[31:0];WQn[40:37]=p_wr_done_gen;
 WQn[1]=req_offer&&p_req_rdy&&H[1]&&p_wr_done_tag=={H[4:2],H[74:43]}&&p_wr_done_gen==H[78:75];Cn[8:6]=1;
 end
 for(n=0;n<3;n=n+1)begin
 c=(n==0)?integer'(H[4:2]):(n==1)?integer'(RQ[4:2]):integer'(WQ[4:2]);
 key=(n==0)?{H[4:2],H[74:43],H[78:75]}:(n==1)?{RQ[4:2],RQ[36:5],RQ[40:37]}:{WQ[4:2],WQ[36:5],WQ[40:37]};
 if(phase[n]!=0&&c>=6)plan_bad=1;
 if(c<6&&phase[n]==1&&!(n==0&&admission_stop))begin
 busy=0;for(j=0;j<9;j=j+1)if(J[j][86]&&integer'(J[j][81:72])/16==c)busy=1;
 if(!busy)begin
 mask=0;hits=0;slot=0;
 for(k=15;k>=0;k=k-1)begin a=16*c+k;row=P[a];
 if(n==0)begin
 if((row[1:0]!=0||row[43])&&row[33:2]==H[74:43]&&row[37:34]==H[78:75]&&row[38]==H[1])plan_bad=1;
 if(row[1:0]==0&&!row[43])begin mask[k]=1;slot=k;hits=hits+1;end
 end else if(row[1:0]==1&&!row[43]&&row[38]==(n==2)&&row[33:2]==key[35:4]&&row[37:34]==key[3:0])begin mask[k]=1;slot=k;hits=hits+1;end
 end
 Qn[2*n]=0;Qn[2*n][15:0]=mask;Qn[2*n][54:16]=key;Qn[2*n][58:55]=4'(slot);
 Qn[2*n][62:59]=P[16*c+slot][42:39];Qn[2*n][63]=1;Qn[2*n][64]=(n==0)?hits==0:hits!=1;
 Cn[3*n+:3]=2;
 end end
 if(c<6&&phase[n]==2&&!(n==0&&admission_stop))begin
 mask=0;slot=0;
 for(k=15;k>=0;k=k-1)begin row=P[16*c+k];
 if(n==0&&row[1:0]==0&&!row[43]||n!=0&&row[1:0]==1&&!row[43]&&row[38]==(n==2)&&row[33:2]==key[35:4]&&row[37:34]==key[3:0])begin mask[k]=1;slot=k;end
 end
 if(!Q[2*n][63]||Q[2*n][64]||Q[2*n][54:16]!=key||Q[2*n][15:0]!=mask||Q[2*n][58:55]!=4'(slot)||
 (n!=0&&popcount16(mask)!=1)||n==0&&mask==0)plan_bad=1;
 else begin Qn[2*n+1]=Q[2*n];Cn[3*n+:3]=3;end
 end
 if(c<6&&phase[n]==3&&!(n==0&&admission_stop))begin
 if(!Q[2*n+1][63]||Q[2*n+1][64]||Q[2*n+1][54:16]!=key)plan_bad=1;
 else begin
 a=16*c+integer'(Q[2*n+1][58:55]);row=P[a];target=row;
 if(row[42:39]!=Q[2*n+1][62:59])plan_bad=1;
 if(n==0)begin
 if(row[1:0]!=0||row[43])plan_bad=1;
 target[43]=1;target[38]=H[1];target[37:34]=H[78:75];target[33:2]=H[74:43];Hn[8:5]=Q[1][58:55];
 end else begin
 if(row[1:0]!=1||row[43]||row[38]!=(n==2)||row[33:2]!=key[35:4]||row[37:34]!=key[3:0])plan_bad=1;
 target[1:0]=(n==1)?2:3;
 end
 prepare(n,a,target);Cn[3*n+:3]=4;
 end end
 end
 // Prepared journal holds the sealed target/address/version for FOUR edges.
 for(j=0;j<9;j=j+1)if(J[j][86]&&J[j][81:72]<96)begin
 a=integer'(J[j][81:72]);target=44'(decode_data(J[j][71:0]));
 if(C[9+2*j+:2]==3)begin
 D[local_index(a)]=target;WE[local_index(a)]=1;Jn[j]=0;Cn[9+2*j+:2]=0;
 if(j==0&&phase[0]==4)begin
 if(target[43])Cn[2:0]=5;
 else begin Hn[0]=0;Qn[0]=0;Qn[1]=0;Cn[2:0]=0;end
 end
 if(j==2)begin WQn[0]=0;Qn[4]=0;Qn[5]=0;Cn[8:6]=0;end
 end else Cn[9+2*j+:2]=C[9+2*j+:2]+1'b1;
 end
 // Read delivery is reserved before asserting valid. The journal-commit edge
 // may publish from its qualified target, without an extra unpriced bubble.
 if(phase[1]==4&&RQ[0]&&!RD[0]&&RQ[4:2]<6)begin
 c=integer'(RQ[4:2]);a=16*c+integer'(Q[3][58:55]);
 if((!J[1][86]&&P[a][1:0]==2||J[1][86]&&C[11+:2]==3)&&completion_open[c])begin
 RDn=0;RDn[0]=1;RDn[3:1]=3'(c);RDn[7:4]=Q[3][58:55];RDn[39:8]=RQ[36:5];RDn[43:40]=RQ[40:37];RDn[299:44]=RQ[296:41];
 RQn[0]=0;Qn[2]=0;Qn[3]=0;Cn[5:3]=0;
 end end
 for(c=0;c<6;c=c+1)if(!S[c][0]&&completion_open[c])begin
 found=0;for(k=15;k>=0;k=k-1)if(P[16*c+k][1:0]==3&&!P[16*c+k][43])begin found=1;slot=k;end
 if(found)begin Sn[c]={4'(slot),1'b1};end
 end
 if(candidate_intents!=0)begin
 if(H[4:2]<6&&candidate_intents[3*integer'(H[4:2])])begin
 a=16*integer'(H[4:2])+integer'(H[8:5]);target=P[a];target[1:0]=1;target[43]=0;
 prepare(0,a,target);Hn[0]=0;Qn[0]=0;Qn[1]=0;Cn[2:0]=0;rrn=(H[4:2]==5)?0:H[4:2]+1'b1;
 end
 if(RD[3:1]<6&&candidate_intents[3*integer'(RD[3:1])+1])begin
 a=16*integer'(RD[3:1])+integer'(RD[7:4]);target=P[a];target[1:0]=0;target[42:39]=target[42:39]+1'b1;
 prepare(1,a,target);RDn[0]=0;
 end
 for(c=0;c<6;c=c+1)if(candidate_intents[3*c+2])begin
 a=16*c+integer'(S[c][4:1]);target=P[a];target[1:0]=0;target[42:39]=target[42:39]+1'b1;
 prepare(3+c,a,target);Sn[c][0]=0;
 end end
 // Stop cancels only the unaccepted source reservation, never an issued row.
 if(admission_stop&&H[0]&&H[4:2]<6)begin
 c=integer'(H[4:2]);
 if(phase[0]>0&&phase[0]<4)begin Hn[0]=0;Qn[0]=0;Qn[1]=0;Cn[2:0]=0;end
 else if(phase[0]==5||phase[0]==4&&!J[0][86])begin
 a=16*c+integer'(H[8:5]);target=P[a];target[43]=0;target[42:39]=target[42:39]+1'b1;
 prepare(0,a,target);Cn[2:0]=4;
 end end
 if(Hn!=H)put_record(96,8,Hn);
 if(RQn!=RQ)put_record(104,7,RQn);
 if(WQn!=WQ)put_record(111,1,352'(WQn));
 if(RDn!=RD)put_record(112,7,RDn);
 if(rrn!=rr)put_record(131,1,352'(rrn));
 for(i=0;i<6;i=i+1)begin
 if(Sn[i]!=S[i])put_record(119+i,1,352'(Sn[i]));
 if(Qn[i]!=Q[i])put_record(133+2*i,2,352'(Qn[i]));
 end
 for(i=0;i<9;i=i+1)if(Jn[i]!=J[i])put_record(169+2*i,2,352'(Jn[i]));
 if(Cn!=C)put_record(187,2,352'(Cn));
 end
 // No late semantic error or quarantined edge may modify primary debt.
 if(!permit||core_bad||!OPT_EXACT||!rst_n)begin
 WE=0;p_req_v=0;c_req_rdy=0;p_rsp_rdy=0;p_wr_done_ready=0;c_rsp_v=0;c_wr_done_v=0;
 end
 // Actual correction commit and context writeback, after eligibility.
 if(OPT_EXACT&&rst_n&&!any_core_bad&&!correction_error)begin
 for(eng=0;eng<8;eng=eng+1)if(repair_scrub_v[eng]&&repair_retire_ready[eng])begin
 a=integer'(repair_index[10*eng+:10]);
 if(a<219&&local_index(a)>=0)begin D[local_index(a)]=P[a];WE[local_index(a)]=1;end
 end
 for(eng=0;eng<8;eng=eng+1)if(repair_context_we[eng])put_record(145+3*eng,3,352'(context_next[96*eng+:96]));
 end
 if(correction_error)plan_bad=1;
 if(plan_bad||core_bad)WE=0;
 end
 always_ff @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin for(integer x=0;x<NW;x=x+1)cw[x]<=seal(0,global_index(x));end
 else if(OPT_EXACT)begin for(integer x=0;x<NW;x=x+1)if(WE[x])cw[x]<=encoded[x];end
 end
endmodule
