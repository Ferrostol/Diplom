import psycopg2
from config import databaseConf, TYPE_ERROR


class database(object):
    def __init__(self):
        self.getConnect()

    def getConnect(self):
        self.connect = psycopg2.connect(
            dbname=databaseConf["dbname"],
            user=databaseConf["user"],
            password=databaseConf["password"],
            host=databaseConf["host"],
        )

    def __del__(self):
        self.connect.close()

    def getTypeError(self):
        sql = "select * from errorlist"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        swt = cursor.fetchall()
        swww = {el[0]: el[1] for el in swt}
        cursor.close()
        return swww

    def getSwitches(self):
        sql = "select switches.id, switches.name, ip, port, model.name from switches join model on model.id=switches.model_id where status=true"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        swww = {}
        swt = cursor.fetchall()
        for el in swt:
            swww[el[0]] = {
                "switches_name": el[1],
                "ip": el[2],
                "port": el[3],
                "model_name": el[4],
            }
        cursor.close()
        return swww

    def getMibs(self):
        sql = "select switches_id, community, proc, idleProc, temp from switches left join mibsList on mibsList.switches_id=switches.id where status=true"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        swww = {}
        swt = cursor.fetchall()
        for el in swt:
            swww[el[0]] = {
                "community": el[1],
                "proc": el[2],
                "idleProc": el[3],
                "temp": el[4],
            }
        cursor.close()
        return swww

    def getDeviceError(self):
        sql = f"select switches.id, id_err_info from switches join model on model.id=switches.model_id join error on error.id_swit=switches.id where status=true"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        swww = {}
        swt = cursor.fetchall()
        for el in swt:
            if el in swww:
                swww[el[0]].append(
                    {
                        "typeEr": [eel for eel in TYPE_ERROR if eel.value == el[1]][0],
                    }
                )
            else:
                swww[el[0]] = [
                    {
                        "typeEr": [eel for eel in TYPE_ERROR if eel.value == el[1]][0],
                    }
                ]
        cursor.close()
        return swww

    def getPortError(self):
        sql = f"select switches.id, num_port, error_in, error_out from switches join lastporterror on lastporterror.switches_id=switches.id where status=true"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        swww = {}
        swt = cursor.fetchall()
        for el in swt:
            if not el[0] in swww:
                swww.update({el[0]: {el[1]: [el[2], el[3]]}})
            else:
                swww[el[0]].update({el[1]: [el[2], el[3]]})
        cursor.close()
        return swww

    def addProcStat(self, procStat):
        if len(procStat) == 0:
            return
        sql = (
            "insert into statcpu (switches_id,procent) values "
            + ",".join([f"({stat[0]},{stat[1]})" for stat in procStat])
            + ";"
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def addTempStat(self, tempStat):
        if len(tempStat) == 0:
            return
        sql = (
            "insert into stattemp (switches_id,num_sensor, value) values "
            + ",".join([f"({stat[0]},{stat[1]},{stat[2]})" for stat in tempStat])
            + ";"
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def addPortStat(self, portStat):
        sql = (
            "insert into statport (switches_id, num_port, error_in,error_out) values "
            + ",".join(
                [f"({stat[0]},{stat[1]},{stat[2]},{stat[3]})" for stat in portStat]
            )
            + ";"
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def addNewError(self, errors):
        if len(errors) == 0:
            return
        sql = (
            "insert into error (id_swit, id_err_info, description) values "
            + ",".join(
                [f"({error[0]},{error[1].value},'{error[2]}')" for error in errors]
            )
            + ";"
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def deleteError(self, deleteMass):
        if len(deleteMass) == 0:
            return
        sql = (
            "delete from error where id_swit in ("
            + ",".join([str(el) for el in deleteMass if len(deleteMass[el]) == 1])
            + ");"
        )
        sql = sql + " ".join(
            [
                f"delete from error where id_swit = {str(el)} and id_err_info = {ell.value};"
                for el in deleteMass
                if len(deleteMass[el]) != 1
                for ell in deleteMass[el]
            ]
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def updateLastPortError(self, lassErrorsPort):
        if len(lassErrorsPort.keys()) == 0:
            return
        sql = " ".join(
            [
                f"select updateLastPortError({switch},{port},{lassErrorsPort[switch][port][0]},{lassErrorsPort[switch][port][1]});"
                for switch in lassErrorsPort
                for port in lassErrorsPort[switch]
            ]
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()
