import hashlib
import base64
import urllib.parse


class PipelineFuncStaticFuncsMixin:

    @staticmethod
    def _default_function(*args, **kwargs):
        return 'null'

    @staticmethod
    def md5(text: str) -> str:
        text = str(text)
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def sha(text: str, algorithm: str) -> str:
        text = str(text)
        algorithm = str(algorithm)
        algorithm = algorithm.lower()
        if algorithm == "sha1":
            return hashlib.sha1(text.encode('utf-8')).hexdigest()
        elif algorithm == "sha224":
            return hashlib.sha224(text.encode('utf-8')).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(text.encode('utf-8')).hexdigest()
        elif algorithm == "sha384":
            return hashlib.sha384(text.encode('utf-8')).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(text.encode('utf-8')).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @staticmethod
    def base64(text: str) -> str:
        text = str(text)
        return base64.b64encode(text.encode('utf-8')).decode('ascii')

    @staticmethod
    def unbase64(text: str) -> str:
        text = str(text)
        return base64.b64decode(text).decode('utf-8')

    @staticmethod
    def encodeUriComponent(text: str) -> str:
        text = str(text)
        return urllib.parse.quote(text, safe='')

    @staticmethod
    def decodeUriComponent(text: str) -> str:
        text = str(text)
        return urllib.parse.unquote(text)

    @staticmethod
    def lower(text: str) -> str:
        text = str(text)
        return text.lower()

    @staticmethod
    def upper(text: str) -> str:
        text = str(text)
        return text.upper()

    @staticmethod
    def number(text: str):
        text = str(text)
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return ""

    @staticmethod
    def substr(text: str, start: int, end: int) -> str:
        text = str(text)
        return text[int(start):int(end)]

    @staticmethod
    def concat(text: str, value: str) -> str:
        text = str(text)
        return text + str(value)

    @staticmethod
    def lconcat(text: str, value: str) -> str:
        text = str(text)
        return str(value) + text

    @staticmethod
    def padEnd(text: str, length: int, pad_char: str) -> str:
        text = str(text)
        return text.ljust(int(length), str(pad_char)[:1] or ' ')

    @staticmethod
    def padStart(text: str, length: int, pad_char: str) -> str:
        text = str(text)
        return text.rjust(int(length), str(pad_char)[:1] or ' ')

    @staticmethod
    def length(text) -> int:
        text = str(text)
        if isinstance(text, (int, float)):
            return len(str(text))
        elif isinstance(text, str):
            return len(text)
        return 0
