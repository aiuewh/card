from pathlib import Path
from PIL import Image
import numpy as np
import json,hashlib,zipfile,io,shutil

OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1];APP=Path(r'C:\1MC\1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
release=json.loads((ROOT/'_black_auction_v1/current-release.json').read_text('utf-8-sig'))
assert sha(ROOT/release['canonicalFile'])==release['sha256']
old=ROOT/'星球/变种扩展_20261025'
sources=[ROOT/'_black_auction_v1/current-release.json',ROOT/release['canonicalFile'],ROOT/'蔚蓝星域的观星者_3.3_航程档案候选版.json',old/'source/NativeBatch.java',old/'source/TexturesForPlanets-original.jar',APP/'Textures for Planets/TexturesForPlanets.exe']
sources+=list((APP/'Colourizers').glob('*.col'))+list((APP/'Templates').glob('*.tfp'))+list((APP/'Tools').glob('*.tool'))
sources+=list((old/'ground').glob('*.png'))
lock={'canonicalFile':release['canonicalFile'],'canonicalSha256':release['sha256'],'sources':[{'file':str(p),'sha256':sha(p)}for p in sources]}
(OUT/'source-lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2),'utf-8')
shutil.copyfile(old/'source/NativeBatch.java',OUT/'source/NativeBatch.java')
palettes=OUT/'Colourizers';palettes.mkdir(exist_ok=True)
def palette(source,name,kind):
    with zipfile.ZipFile(APP/'Colourizers'/source) as z:
        images=[]
        for n in z.namelist():
            if not (n.startswith('colours')and n.endswith('.png')):continue
            rgb=np.asarray(Image.open(z.open(n)).convert('RGB'),dtype=float)/255
            l=rgb[:,:,0]*.2126+rgb[:,:,1]*.7152+rgb[:,:,2]*.0722
            if kind=='silver':
                v=np.clip(l*.90+.10,0,1);arr=np.stack([v*.99,v,v*1.025],axis=2)
            elif kind=='basalt':
                v=np.clip(l*.80+.025,0,1);arr=np.stack([v,v*.99,v*1.02],axis=2)
            elif kind=='dirtyice':
                arr=np.clip(rgb*np.array([.82,.80,.74])+.045,0,1)
            elif kind=='sulfur':
                # Preserve the original height/latitude-dependent texture variation.
                arr=np.stack([.25+.68*l,.19+.59*l,.055+.24*l],axis=2)
                hot=np.maximum(rgb[:,:,0]-rgb[:,:,1],0)
                arr[:,:,0]+=hot*.12;arr[:,:,1]-=hot*.20
            images.append((n,Image.fromarray(np.clip(arr*255,0,255).astype('uint8'))))
        sample=Image.open(z.open('sample.png')).convert('RGB')
        # The palette itself is the honest swatch, rather than the source world's old sample.
        sample=images[0][1].resize(sample.size)
    path=palettes/(kind+'.col')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('colourizer.txt',f'name={name}\nauthor=Stargazer local moon palette; based on installed Textures for Planets palette\ntemplate=cratered\ntemplate_colourizer_surface={name}\nshow_in_start_gallery=true\n')
        for n,im in images+[('sample.png',sample)]:
            b=io.BytesIO();im.save(b,format='PNG');z.writestr(n,b.getvalue())
    return path
palette('rock.col','Moon Silver Rock','silver')
palette('martian.col','Moon Dark Basalt','basalt')
palette('ice.col','Moon Dirty Ice','dirtyice')
palette('volcanic.col','Moon Sulfur','sulfur')
specs=[
 {'id':'moon_silver_crater','name':'银灰环坑','description':'密集撞击坑、明暗相间的灰色岩质高地。','template':'cratered','colourizer':'Moon Silver Rock','seed':2026102701,'iterations':2200,'craterCount':[85,115],'craterSize':[8,35],'canyonCount':[0,0],'volcanoCount':[0,0]},
 {'id':'moon_basalt_maria','name':'玄武月海','description':'暗色玄武岩平原与较明亮的古老高地，撞击坑较稀疏。','template':'cratered','colourizer':'Moon Dark Basalt','seed':2026102702,'iterations':1300,'craterCount':[18,30],'craterSize':[15,60],'canyonCount':[0,0],'volcanoCount':[0,0]},
 {'id':'moon_rust_rock','name':'赤褐岩月','description':'赤褐色矿物岩壳与大小交叠的陨石坑。','template':'cratered','colourizer':'Martian','seed':2026102703,'iterations':2600,'craterCount':[45,70],'craterSize':[10,48],'canyonCount':[0,0],'volcanoCount':[0,0]},
 {'id':'moon_fractured_ice','name':'裂纹冰卫','description':'浅色冰壳、长裂谷与少量古老撞击盆地。','template':'crackedandcratered','colourizer':'Ice','seed':2026102704,'iterations':1800,'craterCount':[12,22],'craterSize':[12,38],'canyonCount':[45,65],'volcanoCount':[0,0]},
 {'id':'moon_ancient_dirtyice','name':'古老脏冰','description':'被尘埃和岩质沉积染暗的冰层，保留密集古坑与较少裂谷。','template':'crackedandcratered','colourizer':'Moon Dirty Ice','seed':2026102705,'iterations':2800,'craterCount':[70,95],'craterSize':[7,38],'canyonCount':[8,15],'volcanoCount':[0,0]},
 {'id':'moon_sulfur_volcanic','name':'硫黄火山','description':'硫黄色沉积、橙褐喷发区与稀疏火山口，无大气云层。','template':'violent','colourizer':'Moon Sulfur','seed':2026102706,'iterations':1400,'craterCount':[0,0],'canyonCount':[16,25],'volcanoCount':[25,40]}
]
for s in specs:
    s.update(width=2048,height=1024,projection='EQUIRECTANGULAR',clouds=False)
    s.setdefault('craterSize',[10,50])
(OUT/'plan.json').write_text(json.dumps({'naturalSatellites':True,'variants':specs},ensure_ascii=False,indent=2),'utf-8')
keys=['id','template','colourizer','seed','iterations','craterCount','canyonCount','volcanoCount','craterSize']
(OUT/'source/jobs.tsv').write_text('\n'.join('\t'.join(','.join(map(str,r[k]))if isinstance(r[k],list)else str(r[k])for k in keys)for r in specs),'utf-8')
print('Six moon recipes prepared; canonical hash verified; source fingerprints recorded.')
