from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import json,hashlib,zipfile,html

OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
lock=json.loads((OUT/'source-lock.json').read_text('utf-8'))
plan=json.loads((OUT/'plan.json').read_text('utf-8'))
changed=[s['file']for s in lock['sources']if sha(s['file'])!=s['sha256']]
assert not changed,changed

def sphere(path,size=320,angle=-.4):
    tex=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32);h,w,_=tex.shape;n=size*2
    yy,xx=np.mgrid[0:n,0:n].astype(np.float32);x=(xx+.5-n/2)/(n*.45);y=-(yy+.5-n/2)/(n*.45)
    mask=x*x+y*y<=1;z=np.sqrt(np.maximum(0,1-x*x-y*y))
    u=(((np.arctan2(x,z)+angle)/(2*np.pi)+.5)%1)*(w-1);v=(.5-np.arcsin(np.clip(y,-1,1))/np.pi)*(h-1)
    i=u.astype(int);j=v.astype(int);a=(u-i)[...,None];b=(v-j)[...,None]
    rgb=(tex[j,i]*(1-a)+tex[j,(i+1)%w]*a)*(1-b)+(tex[np.minimum(j+1,h-1),i]*(1-a)+tex[np.minimum(j+1,h-1),(i+1)%w]*a)*b
    light=(.24+.76*np.maximum(0,-.42*x+.38*y+.82*z))*(.82+.18*z)
    data=np.zeros((n,n,4),dtype=np.uint8);data[:,:,:3]=np.clip(rgb*light[...,None],0,255).astype('uint8');data[:,:,3]=mask.astype('uint8')*255;data[~mask,:3]=0
    return Image.fromarray(data).resize((size,size),Image.Resampling.LANCZOS)

(OUT/'preview').mkdir(exist_ok=True)
records=[];seen=set()
for r in plan['variants']:
    p=OUT/'textures'/(r['id']+'.png');assert p.is_file(),str(p)
    with Image.open(p) as im:
        im.load();assert im.size==(2048,1024);assert im.convert('RGBA').getextrema()[3]==(255,255)
        data=np.asarray(im.convert('RGB'),dtype=float);assert data.std()>6
        seam=float(np.mean(abs(data[:,0]-data[:,-1])));adj=float((np.mean(abs(data[:,0]-data[:,1]))+np.mean(abs(data[:,-1]-data[:,-2])))/2)
        assert seam/max(.001,adj)<3,(r['id'],'seam',seam,adj)
        im.convert('RGB').resize((600,300),Image.Resampling.LANCZOS).save(OUT/'preview'/(r['id']+'_flat.webp'),quality=93)
    digest=sha(p);assert digest not in seen;seen.add(digest)
    sphere(p).save(OUT/'preview'/(r['id']+'.webp'),quality=94)
    sphere(p,angle=2.1).save(OUT/'preview'/(r['id']+'_back.webp'),quality=94)
    project=OUT/'projects'/(r['id']+'.tfp');assert project.is_file()
    r.update(file='textures/'+r['id']+'.png',sha256=digest,bytes=p.stat().st_size,project='projects/'+r['id']+'.tfp',projectSha256=sha(project))
    records.append({'id':r['id'],'size':[2048,1024],'opaque':True,'standardDeviation':round(float(data.std()),3),'seamMean':round(seam,3),'adjacentMean':round(adj,3),'seamRatio':round(seam/max(.001,adj),3)})

fontpath=r'C:\Windows\Fonts\msyh.ttc';title=ImageFont.truetype(fontpath,36);heading=ImageFont.truetype(fontpath,27);small=ImageFont.truetype(fontpath,19)
sheet=Image.new('RGB',(1440,120+3*345),(9,17,27));draw=ImageDraw.Draw(sheet)
draw.text((30,22),'观星者 · 天然卫星贴图',font=title,fill='#edf7fa');draw.text((32,76),'6 种外观  /  2048 × 1024  /  岩质、冰质与火山卫星',font=small,fill='#8eb1bd')
for i,r in enumerate(plan['variants']):
    x=(i%2)*710+10;y=120+(i//2)*345
    draw.rounded_rectangle((x+8,y+8,x+700,y+335),radius=12,fill='#11202b',outline='#283d48')
    ball=Image.open(OUT/'preview'/(r['id']+'.webp')).convert('RGBA').resize((290,290));sheet.paste(ball,(x+10,y+25),ball)
    draw.text((x+309,y+32),r['name'],font=heading,fill='#e5f0f3')
    im=Image.open(OUT/'preview'/(r['id']+'_flat.webp')).resize((365,182));sheet.paste(im,(x+308,y+94))
    draw.text((x+309,y+290),f'0{i+1} · 无大气云层',font=small,fill='#90adb7')
sheet.save(OUT/'天然卫星_6张总览.jpg',quality=95)

manifest={'schema':1,'version':'moon-textures-v1','created':'2026-10-25','generator':'Installed Textures for Planets 2.1 native strategy pipeline','canonicalFile':lock['canonicalFile'],'canonicalSha256':lock['canonicalSha256'],'cardModified':False,'count':6,'projection':'EQUIRECTANGULAR','resolution':[2048,1024],'textureKind':'natural-satellite surface colour maps; no baked directional lighting or atmosphere','customPaletteDirectory':'Colourizers','customPalettes':[{'file':p.relative_to(OUT).as_posix(),'sha256':sha(p)}for p in (OUT/'Colourizers').glob('*.col')],'variants':plan['variants'],'seedProtocol':'java.util.Random(seed), consume nextDouble once, use palette fraction 0.2; same native strategy execution as GUI'}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
cards=''
for r in plan['variants']:
    cards+=f'''<article><div class="spheres"><img src="preview/{r['id']}.webp" alt="{r['name']}球面正视图"><img src="preview/{r['id']}_back.webp" alt="{r['name']}另一经度球面图"></div><div class="content"><h2>{r['name']}</h2><p>{r['description']}</p><a href="{r['file']}" target="_blank"><img class="flat" src="preview/{r['id']}_flat.webp" alt="{r['name']}完整展开图"></a><div class="links"><a href="{r['file']}" download>下载 2048×1024 原图</a><a href="{r['project']}" download>原生工程</a></div></div></article>'''
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>观星者 · 天然卫星贴图</title><style>
:root{color-scheme:dark;background:#09111b;color:#e1eef1;font-family:"Microsoft YaHei",system-ui,sans-serif}*{box-sizing:border-box}body{margin:0}main{max-width:1280px;margin:auto;padding:42px 26px}small{color:#75c9bd;letter-spacing:3px}h1{font-size:clamp(28px,4vw,43px);margin:16px 0}p{color:#9eb6c0;font-size:14px;line-height:1.9}header{margin-bottom:32px}.stats{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}.stats span{padding:8px 13px;border:1px solid #314852;border-radius:4px;font-size:12px;color:#b4d2da}article{display:grid;grid-template-columns:1fr 1fr;gap:24px;background:linear-gradient(120deg,#142530,#0e1b26);border:1px solid #2b414d;border-radius:10px;padding:22px;margin:22px 0}.spheres{display:flex;align-items:center;min-width:0}.spheres img{width:50%;min-width:0}.content{min-width:0}h2{font-size:23px;margin:6px 0}.flat{display:block;width:100%;border:1px solid #3a505a;border-radius:4px}.links{display:flex;gap:18px;margin-top:18px;flex-wrap:wrap}a{color:#8bdacb;font-size:13px;text-decoration:none}a:hover{text-decoration:underline}footer{border-top:1px solid #2a414b;margin-top:35px;padding:22px 0;color:#89a2ad;font-size:12px;line-height:1.9}@media(max-width:680px){main{padding:26px 16px}article{grid-template-columns:1fr;padding:15px;gap:4px}.spheres{max-width:500px;margin:auto}}
</style><main><header><small>STARGAZER / NATURAL SATELLITES</small><h1>六种卫星，六片不同的地表。</h1><p>从密集撞击坑与玄武岩月海，到破裂冰壳与硫黄火山沉积。原图不带球面光照、不叠加大气云层；下方两张球面展示不同经度，帮助检查表面分布。</p><div class="stats"><span>6 张新贴图</span><span>2048 × 1024 PNG</span><span>6 份原生工程</span><span>无需联网</span></div></header>'''+cards+'''<footer>本批是独立素材包，未接入角色卡。球面光照只用于预览。部分工程使用本包 Colourizers 文件夹中的自定义配色；若要在原软件重新渲染，请先将这些 .col 文件复制到原软件的 Colourizers 目录。未自动修改软件目录。<br><a href="天然卫星_6张总览.jpg" target="_blank">打开总览图</a> · <a href="manifest.json">素材与参数清单</a> · <a href="交付说明.md">交付说明</a></footer></main></html>'''
(OUT/'天然卫星贴图预览.html').write_text(page,'utf-8')
validation={'imageChecks':records,'uniqueTextures':len(seen),'sourcesUnchanged':len(lock['sources']),'canonicalUnchanged':True,'nativeProjectReadback':'6/6; native deserialization after save','browserInteraction':'not_run; static gallery, local-file browser policy blocked in previous task','visualReview':'pending','status':'asset checks passed'}
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),'utf-8')
readme=f'''# 天然卫星贴图 v1（2026-10-25）

6 张专用于天然卫星的 2048×1024 PNG：银灰环坑、玄武月海、赤褐岩月、裂纹冰卫、古老脏冰、硫黄火山。

使用本机 Textures for Planets 2.1 的原生球面网格、地貌、撞击坑、峡谷、火山及渲染策略生成。每张采用独立种子与工具参数，部分使用为本批配置的颜色表。原始贴图没有预览中的方向光照，不包含大气云层。

- `textures/`：六张完整展开贴图，可用于球面。
- `projects/`：六份原软件 `.tfp` 工程文件。
- `Colourizers/`：四份自定义 `.col` 配色文件。
- `preview/`：静态球面不同经度及展开缩略预览。
- `manifest.json`：每张图的配方、种子、来源基线和文件指纹。
- `source-lock.json`：生成前记录的 {len(lock['sources'])} 个来源指纹，生成后再次验证。

打开“天然卫星贴图预览.html”或“天然卫星_6张总览.jpg”查看。预览页不加载外部资源。

## 在原软件继续调整

先把本包 `Colourizers/` 下的 `.col` 配色文件复制到原软件使用的 `Colourizers` 目录，再打开 `projects/` 下的工程。赤褐岩月与裂纹冰卫使用内置配色。工程保留原生地貌和渲染参数；软件界面再次运行会抽取新随机图案，本批确切种子保存在清单和 jobs.tsv。没有自动写入软件安装目录或改动全局设置。

本次只交付素材，没有修改角色卡或旧行星贴图。核对的当前完整卡为 `{lock['canonicalFile']}`，指纹 `{lock['canonicalSha256']}`。不涉及角色卡构建，当前版本指针保持。
'''
(OUT/'交付说明.md').write_text(readme,'utf-8')
print(json.dumps({'count':len(seen),'sourcesUnchanged':len(lock['sources']),'maxSeamRatio':max(r['seamRatio']for r in records),'status':'ready for visual review'}))
