def fields_query(v):
    # fields queries were deprecated in 5.0
    major = int(v[0])
    if major >= 5:
        return False
    return True


def mapping_url_0x(v):
    return v.startswith("0")


def type_get(v):
    return v.startswith("0")


def create_with_mapping_post(v):
    major = int(v[0])
    return not major >= 5


def source_include(v):
    if v.startswith("5"):
        return False
    return True
