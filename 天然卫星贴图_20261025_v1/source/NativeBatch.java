import com.texturesforplanets.colourize.*;
import com.texturesforplanets.model.*;
import com.texturesforplanets.strategies.*;
import com.texturesforplanets.renderer.*;
import com.texturesforplanets.tool.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.ZipFile;
import java.lang.reflect.*;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;

/** Invokes the installed TFP 2.1 strategy pipeline without changing its UI or preferences. */
public class NativeBatch {
  static File app, out;
  static final IStrategyListener listener = new IStrategyListener() {
    public boolean update(IStrategy strategy, int step) { return true; }
  };
  static void loadColours() throws Exception {
    Method load=ColourizerLoader.class.getDeclaredMethod("load",ZipFile.class);
    load.setAccessible(true);
    Map<String,Colourizer> colours=new LinkedHashMap<String,Colourizer>();
    File[] files=new File(app,"Colourizers").listFiles();
    Arrays.sort(files);
    for(File f:files) if(f.getName().endsWith(".col")) {
      Colourizer c=(Colourizer)load.invoke(null,new ZipFile(f));
      if(c==null) throw new IOException("Invalid colourizer: "+f);
      colours.put(c.getName(),c);
    }
    for(String field:new String[]{"allColourizers","allColourizersOrdered","newDialogColourizersOrdered"}) {
      Field f=ColourizerLoader.class.getDeclaredField(field);f.setAccessible(true);
      f.set(null,field.equals("allColourizers")?colours:new ArrayList<Colourizer>(colours.values()));
    }
  }
  static BuildModel template(String name) throws Exception {
    ObjectInputStream in=new ObjectInputStream(new FileInputStream(new File(app,"Templates/"+name+".tfp")));
    try{return (BuildModel)in.readObject();}finally{in.close();}
  }
  static void loadTools() throws Exception {
    Method load=ToolLoader.class.getDeclaredMethod("load",ZipFile.class);load.setAccessible(true);
    Map<String,Tool> tools=new LinkedHashMap<String,Tool>();
    File[] files=new File(app,"Tools").listFiles();Arrays.sort(files);
    for(File f:files)if(f.getName().endsWith(".tool")){
      Tool t=(Tool)load.invoke(null,new ZipFile(f));if(t==null)throw new IOException("Invalid tool "+f);tools.put(t.getName(),t);
    }
    Field map=ToolLoader.class.getDeclaredField("allTools");map.setAccessible(true);map.set(null,tools);
    Field list=ToolLoader.class.getDeclaredField("allToolsOrdered");list.setAccessible(true);list.set(null,new ArrayList<Tool>(tools.values()));
  }
  static RenderStrategy render(Colourizer c,boolean ground,boolean cloud,int w) {
    RenderStrategy r=new RenderStrategy(c);r.setWidth(w);r.setHeight(w/2);
    r.setProjection(EProjection.EQUIRECTANGULAR);r.setRenderGroundLayer(ground);r.setRenderCloudLayer(cloud);
    r.setCloudColourizer(cloud&&!ground?c:ColourizerLoader.getDefaultCloudsColourizer());return r;
  }
  static void run(String[] row,int width) throws Exception {
    String id=row[0],tn=row[1]; long seed=Long.parseLong(row[3]);int variant=Integer.parseInt(row[7]);
    boolean auxiliaryClouds=Boolean.parseBoolean(row[6]);
    Colourizer c=ColourizerLoader.getColourizer(row[2]);if(c==null)throw new IOException("Missing "+row[2]);
    BuildModel model=new BuildModel(); boolean cloudAdded=false;
    for(IStrategy s:template(tn).strategies()) {
      if(s instanceof RenderStrategy)continue;
      if(s instanceof CreateMeshStrategy)((CreateMeshStrategy)s).setDivisions(6);
      if(s instanceof PerturbStrategy)((PerturbStrategy)s).setIterations(Integer.parseInt(row[4]));
      if(s instanceof CloudStrategy) {
        cloudAdded=true;
        CloudStrategy q=(CloudStrategy)s;
        if(tn.equals("gasgiant")) {
          q.setMinimumBandCount(variant==1?12:6);q.setMaximumBandCount(variant==1?20:11);
          q.setMinimumIterations(variant==1?150:240);q.setMaximumIterations(variant==1?220:320);
          q.setMinimumStormSpeed(variant==1?8:16);q.setMaximumStormSpeed(variant==1?18:32);
        }
      }
      if(s instanceof ToolStrategy) {
        ToolStrategy q=(ToolStrategy)s;
        if(id.startsWith("frozen_dwarf")&&variant==1){q.setMinCount(70);q.setMaxCount(110);}
        if(id.startsWith("frozen_")&&!id.startsWith("frozen_dwarf")&&variant==2){q.setMinCount(Math.max(1,q.getMinCount()/2));q.setMaxCount(Math.max(2,q.getMaxCount()/2));}
      }
      model.add(s);
    }
    if(auxiliaryClouds&&!cloudAdded) {
      for(IStrategy s:template("terrestrialclouds").strategies())if(s instanceof CloudStrategy){model.add(s);break;}
    }
    boolean atmospheric=tn.equals("gasgiant")||tn.equals("venusianclouds");
    if(atmospheric)model.add(render(c,false,true,width));
    else {
      model.add(render(c,true,false,width));
      if(auxiliaryClouds) {
        RenderStrategy cloud=render(ColourizerLoader.getDefaultCloudsColourizer(),false,true,width);
        model.add(cloud);
        model.add(render(c,true,true,width));
      }
    }
    File projects=new File(out,"projects");projects.mkdirs();
    File project=new File(projects,id+".tfp");
    ByteArrayOutputStream bytes=new ByteArrayOutputStream();ObjectOutputStream save=new ObjectOutputStream(bytes);save.writeObject(model);save.close();
    if(project.exists()) {
      if(!Arrays.equals(bytes.toByteArray(),Files.readAllBytes(project.toPath())))throw new IOException("Refusing different project overwrite: "+project);
    } else Files.write(project.toPath(),bytes.toByteArray(),StandardOpenOption.CREATE_NEW);
    Random random=new Random(seed);random.nextDouble();
    double palette=Double.parseDouble(row[5]);
    Output output=new Output(model,false);Icosahedron mesh=null;
    long started=System.currentTimeMillis();
    System.out.println("START "+id+" colour="+c.getName()+" paletteIndex="+(int)(palette*c.getColoursImageCount()));
    for(IStrategy s:model.strategies()) {
      long at=System.currentTimeMillis();
      mesh=s.execute(random,mesh,output,listener,palette,false);
      if(mesh==null)throw new IOException("Cancelled "+id+" "+s.getClass().getSimpleName());
      System.out.println("  "+s.getClass().getSimpleName()+" "+(System.currentTimeMillis()-at)+"ms");
    }
    String[] names=auxiliaryClouds?new String[]{"ground","clouds","composite"}:new String[]{"ground"};
    if(output.numberOfRenderings()!=names.length)throw new IOException("Unexpected render count");
    for(int i=0;i<names.length;i++){
      File folder=new File(out,names[i]);folder.mkdirs();File target=new File(folder,id+".png");
      if(target.exists())throw new IOException("Refusing to overwrite: "+target);
      BufferedImage image=output.getRendering(i).getImage();
      if(image.getWidth()!=width||image.getHeight()!=width/2)throw new IOException("Bad dimensions");
      ImageIO.write(image,"png",target);
    }
    System.out.println("DONE "+id+" "+(System.currentTimeMillis()-started)+"ms");
    mesh=null;output=null;System.gc();
  }
  public static void main(String[] args) throws Exception {
    app=new File(args[0]);out=new File(args[1]);out.mkdirs();loadColours();loadTools();
    if(args.length>3&&args[3].equals("verify")) {
      File[] projects=new File(out,"projects").listFiles();int count=0;
      for(File f:projects)if(f.getName().endsWith(".tfp")){
        ObjectInputStream input=new ObjectInputStream(new FileInputStream(f));BuildModel m=(BuildModel)input.readObject();input.close();
        if(m.countStrategies()<3)throw new IOException("Incomplete project "+f);
        int renderings=0;
        for(IStrategy s:m.strategies())if(s instanceof RenderStrategy){RenderStrategy r=(RenderStrategy)s;if(r.getWidth(false)!=2048||r.getHeight(false)!=1024||r.getGroundColourizer()==null||r.getCloudColourizer()==null)throw new IOException("Bad render settings "+f);renderings++;}
        if(renderings!=1&&renderings!=3)throw new IOException("Bad project render count "+f);count++;
      }
      if(count!=24)throw new IOException("Expected 24 projects, got "+count);
      System.out.println("{\"nativeProjectReadback\":24,\"renderSettings\":\"pass\"}");return;
    }
    int width=args.length>4?Integer.parseInt(args[4]):2048;
    for(String line:Files.readAllLines(Paths.get(args[2]),java.nio.charset.StandardCharsets.UTF_8)) {
      String[] row=line.split("\t");if(args.length>3&&!args[3].equals("all")&&!row[0].matches(args[3]))continue;
      run(row,width);
    }
    System.out.println("BATCH COMPLETE");
  }
}
