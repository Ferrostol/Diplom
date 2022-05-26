import time  # Библиотека для работы со временем
import subprocess  # Библиотека для работы с процессами ОС

import asyncio  # Библиотека для асинхронного программирования
from psycopg2 import OperationalError
import aiosnmp  # Библиотека для работы с SNMP
import schedule  # Библиотека для запуска функции с периодичностью

from database import database
from config import TYPE_ERROR, LIMIT


try:
    huta = database()
except OperationalError as e:
    print(e)
    exit()


switches = []  # Инициализация массива в котором будет храниться информация о свичах
mibsList = (
    []
)  # Инициализация массива в котором будет храниться информация о oid для свичей
procStat = (
    []
)  # Инициализация массива в котором будет собрана статистика по работе процессора свичей
tempStat = (
    []
)  # Инициализация массива в котором будет собрана статистика по температуре датчиков свичей

error = {}  # Найденные ошибки в проверке свичей за 5 минут
twoError = {}  # Найденные ошибки в проверке свичей за 2 минут
oneError = {}  # Найденные ошибки в проверке свичей за 1 минут


async def request(switch, mib):
    global snmpEngine, switches, procStat, tempStat
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
                        if switch in error:
                            error[switch].append(
                                {
                                    "typeEr": TYPE_ERROR.CPU_LOAD,
                                    "ip": switches[switch]["ip"],
                                    "description": f"Загрузка процессора более {LIMIT.MAX_CPU_LOAD}%. = {rezult}%",
                                }
                            )
                        else:
                            error[switch] = [
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
                        if switch in error:
                            error[switch].append(
                                {
                                    "typeEr": TYPE_ERROR.TEMPERATURE,
                                    "ip": switches[switch]["ip"],
                                    "description": f"Температура датчика {i} более {LIMIT.MAX_TEMPERATURE}%. = {rezult} C",
                                }
                            )
                        else:
                            error[switch] = [
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


def check(switch_list):
    global mibsList, procStat, tempStat
    ioloop = asyncio.get_event_loop()
    tasks = []
    for switch in switch_list:
        tasks.append(ioloop.create_task(request(switch, mibsList[switch])))
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
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


def pingAll():
    global switches, error, procStat, tempStat, mibsList
    temp = []
    error = {}
    for switch in switches:
        rez = subprocess.call(
            f"ping -c 1 -t 1 {switches[switch]['ip']} > /dev/null", shell=True
        )
        if rez == 0:
            temp.append(switch)
        else:
            rez = subprocess.call(
                f"ping -c 3 -t 1 {switches[switch]['ip']} > /dev/null", shell=True
            )
            if rez <= 2:
                temp.append(switch)
            else:
                error[switch] = {
                    "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                    "ip": switches[switch]["ip"],
                    "description": None,
                }
                if not mibsList[switch]["proc"] in (None, ""):
                    procStat.append([switch, "null"])
                if not mibsList[switch]["temp"] in (None, ""):
                    tempStat.append([switch, 0, "null"])
    errorInsert(error)
    return temp


def fiveMinutesMain():
    global huta, switches, mibsList
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches = pingAll()
    check(onSwitches)
    print(error)  # Отображаем на экране имеющиеся ошибки


def twoMinutesMain():
    global huta, switches, mibsList
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches = pingAll()
    check(onSwitches)
    print(error)  # Отображаем на экране имеющиеся ошибки


def oneMinutesMain():
    global huta, switches, mibsList
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches = pingAll()
    check(onSwitches)
    print(error)  # Отображаем на экране имеющиеся ошибки


def startProgramm():
    global huta, oneError
    oneError = huta.getDeviceError()
    pass
    # Получить список ошибок с БД
    # Сформировать объект для проверки этих ошибок раз в минуту


if __name__ == "__main__":
    schedule.every(5).minutes.do(fiveMinutesMain)
    # schedule.every(2).minutes.do(twoMinutesMain)
    # schedule.every(1).minutes.do(oneMinutesMain)
    startProgramm()
    fiveMinutesMain()
    while True:
        schedule.run_pending()
        time.sleep(1)
