from BerkeleySync import SyncClient, SyncServer

if __name__ == '__main__':
    client = SyncClient()
    newServerInfo = client.start_syncronizing()
    if newServerInfo != None:
        server = SyncServer(newServerInfo[0], newServerInfo[1])
        server.start_server()
    else:
        print("Server not find")