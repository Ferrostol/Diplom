import psycopg2
from config import databaseConf


class database(object):
    def __init__(self):
        self.getConnect()
        self.getCursor()

    def getConnect(self):
        self.connect = psycopg2.connect(
            dbname=databaseConf["dbname"],
            user=databaseConf["user"],
            password=databaseConf["password"],
            host=databaseConf["host"],
        )

    def getCursor(self):
        self.cursor = self.connect.cursor()

    def __del__(self):
        self.cursor.close()
        self.connect.close()

    def getTypeError(self):
        sql = "select * from errorlist"
        self.cursor.execute(sql)
        swt = self.cursor.fetchall()
        swww = {el[0]: el[1] for el in swt}
        return swww

    def getSwitches(self):
        sql = "select switches.id, switches.name, ip, port, model.name from switches join model on model.id=switches.model_id where status=true"
        self.cursor.execute(sql)
        swww = {}
        swt = self.cursor.fetchall()
        for el in swt:
            swww[el[0]] = {
                "switches_name": el[1],
                "ip": el[2],
                "port": el[3],
                "model_name": el[4],
            }
        return swww

    def getMibs(self):
        sql = "select switches_id, community, proc, idleProc, temp from switches left join mibsList on mibsList.switches_id=switches.id where status=true"
        self.cursor.execute(sql)
        swww = {}
        swt = self.cursor.fetchall()
        for el in swt:
            swww[el[0]] = {
                "community": el[1],
                "proc": el[2],
                "idleProc": el[3],
                "temp": el[4],
            }
        return swww

    def getDeviceError(self):
        sql = f"select switches.id, id_err_info from switches join model on model.id=switches.model_id join error on error.id_swit=switches.id where status=true"
        self.cursor.execute(sql)
        swww = {}
        swt = self.cursor.fetchall()
        for el in swt:
            swww[el[0]] = {
                "id_err_info": el[1],
            }
        return swww

    def getPortError(self):
        sql = f"select switches.id, num_port, error_in, error_out from switches join lastporterror on lastporterror.switches_id=switches.id where status=true"
        self.cursor.execute(sql)
        swww = {}
        swt = self.cursor.fetchall()
        for el in swt:
            if not el[0] in swww:
                swww.update({el[0]: {el[1]: [el[2], el[3]]}})
            else:
                swww[el[0]].update({el[1]: [el[2], el[3]]})
        return swww

    def addProcStat(self, procStat):
        if len(procStat) == 0:
            return
        sql = (
            "insert into statcpu (switches_id,procent) values "
            + ",".join([f"({stat[0]},{stat[1]})" for stat in procStat])
            + ";"
        )
        self.cursor.execute(sql)
        self.connect.commit()

    def addTempStat(self, tempStat):
        if len(tempStat) == 0:
            return
        sql = (
            "insert into stattemp (switches_id,num_sensor, value) values "
            + ",".join([f"({stat[0]},{stat[1]},{stat[2]})" for stat in tempStat])
            + ";"
        )
        self.cursor.execute(sql)
        self.connect.commit()

    def addPortStat(self, portStat):
        sql = (
            "insert into statport (switches_id, num_port, error_in,error_out) values "
            + ",".join(
                [f"({stat[0]},{stat[1]},{stat[2]},{stat[3]})" for stat in portStat]
            )
            + ";"
        )
        self.cursor.execute(sql)
        self.connect.commit()

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
        self.cursor.execute(sql)
        self.connect.commit()

    def deleteError(self, deleteMass):
        if len(deleteMass) == 0:
            return
        sql = (
            "delete from error where id_swit in ("
            + ",".join([str(el[0]) for el in deleteMass if len(el) == 1])
            + ");"
        )
        sql = sql + " ".join(
            [
                f"delete from error where id_swit = {str(el[0])} and id_err_info = {str(el[1])};"
                for el in deleteMass
                if len(deleteMass) == 2
            ]
        )
        self.cursor.execute(sql)
        self.connect.commit()

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
        self.cursor.execute(sql)
        self.connect.commit()
