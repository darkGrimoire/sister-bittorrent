def searchDictIdx(a_list: list, key, value):
    for idx, x in enumerate(a_list):
        if x[key] == value:
            return idx, x
    else:
        return -1, None