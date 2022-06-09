import time  # Библиотека для работы со временем
import subprocess  # Библиотека для работы с процессами ОС

import asyncio  # Библиотека для асинхронного программирования
from psycopg2 import OperationalError  # Импорт ошибки при работе с БД
import aiosnmp  # Библиотека для работы с SNMP
from aiosnmp import exceptions
import schedule  # Библиотека для запуска функции с периодичностью

from database import database
from config import TYPE_ERROR, LIMIT


try:
    huta = database()
except OperationalError as e:
    print(e)
    exit()


twoError = {}  # Ошибки которые надо проверить за 2 минут
oneError = {}  # Ошибки которые надо проверить за 1 минут


async def request(switch, switches, mib):
    errors = {}
    procStat = []
    tempStat = []
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
            except exceptions.SnmpTimeoutError:
                errors[switch] = {
                    "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                    "ip": switches[switch]["ip"],
                    "description": None,
                }
                if not mib["proc"] in (None, ""):
                    procStat.append([switch, "null"])
                if not mib["temp"] in (None, ""):
                    tempStat.append([switch, 0, "null"])

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
            except exceptions.SnmpTimeoutError:
                errors[switch] = {
                    "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                    "ip": switches[switch]["ip"],
                    "description": None,
                }
                if not mib["proc"] in (None, ""):
                    procStat.append([switch, "null"])
                if not mib["temp"] in (None, ""):
                    tempStat.append([switch, 0, "null"])
    return (errors, procStat, tempStat)


def check(switch_list, mibsList):
    ioloop = asyncio.get_event_loop()
    tasks = []
    for switch in switch_list:
        tasks.append(
            ioloop.create_task(request(switch, switch_list[switch], mibsList[switch]))
        )
    wait_tasks = asyncio.wait(tasks)
    result = ioloop.run_until_complete(wait_tasks)
    errors = {}
    [errors.update(el.result()[0]) for el in result[0]]
    procStat = []
    tempStat = []
    return (errors, procStat, tempStat)


def errorInsert(errorList):
    massError = []
    for swt in errorList:
        pass


def ping(ip):
    rez = subprocess.run(f"ping -c 1 -t 1 {ip}", stdout=subprocess.DEVNULL).returncode
    if rez == 0:
        return True
    else:
        rez = subprocess.run(
            f"ping -c 3 -t 1 {ip}", stdout=subprocess.DEVNULL
        ).returncode
        if rez == 0:
            return True
        else:
            return False


def pingList(switches, mibsList):
    procStat = []
    tempStat = []
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
    return (temp, errors, procStat, tempStat)


def runningCheck(switches, mibsList):
    onSwitches, errors, procStat, tempStat = pingList(switches, mibsList)
    err, proc, temp = check(onSwitches, mibsList)
    errors.update(err)
    procStat = procStat + proc
    tempStat = tempStat + temp
    huta.addProcStat(procStat)
    huta.addTempStat(tempStat)
    print(procStat)
    print(tempStat)
    return errors


def fiveMinutesMain():
    global huta
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    switches = {
        key: val
        for key, val in switches.items()
        if not key in oneError.keys() and not key in twoError.keys()
    }
    mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
    if len(switches.keys()):
        print("Five minutes")
        error = runningCheck(switches, mibsList)
        errorInsert(error)
        print(error)
        twoError.update(error)


def twoMinutesMain():
    global huta, twoError
    errorTemp = twoError
    twoError = {}
    if len(errorTemp.keys()):
        switches = huta.getSwitches()
        mibsList = huta.getMibs()
        switches = {
            key: val for key, val in switches.items() if key in errorTemp.keys()
        }
        mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
        if len(switches.keys()) != len(errorTemp):
            pass  # Удалить лишнее
        if len(switches.keys()):
            print("Two minutes")
            errors = runningCheck(switches, mibsList)
            print(errors)
            oneError.update(errors)


def oneMinutesMain():
    global huta, oneError
    errorTemp = oneError
    oneError = {}
    if len(errorTemp.keys()):
        switches = huta.getSwitches()
        mibsList = huta.getMibs()
        switches = {
            key: val for key, val in switches.items() if key in errorTemp.keys()
        }
        mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
        if len(switches.keys()) != len(errorTemp):
            pass  # Удалить лишнее
        if len(switches.keys()):
            print("One minutes")
            errors = runningCheck(switches, mibsList)
            print(errors)
            oneError.update(errors)


def startProgramm():
    global huta, oneError
    oneError = huta.getDeviceError()


if __name__ == "__main__":
    schedule.every(5).minutes.do(fiveMinutesMain)
    schedule.every(2).minutes.do(twoMinutesMain)
    schedule.every(1).minutes.do(oneMinutesMain)
    startProgramm()
    fiveMinutesMain()
    twoMinutesMain()
    oneMinutesMain()
    while True:
        schedule.run_pending()
        time.sleep(1)
