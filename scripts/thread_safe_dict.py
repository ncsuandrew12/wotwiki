import threading

class ThreadSafeDict(dict):
    def __init__(self, lock=threading.Lock()):
        super().__init__()
        self.lock = lock

    def __getitem__(self, key):
        with self.lock:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        with self.lock:
            super().__setitem__(key, value)