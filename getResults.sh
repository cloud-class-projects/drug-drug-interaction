declare -a counts=("tweetCount", "DrugCount", "SymptomCount", "coDrugCount", "coDrugSymptomCount", "coCoDrugSymptomCount")
for folder in "${counts[@]}":
do
    hadoop fs -get /lists/"$folder" ./results/
done
