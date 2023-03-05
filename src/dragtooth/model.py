import dataclasses


@dataclasses.dataclass
class Credentials:
    login: str
    password: str


@dataclasses.dataclass
class SessionPair:
    encoder: str
    decoder: str
    port: int