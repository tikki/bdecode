from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, ParseResult as URL
import codecs
import dataclasses
import math
import typing

from bdecode import bdecode

Info = typing.Union["SingleFile", "MultiFile"]
_PathLike = typing.Union[str, bytes, int]
_RawType = typing.Dict[
    bytes,
    typing.Union[typing.Dict[bytes, typing.Any], typing.List[typing.Any], int, bytes],
]


@dataclasses.dataclass
class _Info:
    piece_length: int
    pieces: typing.List[bytes]
    private: typing.Optional[bool]
    name: Path


@dataclasses.dataclass
class _SingleFile:
    name: Path
    length: int
    md5sum: typing.Optional[bytes]


@dataclasses.dataclass
class SingleFile(_Info, _SingleFile):
    pass


@dataclasses.dataclass
class MultiFile(_Info):
    files: typing.List[_SingleFile]


@dataclasses.dataclass
class Torrent:
    info: Info
    announce: URL
    announce_lists: typing.List[typing.List[URL]]
    creation_date: typing.Optional[datetime]
    comment: typing.Optional[bytes]
    created_by: typing.Optional[bytes]
    encoding: typing.Optional[bytes]


_ChunkT = typing.TypeVar("_ChunkT")


def _chunk(
    iterable: typing.Iterable[_ChunkT], n: int
) -> typing.Iterator[typing.Tuple[_ChunkT, ...]]:
    args = [iter(iterable)] * n
    return zip(*args)


def _load_single(raw: _RawType, args: typing.Dict[str, typing.Any]) -> SingleFile:
    return SingleFile(**args)


def _load_multi(raw: _RawType, args: typing.Dict[str, typing.Any]) -> MultiFile:
    if not isinstance(raw[b"files"], list):
        raise TypeError("invalid files list")
    args["files"] = [
        _SingleFile(
            name=Path(*[s.decode("utf-8") for s in file[b"path"]]),
            length=file[b"length"],
            md5sum=file.get(b"md5sum"),
        )
        for file in raw[b"files"]
    ]

    for file in args["files"]:
        if not isinstance(file.length, int) or file.length < 0:
            raise TypeError("invalid file length")
        if file.md5sum is not None:
            if not isinstance(file.md5sum, bytes) or len(file.md5sum) != 32:
                raise TypeError("invalid md5sum")
            file.md5sum = codecs.decode(file.md5sum, "hex")

    return MultiFile(**args)


def _load_info(raw: _RawType) -> Info:
    args: typing.Dict[str, typing.Any] = {
        "piece_length": raw[b"piece length"],
        "pieces": raw[b"pieces"],
        "private": raw.get(b"private"),
        "name": raw[b"name"],
    }

    if not isinstance(args["piece_length"], int) or args["piece_length"] < 1:
        raise TypeError("invalid piece length")

    if not isinstance(args["pieces"], bytes) or len(args["pieces"]) % 20 != 0:
        raise TypeError("invalid piece list")
    args["pieces"] = [bytes(chunk) for chunk in _chunk(args["pieces"], 20)]

    if args["private"] is not None:
        if args["private"] == 0:
            args["private"] = False
        elif args["private"] == 1:
            args["private"] = True
        else:
            raise ValueError("invalid private flag")

    if not isinstance(args["name"], bytes):
        raise TypeError("invalid name")
    args["name"] = Path(args["name"].decode("utf-8"))

    return _load_multi(raw, args) if b"files" in raw else _load_single(raw, args)


def load(path: _PathLike) -> Torrent:
    """Load data from torrent file."""
    with open(path, "rb") as fo:
        buf = fo.read()
    return loads(buf)


def loads(data: bytes) -> Torrent:
    """Load data from torrent file contents."""
    meta = bdecode(data)
    if not isinstance(meta, dict):
        raise TypeError("invalid metadata")

    args: typing.Dict[str, typing.Any] = {
        "info": meta[b"info"],  # XXX
        "announce": meta[b"announce"],
        "announce_lists": meta.get(b"announce-list"),  # XXX
        "creation_date": meta.get(b"creation date"),
        "comment": meta.get(b"comment"),
        "created_by": meta.get(b"created by"),
        "encoding": meta.get(b"encoding"),
    }

    if not isinstance(args["info"], dict):
        raise TypeError("invalid info block")
    args["info"] = _load_info(args["info"])

    if not isinstance(args["announce"], bytes):
        raise TypeError("invalid announce URL")
    args["announce"] = urlparse(args["announce"].decode("utf-8"))

    if args["announce_lists"] is None:
        args["announce_lists"] = []
    else:
        if not isinstance(args["announce_lists"], list):
            raise TypeError("invalid announce list")
        urls = []
        for url in args["announce_lists"]:  # XXX
            if not isinstance(url, bytes):
                raise TypeError("invalid announce list element")
            urls.append(urlparse(url))
        args["announce_lists"] = urls

    if args["creation_date"] is not None:
        if not isinstance(args["creation_date"], int):
            raise TypeError("invalid creation date")
        args["creation_date"] = datetime.fromtimestamp(args["creation_date"])

    if args["comment"] is not None:
        if not isinstance(args["comment"], bytes):
            raise TypeError("invalid comment")
        args["comment"] = args["comment"].decode("utf-8")

    if args["created_by"] is not None:
        if not isinstance(args["created_by"], bytes):
            raise TypeError("invalid creator")
        args["created_by"] = args["created_by"].decode("utf-8")

    if args["encoding"] is not None:
        if not isinstance(args["encoding"], bytes):
            raise TypeError("invalid encoding")
        args["encoding"] = args["encoding"].decode("utf-8")

    return Torrent(**args)


def files(t: Torrent) -> typing.List:
    t = testt()
    if hasattr(t.info, "files"):
        files = [
            {
                "path": t.info.name / file.name,
                "size": file.length,
                "md5": file.md5sum,
                "chunks": [],
            }
            for file in t.info.files
        ]
    else:
        files = [
            {
                "path": t.info.name,
                "size": t.info.length,
                "md5": t.info.md5sum,
                "chunks": [],
            }
        ]
    # fit = iter(files)
    pieces = iter(t.info.pieces)
    chunk_size = t.info.piece_length
    pos = 0
    for file in files:
        startpos = pos
        start = pos // t.info.piece_length
        startdelta = pos - start * t.info.piece_length
        pos += file["size"]
        end = math.ceil(pos / t.info.piece_length)
        enddelta = pos // t.info.piece_length
        pieces = t.info.pieces[start:end]
        # if startdelta == 0:
        # list(range(startdelta, pos, t.info.piece_length))
        # [startdelta] + file["chunks"] + [enddelta]
        # file["chunks"] = [(i, c) for i, c in enumerate(t.info.pieces[start:end])]
        # file["chunks"] = [startdelta] + file["chunks"] + [enddelta]
        file["chunks"] = [
            startpos // t.info.piece_length * t.info.piece_length,
            enddelta,
        ]
        # file["chunks"] = list(range(startdelta, pos, t.info.piece_length))
        # while pos > 0:
        #     current(pieces)
        #     sha1 = next(pieces)
        #     file.chunks.append(chunk_size)
    # for p in t.info.pieces:
    """
- path: f1
    size: 8
    chunks:
        - sha1: c1
            from: 0
            to: 4
        - sha1: c2
            from: 4
            to: 8
- path: f2
    size: 6
    chunks:
        - sha1: c3
            from: 0
            to: 4
        - sha1: c4
            from: 4
            to: 8
- path: f3
    size: 4
    chunks:
        - sha1: c4
            from: -2
            to: 2
        - sha1: c5
            from: 2
            to: 6
    """
    return files


def testt():
    """
    0    4    8    12   16  18
    [    f1   |  f2  |  f3  ]
    [ c1 | c2 | c3 | c4 | c5]
    """
    return Torrent(
        info=MultiFile(
            piece_length=4,
            name=Path(),
            pieces=[b"c1", b"c2", b"c3", b"c4", b"c5"],
            private=None,
            files=[
                _SingleFile(name="f1", length=8, md5sum=None),
                _SingleFile(name="f2", length=6, md5sum=None),
                _SingleFile(name="f3", length=4, md5sum=None),
            ],
        ),
        announce=None,
        announce_lists=None,
        creation_date=None,
        comment=None,
        created_by=None,
        encoding=None,
    )
