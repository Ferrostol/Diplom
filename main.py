#!/usr/local/bin/python3
from distutils.dep_util import newer
import logging
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

logger = logging.getLogger("mainFile")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("huta.log")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info("Program started")

try:
    logger.info("Started connect to database")
    huta = database()
except OperationalError as e:
    logger.error("Database initialization error")
    logger.error(e)
    logger.warning("Program ended")
    exit()
else:
    logger.info("Successful connection to database")

twoError = {}  # Ошибки которые надо проверить за 2 минут
oneError = {}  # Ошибки которые надо проверить за 1 минут

noSendingErrorToMail = {}  # Ошибки о которых не сообщили администратору
noSendingErrorToDatabase = {}  # Ошибки о которых не отправлены в базу данных


async def request(switch, switches, mib, lassErrorsPort):
    global logger
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
        logger.error(f"SNMP connect error {switches['ip']}")
        logger.error(e)
        errors[switch] = [
            {
                "typeEr": TYPE_ERROR.SNMP_ERROR,
                "ip": switches[switch]["ip"],
                "description": "null",
                "name_switches": switches["switches_name"],
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
                                    "description": rezult,
                                    "name_switches": switches["switches_name"],
                                }
                            )
                        else:
                            errors[switch] = [
                                {
                                    "typeEr": TYPE_ERROR.CPU_LOAD,
                                    "ip": switches["ip"],
                                    "description": rezult,
                                    "name_switches": switches["switches_name"],
                                }
                            ]
            except exceptions.SnmpTimeoutError:
                if switch in errors:
                    errors[switch].append(
                        {
                            "typeEr": TYPE_ERROR.SNMP_ERROR,
                            "ip": switches["ip"],
                            "description": "При проверке процессора",
                            "name_switches": switches["switches_name"],
                        }
                    )
                else:
                    errors[switch] = [
                        {
                            "typeEr": TYPE_ERROR.SNMP_ERROR,
                            "ip": switches["ip"],
                            "description": "При проверке процессора",
                            "name_switches": switches["switches_name"],
                        }
                    ]
                if not mib["proc"] in (None, ""):
                    procStat.append([switch, "null"])
            except Exception as e:
                logger.error(f"Processor data acquisition error. {switches['ip']}")
                logger.error(e)

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
                                    "description": [i, rezult],
                                    "name_switches": switches["switches_name"],
                                }
                            )
                        else:
                            errors[switch] = [
                                {
                                    "typeEr": TYPE_ERROR.TEMPERATURE,
                                    "ip": switches["ip"],
                                    "description": [i, rezult],
                                    "name_switches": switches["switches_name"],
                                }
                            ]
                    i = i + 1
            except exceptions.SnmpTimeoutError:
                if switch in errors:
                    errors[switch].append(
                        {
                            "typeEr": TYPE_ERROR.SNMP_ERROR,
                            "ip": switches["ip"],
                            "description": "При проверке температуры",
                            "name_switches": switches["switches_name"],
                        }
                    )
                else:
                    errors[switch] = [
                        {
                            "typeEr": TYPE_ERROR.SNMP_ERROR,
                            "ip": switches["ip"],
                            "description": "При проверке температуры",
                            "name_switches": switches["switches_name"],
                        }
                    ]
                if not mib["temp"] in (None, ""):
                    tempStat.append([switch, 0, "null"])
            except Exception as e:
                logger.error(f"Temperature data acquisition error. {switches['ip']}")
                logger.error(e)

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
                                "description": [
                                    "входе",
                                    {int(str(port)[-4:])},
                                    valueIn,
                                ],
                                "name_switches": switches["switches_name"],
                            }
                        )
                    else:
                        errors[switch] = [
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": [
                                    "входе",
                                    {int(str(port)[-4:])},
                                    valueIn,
                                ],
                                "name_switches": switches["switches_name"],
                            }
                        ]
                if valueOut > 0:
                    if switch in errors:
                        errors[switch].append(
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": [
                                    "выходе",
                                    {int(str(port)[-4:])},
                                    valueOut,
                                ],
                                "name_switches": switches["switches_name"],
                            }
                        )
                    else:
                        errors[switch] = [
                            {
                                "typeEr": TYPE_ERROR.PORT_LOAD,
                                "ip": switches["ip"],
                                "description": [
                                    "выходе",
                                    {int(str(port)[-4:])},
                                    valueOut,
                                ],
                                "name_switches": switches["switches_name"],
                            }
                        ]
        except exceptions.SnmpTimeoutError:
            if switch in errors:
                errors[switch].append(
                    {
                        "typeEr": TYPE_ERROR.SNMP_ERROR,
                        "ip": switches["ip"],
                        "description": "При проверке портов",
                        "name_switches": switches["switches_name"],
                    }
                )
            else:
                errors[switch] = [
                    {
                        "typeEr": TYPE_ERROR.SNMP_ERROR,
                        "ip": switches["ip"],
                        "description": "При проверке портов",
                        "name_switches": switches["switches_name"],
                    }
                ]

        except Exception as e:
            logger.error(f"Ports data acquisition error. {switches['ip']}")
            logger.error(e)

    return (errors, procStat, tempStat, portStat, {switch: lastValuePortError})


def check(switch_list, mibsList, lassErrorsPort):
    global logger
    logger.info("Start sending asynchronous requests")
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
    logger.info("End sending asynchronous requests")
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
    global huta, twoError, oneError, noSendingErrorToMail, noSendingErrorToDatabase, logger
    logger.info("Start sending error information")
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
    if len(massError):
        logger.info("Start sending error information to the database")
        try:
            huta.addNewError(massError)
        except OperationalError as e:
            logger.error("Error sending error information to the database")
            logger.error(e)
            huta = database()
            noSendingErrorToDatabase = errorList
        except Exception as e:
            logger.error("Error sending error information to the database")
            logger.error(e)
            noSendingErrorToDatabase = errorList
        else:
            noSendingErrorToDatabase = {}
            logger.info("End sending error information to the database")

    if len(noSendingErrorToMail.keys()):
        swtList = list(twoError.keys()) + list(oneError.keys())
        noSendingErrorToMail = {
            key: val for key, val in noSendingErrorToMail.items() if key in swtList
        }
        errorListMail.update(noSendingErrorToMail)

    if len(errorListMail.keys()):
        logger.info("Start sending error information to email")
        try:
            mailClient().sendEmailError(typeErrorList, errorListMail)
        except Exception as e:
            logger.error("Error sending error information to email")
            logger.error(e)
            noSendingErrorToMail = errorListMail
        else:
            noSendingErrorToMail = {}
            logger.info("End sending error information to email")

    logger.info("End sending error information")


def ping(ip):
    rez = subprocess.run(
        ["ping", "-c", "1", "-t", "1", ip], stdout=subprocess.DEVNULL
    ).returncode
    if rez == 0:
        return True
    else:
        time.sleep(0.2)
        rez = subprocess.run(
            ["ping", "-c", "3", "-t", "1", ip], stdout=subprocess.DEVNULL
        ).returncode
        if rez == 0:
            return True
        else:
            return False


def pingList(switches, mibsList):
    global logger
    procStat = []
    tempStat = []
    temp = {}
    errors = {}
    logger.info("Start checking the connection with switches")
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
                    "name_switches": switches[switch]["switches_name"],
                }
            ]
            if not mibsList[switch]["proc"] in (None, ""):
                procStat.append([switch, "null"])
            if not mibsList[switch]["temp"] in (None, ""):
                tempStat.append([switch, 0, "null"])
    logger.info("End checking the connection with switches")
    return (temp, errors, procStat, tempStat)


def errorCorrectionCheck(oldError: dict, newError: dict):
    deleteMass = {}
    for swtOld in oldError:
        if not swtOld in newError:
            ls = list(set([el["typeEr"] for el in oldError[swtOld] if "typeEr" in el]))
        else:
            ls = list(
                set([el["typeEr"] for el in oldError[swtOld] if "typeEr" in el])
                - set([el["typeEr"] for el in newError[swtOld] if "typeEr" in el])
            )
        if len(ls):
            deleteMass[swtOld] = []
            for typeEr in ls:
                deleteMass[swtOld].append(typeEr)
    return deleteMass


def runningCheck(switches, mibsList, lassErrorsPort, errorTemp):
    global logger, huta
    onSwitches, errors, procStat, tempStat = pingList(switches, mibsList)
    if len(onSwitches.keys()):
        err, proc, temp, portStat, lastValuePortError = check(
            onSwitches, mibsList, lassErrorsPort
        )
        errors.update(err)
        procStat = procStat + proc
        tempStat = tempStat + temp
        logger.info("Start sending statistics to the database by ports")
        try:
            huta.addPortStat(portStat)
            huta.updateLastPortError(lastValuePortError)
        except OperationalError as e:
            logger.error("Error sending statistics by ports to the database")
            logger.error(e)
            huta = database()
            huta.addPortStat(portStat)
            huta.updateLastPortError(lastValuePortError)
        except Exception as e:
            logger.error("Error sending statistics by ports to the database")
            logger.error(e)
        else:
            logger.info("End sending statistics to the database by ports")

    logger.info("Start sending statistics to the database by processor")
    try:
        huta.addProcStat(procStat)
    except OperationalError as e:
        logger.error("Error sending statistics by processor to the database")
        logger.error(e)
        huta = database()
        huta.addProcStat(procStat)
    except Exception as e:
        logger.error("Error sending statistics by processor to the database")
        logger.error(e)
    else:
        logger.info("End sending statistics to the database by processor")

    logger.info("Start sending statistics to the database by temperature")
    try:
        huta.addTempStat(tempStat)
    except OperationalError as e:
        logger.error("Error sending statistics by temperature to the database")
        logger.error(e)
        huta = database()
        huta.addTempStat(tempStat)
    except Exception as e:
        logger.error("Error sending statistics by temperature to the database")
        logger.error(e)
    else:
        logger.info("End sending statistics to the database by temperature")

    deleteMass = errorCorrectionCheck(errorTemp, errors)
    if len(deleteMass):
        logger.info("Start deleting errors from the database")
        try:
            huta.deleteError(deleteMass)
        except OperationalError as e:
            logger.error("Error deleting errors from the database")
            logger.error(e)
            huta = database()
            huta.deleteError(deleteMass)
        except Exception as e:
            logger.error("Error deleting errors from the database")
            logger.error(e)
        else:
            logger.info("End deleting errors from the database")

        logger.info("Start sending a message about restoring health")
        try:
            mailClient().sendEmailCorrecionError(deleteMass, switches)
        except Exception as e:
            logger.error("Error sending a message about restoring health")
            logger.error(e)
        else:
            logger.info("End sending a message about restoring health")

    return errors


def fiveMinutesMain():
    global huta, logger
    logger.info("Start of the check every 5 minutes")
    try:
        logger.info("Start of getting data from the database")
        switches = huta.getSwitches()
        mibsList = huta.getMibs()
        lassErrorsPort = huta.getPortError()
    except Exception as e:
        logger.error("Error getting data from the database")
        logger.error(e)
        return
    else:
        logger.info("Successful of getting data from the database")

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
        logger.info("Start check")
        error = runningCheck(switches, mibsList, lassErrorsPort, {})
        errorInsert(error)
        twoError.update(error)
    logger.info("End of the check every 5 minutes")


def twoMinutesMain():
    global huta, twoError, noSendingErrorToMail, noSendingErrorToDatabase, logger
    errorTemp = twoError
    twoError = {}
    logger.info("Start of the check every 2 minutes")
    if len(errorTemp.keys()):
        try:
            logger.info("Start of getting data from the database")
            switches = huta.getSwitches()
            mibsList = huta.getMibs()
            lassErrorsPort = huta.getPortError()
        except Exception as e:
            logger.error("Error getting data from the database")
            logger.error(e)
            return
        else:
            logger.info("Successful of getting data from the database")

        switches = {
            key: val for key, val in switches.items() if key in errorTemp.keys()
        }
        lassErrorsPort = {
            key: val for key, val in lassErrorsPort.items() if key in switches.keys()
        }
        mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
        if len(switches.keys()):
            logger.info("Start check")
            errors = runningCheck(switches, mibsList, lassErrorsPort, errorTemp)
            oneError.update(errors)
            if len(
                list(noSendingErrorToDatabase.keys())
                + list(noSendingErrorToMail.keys())
            ):
                errorInsert({})

    logger.info("End of the check every 2 minutes")


def oneMinutesMain():
    global huta, oneError
    errorTemp = oneError
    oneError = {}
    logger.info("Start of the check every 1 minutes")
    if len(errorTemp.keys()):
        try:
            logger.info("Start of getting data from the database")
            switches = huta.getSwitches()
            mibsList = huta.getMibs()
            lassErrorsPort = huta.getPortError()
        except Exception as e:
            logger.error("Error getting data from the database")
            logger.error(e)
            return
        else:
            logger.info("Successful of getting data from the database")

        switches = {
            key: val for key, val in switches.items() if key in errorTemp.keys()
        }
        mibsList = {key: val for key, val in mibsList.items() if key in switches.keys()}
        lassErrorsPort = {
            key: val for key, val in lassErrorsPort.items() if key in switches.keys()
        }
        if len(switches.keys()):
            logger.info("Start check")
            errors = runningCheck(switches, mibsList, lassErrorsPort, errorTemp)
            oneError.update(errors)
            if len(
                list(noSendingErrorToDatabase.keys())
                + list(noSendingErrorToMail.keys())
            ):
                errorInsert({})
    logger.info("End of the check every 1 minutes")


def startProgramm():
    global huta, oneError, typeErrorList, logger
    try:
        logger.info("Start of receiving initial data")
        oneError = huta.getDeviceError()
        typeErrorList = huta.getTypeError()
    except Exception as e:
        logger.error("Initial data acquisition error")
        logger.error(e)
    else:
        logger.info("Successful of receiving initial data")


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
