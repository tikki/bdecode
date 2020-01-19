import typing

_BType = typing.Union[dict, list, int, bytes]


def bdecode(data: bytes) -> _BType:
    """decode bencoded data to python objects"""
    return _dechunk(data, 0)[0]


def _dechunk(data: bytes, i: int) -> typing.Tuple[_BType, int]:
    c = data[i : i + 1]
    i += 1
    # check for known data types (dict, list, integer, string)
    if c == b"d":  # dict
        od = {}
        while 1:
            k, i = _dechunk(data, i)
            if not isinstance(k, bytes):
                raise ValueError("invalid key type")
            v, i = _dechunk(data, i)
            od[k] = v
            if data[i : i + 1] == b"e":
                return od, i + 1
    elif c == b"l":  # list
        ol = []
        while 1:
            e, i = _dechunk(data, i)
            ol.append(e)
            if data[i : i + 1] == b"e":
                return ol, i + 1
    elif c == b"i":  # integer
        oi = b""
        while 1:
            if data[i : i + 1] == b"e":
                return int(oi), i + 1
            oi += data[i : i + 1]
            i += 1
    elif c.isdigit():  # (byte) string
        # get the string size
        e = data.find(b":", i)
        l = int(
            data[i - 1 : e]
        )  # - 1 because of the initial increment at the beginning of dechunk
        # calc string boundaries
        s = e + 1
        # read data
        return data[s : s + l], s + l
    raise ValueError("unknown data type")
