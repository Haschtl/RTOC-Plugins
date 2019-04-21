class Stat_Filter():
    # temperature filter
    def __init__(self, min_class=0, max_class=100, class_size=2, N_mean=10):
        self._class_size = class_size
        self._N_mean = N_mean
        self._min_class = min_class
        self._max_class = max_class

        self._N_class = int((self._max_class-self._min_class)/self._class_size)

        self._ringbuffer = [0 for y in range(self._N_mean)]
        self._ringindex = 0

    def mean(self, list):
        sum = 0
        for l in list:
            sum += l
        return round(sum/len(list), 2)

    def statistic_filter(self, value):
        # handle ringbuffer
        if value is not None and value > self._min_class and value < self._max_class:
            self._ringbuffer[self._ringindex] = value
            self._ringindex += 1
            if self._ringindex >= self._N_mean:
                self._ringindex = 0

        # create histogram
        self._histogram = [[] for y in range(self._N_class)]
        for r in self._ringbuffer:
            i = int((r-self._min_class)/self._class_size)
            self._histogram[i].append(r)

        # get histogram maximum
        longest = []
        maxlen = 0
        for h in self._histogram:
            if len(h) > maxlen:
                maxlen = len(h)
                longest = h
        #print(self._histogram)
        print(value)
        return self.mean(longest)

    # def _WORKAROUND_READERROR(self, value, x=15, gain=1, oldvalue=None):
    #
    #     if value == None:
    #         value = 0
    #     value = value*gain
    #     if oldvalue is not None:
    #         while value > pow(2, x):
    #             value = value - pow(2, x)
    #     else:
    #         if value > pow(2, x):
    #             value = oldvalue
    #     value = value/gain
    #
    #     return value
