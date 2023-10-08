from ChristianSync import SyncClient

if __name__ == '__main__':
    connection = SyncClient()
    connection.update_time_periodicaly(60, intentional_delay = 2)
