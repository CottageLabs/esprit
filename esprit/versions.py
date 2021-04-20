def fields_query(v):
    # fields queries were deprecated in 5.0
    if int(v[0]) >= 5:
        return False
    return True


def mapping_url_0x(v):
    return v.startswith("0")


def type_get(v):
    return v.startswith("0")


def create_with_mapping_post(v):
    return int(v[0]) < 5


def source_include(v):
    if int(v[0]) >= 5:
        return False
    return True
