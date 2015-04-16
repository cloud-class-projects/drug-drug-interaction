data = LOAD 'hbase://tweets' USING org.apache.pig.backend.hadoop.hbase.HBaseStorage('user_id:, symptom:, drug:', '-loadKey true') AS (id:bytearray, user_id:map[], symptom:map[], drug:map[]);
--load the data

tokenizedDS = FOREACH data GENERATE user_id#'' as userid,FLATTEN(TOKENIZE(drug#'')) as drug, FLATTEN(TOKENIZE(symptom#'')) as symptom;
tokenizedDrugs = FOREACH data GENERATE user_id#'' as userid,FLATTEN(TOKENIZE(drug#'')) as drug;
tokenizedSymptoms = FOREACH data GENERATE user_id#'' as userid,FLATTEN(TOKENIZE(symptom#'')) as symptom;

--group by user
byUser = GROUP data by user_id#'';
byUserDS = GROUP tokenizedDS by userid;
byUserDrugs = Group tokenizedDrugs by userid;
byUserSymptoms = Group tokenizedSymptoms by userid;

--limit tuples to users and words only (necessary for the DISTINCT statement)
byUserDS = FOREACH byUserDS GENERATE group as userid, tokenizedDS.drug as drugs, tokenizedDS.symptom as symptoms;
byUserDrugs = FOREACH byUserDrugs GENERATE group as userid, tokenizedDrugs.drug as drugs;
byUserSymptoms = FOREACH byUserSymptoms GENERATE group as userid, tokenizedSymptoms.symptom as symptoms;

--use only distinct words
byUserDS = FOREACH byUserDS {drugs = DISTINCT drugs; symptoms = DISTINCT symptoms; GENERATE userid, drugs, symptoms;};
byUserDrugs = FOREACH byUserDrugs {drugs = DISTINCT drugs; GENERATE userid, drugs;};
byUserSymptoms = FOREACH byUserSymptoms {symptoms = DISTINCT symptoms; GENERATE userid, symptoms;};

--create flattened unigrams for users:
DrugCount = FOREACH byUserDrugs {GENERATE userid, FLATTEN(drugs.drug) AS drug;};
SymptomCount = FOREACH byUserSymptoms {GENERATE userid, FLATTEN(symptoms.symptom) AS symptom;};

--create flattened bigrams (two-word pairs) for users
coDrugCount= FOREACH byUserDrugs {coDrugs = CROSS drugs.drug, drugs.drug; generate userid, FLATTEN(coDrugs) as (drug1, drug2);};
coDrugSymptomCount = FOREACH byUserDS {coDrugSymptoms = CROSS drugs.drug, symptoms.symptom; GENERATE userid, FLATTEN(coDrugSymptoms) as (drug, symptom);};
coCoDrugSymptomCount =  FOREACH byUserDS {coDrugs = CROSS drugs.drug, drugs.drug; coDrugSymptoms = CROSS coDrugs, symptoms.symptom; generate userid, FLATTEN(coDrugSymptoms) as (drug1, drug2, symptom);};

--filter out same-word and flipped tuples (put bigrams in alphabetical order)
coDrugCount = FILTER coDrugCount BY drug1 < drug2;
coCoDrugSymptomCount = FILTER coCoDrugSymptomCount BY drug1 < drug2;

--group tuples by drug/symptom
DrugCount = GROUP DrugCount BY drug;
SymptomCount = GROUP SymptomCount BY symptom;
coDrugCount = GROUP coDrugCount BY (drug1, drug2);
coDrugSymptomCount = GROUP coDrugSymptomCount BY (drug, symptom);
coCoDrugSymptomCount = GROUP coCoDrugSymptomCount BY (drug1, drug2, symptom);

--count the users using each bigram
tweetCount = FOREACH (GROUP data ALL) GENERATE COUNT(data);
userCount = FOREACH (GROUP byUser ALL) GENERATE COUNT(byUser);
DrugCount = FOREACH DrugCount GENERATE group as drug, COUNT(DrugCount) as count;
SymptomCount = FOREACH SymptomCount GENERATE group as symptom, COUNT (SymptomCount) as count;
coDrugCount = FOREACH coDrugCount GENERATE group as drugdrug, COUNT(coDrugCount) as count;
coDrugSymptomCount = FOREACH coDrugSymptomCount GENERATE group as drugsymptom, COUNT(coDrugSymptomCount) as count;
coCoDrugSymptomCount = FOREACH coCoDrugSymptomCount GENERATE group as drugdrugsymptom, COUNT(coCoDrugSymptomCount) as count;

--order by frequency
DrugCount = ORDER DrugCount BY count;
SymptomCount = ORDER SymptomCount BY count;
coDrugCount = ORDER coDrugCount BY count;
coDrugSymptomCount = ORDER coDrugSymptomCount BY count;
coCoDrugSymptomCount = ORDER coCoDrugSymptomCount BY count;

--Remove Old Results!
rmf /lists/tweetCount;
rmf /lists/userCount;
rmf /lists/DrugCount;
rmf /lists/SymptomCount;
rmf /lists/coDrugCount;
rmf /lists/coDrugSymptomCount;
rmf /lists/coCoDrugSymptomCount

--Store Results!
store tweetCount into '/lists/tweetCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');
store userCount into '/lists/userCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');
store DrugCount into '/lists/DrugCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');
store SymptomCount into '/lists/SymptomCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');
store coDrugCount into '/lists/coDrugCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');
store coDrugSymptomCount into '/lists/coDrugSymptomCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');
store coCoDrugSymptomCount into '/lists/coCoDrugSymptomCount' using org.apache.pig.piggybank.storage.CSVExcelStorage(',');

