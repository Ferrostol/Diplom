#!/usr/local/bin/python3
import psycopg2
import sys
import os


databaseConf = {
    "dbname": "databasename",
    "user": "user",
    "password": "password",
    "host": "localhost",
}


def helpInfo():
    text = f"""
        USAGE: ./{os.path.basename(__file__)} startIP [endIP]

        EXAMPLE:
            {os.path.basename(__file__)} 10
        RESULT:
            Switch IP: 10.10.10.10. Switch name: TestName.
            Last CPU load: 4%.
            Last temperature: 40 C.
        
        EXAMPLE:
            {os.path.basename(__file__)} 10 12
        RESULT:
            Switch IP: 10.10.10.10. Switch name: TestName.
            Last CPU load: 4%.
            Last temperature on 1 sensor: 35 C.
            Last temperature on 2 sensor: 35 C.

            Switch IP: 10.10.10.11. Switch name: TestName2.
            Last CPU load: 1%.
            Last temperature: 25 C.

            Switch IP: 10.10.10.12. Switch name: TestName3.
            Last CPU load: 15%.
            Last temperature: 40 C.
    """
    print(text)


def printInfo(info):
    for swt in info:
        print(
            f"""
Switch IP: {info[swt]['ip']}. Switch name: {info[swt]['name']}.
{'Last CPU load: ' + str(info[swt]['procent']) + '%.' if info[swt]['procent'] != None else ''}"""
        )
        for el in info[swt]["temperature"]:
            if len(info[swt]["temperature"]) == 1:
                print(f"Last temperature: {el[1]}C")
            else:
                print(f"Last temperature on {el[0] + 1} sensor: {el[1]} C.")
        if len(info[swt]["error"]):
            print("Errors:")
        for el in info[swt]["error"]:
            print(f"--{el}")


def statistic(start, finish=None):
    if finish == None:
        finish = start
    if not str(start).isdigit() or not str(finish).isdigit():
        helpInfo()
        exit()
    connect = psycopg2.connect(
        dbname=databaseConf["dbname"],
        user=databaseConf["user"],
        password=databaseConf["password"],
        host=databaseConf["host"],
    )
    with connect:
        cursor = connect.cursor()
        sql = f"""
            select switches.id, ip, name, procent,num_sensor,value, description
            from switches
            left join (select statcpu.switches_id id, procent
            from statcpu
            join (select distinct switches_id, max(datevrem) over (PARTITION BY switches_id) datevrem
            from statcpu) maxx on maxx.switches_id = statcpu.switches_id and maxx.datevrem = statcpu.datevrem) cpu on cpu.id=switches.id
            left join (select stattemp.switches_id id, num_sensor,value
            from stattemp
            join (select distinct switches_id, max(datevrem) over (PARTITION BY switches_id) datevrem
            from stattemp) maxx on maxx.switches_id = stattemp.switches_id and maxx.datevrem = stattemp.datevrem) tempstat on tempstat.id=switches.id
            left join error on error.id_swit=switches.id
            where ip like '10.10.10.%' and to_number(split_part(ip, '10.10.10.',2 ),'9999') between {start} and {finish}
            order by switches.id,num_sensor;
        """
        cursor.execute(sql)
        swww = {}
        swt = cursor.fetchall()

        for el in swt:
            if el[0] in swww:
                if el[4] != None and not [el[4], el[5]] in swww[el[0]]["temperature"]:
                    swww[el[0]]["temperature"].append([el[4], el[5]])
                if el[6] != None and not el[6] in swww[el[0]]["error"]:
                    swww[el[0]]["error"].append(el[6])
            else:
                swww[el[0]] = {
                    "ip": el[1],
                    "name": el[2],
                    "procent": el[3],
                    "temperature": [],
                    "error": [],
                }
                if el[4] != None:
                    swww[el[0]]["temperature"].append([el[4], el[5]])
                if el[6] != None:
                    swww[el[0]]["error"].append(el[6])
        if len(swt):
            printInfo(swww)
    connect.close()


if __name__ == "__main__":
    if len(sys.argv) in (2, 3):
        statistic(*sys.argv[1:3])
    else:
        helpInfo()
