1 System Overview
==
In order to detect and analyze data from Twitter we will build the following system using components from the Apache Big Data Stack of open source software. The Futuresystems Openstack service is used to deploy virtual machines as the cluster of servers for our system. Chef, the devops software, is used to help with some installation. The Apache Hadoop framework with its distributed file system and MapReduce system is a dependency of the other pieces of the system. Zookeeper is used as a coordination service. Apache HBase is a distributed NoSQL database used for data storage. Apache Pig is a high-level language used for data analysis. Python is used for installation and final analysis. Java is used for the actual data collection program. The system is organized on a cluster of three servers, although expansion to more servers should be straightforward. One server is used as a master for the rest when relevant, including the Hadoop NameNode, ResourceManager, and NodeManager, as well as the HBase HMaster. The master server also holds the Apache Pig installation for data analysis. The remaining servers run Hadoop DataNodes. All servers run an HBase HRegionServer and Zookeeper QuorumPeer. Two dictionaries are used from Lin et al.'s 2010 BICEPP paper [2], using the 857 generic drug names as well as 107 adverse effects (symptoms) from the Australian Medicines Handbook. A streaming filter is created to collect all public tweets from Twitter's public streaming API that mention any of these terms. Using the free API, up to 1000 such terms can be tracked. The user id, text, creation timestamp, and the symptoms and drugs mentioned in the tweet are saved to an HBase table. This data is later processed through Pig scripts and further ipython scripts.

2 Installing and Running the System
==
To install the drug-drug interaction symptom detector follow the steps below.

2.1 Initialize VMs
--
On india.futuresystems.org or other OpenStack server, clone the github repository:
  $git clone https://github.com/cloud-class-projects/drug-drug-interaction.git
Create three virtual machines (VMs) using the futuresystems/ubuntu-14.04 image, and associate three floating IP addresses with those VMs. A script is provided to help with the creation of the servers, named drug-drug-interaction/SetupResources/createServer.sh. This script requires three available floating IP address. If using the script, replace all the VM names with your own username and id number, replace the key name with your ssh key's name, and replace the floating-IP addresses with your  floating IP addresses. Run the script to create the VMs and associate the floating IP addresses. In the drug-drug-interaction/SetupResources folder of the git repo, create a file called pword.txt,which contains the password to the ssh key used to create the VMs. This is read by the setup script to connect to the VMs. Also edit the file configServers.py to include the names, privateip addresses, and public ip addresses of your VMs. The data associated with a particular VM should appear in the same location in each list. The rst VM is particularly important, as it will be the master server, containing the Hadoop Namenode, all managers, and analysis code. In the rest of this procedure the VMs will be referred to as hadoop1, hadoop2, and hadoop3 in the order they are entered into configServers.py

2.2 Install Software
--
Once your VMs are ready, make sure you are in the drug-drug-interaction/SetupResources folder. Start a python shell (tested for python 2.7.9). Issue the following commands in order:
  >from deploy_servers import *
  # Connect to the VMs and establish a session
  > establishConnections ()
  # Setup the VMs to allow communication with each other
  > connectHosts ()
  # Install Chef to help with Hadoop setup
  > installChef ()
  # Move necessary files and install Hadoop
  > moveFilesAndSetupHadoop ()
  # Install Zookeeper
  > setupZookeeper ()
  # Install HBase
  >setupHBase ()
  # Install Pig on the first server
  >setupPig ()
Note that installation will take some time and many messages will be printed. I find it is helpful to have a second ssh terminal open to hadoop1 to check on progress. Some particular things to watch for: installChef() may return before the chef-repo is fully set up. Either wait or try calling installChef() again before calling moveFilesAndSetupHadoop(). Often if something goes wrong during a step it can be xed by calling the function again (although this is not necessarily the cleanest way to fix the problem). If the python shell needs to be terminated, the process can pick up where it left off by first calling establishConnections() and then the next step of the process. To see if each step is successful the following should be true. After connectHosts(), the root user should be able to ssh into hadoop1, hadoop2, or hadoop3 from any of the machines. After installChef(), a chef-repo folder with full permissions should be located in /home/ubuntu. After moveFilesAndSetupHadoop() the services (run $jps) Namenode, NodeManager, and ResourceManager should be running on the hadoop1, and the service DataNode should be running on the hadoop2 and hadoop3. After setupZookeeper() the service QuorumPeerMain should be running on every VM. After setupHBase() the service HMaster should be running on hadoop1 and HRegionServer on all VMs. The function setupPig() finishes quickly, but the actual download and installation on the VM takes longer; it is done when a folder called Pig exists and the grunt shell can be accessed by calling $/home/ubuntu/pig/bin/pig after setting environment variables with $source /home/ubuntu/. bash_profile.

In my experience errors are most likely occur during the installation of HBase. I think this is due to the movement of les between india (or OpenStack server) and the VMs. Running setupHBase() a second time often xes this problem. If that still does not solve the problem, ssh into hadoop1 and try to manually start HBase as root user. Run source /home/ubuntu/.bash_profile to set proper environment variables. Check which services are running, both HRegionServer and HMaster should run on hadoop1. They can be started by calling
  /home/ubuntu/hbase/bin/hbase -daemon.sh --config /home/ubuntu/hbase/conf/start $service
where $service is either \master" or \regionserver". If you notice problems connecting to ZooKeeper in the logs, try killing the zookeeper process (run jps to see its process id). Since it is supervised, it should start up again; try starting the HBase daemons after Zookeeper has restarted.
2.3 Collect Data
On hadoop1, install git with $apt-get install git and clone the drug-drug-interaction github repository as done for india or the OpenStack server used to setup the VMs. In the GetTweets/conf folder is a blank conguration le named twitterConnectBlank.yml you will need to connect to Twitter. Rename the le twitterConnect.yml and enter your Twitter API credentials (you can apply for free here: https://apps.twitter.com/), or I can provide my twitter app credentials for the purpose of evaluation.

Source the /home/ubuntu/.bash_profile le. Run the hbase shell to create the table for the twitter data:
  $/home/ubuntu/hbase/bin/hbase shell
  >create 'tweets ', 'user_id ', 'drug ', 'symptom ', 'creation_ts ', 'tweet_text '
  >quit
To collect the tweets we supervise an executable jar located in GetTweets. A built jar is provided in the repo for convenience. If building from source, build the jar with dependencies using Maven and java 1.6 (netbeans project les are included) and move the jar to the GetTweets folder and name the jar GetTweets-1.0-SNAPSHOT-jar-with-dependencies.jar.

Create a new window in a tmux session. In the drug-drug-interaction folder run:
  $supervise GetTweets
You should see messages indicating the IDs of the tweets being collected. Allow this to run for some time. You can exit the tmux session but don't close the SSH session. For reasons I haven't been able to determine, tweet collection stops about an hour after the ssh session is closed.
2.4 Analyze Data
--
After tweets have been collecting for a while, run the analysis with Pig to count the number of users that have mentioned the drugs and symptoms in the dictionaries, also counting the number of users that have mentioned a drug and a symptom, two drugs, and two drugs and a symptom. As root user on hadoop1, run $source /home/ubuntu/.bash_profile. In drug-drug-interaction/GetTweets run the pig script wordCounts.pig with:
  $/ home / ubuntu / pig /bin/ pig wordCounts . pig
This should exit without any failures. Once the pig script is nished, the results reside on the hdfs; collect them to a local folder and reorganize them to a more convenient format by calling $./getResults.sh. The results folder will now contain the counts and co-occurence counts of users mentioning drugs and symptoms as a series of csv files.The ipython notebook AssociationRules.ipynb contains code for calculating measures fromassociation rule learning for the user counts, in particular producing rules for the association between sets of co-occuring drug-symptom combos. Example results for over one million tweets and users are included in the results folder but will be overwritten by running getResults.sh and AssociationRules.ipynb.
