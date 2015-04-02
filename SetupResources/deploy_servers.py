import sys
import uuid
import cloudmesh
import time
import paramiko as pm
import socket
#had to run manual commands, mongo.start, mongo.boot y, mongo.boot N, user.mongo, mongo.simple
#changed key name to ibwood_ubuntu-key (so ibwood_ibwood_ubuntu-key)
#requires cmd 1.2.2
cloudmesh.shell("cloud on india")
username = cloudmesh.load().username()
mesh = cloudmesh.mesh("mongo")
mesh.activate(username)
mesh.refresh(username, types=['flavors', 'images', 'servers'], names=['india'])
image = 'futuresystems/ubuntu-14.04'
flavor= 'm1.medium'
cloud = 'india'

vmNames = []
serverIds = []
serverIps = []
serverPublicIps = []
serverPubKeys = []
clients = []

numStart = 3
def initializeMachines():
    print('Initializing Machines')   
    for i in range(numStart):
        print(i)
        result = mesh.start(cloud=cloud, cm_user_id=username, image=image, flavor=flavor)
        print(result)
        vmNames.append(result['name'])
        serverIds.append(result['server']['id'])
    return(vmNames, serverIds)
def collectIpAddresses(vmNames):
    ips = {}
    pubips = {}
    ids = {}
    servers=mesh.servers(clouds=['india'], cm_user_id=username)['india']
    for serverId in servers:
        server = servers[serverId]
        print(server)
        if server['name'] in vmNames:
            ips[server['name']]=server['addresses']['int-net'][0]['addr']
            pubips[server['name']]=server['addresses']['int-net'][1]['addr']
            ids[server['name']] = serverId
    for name in vmNames:
        serverIps.append(ips[name])
	serverPublicIps.append(pubips[name])
        serverIds.append(ids[name])
    return(serverIps)
def collectAndSetIPAddresses(serverIds):
    print('Collecting IPs')
    mesh.refresh(username, names=['india'], types=['servers'])
    i = 0
    for serverid in serverIds:
        print(i)
        i+=1
        server = mesh.servers(clouds=['india'], cm_user_id=username)['india'][serverid]
        while not server['status'] == 'ACTIVE':
            time.sleep(2)
            mesh.refresh(username, names=['india'], types=['servers'])
            server = mesh.servers(clouds=['india'], cm_user_id=username)['india'][serverid]
        time.sleep(1)
        #print(server)
	serverIps.append(server['addresses']['int-net'][0]['addr'])
        serverPublicIps.append(mesh.assign_public_ip('india', serverid, username))
    return(serverIps, serverPublicIps)
#time.sleep(30)
def buildHostString( serverIps, vmNames):
    print('Building Hosts String')
    hostString = '#hadoop \n'
    for i in range(numStart):
        print(i)
        hostString += str(serverIps[i]) + ' ' + str(vmNames[i]) + ' '+ str(vmNames[i]).replace('_', '-') + ' hadoop' + str(i+1)+'\n'
    #    hostString += str(serverPublicIps[i]) + ' ' + str(vmNames[i]) + ' hadoop' + str(i+1)+'\n'
    return(hostString)

def deleteServers():
    for serverID in serverIds:
        print(serverID)
        print(mesh.delete(cloud, serverID, username))
#"""sudo bash -c 'echo "%s" >> /etc/hosts'\n"""%hostString
#def startClients(): 
#    #for ip in serverPublicIps:
#    print('Adding Host IP Addresses and creating public keys')
#    i = 1
#    for ip in serverIps:
#        print(i)
#        i += 1
##        print(ip)
#        
#        #mesh.ssh_execute(ipaddr=ip, username='ubuntu', command = addHostsCommand)
#        client = pm.SSHClient()
#        client.set_missing_host_key_policy(pm.client.AutoAddPolicy())
#        #print('trying to connect')
#        #pk = pm.rsakey.RSAKey(filename='../.ssh/id_rsa')
#        #print('got key')
#        #sys.stdout.flush()
#        #scon = socket.create_connection((ip, '22'))
#        #print('created socket')
#        #sys.stdout.flush()
#        #tscon = pm.transport.Transport(scon)
#        #print('creating transport')
#        #sys.stdout.flush()
#        #tscon.connect(username='ubuntu', pkey=pk)
#        
#        #transports.append(tscon)
#    #return(transports)
#vmNames = ['ibwood_36', 'ibwood_37', 'ibwood_38']
#serverIps = collectIpAddresses(vmNames)
initializeMachines()
serverIps = collectAndSetIPAddresses(serverIds)[0]
hostString = buildHostString(serverPublicIps, vmNames)
addHostsCommand =   """echo "%s" >> /etc/hosts \n""" %hostString
transports = []
chans = []
sftps = []
hkeys = []
def establishConnections():
    for i in range(numStart):
        ip = serverPublicIps[i]
        pk=pm.rsakey.RSAKey(filename='../../.ssh/id_rsa')
        scon = socket.create_connection((ip, '22'))
        tscon = pm.transport.Transport(scon)
        tscon.connect(username='ubuntu', pkey=pk)
        transports.append(tscon)
        chan = transports[i].open_session()
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
        
    for i in range(numStart):
        sf = sftps[i]
        f = sf.open('hadoop'+str(i)+'.pub', 'r')
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
                if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\nroot':
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
    time.sleep(60)
    for chan in chans:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                print(result)
                if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\nroot':
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
    for chan in chans[:1]:
        chan.send('sudo su \n')
        chan.send('cd /home/ubuntu \n')
        #chan.send('wget http://mirrors.sonic.net/apache/hbase/stable/hbase-0.98.10-hadoop2-bin.tar.gz \n')
        chan.send('wget http://mirrors.sonic.net/apache/hbase/stable/hbase-1.0.0-bin.tar.gz \n')
        chan.send('tar xzf hbase-1* \n')
        chan.send('rm *.tar.gz \n')
        chan.send('mv hbase-1* hbase \n')
        chan.send('mv hbase-* hbase \n')
        chan.send('cd hbase \n')
        chan.send('export JAVA_HOME=/usr \n')
        chan.send('export HADOOP_USER_NAME=hdfs\n')
        chan.send('echo "done"\n')
    time.sleep(60)
    for chan in chans[:1]:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                print(result)
                if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\nroot':
                    doneyet = True
                    print('DONEDONE3')

    for sf in sftps[:1]:
        sf.put('zoo.cfg', 'zoo.cfg')
        sf.put('hbase-env.sh', 'hbase-env.sh')
        sf.put('hbase-site.xml', 'hbase-site.xml')
        sf.put('regionservers', 'regionservers')
    for chan in chans[:1]:
        chan.send('mv /home/ubuntu/zoo.cfg /home/ubuntu/hbase/conf/zoo.cfg \n')
        chan.send('mv /home/ubuntu/hbase-env.sh /home/ubuntu/hbase/conf/hbase-env.sh \n')
        chan.send('mv /home/ubuntu/hbase-site.xml /home/ubuntu/hbase/conf/hbase-site.xml \n')
        chan.send('mv /home/ubuntu/regionservers /home/ubuntu/hbase/conf/regionservers \n')
        chan.send('y \n y \n')

    chans[0].send('./bin/start-hbase.sh')
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
    chans[0].send('su hdfs\n')
    chans[0].send('hadoop fs -mkdir lists\n')
    chans[0].send('hadoop fs -chown -R root hbase\n')
    chans[0].send('hadoop fs -chown -R root lists\n')
    chans[0].send('exit\n')
    chans[0].send('wget http://download.nextag.com/apache/pig/pig-0.14.0/pig-0.14.0.tar.gz\n')
    chans[0].send('tar -xvf pig-0.14.0.tar.gz\n')
    chans[0].send('rm *.tar.gz\n')
    chans[0].send('mv pig-0.14.0 pig\n')
    chans[0].send("echo 'PIG_CLASSPATH=/home/ubuntu/pig/lib/*:/home/ubuntu/hbase/*:/home/ubuntu/hbase/lib/*' >> .bash_profile \n")
    chans[0].send("source ~/.bash_profile\n")

#To Run
#./hbase/bin/hbase shell
#>create 'tweets', 'userid', 'drug', 'symptom', 'creation_ts', 'tweet_text'
#>quit
#tmux a
#C+b c
#cd ~
#supervise GetTweets


