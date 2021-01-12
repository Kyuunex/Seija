def in_db_list(a_list, what):
    for item in a_list:
        if what == item[0]:
            return True
    return False


def unnest_list(a_list):
    buffer_list = []
    for item in a_list:
        buffer_list.append(item[0])
    return buffer_list