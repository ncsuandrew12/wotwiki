import time

class Ticker():
    def __init__(self, period=5):
        self.period = period
        self.last_time = None

    def restart(self):
        last = bool(self.last_time)
        self.last_time = None
        return last

    def tick(self):
        new_time = time.time()
        delta = self.last_time and (new_time - self.last_time) or int(new_time)
        if self.last_time is None or (delta >= self.period):
            self.last_time = new_time
            return True
        return False
