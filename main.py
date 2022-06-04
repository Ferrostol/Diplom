import time  # Библиотека для работы со временем
import subprocess  # Библиотека для работы с процессами ОС

import asyncio  # Библиотека для асинхронного программирования
from psycopg2 import OperationalError  # Импорт ошибки при работе с БД
import aiosnmp  # Библиотека для работы с SNMP
import schedule  # Библиотека для запуска функции с периодичностью

from database import database
from config import TYPE_ERROR, LIMIT


try:
    huta = database()
except OperationalError as e:
    print(e)
    exit()


switches = []  # Информация о свитчах
mibsList = []  # MIB свитчей
procStat = []  # Статистика процессора
tempStat = []  # Статистика температуры

error = {}  # Найденные ошибки в проверке свитчей за 5 минут
twoError = {}  # Найденные ошибки в проверке свитчей за 2 минут
oneError = {}  # Найденные ошибки в проверке свитчей за 1 минут


async def request(switch, mib):
    global switches, procStat, tempStat
    errors = {}
    try:
        snmp = aiosnmp.Snmp(
            host=switches[switch]["ip"],
            port=switches[switch]["port"],
            community=mib["community"],
            timeout=4,
        )
    except Exception as e:
        print("1")
        print(switches[switch]["ip"])
        raise e
    else:
        if not mib["proc"] in (None, ""):
            try:
                for res in await snmp.bulk_walk(mib["proc"]):
                    rezult = (
                        (100 - int(res.value)) if mib["idleProc"] else int(res.value)
                    )
                    procStat.append([switch, rezult])
                    if LIMIT.MAX_CPU_LOAD <= rezult:
                        if switch in errors:
                            errors[switch].append(
                                {
                                    "typeEr": TYPE_ERROR.CPU_LOAD,
                                    "ip": switches[switch]["ip"],
                                    "description": f"Загрузка процессора более {LIMIT.MAX_CPU_LOAD}%. = {rezult}%",
                                }
                            )
                        else:
                            errors[switch] = [
                                {
                                    "typeEr": TYPE_ERROR.CPU_LOAD,
                                    "ip": switches[switch]["ip"],
                                    "description": f"Загрузка процессора более {LIMIT.MAX_CPU_LOAD}%. = {rezult}%",
                                }
                            ]
            except Exception as e:
                print("2")
                print(switches[switch]["ip"])
                print(mib["proc"])
                raise e

        if not mib["temp"] in (None, ""):
            try:
                i = 0
                for res in await snmp.bulk_walk(mib["temp"]):
                    rezult = int(res.value)
                    tempStat.append([switch, i, rezult])
                    if LIMIT.MAX_TEMPERATURE <= rezult:
                        if switch in errors:
                            errors[switch].append(
                                {
                                    "typeEr": TYPE_ERROR.TEMPERATURE,
                                    "ip": switches[switch]["ip"],
                                    "description": f"Температура датчика {i} более {LIMIT.MAX_TEMPERATURE}%. = {rezult} C",
                                }
                            )
                        else:
                            errors[switch] = [
                                {
                                    "typeEr": TYPE_ERROR.TEMPERATURE,
                                    "ip": switches[switch]["ip"],
                                    "description": f"Температура датчика {i} более {LIMIT.MAX_TEMPERATURE}%. = {rezult} C",
                                }
                            ]
                    i = i + 1
            except Exception as e:
                print("2")
                print(switches[switch]["ip"])
                print(mib["temp"])
                raise e
    return errors


def check(switch_list):
    global mibsList, procStat, tempStat
    ioloop = asyncio.get_event_loop()
    tasks = []
    for switch in switch_list:
        tasks.append(ioloop.create_task(request(switch, mibsList[switch])))
    wait_tasks = asyncio.wait(tasks)
    result = ioloop.run_until_complete(wait_tasks)
    print(result)
    print(procStat)
    print(tempStat)
    huta.addProcStat(procStat)
    huta.addTempStat(tempStat)
    procStat = []
    tempStat = []


def errorInsert(errorList):
    massError = []
    for swt in errorList:
        pass


def ping(ip):
    rez = subprocess.call(f"ping -c 1 -t 1 {ip} > /dev/null", shell=True)
    if rez == 0:
        return True
    else:
        rez = subprocess.call(f"ping -c 3 -t 1 {ip} > /dev/null", shell=True)
        if rez <= 2:
            return True
        else:
            return False


def pingAll(switches):
    global procStat, tempStat, mibsList
    temp = []
    errors = {}
    for switch in switches:
        rez = ping(switches[switch]["ip"])
        if rez:
            temp.append(switch)
        else:
            errors[switch] = {
                "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                "ip": switches[switch]["ip"],
                "description": None,
            }
            if not mibsList[switch]["proc"] in (None, ""):
                procStat.append([switch, "null"])
            if not mibsList[switch]["temp"] in (None, ""):
                tempStat.append([switch, 0, "null"])
    return (temp, errors)


def fiveMinutesMain():
    global huta, switches, mibsList, error
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches, error = pingAll(switches)
    check(onSwitches)
    errorInsert(error)
    print(error)


def twoMinutesMain():
    global huta, switches, mibsList, twoError
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches, errors = pingAll(switches)
    check(onSwitches)
    print(error)


def oneMinutesMain():
    global huta, switches, mibsList, oneError
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches, errors = pingAll(switches)
    check(onSwitches)
    print(error)


def startProgramm():
    global huta, oneError
    oneError = huta.getDeviceError()


if __name__ == "__main__":
    schedule.every(5).minutes.do(fiveMinutesMain)
    # schedule.every(2).minutes.do(twoMinutesMain)
    # schedule.every(1).minutes.do(oneMinutesMain)
    startProgramm()
    fiveMinutesMain()
    while True:
        schedule.run_pending()
        time.sleep(1)
