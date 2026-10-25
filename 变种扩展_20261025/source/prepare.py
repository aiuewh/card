from pathlib import Path
import json, hashlib, re, zipfile
from PIL import Image, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
APP = Path(r'C:\1MC\1')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
release = json.loads((ROOT/'_black_auction_v1/current-release.json').read_text('utf-8-sig'))
card = ROOT/release['canonicalFile']
assert sha(card) == release['sha256']
data = json.loads(card.read_text('utf-8-sig'))
terminal = next(s['content'] for s in data['data']['extensions']['tavern_helper']['scripts'] if s['name']=='终端')
def block(name):
    return re.search(r'var '+name+r'\s*=\s*\[(.*?)\n\s*\];',terminal,re.S).group(1)
types = sorted(set(re.findall(r"type:\s*'([^']+)'",block('PLANET_TEMPLATES')+block('HABITABLE_WORLD_PROFILES'))))
print('Current generator types:',types)
specs = [
 ('continental','大陆世界',[('terrestrialclouds','Terrestrial','碧海长陆',2026102501,2200,.20),('terrestrialclouds','Alpine','雪岭群陆',2026102502,3100,.65)]),
 ('ocean','海洋世界',[('terrestrialclouds','Oceanic','深蓝群岛',2026102511,1600,.20),('terrestrialclouds','Oceanic','破碎海盆',2026102512,3200,.70)]),
 ('desert','沙漠世界',[('plain','Oasis','沙海绿洲',2026102521,1700,.20),('crackedandcratered','Dry','龟裂旱海',2026102522,2700,.70)]),
 ('tundra','寒冷世界',[('terrestrialclouds','Tundral','苔原冻海',2026102531,1800,.20),('terrestrialclouds','Alpine','高纬雪原',2026102532,2800,.70)]),
 ('tropical','热带世界',[('terrestrialclouds','Tropical','雨林大洋',2026102541,1800,.20),('terrestrialclouds','Wetlands','湿地水网',2026102542,3000,.70)]),
 ('molten','熔岩世界',[('violent','Volcanic','熔脉焦壳',2026102551,1800,.20),('violent','Volcanic','赤热裂域',2026102552,3200,.70)]),
 ('toxic','毒气世界',[('venusianclouds','Venusian','硫雾涡旋',2026102561,2000,.05),('venusianclouds','Venusian','绛色毒霭',2026102562,2000,.45)]),
 ('barren','荒原世界',[('cratered','Martian','赤砂陨原',2026102571,1800,.20),('cratered','Rock','灰岩环坑',2026102572,2600,.70)]),
 ('gas_giant','气态巨行星',[('gasgiant','Gas Giant','琥珀风带',2026102581,2000,.05),('gasgiant','Gas Giant','绯云巨涡',2026102582,2000,.40)]),
 ('ice_giant','冰巨星',[('gasgiant','Gas Giant','青蓝风带',2026102591,2000,.50),('gasgiant','Gas Giant','青碧风暴',2026102592,2000,.78)]),
 ('frozen','冰封世界',[('crackedandcratered','Ice','裂冰大洋',2026102601,2000,.20),('crackedandcratered','Ice','霜白裂原',2026102602,3300,.70)]),
 ('frozen_dwarf','冰封矮星',[('cratered','Ice','密坑冰壳',2026102611,1400,.20),('crackedandcratered','Ice','古裂冰丘',2026102612,2400,.70)])
]
assert set(types)==set(s[1] for s in specs)
existing_keys={
 'continental':['TexturesForPlanets-TerrestrialWorldsPack/Terrestrial1.png'],
 'ocean':['TexturesForPlanets-TerrestrialWorldsPack/Terrestrial3.png'],
 'desert':['TexturesForPlanets-InhospitableWorldsPack/Martian.png'],
 'tundra':['TexturesForPlanets-InhospitableWorldsPack/Icy.png'],
 'tropical':['TexturesForPlanets-TerrestrialWorldsPack/Terrestrial2.png'],
 'molten':['TexturesForPlanets-InhospitableWorldsPack/Volcanic.png'],
 'toxic':['TexturesForPlanets-InhospitableWorldsPack/Venusian.png','4k_venus_atmosphere.jpg'],
 'barren':['TexturesForPlanets-InhospitableWorldsPack/Martian.png'],
 'gas_giant':['TexturesForPlanets-GasGiantPack/Gaseous2.png','TexturesForPlanets-GasGiantPack/Gaseous4.png','8k_jupiter.jpg','8k_saturn.jpg'],
 'ice_giant':['TexturesForPlanets-GasGiantPack/Gaseous3.png','2k_neptune.jpg','2k_uranus.jpg'],
 'frozen':['TexturesForPlanets-InhospitableWorldsPack/Icy.png'],
 'frozen_dwarf':['4k_ceres_fictional.jpg','4k_eris_fictional.jpg','4k_haumea_fictional.jpg','4k_makemake_fictional.jpg']
}
records=[]; categories=[]
for key,label,variants in specs:
    existing=[]
    for name in existing_keys[key]:
        p=ROOT/'星球'/'_stargazer_repo'/name if '/' in name else ROOT/'星球'/'Solar System Scope Textures'/name
        with Image.open(p) as im: size=im.size
        existing.append({'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'size':size})
    categories.append({'id':key,'type':label,'existing':existing})
    for i,(template,colour,name,seed,iterations,palette) in enumerate(variants,1):
        records.append({'id':f'{key}_v{i:02}','category':key,'type':label,'name':name,'template':template,'colourizer':colour,'seed':seed,'iterations':iterations,'palette':palette,'clouds':key in ['continental','ocean','desert','tundra','tropical'],'variant':i,'width':2048,'height':1024})
sources=[card,ROOT/'_black_auction_v1/current-release.json',ROOT/'src/terminal.js',ROOT/'蔚蓝星域的观星者_3.3_航程档案候选版.json',APP/'Textures for Planets/TexturesForPlanets.exe']
sources+=list((APP/'Templates').glob('*.tfp'))+list((APP/'Colourizers').glob('*.col'))+list((APP/'Tools').glob('*.tool'))
sources+=list((ROOT/'星球/stargazer-textures').rglob('*.png'))+list((ROOT/'星球/_stargazer_repo').rglob('*.png'))+list((ROOT/'星球/Solar System Scope Textures').glob('*'))
lock={'canonicalFile':release['canonicalFile'],'canonicalSha256':release['sha256'],'sources':[{'file':str(p),'sha256':sha(p)} for p in sources if p.is_file()]}
(OUT/'source-lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2),'utf-8')
(OUT/'plan.json').write_text(json.dumps({'categories':categories,'variants':records},ensure_ascii=False,indent=2),'utf-8')
(OUT/'source/jobs.tsv').write_text('\n'.join('\t'.join(str(r[k]).lower() if isinstance(r[k],bool) else str(r[k]) for k in ['id','template','colourizer','seed','iterations','palette','clouds','variant']) for r in records),'utf-8')
font=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',20)
sheet=Image.new('RGB',(1200,len(categories)*164),(10,17,27)); draw=ImageDraw.Draw(sheet)
for y,cat in enumerate(categories):
    draw.text((16,y*164+15),cat['type'],font=font,fill='white')
    for x,old in enumerate(cat['existing']):
        im=Image.open(ROOT/old['file']).convert('RGB'); im.thumbnail((245,123)); sheet.paste(im,(170+x*255,y*164+6))
        draw.text((170+x*255,y*164+130),Path(old['file']).stem,font=font,fill='#a8c4d2')
sheet.save(OUT/'已有贴图核对.jpg',quality=90)
gas=zipfile.ZipFile(APP/'Colourizers/gas.col'); ns=[n for n in gas.namelist() if n.startswith('colours') and n.endswith('.png')]
sheet=Image.new('RGB',(640,140*((len(ns)+3)//4)),(15,20,28)); draw=ImageDraw.Draw(sheet)
for i,n in enumerate(ns):
    im=Image.open(gas.open(n)).convert('RGB'); im.thumbnail((150,110)); x=(i%4)*160;y=(i//4)*140;sheet.paste(im,(x,y)); draw.text((x,y+112),f'{i}: {n}',fill='white')
sheet.save(OUT/'source/gas-palettes.jpg',quality=92)
print('24 variants planned, source fingerprints recorded.')
