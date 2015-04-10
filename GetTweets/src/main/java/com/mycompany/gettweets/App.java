package com.mycompany.gettweets;

import com.google.common.collect.Lists;
import com.google.protobuf.ServiceException;
import com.twitter.hbc.ClientBuilder;
import com.twitter.hbc.core.Client;
import com.twitter.hbc.core.Constants;
import com.twitter.hbc.core.endpoint.StatusesFilterEndpoint;
import com.twitter.hbc.core.processor.StringDelimitedProcessor;
import com.twitter.hbc.httpclient.auth.Authentication;
import com.twitter.hbc.httpclient.auth.OAuth1;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.io.*;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import org.json.*;
import org.yaml.snakeyaml.*;
import com.mongodb.*;
import com.mongodb.MongoClient;
import java.nio.charset.Charset;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import javax.ws.rs.Path;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.MasterNotRunningException;
import org.apache.hadoop.hbase.ZooKeeperConnectionException;
import org.apache.hadoop.hbase.client.Append;
import org.apache.hadoop.hbase.client.HBaseAdmin;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Row;

/**
 * Hello world!
 *
 */
public class App 
{
    public static void collect(List<String> symptoms, List<String> drugs, HTable hTable) throws InterruptedException, IOException
    {
        BlockingQueue<String> queue = new LinkedBlockingQueue<String>(10000);
        StatusesFilterEndpoint endpoint = new StatusesFilterEndpoint();
        // add some track terms
        endpoint.trackTerms(symptoms);//Lists.newArrayList("twitterapi", "#yolo"));
        //endpoint.trackTerms(Lists.newArrayList("alcohol", "zoloft", "prozac", "claritin", "advil", "acetomenaphen"));
        
        
        //Path connectPath = FileSystems.getDefault().getPath("conf", "twitterConnect.yml");
        String connectPath = System.getProperty("user.dir")+"/conf/twitterConnect.yml";   
        String connectYamlString = "";
        File ftwc = new File(connectPath);
        FileReader fr = new FileReader(ftwc);
        BufferedReader reader  =new BufferedReader(fr);
        String line = reader.readLine();
        while (line != null){
            //System.out.print(line);
            connectYamlString += line+"\n";
            line = reader.readLine();
        }
        //String connectYamlString=new String(File.readAllBytes(connectPath), "UTF-8");
        Yaml twty = new Yaml();
        Map<String, String> connectMap = (Map<String, String>) twty.load(connectYamlString);
        
        String consumerKey=connectMap.get("consumerKey");
        String consumerSecret=connectMap.get("consumerSecret");
        String token=connectMap.get("token");
        String secret=connectMap.get("secret");
        
        Authentication auth = new OAuth1(consumerKey, consumerSecret, token, secret);
        // Authentication auth = new BasicAuth(username, password);

        // Create a new BasicClient. By default gzip is enabled.
        Client client = new ClientBuilder()
                .hosts(Constants.STREAM_HOST)
                .endpoint(endpoint)
                .authentication(auth)
                .processor(new StringDelimitedProcessor(queue))
                .build();

        // Establish a connection
        client.connect();

        // Do whatever needs to be done with messages
        //for (int msgRead = 0; msgRead < 1000; msgRead++) {
        
        //for (int msgRead = 0; msgRead < 1; msgRead++)
        while(!client.isDone())
        {
            String msg = queue.take();
            JSONObject obj = new JSONObject(msg);

            //System.out.println(msg);
            String[] keyobjs = JSONObject.getNames(obj);
            List<String> tweetSymptoms = new ArrayList<String>();
            List<String> tweetDrugs = new ArrayList<String>();
            String tweetId = "";
            String userId = "";
            String date = "";
            String tweetText = "";
            String drugString = "";
            String symptomString = "";
            for (String keyobj : keyobjs) {
                if(keyobj.contentEquals("text"))
                {
                    tweetText = obj.getString(keyobj);
                    for (String symptom: symptoms)
                    {
                        if (tweetText.toLowerCase().contains(symptom))
                        {
                            tweetSymptoms.add(symptom);
                            if(symptomString.length() == 0)
                                symptomString += symptom;
                            else
                                symptomString += ","+ symptom;
                        }
                    }
                    for (String drug: drugs)
                    {
                        if (tweetText.toLowerCase().contains(drug))
                        {
                            tweetDrugs.add(drug);
                            if(drugString.length() == 0)
                                drugString += drug;
                            else
                                drugString += ","+ drug;
                        }
                    }
                }
                if(keyobj.contentEquals("id_str"))
                {
                    tweetId = obj.getString(keyobj);
                    //System.out.println(tweetId);
                }
                if(keyobj.contentEquals("user"))
                {
                    userId = obj.getJSONObject(keyobj).getString("id_str");
                    //System.out.println(obj.getJSONObject(keyobj).getString("id_str"));
                }
                if(keyobj.contentEquals("created_at"))
                {
                    SimpleDateFormat dForm = new SimpleDateFormat("E MMM dd HH:mm:ss Z yyyy");
                    try{
                        Date creation = dForm.parse(obj.getString("created_at"));
                        //System.out.println(creation);
                        long dateLong = creation.getTime();
                        date = String.valueOf(dateLong);
                    }
                    
                    catch (ParseException e){
                        //System.out.println(e);
                    }
                }
            }
            //System.out.println(tweetSymptoms);
            if (!tweetId.isEmpty()){
                Put tweetRow = new Put(tweetId.getBytes());
                tweetRow.add("tweet_text".getBytes(Charset.forName("UTF-8")), null, tweetText.getBytes());
                tweetRow.add("user_id".getBytes(), null, userId.getBytes());
                tweetRow.add("creation_ts".getBytes(), null, date.getBytes());
                tweetRow.add("drug".getBytes(), null, drugString.getBytes());
                tweetRow.add("symptom".getBytes(), null, symptomString.getBytes());
                //for(String drug: tweetDrugs)
                //{
                //    tweetRow.add("drug".getBytes(), drug.getBytes(), "t".getBytes());
                //}
                //for(String symptom: tweetSymptoms)
                //{
                //    tweetRow.add("symptom".getBytes(), symptom.getBytes(), "t".getBytes());
                //}
                //byte[] hello = "cf".getBytes(Charset.forName("UTF-8"));
                //byte[] qual = "qualifier".getBytes(Charset.forName("UTF-8"));
                //byte[] bang = "another".getBytes(Charset.forName("UTF-8"));

                //insRow.add(hello, qual, bang);
                System.out.println("Adding Tweet ID: "+tweetId.toString());
                System.out.flush();
                hTable.put(tweetRow );
            }
        }

        client.stop();
    }
    public static void main( String[] args ) throws InterruptedException, UnsupportedEncodingException, IOException, MasterNotRunningException, ZooKeeperConnectionException, ServiceException
    {
        //MongoClient mongoClient = new MongoClient("localhost");
        //DB db = mongoClient.getDB( "TweetDDI" );
        
        Configuration hBaseConfig = HBaseConfiguration.create();
        //hBaseConfig.set("hbase.zookeeper.quorum", "149.165.158.33,149.165.158.34,149.165.158.35");
        //hBaseConfig.set("hbase.zookeeper.property.clientPort","2181");
        //hBaseConfig.set("hbase.master.info.bindAddress", "149.165.158.33");
        //hBaseConfig.set("hbase.master.indo.port", "60010");
        HBaseAdmin.checkHBaseAvailable(hBaseConfig);
        
        
        //System.out.println(hBaseConfig.toString());
        //Connection connection = ConnectionFactory.createConnection(hBaseConfig);
        
        HTable hTable = new HTable(hBaseConfig, "tweets");
        String testString = "";
        
        /*Put insRow = new Put("javaRow".getBytes());
        
        byte[] hello = "cf".getBytes(Charset.forName("UTF-8"));
        byte[] qual = "qualifier".getBytes(Charset.forName("UTF-8"));
        byte[] bang = "another".getBytes(Charset.forName("UTF-8"));
        
        insRow.add(hello, qual, bang);
        System.out.println("Before Adding");
        System.out.flush();
        hTable.put(insRow );
        System.out.println("After Adding");
        System.out.flush();
        
        System.out.println("Before Scanning");
        System.out.flush();
        ResultScanner rs= hTable.getScanner(hello);
        for (Result row: rs)
        {
            System.out.println(row.toString());
        }
        System.out.println("After Scanning");
        System.out.flush();*/
        // PUT hbase on CLASSPATH
        //hBaseConfig.setInt("timeout", 120000);
        //hBaseConfig.set("hbase.master", "149.165.158.33:2181");
        //Path symptomPath = FileSystems.getDefault().getPath("dictionaries", "symptoms.json");
        //String symptomString = new String(Files.readAllBytes(symptomPath), "UTF-8");
        String symptonPath = System.getProperty("user.dir")+"/dictionaries/symptoms.json";
        String symptomString = "";
        File sf = new File(symptonPath);
        FileReader sfr = new FileReader(sf);
        BufferedReader sreader = new BufferedReader(sfr);
        String line = sreader.readLine();
        while (line != null){
            //System.out.print(line);
            symptomString += line;
            line = sreader.readLine();
        }
        JSONObject symptomJSON = new JSONObject(symptomString);
        JSONArray symptomArray = symptomJSON.getJSONArray("symptoms");
        List<String> symptoms = new ArrayList<String>();
        List<String> symptomIds = new ArrayList<String>();
        for(int sIt = 0; sIt < symptomArray.length(); sIt++)
        {
            symptoms.add(symptomArray.getString(sIt));
          
            
            
            //symptomIds.add(dbObj.get("_id").toString());
        }
        
        //Path drugPath = FileSystems.getDefault().getPath("dictionaries", "alldrugs.json");
        //String drugString = new String(Files.readAllBytes(drugPath), "UTF-8");
        String drugPath = System.getProperty("user.dir") + "/dictionaries/alldrugs.json";
        String drugString = "";
        File df = new File(drugPath);
        FileReader dfr = new FileReader(df);
        BufferedReader dreader = new BufferedReader(dfr);
        String dline = dreader.readLine();
        while (dline != null){
            drugString += dline;
            dline = dreader.readLine();
        }
        JSONObject drugJSON = new JSONObject(drugString);
        JSONArray drugArray = drugJSON.getJSONArray("drugs");
        List<String> drugs = new ArrayList<String>();
        List<String> drugIds = new ArrayList<String>();
        for(int dIt = 0; dIt < drugArray.length(); dIt++)
        {
            //System.out.println(drugArray.getString(dIt)
            drugs.add(drugArray.getString(dIt));

            //symptomIds.add(dbObj.get("_id").toString());
            //symptomIds.add(dbObj.get(symptomString));
        }
        //System.out.println(drugs.get(0));
        
        
        //System.out.println(inDB.toString());
        collect(symptoms, drugs, hTable);
        //testYaml();
    }
}

 /*MongoClient mongoClient = new MongoClient("localhost");
        DB db = mongoClient.getDB( "TweetDDI" );
        
        DBCollection coll = db.getCollection("Symptoms");
        Path symptomPath = FileSystems.getDefault().getPath("dictionaries", "symptoms.json");
        String symptomString = new String(Files.readAllBytes(symptomPath), "UTF-8");
        JSONObject symptomJSON = new JSONObject(symptomString);
        JSONArray symptomArray = symptomJSON.getJSONArray("symptoms");
        List<String> symptoms = new ArrayList<String>();
        List<String> symptomIds = new ArrayList<String>();
        for(int sIt = 0; sIt < symptomArray.length(); sIt++)
        {
            symptoms.add(symptomArray.getString(sIt));
            DBObject query = new BasicDBObject("symptom", symptoms.get(sIt));
            DBObject dbObj = coll.findOne(query);
            
            if(dbObj == null)
            {
                coll.insert(query);
                dbObj = coll.findOne(query);
            }
            symptomIds.add(dbObj.get("_id").toString());
            //symptomIds.add(dbObj.get(symptomString));
        }
        System.out.println(coll.count() );
        
        coll = db.getCollection("Drugs");
        Path drugPath = FileSystems.getDefault().getPath("dictionaries", "alldrugs.json");
        String drugString = new String(Files.readAllBytes(drugPath), "UTF-8");
        JSONObject drugJSON = new JSONObject(drugString);
        JSONArray drugArray = drugJSON.getJSONArray("drugs");
        List<String> drugs = new ArrayList<String>();
        List<String> drugIds = new ArrayList<String>();
        for(int dIt = 0; dIt < drugArray.length(); dIt++)
        {
            //System.out.println(drugArray.getString(dIt)
            drugs.add(drugArray.getString(dIt));
            DBObject query = new BasicDBObject("drug", drugs.get(dIt));
            DBObject dbObj = coll.findOne(query);
            if(dbObj == null)
            {
                coll.insert(query);
                dbObj = coll.findOne(query);
            }
            symptomIds.add(dbObj.get("_id").toString());
            //symptomIds.add(dbObj.get(symptomString));
        }
        System.out.println(coll.count());
        System.out.println(drugs.get(0));
        
        
        //System.out.println(inDB.toString());
        collect(symptoms, drugs);
        //testYaml();*/