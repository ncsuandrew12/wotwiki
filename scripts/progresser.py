from ticker import Ticker

class Progresser():
    def __init__(self, period=5):
        self.period = period
        self.ticker = Ticker(period)

    def tick(self):
        if self.ticker.tick():
            return self.emit_tick()
        return False
    
    def emit_tick(self):
        print(".", end="", flush=True)
        return True
    
    def done(self):
        ret = self.emit_done()
        self.restart()
        return ret
    
    def emit_done(self):
        print("done", flush=True)
        return True

    def restart(self):
        return self.ticker.restart()
