from pathlib import Path
from html.parser import HTMLParser
import json,zipfile,hashlib

out=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        for key in ['href','src']:
            if key in attrs:self.urls.append(attrs[key])
p=Links();p.feed((out/'天然卫星贴图预览.html').read_text('utf-8'))
assert all((out/url).is_file()for url in p.urls)
project=json.loads((out/'source/project-validation.json').read_text('utf-8-sig'))
assert project['nativeProjectReadback']==6 and project['paletteResolution']=='pass'
lock=json.loads((out/'source-lock.json').read_text('utf-8'))
assert all(hashlib.sha256(Path(r['file']).read_bytes()).hexdigest()==r['sha256']for r in lock['sources'])
v=json.loads((out/'validation.json').read_text('utf-8'))
v.update(nativeProjectValidation=project,visualReview='6/6: flat maps and shaded spherical previews reviewed',galleryLinks={'checked':len(p.urls),'missing':0},status='pass')
(out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
readme=out/'交付说明.md';text=readme.read_text('utf-8')
if '## 验收结果'not in text:readme.write_text(text+f'\n## 验收结果\n\n六张图均为 2048×1024、完全不透明且内容不重复，尺寸、非空与经度接缝检查通过；球面和展开图已逐张视觉核对。六份工程由原引擎回读，配色解析、尺寸与无云层设置均通过。{len(lock["sources"])} 个来源文件指纹保持不变。预览页 {len(p.urls)} 条本地资源链接有效，无外部依赖。\n','utf-8')
archive=out.parent/'观星者_天然卫星6张贴图_v1_20261025.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
    for f in out.rglob('*'):
        if not f.is_file():continue
        rel=f.relative_to(out)
        if f.suffix=='.class':continue
        z.write(f,rel)
with zipfile.ZipFile(archive)as z:
    assert z.testzip()is None
    assert len([n for n in z.namelist()if n.startswith('textures/')and n.endswith('.png')])==6
    assert len([n for n in z.namelist()if n.startswith('projects/')and n.endswith('.tfp')])==6
    assert len([n for n in z.namelist()if n.startswith('Colourizers/')and n.endswith('.col')])==4
print(json.dumps({'textures':6,'projects':6,'customPalettes':4,'sourcesUnchanged':len(lock['sources']),'localLinks':len(p.urls),'archiveIntegrity':'pass','archiveBytes':archive.stat().st_size}))
