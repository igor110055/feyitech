import math

def roundup(x, nearest):
    return int(math.ceil(x / float(nearest))) * int(nearest)