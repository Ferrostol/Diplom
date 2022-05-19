import time     # Библиотека для работы со временем
import os       # Библиотека для работы с ОС

import asyncio  # Библиотека для асинхронного программирования
from psycopg2 import OperationalError
import aiosnmp  # Библиотека для работы с SNMP
import schedule # Библиотека для запуска функции с периодичностью

from database import database
from config import TYPE_ERROR,LIMIT


try:
    huta = database()
except OperationalError as e:
    print(e)
    exit()


switches = [] # Инициализация массива в котором будет храниться информация о свичах
mibsList = [] # Инициализация массива в котором будет храниться информация о oid для свичей
procStat = [] # Инициализация массива в котором будет собрана статистика по работе процессора свичей
error = {}    # Инициализация Объекта в котором будет собраны ошибки по работе свичей


async def request(switch, typeMib, mib):
    global snmpEngine,switches,procStat
    try:
        snmp = async with aiosnmp.Snmp(host=switches[switch]['ip'], 
                                port=switches[switch]['port'], 
                                community=mib['community'], 
                                timeout=4)
    except Exception as e:
        print('1')
        print(switches[switch]['ip'])
        print(mib['proc'])
        raise e 
    else:
        if typeMib == 'CPU' and not mib['proc'] in (None,''):
            try:
                for res in await snmp.bulk_walk(mib['proc']):
                    rezult = (100 - int(res.value)) if mib['idleProc'] else int(res.value)
                    procStat.append([switch,rezult])
                    if LIMIT.MAX_CPU_LOAD <= rezult:
                        if switch in error:
                            error[switch].append({ typeEr=TYPE_ERROR.HOST_UNKNOWN, ip=switches[switch]['ip']})
                        else
                            error[switch] = [{ typeEr=TYPE_ERROR.HOST_UNKNOWN, ip=switches[switch]['ip']}]
            except Exception as e:
                print('2')
                raise e
            
            

def cpuCheck(switch_list):
    global mibsList,procStat
    ioloop = asyncio.get_event_loop()
    tasks = []
    for switch in switch_list:
        tasks.append(ioloop.create_task(request(switch, 'CPU', mibsList[switch])))
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    huta.addProcStat(procStat)
    #print(procStat)
    procStat = []


def errorInsert(errorList):
    for swt in errorList:
        pass


def pingAll():
    global switches, error
    temp = []
    error = {}
    for switch in switches:
        rez = os.system(f"ping -c 1 -t 1 {switches[switch]['ip']} > /dev/null")
        if rez == 0:
            temp.append(switch)
        else:
            rez = os.system(f"ping -c 2 -t 1 {switches[switch]['ip']} > /dev/null")
            if rez == 0:
                temp.append(switch)
            else:
                error[switch] = { typeEr=TYPE_ERROR.HOST_UNKNOWN, ip=switches[switch]['ip']}
                procStat.append([switch,'null'])
    errorInsert(error)
    print(error) # Отображаем на экране имеющиеся ошибки
    return temp


def main():
    global huta,switches,mibsList
    switches = huta.getSwitches()
    mibsList = huta.getMibs()
    onSwitches = pingAll()
    cpuCheck(onSwitches)
    #print(onSwitches)


if __name__ == '__main__':
    #schedule.every(1).minutes.do(main)
    schedule.every(5).minutes.do(main)
    main()
    while True:
        schedule.run_pending()
        time.sleep(1)