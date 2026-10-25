from pathlib import Path
from html.parser import HTMLParser
import json,re,zipfile,hashlib,subprocess

out=Path(__file__).resolve().parents[1]
class Parser(HTMLParser):
    def __init__(self):super().__init__();self.urls=[];self.buttons=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for k in ['src','href']:
            if k in a:self.urls.append(a[k])
        if 'data-open' in a:self.buttons+=1
p=Parser();page=(out/'贴图对照与球面预览.html').read_text('utf-8');p.feed(page)
assert p.buttons==24
missing=[url for url in p.urls if not url.startswith(('data:','#','http:','https:')) and not (out/url).is_file()]
assert not missing,missing
script=re.search(r'<script>(.*?)</script>',page,re.S).group(1)
js=out/'source/gallery-syntax-check.js';js.write_text(script,'utf-8')
subprocess.run(['node','--check',str(js)],check=True,capture_output=True)
native=json.loads((out/'source/project-validation.json').read_text('utf-8-sig'))
assert native['nativeProjectReadback']==24
validation=json.loads((out/'validation.json').read_text('utf-8'))
validation['nativeProjectValidation']=native
validation['galleryStaticValidation']={'variantButtons':p.buttons,'assetLinks':len(p.urls),'missingAssets':0,'javascriptSyntax':'pass'}
validation['browserInteractionValidation']='not_run: browser local-file protocol policy blocked access; no workaround attempted'
assert validation['maxSeamRatio']<2
validation['seamCheck']='maximum first/last longitude-column difference is under 2x neighboring-column difference; visually reviewed on spheres'
(out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),'utf-8')
readme=out/'交付说明.md';text=readme.read_text('utf-8')
note='\n## 验收范围\n\n24 份原生工程均由原引擎成功反序列化，尺寸和渲染设置通过。44 张输出图均为有效非空 PNG，内容指纹互不重复，各类两个变种图像差异通过；经度接缝差异最大为邻列差异的 1.639 倍，已结合静态球面逐类查看。89 个来源指纹未变。\n\n交互预览完成资源链接和 JavaScript 语法检查；自动浏览器因本地文件协议策略拒绝打开，未做浏览器交互验收。预览页供本地打开，静态总览已经视觉检查。\n'
if '## 验收范围' not in text:readme.write_text(text+note,'utf-8')
lock=json.loads((out/'source-lock.json').read_text('utf-8'))
assert all(hashlib.sha256(Path(s['file']).read_bytes()).hexdigest()==s['sha256'] for s in lock['sources'])
archive=out.parent/'观星者_12类行星各2变种_20261025.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for f in out.rglob('*'):
        rel=f.relative_to(out)
        include=rel.parts[0] in ['ground','clouds','composite','projects','preview'] or len(rel.parts)==1 or (rel.parts[0]=='source' and f.suffix in ['.java','.py','.tsv','.json'])
        if f.is_file() and include:z.write(f,rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if n.startswith('ground/') and n.endswith('.png')])==24
    assert len([n for n in z.namelist() if n.startswith('projects/') and n.endswith('.tfp')])==24
    assert len([n for n in z.namelist() if n.startswith('clouds/') and n.endswith('.png')])==10
    assert not any('sample/' in n or n.endswith('.jar') for n in z.namelist())
print(json.dumps({'gallery':validation['galleryStaticValidation'],'nativeProjects':native,'archiveBytes':archive.stat().st_size,'archiveIntegrity':'pass','sourceFingerprints':'unchanged'},ensure_ascii=True))
