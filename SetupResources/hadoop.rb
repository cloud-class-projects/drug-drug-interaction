name "hadoop"
description "set Hadoop attributes"
default_attributes(
  "hadoop" => {
    "distribution" => "bigtop",
    "core_site" => {
      "fs.defaultFS" => "hdfs://hadoop1"
    },
    "yarn_site" => {
      "yarn.resourcemanager.hostname" => "hadoop1"
    }
  }
)
run_list(
  "recipe[hadoop]"
)
