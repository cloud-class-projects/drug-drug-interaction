declare -a counts=("tweetCount" "DrugCount" "SymptomCount" "coDrugCount" "coDrugSymptomCount" "coCoDrugSymptomCount")
for folder in "${counts[@]}"
do
    echo "Getting $folder"
    hadoop fs -get /lists/$folder ./results/
    echo "Sending Results to File"
    mv ./results/$folder/part-r-00000 ./results/$folder.csv
    echo "Cleaning"
    rm -rf ./results/$folder
done
