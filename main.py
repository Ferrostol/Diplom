import time
import asyncio
from psycopg2 import OperationalError

from pysnmp.hlapi.asyncio import *
from ping3 import ping
import schedule

from database import database



snmpEngine = SnmpEngine()

try:
    huta = database()
except OperationalError as e:
    print(e)
    exit()
    
switches = huta.getSwitches()
mibsList = huta.getMibs()



async def request(switch, typeMib, mib):
    global snmpEngine,switches
    errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
        snmpEngine,
        CommunityData(mib['community']),
        UdpTransportTarget((switches[switch]['ip'], switches[switch]['port'])),
        ContextData(),
        ObjectType(ObjectIdentity(mib['proc']))
    )
    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(), 
            errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            print(' = '.join([x.prettyPrint() for x in varBind]))



def cpuCheck(switch_list):
    global mibsList
    ioloop = asyncio.get_event_loop()
    tasks = []
    for switch in switch_list:
        tasks.append(ioloop.create_task(request(switch, 'CPU', mibsList[switch])))
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)


def errorInsert(errorList):
    for swt in errorList:
        pass


def pingAll():
    global switches
    temp = []
    error = {}
    for a in switches:  
        rez = ping(switches[a]['ip'])
        if rez == None:
            #TimeOut
            error[a] = 'TimeOut'
        elif rez == False:
            #Host unknown
            error[a] = 'Host unknown'
        elif rez > 2:
            #Host delay 2 sec
            error[a] = 'Host delay 2 sec'
        else:
            temp.append(a) 
    errorInsert(error)
    return temp           


def main():
    onSwitches = pingAll()
    

if __name__ == '__main__':
    schedule.every(1).minutes.do(main)
    # schedule.every(5).minutes.do(main)
    main()
    while True:
        schedule.run_pending()
        time.sleep(1)