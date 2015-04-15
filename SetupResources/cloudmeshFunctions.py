#Functions For VM Setup with Cloudmesh
#Warning, with newer versions of cloudmesh and openstack juno, I could not get this working
import cloudmesh

cloudmesh.shell("cloud on india")
username = cloudmesh.load().username()
mesh = cloudmesh.mesh("mongo")
mesh.activate(username)
mesh.refresh(username, types=['flavors', 'images', 'servers'], names=['india'])
image = 'futuresystems/ubuntu-14.04'
flavor= 'm1.medium'
cloud = 'india'
numstart =3

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


def deleteServers():
    for serverID in serverIds:
        print(serverID)
        print(mesh.delete(cloud, serverID, username))
