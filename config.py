from enum import Enum


class LIMIT:
    MAX_CPU_LOAD = 50
    MAX_TEMPERATURE = 50


class TYPE_ERROR(Enum):
    HOST_UNKNOWN = 1
    CPU_LOAD = 2
    MEMORY_LOAD = 3
    PORT_LOAD = 4
    TEMPERATURE = 5
    SNMP_ERROR = 6


mailConf = {
    "user": "ferrostol@sibstrin.ru",
    "server": "127.0.0.1",
    "port": 25,
    "to": ["skudin2000@yandex.ru", "skudin2000@mail.ru"],
}
