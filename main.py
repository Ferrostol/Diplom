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


async def request(switch, switches, mib, lassErrorsPort):
    errors = {}
    procStat = []
    tempStat = []
    portStat = []
    lastValuePortError = {}
    try:
        snmp = aiosnmp.Snmp(
            host=switches["ip"],
            port=switches["port"],
            community=mib["community"],
            timeout=4,
        )
    except Exception as e:
        print("1")
        print(switches["ip"])
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
                                    "ip": switches["ip"],
                                    "description": f"Загрузка процессора более {LIMIT.MAX_CPU_LOAD}%. = {rezult}%",
                                }
                            )
                        else:
                            errors[switch] = [
                                {
                                    "typeEr": TYPE_ERROR.CPU_LOAD,
                                    "ip": switches["ip"],
                                    "description": f"Загрузка процессора более {LIMIT.MAX_CPU_LOAD}%. = {rezult}%",
                                }
                            ]
            except exceptions.SnmpTimeoutError:
                if switch in errors:
                    errors[switch].append(
                        {
                            "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                            "ip": switches["ip"],
                            "description": "null",
                        }
                    )
                else:
                    errors[switch] = [
                        {
                            "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                            "ip": switches["ip"],
                            "description": "null",
                        }
                    ]
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
                                    "ip": switches["ip"],
                                    "description": f"Температура датчика {i} более {LIMIT.MAX_TEMPERATURE}%. = {rezult} C",
                                }
                            )
                        else:
                            errors[switch] = [
                                {
                                    "typeEr": TYPE_ERROR.TEMPERATURE,
                                    "ip": switches["ip"],
                                    "description": f"Температура датчика {i} более {LIMIT.MAX_TEMPERATURE}%. = {rezult} C",
                                }
                            ]
                    i = i + 1
            except exceptions.SnmpTimeoutError:
                if switch in errors:
                    errors[switch].append(
                        {
                            "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                            "ip": switches["ip"],
                            "description": "null",
                        }
                    )
                else:
                    errors[switch] = [
                        {
                            "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                            "ip": switches["ip"],
                            "description": "null",
                        }
                    ]
                if not mib["proc"] in (None, ""):
                    procStat.append([switch, "null"])
                if not mib["temp"] in (None, ""):
                    tempStat.append([switch, 0, "null"])

        # Получаем какие порты являются портами для интернета
        massIndex = [
            int(res.oid[str(res.oid).rindex(".") + 1 :])
            for res in await snmp.bulk_walk("1.3.6.1.2.1.2.2.1.3")
            if res.value in (6, 62)
        ]

        massIn = {
            int(res.oid[str(res.oid).rindex(".") + 1 :]): res.value
            for res in await snmp.bulk_walk("1.3.6.1.2.1.2.2.1.14")
            if int(res.oid[str(res.oid).rindex(".") + 1 :]) in massIndex
        }
        massOut = {
            int(res.oid[str(res.oid).rindex(".") + 1 :]): res.value
            for res in await snmp.bulk_walk("1.3.6.1.2.1.2.2.1.20")
            if int(res.oid[str(res.oid).rindex(".") + 1 :]) in massIndex
        }

        for port in massIn:
            if port in lassErrorsPort:
                valueIn = lassErrorsPort[port][0] - massIn[port]
                valueOut = lassErrorsPort[port][0] - massOut[port]
            else:
                valueIn = massIn[port]
                valueOut = massOut[port]
            lastValuePortError[port] = [massIn[port], massOut[port]]
            if valueIn < 0:
                valueIn = 0

            if valueOut < 0:
                valueOut = 0

            portStat = [switch, int(str(port)[-3:]), valueIn, valueOut]

            if valueIn > 0:
                if switch in errors:
                    errors[switch].append(
                        {
                            "typeEr": TYPE_ERROR.PORT_LOAD,
                            "ip": switches["ip"],
                            "description": f"Ошибки на входе порта {int(str(port)[-3:])} появилось {valueIn} ошибок",
                        }
                    )
                else:
                    errors[switch] = [
                        {
                            "typeEr": TYPE_ERROR.PORT_LOAD,
                            "ip": switches["ip"],
                            "description": f"Ошибки на входе порта {int(str(port)[-3:])} появилось {valueIn} ошибок",
                        }
                    ]
            if valueOut > 0:
                if switch in errors:
                    errors[switch].append(
                        {
                            "typeEr": TYPE_ERROR.PORT_LOAD,
                            "ip": switches["ip"],
                            "description": f"Ошибки на выходе порта {int(str(port)[-3:])} появилось {valueOut} ошибок",
                        }
                    )
                else:
                    errors[switch] = [
                        {
                            "typeEr": TYPE_ERROR.PORT_LOAD,
                            "ip": switches["ip"],
                            "description": f"Ошибки на выходе порта {int(str(port)[-3:])} появилось {valueOut} ошибок",
                        }
                    ]

    return (errors, procStat, tempStat, portStat, {switch: lassErrorsPort})


def check(switch_list, mibsList, lassErrorsPort):
    ioloop = asyncio.get_event_loop()
    tasks = []
    for switch in switch_list:
        tasks.append(
            ioloop.create_task(
                request(
                    switch,
                    switch_list[switch],
                    mibsList[switch],
                    lassErrorsPort[switch],
                )
            )
        )
    wait_tasks = asyncio.wait(tasks)
    result = ioloop.run_until_complete(wait_tasks)
    errors = {}
    [errors.update(el.result()[0]) for el in result[0]]
    procStat = [ell for el in result[0] for ell in el.result()[1] if len(ell)]
    tempStat = [ell for el in result[0] for ell in el.result()[2] if len(ell)]
    portStat = [ell for el in result[0] for ell in el.result()[3] if len(ell)]

    lastValuePortError = {}
    for el in result[0]:
        for ell in el.result()[4]:
            lastValuePortError.update(ell)
    return (errors, procStat, tempStat, portStat, lastValuePortError)


def errorInsert(errorList):
    global huta
    massError = []
    for swt in errorList:
        for el in errorList[swt]:
            massError.append([swt, el["typeEr"], el["description"]])
    huta.addNewError(massError)


def ping(ip):
    rez = subprocess.run(
        ["ping", "-c", "1", "-t", "1", ip], stdout=subprocess.DEVNULL
    ).returncode
    if rez == 0:
        return True
    else:
        rez = subprocess.run(
            ["ping", "-c", "3", "-t", "1", ip], stdout=subprocess.DEVNULL
        ).returncode
        if rez == 0:
            return True
        else:
            return False


def pingList(switches, mibsList):
    procStat = []
    tempStat = []
    temp = {}
    errors = {}
    for switch in switches:
        rez = ping(switches[switch]["ip"])
        if rez:
            temp[switch] = switches[switch]
        else:
            errors[switch] = [
                {
                    "typeEr": TYPE_ERROR.HOST_UNKNOWN,
                    "ip": switches[switch]["ip"],
                    "description": "null",
                }
            ]
            if not mibsList[switch]["proc"] in (None, ""):
                procStat.append([switch, "null"])
            if not mibsList[switch]["temp"] in (None, ""):
                tempStat.append([switch, 0, "null"])
    return (temp, errors, procStat, tempStat)


def runningCheck(switches, mibsList, lassErrorsPort):
    onSwitches, errors, procStat, tempStat = pingList(switches, mibsList)
    if len(onSwitches.keys()):
        err, proc, temp, portStat, lastValuePortError = check(
            onSwitches, mibsList, lassErrorsPort
        )
        errors.update(err)
        procStat = procStat + proc
        tempStat = tempStat + temp
        huta.addPortStat(portStat)
    huta.addProcStat(procStat)
    huta.addTempStat(tempStat)
    print(procStat)
    print(tempStat)
    return errors


def fiveMinutesMain():
    global huta
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    lassErrorsPort = huta.getPortError()
    switches = {
        key: val
        for key, val in switches.items()
        if not key in oneError.keys() and not key in twoError.keys()
    }
    mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
    lassErrorsPort = {
        key: val for key, val in lassErrorsPort.items() if key in switches.keys()
    }
    if len(switches.keys()):
        print("Five minutes")
        error = runningCheck(switches, mibsList, lassErrorsPort)
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
        lassErrorsPort = huta.getPortError()
        switches = {
            key: val for key, val in switches.items() if key in errorTemp.keys()
        }
        lassErrorsPort = {
            key: val for key, val in lassErrorsPort.items() if key in switches.keys()
        }
        mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
        if len(switches.keys()):
            print("Two minutes")
            errors = runningCheck(switches, mibsList, lassErrorsPort)
            huta.deleteError(list(errorTemp.keys() - errors.keys()))
            print(errors)
            oneError.update(errors)


def oneMinutesMain():
    global huta, oneError
    errorTemp = oneError
    oneError = {}
    if len(errorTemp.keys()):
        switches = huta.getSwitches()
        mibsList = huta.getMibs()
        lassErrorsPort = huta.getPortError()
        switches = {
            key: val for key, val in switches.items() if key in errorTemp.keys()
        }
        mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
        lassErrorsPort = {
            key: val for key, val in lassErrorsPort.items() if key in switches.keys()
        }
        if len(switches.keys()):
            print("One minutes")
            errors = runningCheck(switches, mibsList, lassErrorsPort)
            huta.deleteError(list(errorTemp.keys() - errors.keys()))
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
