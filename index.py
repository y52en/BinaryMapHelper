from inspect import currentframe, getframeinfo
import json
from typing import Any, Callable, TypeVar, TypedDict


class BinaryMapItem(TypedDict):
    name: str
    address: int
    size: int
    type: str
    value: Any
    line: int


binaryMap: list[BinaryMapItem] = []


def get_linenumber() -> int:
    cf = currentframe()
    return cf.f_back.f_back.f_lineno


def get_function_name() -> str:
    cf = currentframe()
    return getframeinfo(cf.f_back.f_back.f_back).function


def get_code() -> list[str]:
    cf = currentframe()
    return getframeinfo(cf.f_back.f_back).code_context


T = TypeVar('T')


def log_map(func: Callable[[Any], T]) -> Callable[[Any, Any], T]:
    def __wrapper(self, *args) -> T:
        if not self._name == "TargetBinary":
            return func(self, *args)
        address = self.tell()
        result = func(self, *args)
        if not get_function_name() in [getframeinfo(currentframe()).function]:
            binaryMap.append({
                "name": get_code()[0].split("=")[0].strip(),
                "address": address,
                "address_end": self.tell(),
                "size": self.tell() - address,
                "type": type(result).__name__,
                "value": result,
                "line": get_linenumber()
            })
        return result

    return __wrapper


def dump_binary_map(path: str) -> str:
    binaryMap.sort(key=lambda x: x["size"])
    binaryMap.sort(key=lambda x: x["address"])

    # 同じsize & addressのものをまとめる
    i = len(binaryMap) - 2
    while True:
        if i < 0:
            break
        if binaryMap[i]["size"] == binaryMap[i + 1]["size"] and binaryMap[i]["address"] == binaryMap[i + 1]["address"]:
            binaryMap[i]["name"] += " , " + binaryMap[i + 1]["name"]
            binaryMap.pop(i + 1)
        i -= 1

    with open(path, "w") as f:
        json.dump(binaryMap, f, indent=4, default=lambda o: str(o))
    return path


def main():
    import struct
    from io import BytesIO

    class binary_reader:
        _name: str

        def __init__(self, buf, endian="<"):
            self.buf = buf

        def read(self, n):
            return self.buf.read(n)

        def tell(self):
            return self.buf.tell()

        @log_map
        def read_int(self) -> int:
            return struct.unpack("<i", self.read(4))[0]

        @log_map
        def read_string(self) -> str:
            out = ""
            while True:
                c = self.read(1)
                if c == b"\x00":
                    break
                out += c.decode("utf-8")
            return out

    b = b"\x00\x01\x02\x03Hello\x00\x09\x0a\x0b\x0c\x0d\x0e\x0f"
    reader = binary_reader(BytesIO(b))
    reader._name = "TargetBinary"
    integer = reader.read_int()
    string = reader.read_string()

    print(binaryMap)


if __name__ == "__main__":
    main()
