import time
import fake_time


if __name__ == "__main__":
    timer = fake_time.fakeTimer()
    initial_time = int(time.time())
    timer.start_timer()
    next_second = initial_time + 1
    while int(time.time()) < initial_time + 60:
        while int(time.time()) < next_second:
            continue
        print(f"real elapsed time: {next_second - initial_time}. Fake timer elapsed time: {timer.get_time()}")
        next_second += 1
    timer.stop_timer()
    print(f"Time at stop: {timer.get_time()}")
    time.sleep(1)
    print(f"Time after 1 second stop: {timer.get_time()}")
    timer.start_timer()
    time.sleep(1)
    print(f"time aster 1 second restart: {timer.get_time()}")
    timer.start_timer()
    timer.stop_timer()

