import sys
import uuid
import cloudmesh
import time
import paramiko as pm
import socket

cloudmesh.shell("cloud on india")
username = cloudmesh.load().username()
mesh = cloudmesh.mesh("mongo")
mesh.activate(username)
image = 'futuregrid/ubuntu-14.04'
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
    for server in mesh.servers(clouds=['india'], cm_user_id=username)['india'].keys():
        if server['name'] in vmNames:
            ips[server['name']]=server['addresses']['private'][0]['addr']
    for name in vmNames:
        serverIps.append(ips[name])
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
        serverIps.append(server['addresses']['private'][0]['addr'])
        serverPublicIps.append(mesh.assign_public_ip('india', serverid, username))
    return(serverIps, serverPublicIps)
#time.sleep(30)
def buildHostString( serverIps, vmNames):
    print('Building Hosts String')
    hostString = '#hadoop \n'
    for i in range(numStart):
        print(i)
        hostString += str(serverIps[i]) + ' ' + str(vmNames[i]) + ' hadoop' + str(i+1)+'\n'
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
#vmNames = ['ibwood_205', 'ibwood_206', 'ibwood_207']
initializeMachines()
serverIps = collectAndSetIpAddresses(vmNames)
#serverIps = collectIpAddresses(vmNames)
hostString = buildHostString(serverIps, vmNames)
addHostsCommand =   """echo "%s" >> /etc/hosts \n""" %hostString
transports = []
chans = []
sftps = []
hkeys = []
def establishConnections():
    for i in range(numStart):
        ip = serverIps[i]
        pm.rsakey.RSAKey(filename='../.ssh/id_rsa')
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
    for chan in chans:
        chan.send('sudo su \n')
        chan.send(addHostsCommand)
        chan.send('ssh-keygen -t rsa -P "" -f /root/.ssh/id_rsa\nn\n')
        chan.send('cat /root/.ssh/id_rsa.pub >> /home/ubuntu/hadoop'+str(i+1) + '.pub\n')
    for i in range(numStart):
        sf = sftps[i]
        f = sf.open('hadoop'+str(i)+'.pub', 'r')
        hkey = f.read()
        f.close()
        hkeys.append(hkey)
    for chan in chans:
        for hkey in hkeys:
            chan.send('echo "%s" >> /root/.ssh/authorized_keys\n'%hkey)
        chan.recv(10e6)
def moveFilesAndSetupHadoop():
    for sf in sftps:
        sf.put('installChef.sh', 'installChef.sh')
    for chan in chans:
        chan.send('source installChef.sh\n')
        chan.send('echo "done"\n')

    time.sleep(60)
    for chan in chans:
        doneyet = False
        while not doneyet:
            if chan.recv_ready():
                result = chan.recv(10e6)
                if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\n\root':
                    doneyet = True
            else:
                time.sleep(60)
    for chan in chans:
        chan.send('cd /home/ubuntu \n')
        chan.send('chmod -R 777 chef-repo\n')
    i = 0
    for sf in sftps:
        sf.put('roles/java.rb', 'chef-repo/roles/java.rb')
        sf.put('roles/hadoop.rb', 'chef-repo/roles/hadoop.rb')
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
                if result[result.rfind('@')-10:result.rfind('@')] == 'done\r\n\root':
                    doneyet = True
            else:
                time.sleep(60)
    chans[0].send('service hadoop-yarn-resourcemanager stop\n')
    chans[0].send('service hadoop-yarn-nodemanager stop\n')
    chans[0].send('/etc/init.d/hadoop-hdfs-namenode init\n')
    chans[0].send('service hadoop-hdfs-namenode start \n')
    chans[0].send('/usr/lib/hadoop/libexec/init-hdfs.sh \n')
    chans[0].send('service hadoop-yarn-resourcemanager start \n')
    chans[0].send('service hadoop-yarn-nodemanager start \n')
    for chan in chans[1:]:
        chan.send('service hadoop-hdfs-datanode start \n')
def setupZookeeper():
    i = 0
    for chan in chans:
        chan.send('cd /home/ubuntu \n')
        chan.send('wget http://www.interior-dsgn.com/apache/zookeeper/zookeeper-3.4.6/zookeeper-3.4.6.tar.gz \n')
        chan.send('tar -zxf zookeeper* \n')
        chan.send('rm *.tar.gz')
        chan.send('cd zookeeper-3.4.6 \n')
        chan.send('mkdir /var/zookeeper \n')
        chan.send('echo "'+str(i+1)+'" >>/var/zookeeper/myid \n')
        chan.send('mv ../chef-repo/zoo.cfg conf/ \n')
        
        chan.send('apt-get install daemontools \n')
        chan.send('cd /home/ubuntu \n')
        chan.send('mkdir zookeeper \n')
        sftps[i].put('run', 'run')
        
        chan.send('mv run zookeeper/run \n')
        chan.send('chmod 755 zookeeper/run \n')
    time.sleep(10)
    for chan in chans:
        chan.send('tmux \n')
        chan.send('supervise zookeeper & \n')
        chan.send('tmux detach \n')
        chan.send('crontab cleanZoo.txt \n')
        i += 1
        
    
     