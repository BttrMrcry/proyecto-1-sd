import time
from fake_time import fakeTimer

NUM_TIMERS = 5
if __name__ == '__main__':
    timers = [fakeTimer() for _ in range(NUM_TIMERS)]
    for timer in timers:
        timer.start_timer()
    print('waiting 60 seconds')
    time.sleep(60)
    for timer in timers:
        timer.stop_timer()
    sum_time = 0

    list_times = [timer.get_time() for timer in timers]
    for i, timer_time in enumerate(list_times):
        print(f'final time of timer {i} = {timer_time}')
    average_time = sum(list_times)/NUM_TIMERS
    differences = [abs(average_time - timer_time) for timer_time in list_times]
    avg_difference = sum(differences)/NUM_TIMERS
    print(f"average difference: {avg_difference}")

     