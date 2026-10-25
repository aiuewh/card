from pathlib import Path
import json, hashlib, os, html, zipfile, math, base64, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
plan=json.loads((OUT/'plan.json').read_text('utf-8'))
lock=json.loads((OUT/'source-lock.json').read_text('utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_sources():
    changed=[s['file'] for s in lock['sources'] if sha(s['file'])!=s['sha256']]
    assert not changed,changed
validate_sources()

def sphere(file,angle=.3,size=256):
    tex=np.asarray(Image.open(file).convert('RGB'),dtype=np.float32)
    h,w,_=tex.shape
    n=size*2
    yy,xx=np.mgrid[0:n,0:n].astype(np.float32)
    x=(xx+.5-n/2)/(n*.445); y=-(yy+.5-n/2)/(n*.445)
    inside=x*x+y*y<=1
    z=np.sqrt(np.maximum(0,1-x*x-y*y))
    lon=np.arctan2(x,z)+angle;lat=np.arcsin(np.clip(y,-1,1))
    u=((lon/(2*np.pi)+.5)%1)*(w-1);v=(.5-lat/np.pi)*(h-1)
    u0=u.astype(int);v0=v.astype(int);u1=(u0+1)%w;v1=np.minimum(h-1,v0+1)
    a=(u-u0)[...,None];b=(v-v0)[...,None]
    rgb=(tex[v0,u0]*(1-a)+tex[v0,u1]*a)*(1-b)+(tex[v1,u0]*(1-a)+tex[v1,u1]*a)*b
    lighting=np.maximum(0,-.45*x+.38*y+.81*z)
    rgb*=((.15+.85*lighting)*(.75+.25*z))[...,None]
    result=np.zeros((n,n,4),dtype=np.uint8)
    result[:,:,:3]=np.clip(rgb,0,255).astype(np.uint8);result[:,:,3]=inside.astype(np.uint8)*255
    result[~inside,:3]=0
    return Image.fromarray(result).resize((size,size),Image.Resampling.LANCZOS)

assets=[];seen=set();validation=[]
(OUT/'preview').mkdir(exist_ok=True)
for r in plan['variants']:
    for layer in ['ground','clouds','composite']:
        p=OUT/layer/(r['id']+'.png')
        if layer!='ground' and not r['clouds']:
            assert not p.exists();continue
        assert p.is_file(),str(p)
        with Image.open(p) as im:
            im.load();assert im.size==(2048,1024),(p,im.size)
            if layer!='clouds':assert im.convert('RGBA').getextrema()[3]==(255,255),(p,'transparent ground')
            arr=np.asarray(im.convert('RGB'),dtype=np.float32)
            seam=float(np.mean(abs(arr[:,0]-arr[:,-1])))
            adjacent=float((np.mean(abs(arr[:,0]-arr[:,1]))+np.mean(abs(arr[:,-1]-arr[:,-2])))/2)
            sd=float(arr.std());assert sd>3,(p,'blank image')
        digest=sha(p);assert digest not in seen,('duplicate',p);seen.add(digest)
        record={'variant':r['id'],'category':r['category'],'type':r['type'],'label':r['name'],'layer':layer,'file':p.relative_to(OUT).as_posix(),'width':2048,'height':1024,'bytes':p.stat().st_size,'sha256':digest}
        assets.append(record)
        validation.append({'file':record['file'],'seamMean':round(seam,3),'adjacentMean':round(adjacent,3),'seamRatio':round(seam/max(.001,adjacent),3),'rgbStd':round(sd,2)})
    p=OUT/'ground'/(r['id']+'.png')
    sphere(p).save(OUT/'preview'/(r['id']+'.webp'),quality=92)
    if r['clouds']:
        sphere(OUT/'composite'/(r['id']+'.png')).save(OUT/'preview'/(r['id']+'_clouds.webp'),quality=92)
    with Image.open(p) as im:im.resize((480,240),Image.Resampling.LANCZOS).save(OUT/'preview'/(r['id']+'_flat.webp'),quality=90)
    project=OUT/'projects'/(r['id']+'.tfp');assert project.is_file()
    r['projectSha256']=sha(project)

pair_checks=[]
for cat in plan['categories']:
    variants=[r for r in plan['variants'] if r['category']==cat['id']]
    pair=[]
    for r in variants:
        with Image.open(OUT/'ground'/(r['id']+'.png')) as im:pair.append(np.asarray(im.convert('RGB').resize((256,128)),dtype=float))
    difference=float(np.mean(abs(pair[0]-pair[1])))
    assert difference>4,(cat['id'],'variants insufficiently distinct',difference)
    pair_checks.append({'category':cat['id'],'meanPixelDifference':round(difference,2)})

for cat in plan['categories']:
    for i,old in enumerate(cat['existing']):
        assert sha(ROOT/old['file'])==old['sha256']
        old['url']=os.path.relpath(ROOT/old['file'],OUT).replace('\\','/')
        old['preview']='preview/'+cat['id']+'_old_'+str(i)+'.webp'
        sphere(ROOT/old['file']).save(OUT/old['preview'],quality=90)
        old['flatPreview']='preview/'+cat['id']+'_old_'+str(i)+'_flat.webp'
        with Image.open(ROOT/old['file']) as im:im.convert('RGB').resize((640,320),Image.Resampling.LANCZOS).save(OUT/old['flatPreview'],quality=90)

manifest={'schema':1,'date':'2026-10-25','generator':'Textures for Planets 2.1 installed native strategy pipeline','generatorExeSha256':next(s['sha256'] for s in lock['sources'] if s['file'].endswith('TexturesForPlanets.exe')),'canonicalFile':lock['canonicalFile'],'canonicalSha256':lock['canonicalSha256'],'status':'local-asset-pack','cardIntegration':'not-modified','existingAssets':'byte-identical','newVariantCount':24,'resolution':[2048,1024],'categories':plan['categories'],'variants':plan['variants'],'assets':assets,'reproduction':{'jobs':'source/jobs.tsv','runner':'source/NativeBatch.java','seed':'java.util.Random(long); one nextDouble consumed as native bulk pipeline; explicit palette fraction used','nativeProjects':'projects/*.tfp','note':'TFP GUI opens saved strategy recipes but uses a fresh seed; exact seed and palette are retained in this manifest and jobs.tsv.'}}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')

font=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',24)
small=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',18)
title=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',34)
sheet=Image.new('RGB',(1320,120+12*226),(9,17,27));d=ImageDraw.Draw(sheet)
d.text((30,22),'观星者 · 行星贴图变种扩展',font=title,fill='#eff8ff')
d.text((32,72),'12 类 × 2 个新变种  |  2048 × 1024  |  Textures for Planets 2.1',font=small,fill='#8faab7')
for y,cat in enumerate(plan['categories']):
    top=120+y*226
    d.line((24,top,1296,top),fill='#263541')
    d.text((30,top+22),cat['type'],font=font,fill='#d8e6ed')
    d.text((30,top+65),'新变种 01 / 02',font=small,fill='#7199a9')
    for x,r in enumerate([r for r in plan['variants'] if r['category']==cat['id']]):
        left=230+x*535
        ball=Image.open(OUT/'preview'/(r['id']+'.webp')).convert('RGBA').resize((192,192))
        sheet.paste(ball,(left,top+15),ball)
        flat=Image.open(OUT/'preview'/(r['id']+'_flat.webp')).convert('RGB').resize((300,150))
        sheet.paste(flat,(left+199,top+20));d.text((left+200,top+179),r['name'],font=small,fill='#d8e6ed')
sheet.save(OUT/'新增24张总览.jpg',quality=94)

payload={'categories':plan['categories'],'variants':[]}
for r in plan['variants']:
    preview=dict(r)
    for layer in (['ground','composite'] if r['clouds'] else ['ground']):
        with Image.open(OUT/layer/(r['id']+'.png')) as im:
            image=im.convert('RGB').resize((1024,512),Image.Resampling.LANCZOS)
            memory=io.BytesIO();image.save(memory,format='WEBP',quality=90)
            preview[layer+'Data']='data:image/webp;base64,'+base64.b64encode(memory.getvalue()).decode('ascii')
    payload['variants'].append(preview)
cards=[]
for cat in plan['categories']:
    old=''.join(f'<a href="{o["flatPreview"]}" target="_blank" title="查看已有贴图的展开缩略图"><img loading="lazy" src="{o["preview"]}" alt="原有贴图"><span>{html.escape(Path(o["file"]).stem)}</span></a>' for o in cat['existing'])
    variants=''
    for r in [r for r in plan['variants'] if r['category']==cat['id']]:
        variants+=f'''<article class="variant" data-id="{r['id']}"><button class="planet" data-open="{r['id']}" aria-label="查看{r['name']}"><img loading="lazy" src="preview/{r['id']}.webp" alt="{r['name']}球面预览"></button><div class="v-info"><small>变种 {r['variant']:02}</small><h3>{r['name']}</h3><a href="ground/{r['id']}.png" target="_blank"><img loading="lazy" class="flat" src="preview/{r['id']}_flat.webp" alt="球面展开图"></a><p><a href="ground/{r['id']}.png" download>下载贴图</a> · <a href="projects/{r['id']}.tfp" download>工程文件</a>{(' · <a href="clouds/'+r['id']+'.png" download>云层</a>') if r['clouds'] else ''}</p></div></article>'''
    cards.append(f'<section data-category="{cat["id"]}"><header><h2>{cat["type"]}</h2><span>原有 {len(cat["existing"])} 张 · 新增 2 张</span></header><div class="row"><aside><div class="caption">原有贴图</div><div class="originals">{old}</div></aside>{variants}</div></section>')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>观星者 · 行星贴图变种扩展</title><style>
:root{color-scheme:dark;font-family:"Microsoft YaHei",system-ui,sans-serif;background:#09111b;color:#d9e8ed}*{box-sizing:border-box}body{margin:0}main{max-width:1460px;padding:42px 30px 80px;margin:auto}.eyebrow{color:#66cabb;letter-spacing:3px;font-size:12px}h1{font-size:clamp(25px,4vw,42px);margin:14px 0}h2{font-size:22px;margin:0}h3{margin:7px 0 15px;font-size:19px}.intro{color:#95abb7;line-height:1.9;max-width:960px}.stats{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0}.stats span{border:1px solid #2b414d;padding:9px 16px;background:#11212b;border-radius:5px}nav{display:flex;gap:8px;flex-wrap:wrap;margin:25px 0 40px}button,select{font:inherit}nav button{cursor:pointer;border:1px solid #28404b;background:#101f29;color:#b4cbd3;padding:9px 13px;border-radius:4px}nav button.active{color:#0b171c;background:#73d9c8;border-color:#73d9c8}section{border-top:1px solid #2a3b46;padding:26px 0 30px}section header{display:flex;gap:15px;align-items:baseline;flex-wrap:wrap;margin-bottom:23px}header span,small,.caption{color:#8ca7b4;font-size:12px}.row{display:grid;grid-template-columns:190px 1fr 1fr;gap:24px}.originals{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.originals a{display:block;width:80px;text-align:center;font-size:9px;overflow-wrap:anywhere}.originals img{display:block;width:80px;height:80px}.originals span{display:block;color:#829ca9}.variant{background:linear-gradient(130deg,#13232e,#0e1c27);border:1px solid #29404b;border-radius:8px;display:flex;gap:5px;align-items:center;padding:13px;min-width:0}.planet{cursor:grab;border:0;background:transparent;padding:0;flex:0 0 43%;min-width:0}.planet img{width:100%;display:block}.v-info{flex:1;min-width:0}.flat{width:100%;display:block;border:1px solid #344854;border-radius:3px}a{color:#8fdbd2;text-decoration:none}a:hover{text-decoration:underline}p{font-size:11px;line-height:1.9}dialog{border:1px solid #45616e;border-radius:10px;background:#0d1a25;color:#e2eef1;width:min(800px,94vw);padding:22px}dialog::backdrop{background:#000c}dialog header{display:flex;justify-content:space-between;align-items:center}dialog button{background:#19323c;color:#e3f2f3;border:1px solid #43606a;border-radius:4px;padding:8px 14px;cursor:pointer}#sphere{width:min(500px,100%);aspect-ratio:1;display:block;margin:auto;touch-action:none;cursor:grab}label{margin-right:16px;color:#afc4cb;font-size:13px}.helper{color:#7e9ca9;text-align:center}.dialog-controls{display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap}.empty{display:none}.foot{border-top:1px solid #2c414d;margin-top:35px;padding-top:20px;color:#819ba8;line-height:1.9;font-size:12px}@media(max-width:1000px){.row{grid-template-columns:1fr 1fr}.row aside{grid-column:1/-1}.originals{flex-wrap:nowrap}.originals a{width:70px}.originals img{width:70px;height:70px}}@media(max-width:650px){main{padding:24px 16px}.row{grid-template-columns:1fr}.variant{padding:10px}.row aside{grid-column:auto}h1{line-height:1.4}nav{gap:6px}nav button{padding:7px 10px}.planet{flex-basis:40%}}
</style><main><div class="eyebrow">STARGAZER / TEXTURE ATLAS</div><h1>每一类行星，再多两种面貌。</h1><div class="intro">按当前统一卡的 12 类实际生成类型整理，逐类展示已有素材与两个新变种。点击新行星可拖动查看球面，或打开原始展开图。所有新图均由本机 Textures for Planets 2.1 原有引擎生成。</div><div class="stats"><span>12 类行星</span><span>24 张新贴图</span><span>2048 × 1024 PNG</span><span>10 份独立云层</span></div><nav id="filters"></nav>''' + ''.join(cards)+'''<div class="foot">当前交付为独立贴图素材包；原角色卡及原有贴图均保持原字节。新增素材尚未上传到角色卡使用的远程贴图仓库，也未改写存档或生成规则。<br>ground 为用于球面的完整外观（气态／毒气行星为大气外观）；clouds 为独立透明云层；composite 为地表与云层合成预览。球面光照仅用于预览，不写入原始贴图。<br><a href="manifest.json">完整素材清单与指纹</a> · <a href="新增24张总览.jpg" target="_blank">打开总览图</a></div></main><dialog id="detail"><header><h2 id="detail-title"></h2><button id="close">关闭</button></header><canvas id="sphere" width="500" height="500" aria-label="拖动旋转行星"></canvas><div class="helper">拖动旋转 · 光照只用于预览</div><div class="dialog-controls"><label><input id="auto" type="checkbox" checked> 自动旋转</label><label id="cloud-label"><input id="cloud" type="checkbox"> 显示云层</label><a id="download">打开原图</a></div><p id="load-state" role="status"></p></dialog><script>
const data=PAYLOAD;
const filters=document.querySelector('#filters');
for(const cat of [{id:'all',type:'全部'},...data.categories]){const b=document.createElement('button');b.textContent=cat.type;b.className=cat.id==='all'?'active':'';b.onclick=()=>{filters.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('section[data-category]').forEach(s=>s.hidden=cat.id!=='all'&&s.dataset.category!==cat.id)};filters.append(b)}
const dialog=document.querySelector('#detail'),canvas=document.querySelector('#sphere'),ctx=canvas.getContext('2d'),cloud=document.querySelector('#cloud'),auto=document.querySelector('#auto'),status=document.querySelector('#load-state');let angle=.3,pixels=null,tw=0,th=0,current=null,drag=null,animation=null,serial=0;
function load(){const turn=++serial;status.textContent='正在载入贴图…';const im=new Image();im.onload=()=>{if(turn!==serial)return;const c=document.createElement('canvas');c.width=1024;c.height=512;const q=c.getContext('2d',{willReadFrequently:true});q.drawImage(im,0,0,1024,512);try{pixels=q.getImageData(0,0,1024,512).data;tw=1024;th=512;status.textContent='';paint()}catch(e){status.textContent='无法读取预览，请使用原图链接。'}};im.onerror=()=>status.textContent='贴图载入失败，请使用原图链接。';im.src=cloud.checked&&current.clouds?current.compositeData:current.groundData}
const N=300,frame=ctx.createImageData(N,N),lookup=[];for(let py=0;py<N;py++)for(let px=0;px<N;px++){const x=(px+.5-N/2)/(N*.445),y=-(py+.5-N/2)/(N*.445),r=x*x+y*y;if(r>1)continue;const z=Math.sqrt(1-r);lookup.push([4*(py*N+px),Math.atan2(x,z),.5-Math.asin(y)/Math.PI,(.15+.85*Math.max(0,-.45*x+.38*y+.81*z))*(.75+.25*z)])}canvas.width=N;canvas.height=N;
function paint(){if(!pixels)return;const d=frame.data;for(const [p,lon,v,light]of lookup){let u=((lon+angle)/(Math.PI*2)+.5)%1;if(u<0)u++;const idx=4*(Math.min(th-1,Math.floor(v*th))*tw+Math.floor(u*tw));d[p]=pixels[idx]*light;d[p+1]=pixels[idx+1]*light;d[p+2]=pixels[idx+2]*light;d[p+3]=255}ctx.putImageData(frame,0,0)}
let last=0;function tick(t){if(!dialog.open)return;if(auto.checked&&!drag&&pixels){angle+=Math.min(50,t-last||16)*.00012;paint()}last=t;animation=requestAnimationFrame(tick)}
document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>{current=data.variants.find(r=>r.id===b.dataset.open);document.querySelector('#detail-title').textContent=current.type+' · '+current.name;document.querySelector('#cloud-label').hidden=!current.clouds;cloud.checked=false;document.querySelector('#download').href='ground/'+current.id+'.png';document.querySelector('#download').target='_blank';angle=.3;pixels=null;ctx.clearRect(0,0,N,N);dialog.showModal();load();cancelAnimationFrame(animation);last=0;animation=requestAnimationFrame(tick)});
canvas.onpointerdown=e=>{drag={x:e.clientX,angle};canvas.setPointerCapture(e.pointerId)};canvas.onpointermove=e=>{if(drag){angle=drag.angle+(e.clientX-drag.x)*.012;paint()}};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;cloud.onchange=load;document.querySelector('#close').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{cancelAnimationFrame(animation);serial++;pixels=null;drag=null});
</script></html>'''
page=page.replace('PAYLOAD',json.dumps(payload,ensure_ascii=False).replace('</','<\\/'))
(OUT/'贴图对照与球面预览.html').write_text(page,'utf-8')

summary={'categories':12,'newGroundTextures':24,'cloudLayers':10,'composites':10,'nativeProjects':24,'uniqueImages':len(seen),'sourceFingerprintsUnchanged':len(lock['sources']),'canonicalUnchanged':sha(ROOT/lock['canonicalFile'])==lock['canonicalSha256'],'checks':validation,'pairDifferences':pair_checks,'reproducibility':json.loads((OUT/'source/reproducibility.json').read_text()),'maxSeamRatio':max(x['seamRatio'] for x in validation),'status':'pass'}
(OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf-8')
readme='''# 观星者行星贴图变种扩展（2026-10-25）

当前统一卡：`CANONICAL`，SHA256：`HASH`。

核对当前实际生成器的 12 类行星，每类新增 2 个变种，共 24 张 2048×1024 PNG。使用本机 Textures for Planets 2.1 的原生网格、地貌、工具、云层与渲染策略生成。每个变种使用独立种子，并调整地貌迭代、风带或撞击坑参数；不是对原图换色。

打开 **贴图对照与球面预览.html** 查看原有素材与新变种，或直接看 **新增24张总览.jpg**。旋转预览使用内嵌的 1024×512 预览数据，无需联网；原图下载链接指向完整的 2048×1024 PNG。

- `ground/`：24 张完整外观贴图。气态巨行星、冰巨星和毒气世界在这里保存大气外观，而非固体地表。
- `clouds/`：五类宜居行星各两份独立透明云层，共 10 张。
- `composite/`：这 10 颗行星的地表与云层合成图。
- `projects/`：24 份可由原软件打开的 `.tfp` 策略工程。
- `manifest.json`：类别、原有素材、变种名称、种子、调色板选择、模板和所有输出指纹。
- `source-lock.json`：构建前的 89 个来源文件指纹；构建后再次核对，全部未变。
- `validation.json`：尺寸、非空、重复内容与经度接缝检查。

这次交付是独立素材扩展包。原有贴图、角色卡、当前版本指针和存档规则均未修改，也没有上传远程仓库。新增 24 张尚未接入角色卡的远程 TEX_MAP 或随机外观选择。

`.tfp` 保存原生策略配方；原软件界面重新运行时会抽新种子。要复现本批相同图案，使用清单中的种子与调色板参数运行 `source/NativeBatch.java`。软件引擎归原作者所有，辅助代码仅调用本机已安装引擎。

## 类别与新增变种

'''.replace('CANONICAL',lock['canonicalFile']).replace('HASH',lock['canonicalSha256'])
for cat in plan['categories']:
    readme+='- '+cat['type']+'：'+'、'.join(r['name'] for r in plan['variants'] if r['category']==cat['id'])+'。\n'
(OUT/'交付说明.md').write_text(readme,'utf-8')
validate_sources()
archive=OUT.parent/'观星者_12类行星各2变种_20261025.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob('*'):
        relative=p.relative_to(OUT)
        include=relative.parts[0] in ['ground','clouds','composite','projects','preview'] or len(relative.parts)==1 or (relative.parts[0]=='source' and p.suffix in ['.java','.py','.tsv','.json'])
        if p.is_file() and include:
            z.write(p,p.relative_to(OUT))
print(json.dumps({k:v for k,v in summary.items() if k!='checks'},ensure_ascii=True,indent=2))
print('Archive bytes:',archive.stat().st_size)
