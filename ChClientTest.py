from ChristianSync import SyncClient

if __name__ == '__main__':
    connection = SyncClient()
    connection.update_time_periodicaly(intentional_delay = 0, period = 60)
