import com.texturesforplanets.colourize.*;
import com.texturesforplanets.model.*;
import com.texturesforplanets.strategies.*;
import com.texturesforplanets.tool.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import java.lang.reflect.*;
import javax.imageio.ImageIO;

/** Uses the same native TFP strategies as its GUI, with moon-specific tool settings. */
public class MoonBatch {
  static File out;
  static int[] range(String s){String[] p=s.split(",");return new int[]{Integer.parseInt(p[0]),Integer.parseInt(p[1])};}
  static void loadPalettes() throws Exception {
    Method loader=ColourizerLoader.class.getDeclaredMethod("load",ZipFile.class);loader.setAccessible(true);
    Field field=ColourizerLoader.class.getDeclaredField("allColourizers");field.setAccessible(true);
    @SuppressWarnings("unchecked") Map<String,Colourizer> map=(Map<String,Colourizer>)field.get(null);
    for(File f:new File(out,"Colourizers").listFiles())if(f.getName().endsWith(".col")){
      Colourizer c=(Colourizer)loader.invoke(null,new ZipFile(f));if(c==null)throw new IOException("Invalid palette "+f);map.put(c.getName(),c);
    }
  }
  static void execute(String[] row) throws Exception {
    String id=row[0];Colourizer c=ColourizerLoader.getColourizer(row[2]);if(c==null)throw new IOException(row[2]);
    BuildModel model=new BuildModel();
    for(IStrategy s:NativeBatch.template(row[1]).strategies()){
      if(s instanceof RenderStrategy||s instanceof CloudStrategy)continue;
      if(s instanceof CreateMeshStrategy)((CreateMeshStrategy)s).setDivisions(6);
      if(s instanceof PerturbStrategy)((PerturbStrategy)s).setIterations(Integer.parseInt(row[4]));
      if(s instanceof ToolStrategy){
        ToolStrategy q=(ToolStrategy)s;String name=q.getTool().getName().toLowerCase();
        int[] count=range(name.contains("crater")?row[5]:name.contains("canyon")?row[6]:row[7]);
        if(count[1]==0)continue;q.setMinCount(count[0]);q.setMaxCount(count[1]);
        if(name.contains("crater")){int[] size=range(row[8]);q.setMinSize(size[0]);q.setMaxSize(size[1]);}
      }
      model.add(s);
    }
    model.add(NativeBatch.render(c,true,false,2048));
    File project=new File(out,"projects/"+id+".tfp");project.getParentFile().mkdirs();
    if(project.exists())throw new IOException("Refusing overwrite "+project);
    ObjectOutputStream save=new ObjectOutputStream(new FileOutputStream(project));save.writeObject(model);save.close();
    Random random=new Random(Long.parseLong(row[3]));random.nextDouble();Output output=new Output(model,false);Icosahedron mesh=null;
    System.out.println("START "+id);long start=System.currentTimeMillis();
    for(IStrategy s:model.strategies()){
      long t=System.currentTimeMillis();mesh=s.execute(random,mesh,output,NativeBatch.listener,.2,false);
      if(mesh==null)throw new IOException("Cancelled "+id);
      System.out.println("  "+s.getClass().getSimpleName()+" "+(System.currentTimeMillis()-t)+"ms");
    }
    if(output.numberOfRenderings()!=1)throw new IOException("Unexpected render count");
    File file=new File(out,"textures/"+id+".png");file.getParentFile().mkdirs();if(file.exists())throw new IOException("Refusing overwrite "+file);
    ImageIO.write(output.getRendering(0).getImage(),"png",file);
    ObjectInputStream input=new ObjectInputStream(new FileInputStream(project));BuildModel restored=(BuildModel)input.readObject();input.close();
    if(restored.countStrategies()!=model.countStrategies())throw new IOException("Project roundtrip mismatch");
    System.out.println("DONE "+id+" "+(System.currentTimeMillis()-start)+"ms; project readback pass");
    mesh=null;output=null;System.gc();
  }
  public static void main(String[] args)throws Exception{
    NativeBatch.app=new File(args[0]);out=new File(args[1]);NativeBatch.loadColours();NativeBatch.loadTools();loadPalettes();
    if(args.length>2&&args[2].equals("verify")){
      int count=0;
      for(String line:Files.readAllLines(new File(out,"source/jobs.tsv").toPath(),java.nio.charset.StandardCharsets.UTF_8)){
        String[] r=line.split("\t");ObjectInputStream in=new ObjectInputStream(new FileInputStream(new File(out,"projects/"+r[0]+".tfp")));BuildModel m=(BuildModel)in.readObject();in.close();
        int renders=0;
        for(IStrategy s:m.strategies()){
          if(s instanceof CloudStrategy)throw new IOException("Unexpected cloud strategy");
          if(s instanceof RenderStrategy){RenderStrategy render=(RenderStrategy)s;renders++;if(!render.getGroundColourizer().getName().equals(r[2])||render.getWidth(false)!=2048||render.getHeight(false)!=1024||render.isRenderCloudLayer())throw new IOException("Incorrect moon settings "+r[0]);}
        }
        if(renders!=1)throw new IOException("Incorrect render count");count++;
      }
      if(count!=6)throw new IOException("Incorrect moon count");
      System.out.println("{\"nativeProjectReadback\":6,\"paletteResolution\":\"pass\",\"noClouds\":true,\"dimensions\":\"pass\"}");return;
    }
    for(String line:Files.readAllLines(new File(out,"source/jobs.tsv").toPath(),java.nio.charset.StandardCharsets.UTF_8))execute(line.split("\t"));
    System.out.println("SIX MOONS COMPLETE");
  }
}
