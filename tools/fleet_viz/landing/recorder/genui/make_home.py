"""A realistic user home for the generative file-manager case: documents, photos (real JPEGs with EXIF), code projects (git), downloads."""
import os, random, datetime, subprocess, json, sys
from PIL import Image
random.seed(7)
H = sys.argv[1]; os.makedirs(H, exist_ok=True)
def touch(p, txt=None, size=None, when=None):
    p = os.path.join(H, p); os.makedirs(os.path.dirname(p), exist_ok=True)
    if txt is not None: open(p, 'w').write(txt)
    elif size is not None:
        with open(p, 'wb') as f: f.truncate(size)
    if when: t = when.timestamp(); os.utime(p, (t, t))
D = lambda s: datetime.datetime.fromisoformat(s)
# Documents
touch('Documents/Housing/lease_2025-2026_signed.txt', """RESIDENTIAL LEASE AGREEMENT\nLandlord: Harbor View Properties LLC\nTenant: Maya Okafor\nPremises: 1420 Alder St, Apt 3B, Seattle WA 98122\nTerm: 2025-11-01 to 2026-10-31 (12 months)\nMonthly rent: $2,450 due on the 1st; late fee $75 after the 5th.\nSecurity deposit: $2,450.\nRenewal: tenant must give written notice of intent to renew or vacate 60 days before the end of term (by 2026-09-01).\nPets: one cat permitted, pet rent $40/month.\n""", when=D('2025-10-14 19:02'))
touch('Documents/Housing/renewal_offer_2026.txt', "Harbor View Properties: renewal offer for Apt 3B. New rent from 2026-11-01: $2,595/month (+5.9%). 12-month term. Reply by 2026-10-15.\n", when=D('2026-09-22 10:31'))
touch('Documents/Housing/move_checklist.md', "# If we move\n- [ ] give notice by Sep 1 (missed!)\n- [x] look at Capitol Hill 2BRs\n- [ ] ask about parking\n", when=D('2026-08-03 22:10'))
touch('Documents/Taxes/2025/W-2_Brightline_Health.txt', "Form W-2 2025\nEmployer: Brightline Health Inc.\nEmployee: Maya Okafor\nWages: 148,250.00\nFederal tax withheld: 27,904.12\nState: WA (no income tax)\n", when=D('2026-01-29 08:15'))
touch('Documents/Taxes/2025/1099-INT_ally.txt', "1099-INT 2025 Ally Bank. Interest income: 1,184.37\n", when=D('2026-02-02 09:00'))
touch('Documents/Taxes/2025/charitable_receipts.csv', "date,org,amount\n2025-03-14,Seattle Food Bank,250\n2025-06-01,KEXP,120\n2025-12-20,Doctors Without Borders,400\n", when=D('2026-02-11 20:40'))
touch('Documents/Taxes/2025/return_2025_filed.pdf', size=412_331, when=D('2026-04-09 21:55'))
touch('Documents/Taxes/2024/return_2024_filed.pdf', size=398_772, when=D('2025-04-12 18:20'))
touch('Documents/Work/Q3_review_notes.md', "# Q3 review prep\n- shipped the claims triage model (precision 0.91 at 0.8 recall)\n- led 2 interns\n- ask: move to staff track; comp band L5 -> L6\n", when=D('2026-09-29 23:12'))
touch('Documents/Work/offsite_agenda_oct.md', "# Team offsite, Oct 21-22, Leavenworth\nDay 1: roadmap 2027, model monitoring\nDay 2: hike + retro\n", when=D('2026-10-02 14:05'))
touch('Documents/Work/Brightline_benefits_2026.pdf', size=1_904_220, when=D('2026-01-05 09:12'))
touch('Documents/Personal/resume_maya_okafor_2026.pdf', size=88_410, when=D('2026-07-18 11:47'))
touch('Documents/Personal/passport_scan.pdf', size=2_310_552, when=D('2024-05-02 16:30'))
touch('Documents/Personal/car_insurance_policy_2026.pdf', size=640_118, when=D('2026-03-01 12:00'))
touch('Documents/Personal/recipes/jollof_rice.md', "# Mum's jollof\n- 3 cups long-grain rice, parboiled\n- tomato/pepper base: 6 roma, 2 red bell, 1 scotch bonnet, 2 onions\n- bay leaves, thyme, curry powder\n", when=D('2025-12-23 17:20'))
touch('Documents/Personal/recipes/miso_salmon.md', "# Miso salmon\n2 tbsp white miso, 1 tbsp mirin, 1 tsp honey. 12 min at 220C.\n", when=D('2026-02-14 19:00'))
touch('Documents/Personal/budget_2026.csv', "month,rent,groceries,transport,eating_out,travel,savings\n" + "\n".join(f"2026-{m:02d},2450,{random.randint(520,780)},{random.randint(90,180)},{random.randint(180,420)},{[0,0,0,1240,0,0,2890,0,410][m-1]},{random.randint(2200,3100)}" for m in range(1, 10)) + "\n", when=D('2026-10-01 21:30'))
touch('Documents/notes/books_2026.md', "# Read 2026\n- The Overstory (5/5)\n- Klara and the Sun (4/5)\n- Designing Data-Intensive Applications, 2nd ed (re-read)\n", when=D('2026-09-10 23:01'))
touch('Documents/notes/gift_ideas.md', "- Dad: Leica lens cap, bird book\n- Ife: climbing shoes size 39\n", when=D('2026-08-28 08:44'))
# Photos: real JPEGs with EXIF date / camera / GPS
trips = [('2026/2026-04 Lisbon', 'Lisbon', (38.7223, -9.1393), '2026-04-11', 23, 'FUJIFILM', 'X100VI'),
         ('2026/2026-07 Olympic NP', 'Olympic National Park', (47.8021, -123.6044), '2026-07-03', 18, 'Apple', 'iPhone 16 Pro'),
         ('2026/2026-09 Ife wedding', 'Portland', (45.5152, -122.6784), '2026-09-13', 31, 'SONY', 'ILCE-7M4'),
         ('2025/2025-12 Lagos', 'Lagos', (6.5244, 3.3792), '2025-12-21', 16, 'Apple', 'iPhone 15 Pro')]
def dms(x):
    x = abs(x); d = int(x); m = int((x - d) * 60); s = round(((x - d) * 60 - m) * 60 * 100)
    from PIL.TiffImagePlugin import IFDRational as R
    return (R(d, 1), R(m, 1), R(s, 100))
for folder, place, (la, lo), day0, n, make, model in trips:
    for i in range(n):
        dt = D(day0 + ' 09:00') + datetime.timedelta(days=i // 7, hours=random.randint(0, 10), minutes=random.randint(0, 59))
        w, h = random.choice([(640, 427), (427, 640), (640, 480)])
        img = Image.new('RGB', (w, h), tuple(random.randint(40, 220) for _ in range(3)))
        ex = Image.Exif(); ex[0x010F] = make; ex[0x0110] = model; ex[0x0132] = dt.strftime('%Y:%m:%d %H:%M:%S')
        g = {1: 'N' if la >= 0 else 'S', 2: dms(la + random.uniform(-0.02, 0.02)), 3: 'E' if lo >= 0 else 'W', 4: dms(lo + random.uniform(-0.02, 0.02))}
        ex[0x8825] = g
        name = f"{'IMG' if make == 'Apple' else 'DSCF' if make == 'FUJIFILM' else 'DSC'}_{random.randint(1000, 9999)}.jpg"
        p = os.path.join(H, 'Pictures', folder, name); os.makedirs(os.path.dirname(p), exist_ok=True)
        img.save(p, quality=70, exif=ex); os.utime(p, (dt.timestamp(), dt.timestamp()))
touch('Pictures/Screenshots/Screenshot 2026-10-06 at 14.22.10.png', size=402_118, when=D('2026-10-06 14:22'))
touch('Pictures/Screenshots/Screenshot 2026-09-30 at 09.01.44.png', size=1_220_904, when=D('2026-09-30 09:01'))
# Code projects (git)
def repo(path, files, msgs):
    for f, txt in files.items(): touch(os.path.join(path, f), txt)
    full = os.path.join(H, path); env = dict(os.environ, GIT_AUTHOR_NAME='Maya Okafor', GIT_AUTHOR_EMAIL='maya@example.com', GIT_COMMITTER_NAME='Maya Okafor', GIT_COMMITTER_EMAIL='maya@example.com')
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=full, check=True)
    for i, (m, when) in enumerate(msgs):
        open(os.path.join(full, 'CHANGELOG'), 'a').write(m + '\n')
        subprocess.run(['git', 'add', '-A'], cwd=full, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', m, '--date', when], cwd=full, check=True, env=dict(env, GIT_COMMITTER_DATE=when))
repo('code/plant-watering-bot', {'README.md': '# plant-watering-bot\nESP32 + soil moisture sensor; posts to a Discord channel when the monstera is thirsty.\n',
     'src/main.py': 'import machine, time\nSENSOR = machine.ADC(34)\nTHRESH = 2100\n\nwhile True:\n    if SENSOR.read() > THRESH:\n        notify("water me")\n    time.sleep(3600)\n', 'requirements.txt': 'requests\n'},
     [('initial sketch', '2026-03-02T21:00:00'), ('calibrate threshold', '2026-03-09T20:15:00'), ('discord webhook', '2026-05-17T11:40:00')])
repo('code/claims-triage-notebooks', {'README.md': '# claims-triage (work, personal copy of public notebooks)\n', 'eval.ipynb': '{"cells": [], "nbformat": 4, "nbformat_minor": 5}\n', 'metrics.json': json.dumps({'precision': 0.91, 'recall': 0.8, 'auc': 0.947}) + '\n'},
     [('eval harness', '2026-06-11T10:00:00'), ('threshold sweep', '2026-08-20T16:30:00')])
repo('code/dotfiles', {'.zshrc': 'export EDITOR=nvim\nalias gs="git status"\n', 'nvim/init.lua': 'vim.opt.number = true\n'}, [('zsh + nvim', '2025-11-30T13:00:00')])
# Downloads
for f, sz, w in [('Zoom-6.2.5.dmg', 98_200_000, '2026-02-03 08:10'), ('Docker.dmg', 712_400_000, '2026-05-21 19:44'), ('Docker (1).dmg', 712_400_000, '2026-08-02 10:05'),
                 ('Obsidian-1.9.12.dmg', 176_300_000, '2026-06-30 22:15'), ('Firefox 141.0.dmg', 138_900_000, '2026-07-15 12:00'),
                 ('Capitol_Hill_2BR_listing.pdf', 2_840_112, '2026-08-04 07:58'), ('wedding_playlist.m3u', 3_412, '2026-09-01 20:20'),
                 ('IMG_4471.HEIC', 3_110_220, '2026-09-14 11:02'), ('boarding_pass_SEA-LIS.pdf', 210_440, '2026-04-10 05:30'),
                 ('Brightline_Q3_allhands.mp4', 1_480_000_000, '2026-10-03 17:25'), ('invoice_ikea_88213.pdf', 98_112, '2026-08-19 13:13'),
                 ('node-v22.11.0.pkg', 89_700_000, '2026-01-12 21:00'), ('lease_2025-2026_signed (1).txt', None, '2025-10-14 19:05')]:
    if sz is None: touch('Downloads/' + f, open(os.path.join(H, 'Documents/Housing/lease_2025-2026_signed.txt')).read(), when=D(w))
    else: touch('Downloads/' + f, size=sz, when=D(w))
touch('Desktop/todo.txt', 'renew lease or not?? decide by Oct 15\nbook Leavenworth carpool\ncall Mom Sunday\n', when=D('2026-10-07 08:01'))
touch('Desktop/flight_LIS_receipt.pdf', size=180_002, when=D('2026-03-02 14:00'))
touch('Music/Ife_wedding_first_dance.m4a', size=8_902_331, when=D('2026-09-01 20:25'))
touch('.ssh/config', 'Host github.com\n  User git\n', when=D('2025-11-30 13:10')); touch('.bash_history', 'ls\ncd code\n', when=D('2026-10-08 22:00'))
touch('.Trash/old_resume_2023.pdf', size=74_000, when=D('2026-07-18 11:50'))
print('ok')
