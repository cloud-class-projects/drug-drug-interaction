import sys
import uuid
#import cloudmesh
import time
import paramiko as pm
import socket
#had to run manual commands, mongo.start, mongo.boot y, mongo.boot N, user.mongo, mongo.simple
#changed key name to ibwood_ubuntu-key (so ibwood_ibwood_ubuntu-key)
#requires cmd 1.2.2

vmNames = []
serverIds = []
serverIps = []
serverPublicIps = []
serverPubKeys = []
clients = []

numStart = 3
def buildHostString( serverIps, vmNames):
    print('Building Hosts String')
    hostString = '#hadoop \n'
    for i in range(numStart):
        print(i)
        hostString += str(serverIps[i]) + ' ' + str(vmNames[i]) + ' '+ str(vmNames[i]).replace('_', '-') + ' hadoop' + str(i+1)+'\n'
    #    hostString += str(serverPublicIps[i]) + ' ' + str(vmNames[i]) + ' hadoop' + str(i+1)+'\n'
    return(hostString)

#If using Clousmesh:
#initializeMachines()
#serverIps = collectAndSetIpAddresses(serverIds)[0]
#Or with existing VMs
#vmNames = [...]
#serverIps = collectIpAddresses(vmNames)

from configServers import *
hostString = buildHostString(serverIps, vmNames)
addHostsCommand =   """echo "%s" >> /etc/hosts \n""" %hostString
transports = []
chans = []
sftps = []
hkeys = []
pwordF = open('pword.txt', 'r')
pword = pwordF.read()
pwordF.close()
def establishConnections():
    for i in range(numStart):
        print(i)
        ip = serverIps[i]#serverPublicIps[i]
        print(ip)
        pk=pm.rsakey.RSAKey(filename='../../.ssh/id_rsa', password=pword)
        scon = socket.create_connection((ip, '22'))
        print('created connection')
        tscon = pm.transport.Transport(scon)
        tscon.connect(username='ubuntu', pkey=pk)
        print('connected transport')
        transports.append(tscon)
        chan = transports[i].open_session()
        print('opened session')
        chan.settimeout(2)
        chan.get_pty()
        chan.invoke_shell()
        
        chans.append(chan)
        
        sf = transports[i].open_sftp_client()
        sftps.append(sf)
def connectHosts():
    for i in range(numStart):
        chan = chans[i]
        chan.send('sudo su \n')
        chan.send(addHostsCommand)
        chan.send('ssh-keygen -t rsa -P "" -f /root/.ssh/id_rsa\nn\n')
        time.sleep(5)
        chan.send('cat /root/.ssh/id_rsa.pub >> /home/ubuntu/hadoop'+str(i) + '.pub\n')
        chan.send('echo "done"\n')
    for chan in chans:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                #print(result)
                lastpart = result[result.rfind('@')-12:result.rfind('@')]
                if 'done' in lastpart and 'root' in lastpart:
                    #if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\nroot':
                    doneyet = True
                    print('DONE KeyGen')
            else:
                time.sleep(60)

    for i in range(numStart):
        sf = sftps[i]
        f = sf.open('/home/ubuntu/hadoop'+str(i)+'.pub', 'r')
        hkey = f.read()
        f.close()
        hkeys.append(hkey)
    for chan in chans:
        for hkey in hkeys:
            hkey = hkey[:-1]
            #print('key: ' + str(hkey))
            appendCommand = """echo "%s" >> /root/.ssh/authorized_keys \n"""%hkey
            #chan.send("""echo "%s" >> /root/.ssh/authorized_keys \n\n"""%hkey)
            chan.send(appendCommand)
            #time.sleep(1)
            result = chan.recv(10e6)
            #print(result)
    for chan in chans:
        for i in range(numStart):
            chan.send('ssh-keyscan hadoop'+str(i+1) +' >> ~/.ssh/known_hosts\n')
def installChef():
    for sf in sftps:
        sf.put('installChef.sh', 'installChef.sh')
    for chan in chans:
        chan.send('sudo su \n')
        chan.send('source installChef.sh\n')
        chan.send('echo "done"\n')

    time.sleep(60)
    for chan in chans:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                print(result)
                lastpart = result[result.rfind('@')-12:result.rfind('@')]
                if 'done' in lastpart and 'root' in lastpart:
                    print("DONEDONE")
                    doneyet = True
            else:
                time.sleep(60)
    for chan in chans:
        chan.send('cd /home/ubuntu \n')
        chan.send('chmod -R 777 chef-repo\n')
    time.sleep(10)
def moveFilesAndSetupHadoop():
    
    for chan in chans:
        chan.send('sudo su \n')
        chan.send('cd /home/ubuntu \n')
    i = 0
    for sf in sftps:
        print(str(i))
        sf.put('java.rb', 'chef-repo/roles/java.rb')
        sf.put('hadoop.rb', 'chef-repo/roles/hadoop.rb')
        sf.put('solo.rb', 'chef-repo/solo.rb')
        sf.put('zoo.cfg', 'chef-repo/zoo.cfg')
        sf.put('cleanZoo.txt', 'cleanZoo.txt')
        if i == 0:
            sf.put('hadoop_manager.json', 'chef-repo/solo.json')
        else:
            sf.put('hadoop_node.json', 'chef-repo/solo.json')
        i += 1
    for chan in chans:
        chan.send('cd chef-repo\n')
        chan.send('chef-solo -j solo.json -c solo.rb\n')
        chan.send('echo "done"\n')
    #print('here')
    time.sleep(60)
    for chan in chans:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                print(result)
                lastpart = result[result.rfind('@')-12:result.rfind('@')]
                if 'done' in lastpart and 'root' in lastpart:
                    #if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\nroot':
                    doneyet = True
                    print('DONEDONE2')
            else:
                time.sleep(60)
    chans[0].send('service hadoop-yarn-resourcemanager stop\n')
    chans[0].send('service hadoop-yarn-nodemanager stop\n')
    chans[0].send('/etc/init.d/hadoop-hdfs-namenode init\n')
    chans[0].send('service hadoop-hdfs-namenode start \n')
    chans[0].send('/usr/lib/hadoop/libexec/init-hdfs.sh \n')
    time.sleep(10)
    chans[0].send('service hadoop-yarn-resourcemanager start \n')
    chans[0].send('service hadoop-yarn-nodemanager start \n')
    for chan in chans[1:]:
        chan.send('service hadoop-hdfs-datanode start \n')
def setupZookeeper():
    i = 0
    for chan in chans:
        chan.send('sudo su \n')
        chan.send('cd /home/ubuntu \n')
        chan.send('wget http://www.interior-dsgn.com/apache/zookeeper/zookeeper-3.4.6/zookeeper-3.4.6.tar.gz \n')
        chan.send('tar -zxf zookeeper* \n')
        time.sleep(2)
        chan.send('rm *.tar.gz \n')
        
        chan.send('mv zookeeper-3.4.6 zookeeper \n')
        chan.send('cd zookeeper \n')
        chan.send('mkdir /var/zookeeper \n')
        chan.send('echo "'+str(i+1)+'" >>/var/zookeeper/myid \n')
        
        chan.send('apt-get install daemontools \n')
        i += 1
    time.sleep(20)
    i = 0
    for chan in chans:
        chan.send('cd /home/ubuntu \n')
        #chan.send('mkdir zookeeper \n')
        sftps[i].put('zoo.cfg', 'zoo.cfg')
        sftps[i].put('run', 'run')
        
        chan.send('mv zoo.cfg zookeeper/conf/zoo.cfg \n')
        chan.send('mv run zookeeper/run \n')
        chan.send('chmod 755 zookeeper/run \n')
        i += 1
    time.sleep(10)
    print(chans[0].recv(10e6))
    for chan in chans:
        chan.send('tmux \n')
        chan.send('cd /home/ubuntu \n')
        time.sleep(10)
        chan.send('supervise zookeeper & \n')
        chan.send('tmux detach \n')
        chan.send('crontab cleanZoo.txt \n')
        i += 1
    time.sleep(60)
    #for chan in chans:
    #    result = chan.recv(10e6)
    #    print(result)
def setupHBase():
    for chan in chans[:]:
        chan.send('sudo su \n')
        chan.send('cd /home/ubuntu \n')
        #chan.send('wget http://mirrors.sonic.net/apache/hbase/stable/hbase-0.98.10-hadoop2-bin.tar.gz \n')
        chan.send('wget http://www.motorlogy.com/apache/hbase/hbase-0.98.11/hbase-0.98.11-hadoop2-bin.tar.gz  \n')
        chan.send('tar xzf hbase-* \n')
        chan.send('rm *.tar.gz \n')
        chan.send('mv hbase-* hbase \n')
        chan.send('cd hbase \n')
        #chan.send('apt-get install openjdk-7-jdk openjdk-7-jre\ny\n')
        chan.send("echo 'export JAVA_HOME=/usr/lib/jvm/java-6-oracle-amd64/' >> /home/ubuntu/.bash_profile \n")
        chan.send("echo 'export HADOOP_USER_NAME=hdfs\n' >> /home/ubuntu/.bash_profile \n")
        #chan.send('export JAVA_HOME=/usr/lib/jvm/java-6-oracle-amd64\n')
        #chan.send('export HADOOP_USER_NAME=hdfs\n')
        chan.send("source /home/ubuntu/.bash_profile \n")
        chan.send('echo "done"\n')
    time.sleep(60)
    for chan in chans[:]:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                print(result)
                lastpart = result[result.rfind('@')-12:result.rfind('@')]
                if 'done' in lastpart and 'root' in lastpart:
                    #if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\nroot':
                    doneyet = True
                    print('DONEDONE3')
                else:
                    time.sleep(10)

    for sf in sftps[:]:
        sf.put('zoo.cfg', 'zoo.cfg')
        sf.put('hbase-env.sh', 'hbase-env.sh')
        sf.put('hbase-site.xml', 'hbase-site.xml')
        sf.put('regionservers', 'regionservers')
    time.sleep(20)
    for chan in chans[:]:
        chan.send('mv /home/ubuntu/zoo.cfg /home/ubuntu/hbase/conf/zoo.cfg \n')
        chan.send('mv /home/ubuntu/hbase-env.sh /home/ubuntu/hbase/conf/hbase-env.sh \n')
        chan.send('mv /home/ubuntu/hbase-site.xml /home/ubuntu/hbase/conf/hbase-site.xml \n')
        chan.send('mv /home/ubuntu/regionservers /home/ubuntu/hbase/conf/regionservers \n')
        chan.send('y \n y \n')
    
    chans[0].send('./bin/hbase-daemon.sh --config /home/ubuntu/hbase/conf start master\n')
    for chan in chans:
        chan.send('./bin/hbase-daemon.sh --config /home/ubuntu/hbase/conf start regionserver\n')
    #chans[0].send('hadoop fs -chown -R root /hbase\n')
    #chans[0].send('hadoop fs -chmod -R 777 /hbase\n')
    #chans[0].send('./bin/start-hbase.sh\n')
        ### Move zoo.cfg
        ### conf/hbase-env.sh
        ### conf/hbase-site.xml
        ### hadoop1 = /bin/start-hbase.sh
        
        #chan.send('wget -O-https://archive.apache.org/dist/bigtop/bigtop-0.7.0/repos/GPG-KEY-bigtop | apt-key add# - \n')
        #chan.send('wget -O /etc/apt/sources.list.d/bigtop.list http://www.apache.org/dist/bigtop/bigtop-0.7.0/repos/quantal/bigtop.list \n')
        #chan.send('apt-get update \n')
        
        #chan.send('cd /home/ubuntu \n')
        #chan.send('rm chef-repo/cookbooks/hadoop/recipes/hbase.rb \n')
        #chan.send("""echo 'package "hbase" \npackage "hbase-doc"\npackage "hbase-master"\npackage "hbase-regionserver"\npackage "hbase-rest"\npackage "hbase-thrift"\npackage "hue-hbase"\npackage "phoenix"' >> /chef-repo/cookbooks/hadoop/recipes/hbase.rb \n""")
    
def setupPig():
    #chans[0].send('sudo su\n')
    #chans[0].send('su hdfs\n')
    chans[0].send('hadoop fs -mkdir /lists\n')
    #chans[0].send('hadoop fs -chown -R root hbase\n')
    #chans[0].send('hadoop fs -chown -R root lists\n')
    #chans[0].send('exit\n')
    chans[0].send('cd /home/ubuntu \n')
    chans[0].send('wget http://download.nextag.com/apache/pig/pig-0.14.0/pig-0.14.0.tar.gz\n')
    chans[0].send('tar -xvf pig-0.14.0.tar.gz\n')
    chans[0].send('rm *.tar.gz\n')
    chans[0].send('mv pig-0.14.0 pig\n')
    chans[0].send("echo 'export PIG_CLASSPATH=/home/ubuntu/hbase/*:/home/ubuntu/hbase/lib/*:/home/ubuntu/pig/lib/*' >> /home/ubuntu/.bash_profile \n")
    chans[0].send("source /home/ubuntu/.bash_profile\n")

#How to To Run-#
#On india: ----#

#Create 3 VMs
#Add Floating Ips (possibly unnecessary)
#update configServers.py

#cd ~/drug-drug-interaction/SetupResources
#python
#>from deploy_servers import *
#>establishConnections()
#>connectHosts()
#>installChef()
#>moveFilesAndSetupHadoop()
#>setupZookeeper()
#>setupHBase()
#>setupPig()

#On Namenode (first VM in configServers.py) ----#
#cd /home/ubuntu
#./hbase/bin/hbase shell
#>create 'tweets', 'user_id', 'drug', 'symptom', 'creation_ts', 'tweet_text'
#>quit
#apt-get install git
#git clone git clone https://github.com/cloud-class-projects/drug-drug-interaction.git
#tmux a
#C+b c
#cd ~
#supervise GetTweets
#cd /home/ubuntu
#su hdfs
#source .bash_profile
#cd drug-drug-interaction
#../pig/bin/pig drug-drug-interaction/wordCounts.pig
#exit
#mkdir results
#./getResults.sh

