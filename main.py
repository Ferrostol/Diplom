#!/usr/local/bin/python3
import time  # Библиотека для работы со временем
import subprocess  # Библиотека для работы с процессами ОС

import asyncio  # Библиотека для асинхронного программирования
from psycopg2 import OperationalError  # Импорт ошибки при работе с БД
import aiosnmp  # Библиотека для работы с SNMP
from aiosnmp import exceptions
import schedule  # Библиотека для запуска функции с периодичностью

from database import database
from emailClient import mailClient
from config import TYPE_ERROR, LIMIT


try:
    huta = database()
except OperationalError as e:
    print(e)
    print("Ошибка подключения к базе данных")
    exit()

try:
    mails = mailClient()
except Exception as e:
    print(e)
    print("Ошибка SMTP")
    exit()

twoError = {}  # Ошибки которые надо проверить за 2 минут
oneError = {}  # Ошибки которые надо проверить за 1 минут

noSendingErrorToMail = {}  # Ошибки о которых не сообщили администратору
noSendingErrorToDatabase = {}  # Ошибки о которых не отправлены в базу данных


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
        print(e)
        print("SNMP error", switches["ip"])
        errors[switch] = [
            {
                "typeEr": TYPE_ERROR.SNMP_ERROR,
                "ip": switches[switch]["ip"],
                "description": "null",
            }
        ]
        if not mib["proc"] in (None, ""):
            procStat.append([switch, "null"])
        if not mib["temp"] in (None, ""):
            tempStat.append([switch, 0, "null"])

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
            except Exception as e:
                print(e)
                print("CPU Error", switches["ip"])

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
                if not mib["temp"] in (None, ""):
                    tempStat.append([switch, 0, "null"])
            except Exception as e:
                print(e)
                print("Temperature Error", switches["ip"])

        try:
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
                    valueOut = lassErrorsPort[port][1] - massOut[port]
                else:
                    valueIn = 0
                    valueOut = 0

                lastValuePortError[port] = [massIn[port], massOut[port]]

                if valueIn < 0:
                    valueIn = 0

                if valueOut < 0:
                    valueOut = 0

                portStat.append([switch, int(str(port)[-4:]), valueIn, valueOut])

                if valueIn > 0:
                    if switch in errors:
                        errors[switch].append(
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": f"Ошибки на входе порта {int(str(port)[-4:])} появилось {valueIn} ошибок",
                            }
                        )
                    else:
                        errors[switch] = [
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": f"Ошибки на входе порта {int(str(port)[-4:])} появилось {valueIn} ошибок",
                            }
                        ]
                if valueOut > 0:
                    if switch in errors:
                        errors[switch].append(
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": f"Ошибки на выходе порта {int(str(port)[-4:])} появилось {valueOut} ошибок",
                            }
                        )
                    else:
                        errors[switch] = [
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": f"Ошибки на выходе порта {int(str(port)[-4:])} появилось {valueOut} ошибок",
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

        except Exception as e:
            print(e)
            print("Port Error", switches["ip"])

    return (errors, procStat, tempStat, portStat, {switch: lastValuePortError})


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
                    lassErrorsPort[switch] if switch in lassErrorsPort else {},
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
        lastValuePortError.update(el.result()[4])
    return (errors, procStat, tempStat, portStat, lastValuePortError)


def errorInsert(errorList):
    global huta, mails, twoError, oneError, noSendingErrorToMail, noSendingErrorToDatabase
    massError = []
    errorListMail = errorList
    if len(noSendingErrorToDatabase.keys()):
        swtList = list(twoError.keys()) + list(oneError.keys())
        noSendingErrorToMail = {
            key: val for key, val in noSendingErrorToDatabase.items() if key in swtList
        }
        errorList.update(noSendingErrorToDatabase)
    for swt in errorList:
        for el in errorList[swt]:
            massError.append([swt, el["typeEr"], el["description"]])

    try:
        huta.addNewError(massError)
    except Exception as e:
        print(e)
        noSendingErrorToDatabase = errorList
    else:
        noSendingErrorToDatabase = {}

    if len(noSendingErrorToMail.keys()):
        swtList = list(twoError.keys()) + list(oneError.keys())
        noSendingErrorToMail = {
            key: val for key, val in noSendingErrorToMail.items() if key in swtList
        }
        errorListMail.update(noSendingErrorToMail)

    try:
        mails.sendEmailError(typeErrorList, errorListMail)
    except Exception as e:
        print(e)
        noSendingErrorToMail = errorListMail
    else:
        noSendingErrorToMail = {}


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
        try:
            huta.addPortStat(portStat)
            huta.updateLastPortError(lastValuePortError)
        except Exception as e:
            print(e)
            print("Ошибка выгрузки статистики по портам")
    try:
        huta.addProcStat(procStat)
        huta.addTempStat(tempStat)
    except Exception as e:
        print(e)
        print("Ошибка выгрузки статистики по процессору и температуре")
    print(procStat)
    print(tempStat)
    return errors


def fiveMinutesMain():
    global huta
    try:
        switches = huta.getSwitches()
        mibsList = huta.getMibs()
        lassErrorsPort = huta.getPortError()
    except Exception as e:
        print(e)
        print("Ошибка получения данных из базы данных")
        return
    switches = {
        key: val
        for key, val in switches.items()
        if not key in list(twoError.keys()) + list(oneError.keys())
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
    global huta, twoError, noSendingErrorToMail, noSendingErrorToDatabase
    errorTemp = twoError
    twoError = {}
    if len(errorTemp.keys()):
        try:
            switches = huta.getSwitches()
            mibsList = huta.getMibs()
            lassErrorsPort = huta.getPortError()
        except Exception as e:
            print(e)
            print("Ошибка получения данных из базы данных")
            return
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
            if len(
                list(noSendingErrorToDatabase.keys())
                + list(noSendingErrorToMail.keys())
            ):
                errorInsert({})


def oneMinutesMain():
    global huta, oneError
    errorTemp = oneError
    oneError = {}
    if len(errorTemp.keys()):
        try:
            switches = huta.getSwitches()
            mibsList = huta.getMibs()
            lassErrorsPort = huta.getPortError()
        except Exception as e:
            print(e)
            print("Ошибка получения данных из базы данных")
            return
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
            if len(
                list(noSendingErrorToDatabase.keys())
                + list(noSendingErrorToMail.keys())
            ):
                errorInsert({})


def startProgramm():
    global huta, oneError, typeErrorList
    oneError = huta.getDeviceError()
    typeErrorList = huta.getTypeError()


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
