package com.mycompany.gettweets;

import com.google.common.collect.Lists;
import com.twitter.hbc.ClientBuilder;
import com.twitter.hbc.core.Client;
import com.twitter.hbc.core.Constants;
import com.twitter.hbc.core.endpoint.StatusesFilterEndpoint;
import com.twitter.hbc.core.processor.StringDelimitedProcessor;
import com.twitter.hbc.httpclient.auth.Authentication;
import com.twitter.hbc.httpclient.auth.OAuth1;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.nio.file.*;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import org.json.*;
import org.yaml.snakeyaml.*;
import com.mongodb.*;
import com.mongodb.MongoClient;
import java.util.Date;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
/**
 * Hello world!
 *
 */
public class App 
{
    public static void collect(List<String> symptoms, List<String> drugs) throws InterruptedException, IOException
    {
        BlockingQueue<String> queue = new LinkedBlockingQueue<String>(10000);
        StatusesFilterEndpoint endpoint = new StatusesFilterEndpoint();
        // add some track terms
        endpoint.trackTerms(symptoms);//Lists.newArrayList("twitterapi", "#yolo"));
        //endpoint.trackTerms(Lists.newArrayList("alcohol", "zoloft", "prozac", "claritin", "advil", "acetomenaphen"));
        
        
        Path connectPath = FileSystems.getDefault().getPath("conf", "twitterConnect.yml");
        String connectYamlString = new String(Files.readAllBytes(connectPath), "UTF-8");
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
        
        for (int msgRead = 0; msgRead < 1; msgRead++)
        {
            String msg = queue.take();
            JSONObject obj = new JSONObject(msg);

            System.out.println(msg);
            String[] keyobjs = JSONObject.getNames(obj);
            List<String> tweetSymptoms = new ArrayList<String>();
            List<String> tweetDrugs = new ArrayList<String>();
            String tweetId = "";
            String userId = "";
            String date = "";
            for (String keyobj : keyobjs) {
                if(keyobj.contentEquals("text"))
                {
                    String tweetText = obj.getString(keyobj);
                    for (String symptom: symptoms)
                    {
                        if (tweetText.contains(symptom))
                        {
                            tweetSymptoms.add(symptom);
                        }
                    }
                    for (String drug: drugs)
                    {
                        if (tweetText.contains(drug))
                        {
                            tweetDrugs.add(drug);
                        }
                    }
                }
                if(keyobj.contentEquals("id_str"))
                {
                    tweetId = obj.getString(keyobj);
                    System.out.println(tweetId);
                }
                if(keyobj.contentEquals("user"))
                {
                    userId = obj.getJSONObject(keyobj).getString("id_str");
                    System.out.println(obj.getJSONObject(keyobj).getString("id_str"));
                }
                //if(keyobj.contectEquals("created_at"))
                //{
                //    Date creation = new Date();
                //    SimpleDateFormat;
                //    creation.obj.getString(keyobj);
                //}
            }
            System.out.println(tweetSymptoms);
        }

        client.stop();
    }
    public static void main( String[] args ) throws InterruptedException, UnsupportedEncodingException, IOException
    {
        MongoClient mongoClient = new MongoClient("localhost");
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
        //testYaml();
    }
}
