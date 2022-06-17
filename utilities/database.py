import string
import datetime
import psycopg2
import sys
import os
from prettytable import PrettyTable


class database:
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

    def getAllTable(self):
        sql = "SELECT table_name FROM INFORMATION_SCHEMA.TABLES where table_schema = 'public' order by table_name;"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        swt = [el[0] for el in cursor.fetchall()]
        cursor.close()
        return swt

    def getInfoOfTable(self, name):
        if name not in self.getAllTable():
            print(self.getAllTable())
            raise Exception("This table not in database.")
        sql = f"""
        SELECT column_name, column_default, data_type,is_nullable 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE table_name = '{name}';
        """
        cursor = self.connect.cursor()
        cursor.execute(sql)
        colnames = [desc[0] for desc in cursor.description]
        swt = [
            [str(el[0] or ""), str(el[1] or ""), str(el[2] or ""), str(el[3] or "")]
            for el in cursor.fetchall()
        ]
        cursor.close()
        return (colnames, swt)

    def getDataFromTable(self, name, sorts):
        if name not in self.getAllTable():
            raise Exception("This table not in database.")
        sql = f"SELECT * FROM {name} {'order by ' if len(sorts) else ''} {', '.join(sorts)};"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        colnames = [desc[0] for desc in cursor.description]
        swt = [[ell for ell in el] for el in cursor.fetchall()]
        cursor.close()
        return (colnames, swt)

    def addData(self, name: string, row: dict):
        sql = (
            f"insert into {name} ("
            + ",".join(row.keys())
            + ") values ("
            + ",".join([f"{row[key]}" for key in row])
            + ");"
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def getRow(self, name, wheres):
        if name not in self.getAllTable():
            print(self.getAllTable())
            raise Exception("This table not in database.")
        sql = f"SELECT * FROM {name} {'where ' if len(wheres) else ''} {' and '.join([f'{el} = {wheres[el]}' for el in wheres])};"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        colnames = [desc[0] for desc in cursor.description]
        all = cursor.fetchall()
        swtObj = [
            {
                colnames[i]: str(ell) if str(ell) in ("0.00") else str(ell or "")
                for i, ell in enumerate(el)
            }
            for el in all
        ]
        swtMass = [
            [str(ell) if str(ell) in ("0.00") else str(ell or "") for ell in el]
            for el in all
        ]
        cursor.close()
        return (colnames, swtObj, swtMass)

    def update(self, name, wheres, newData):
        sql = (
            f"update {name} set "
            + ", ".join([f"{key}={newData[key]}" for key in newData])
            + f" {'where ' if len(wheres) else ''} {' and '.join([f'{el} = {wheres[el]}' for el in wheres])};"
        )
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()

    def delete(self, name, wheres):
        if name not in self.getAllTable():
            print(self.getAllTable())
            raise Exception("This table not in database.")
        sql = f"delete FROM {name} {'where ' if len(wheres) else ''} {' and '.join([f'{el} = {wheres[el]}' for el in wheres])};"
        cursor = self.connect.cursor()
        cursor.execute(sql)
        self.connect.commit()
        cursor.close()


def helpInfo(argum):
    text = f"""
USAGE: ./{os.path.basename(__file__)} [OPTIONS]
OPTIONS:
    -h                  display this help message

Working with database:
    -a                  select all table in database
    -d TABLE_NAME       output of records from the table

                        Additional parameters:
                        -sr COLUMN              sorts rows by the selected column

                        Example:
                            {os.path.basename(__file__)} -d switches -c id -c model_id

                        -srd COLUMN             sorts rows by the selected column in reverse order

                        Example:
                            {os.path.basename(__file__)} -d switches -cd id

    -s TABLE_NAME       output of information about the table
    -i TABLE_NAME       adding new data in database
    -r TABLE_NAME       deleting data from the database
                        
                        Required parameters:
                        -k PR_KEY               The key by which it is deleted
                        -v VALUE_PR_KEY         Key value
                        If there are several keys then enter one at a time:
                        
                        Example:
                            Delete CPU statistics for 4 switches in 2022-05-09 19:01:27.126789:
                            {os.path.basename(__file__)} -d statcpu -k switches_id -v 4 -k datevrem '2022-05-09 19:01:27.126789'
                            Delete CPU statistics for 4 switches:
                            {os.path.basename(__file__)} -d statcpu -k switches_id -v 4

    -u TABLE_NAME       сhanging the data in the database 

                        Required parameters:
                        -k PR_KEY               The key by which it is сhanging
                        -v VALUE_PR_KEY         Key value

                        If there are several keys then enter one at a time:

                        Example:
                            Edit the CPU statistics entry for 4 switches in 2022-05-09 19:01:27.126789:
                            {os.path.basename(__file__)} -u statcpu -k switches_id -v 4 -k datevrem '2022-05-09 19:01:27.126789'    
    """
    print(text)


def printTable(columns, rows):
    table = PrettyTable()
    table.field_names = columns
    table.add_rows(rows)
    print(table)


def allTable(argum):
    if len(argum):
        helpInfo([])
        return
    mass = [[el] for el in database().getAllTable()]
    print("""   List of table""")

    printTable(["Name"], mass)


def dataFromTable(argum):
    sorts = []
    srt = {"-sr": "", "-srd": " desc"}
    if len(argum) != 1:
        for i in range(1, len(argum)):
            if i % 2 and argum[i] not in ("-sr", "-srd"):
                helpInfo([])
                return
            elif i % 2:
                if argum[i] not in srt or i + 1 == len(argum):
                    helpInfo([])
                    return
                sorts.append(argum[i + 1] + srt[argum[i]])
    try:
        column, row = database().getDataFromTable(argum[0], sorts)
        printTable(column, row)
    except Exception as e:
        print(e)
        exit()


def infoTable(argum):
    if len(argum) != 1:
        helpInfo([])
        return
    try:
        column, row = database().getInfoOfTable(argum[0])
        printTable(column, row)
    except Exception as e:
        print(e)
        exit()


def checkType(column, inp):
    if column[3] == "NO" and str(inp).strip() == "" and column[1] == "":
        return False
    if str(column[2]).lower() in ("integer"):
        return str(inp).isdigit()
    if str(column[2]).lower() in ("numeric"):
        return str(inp).isnumeric()
    if str(column[2]).lower() in ("character varying", "text"):
        return True
    if str(column[2]).lower() in ("boolean"):
        return str(inp).lower().strip() in ("false", "true")

    if str(column[2]).lower() in ("timestamp without time zone"):
        try:
            datetime.datetime.strptime(inp, "%Y-%m-%d-%H.%M.%S")
        except ValueError:
            return False
        else:
            return True
    return True


def correctValue(column, inp):
    if str(column[2]).lower() in (
        "character varying",
        "text",
        "timestamp without time zone",
    ):
        return f"'{inp}'"
    return inp


def addData(argum):
    if len(argum) != 1:
        helpInfo([])
        return
    try:
        columns, rows = database().getInfoOfTable(argum[0])
    except Exception as e:
        print(e)
        exit()
    value = {}
    search = "nextval("
    for column in rows:
        inp = input(
            f"{column[0]} field"
            + f"{'' if column[1] in (None, '') else f'(Default: {column[1]})' if str(column[1]).find(search) == -1 else '(Default:AUTO GENERATE)'}."
            + f" is_nullable({column[3]}){' Format ' if str(column[2]).lower() == 'timestamp without time zone' else ''}:"
        )
        while not checkType(column, inp):
            inp = input(
                f"Error input. {column[0]} field"
                + f"{'' if column[1] in (None, '') else f'(Default: {column[1]})' if str(column[1]).find(search) == -1 else '(Default:AUTO GENERATE)'}."
                + f" is_nullable({column[3]}){' Format ' if str(column[2]).lower() == 'timestamp without time zone' else ''}:"
            )
        inp = correctValue(column, inp)
        value[column[0]] = inp
    assent = input("Confirm adding the entry[y/n]:").lower()
    if assent in ("y", "yes"):
        try:
            database().addData(argum[0], value)
        except Exception as e:
            print(e)
            exit()
        else:
            print("Entry added")
            exit()


def deleteData(argum):
    wheres = {}
    if len(argum) != 1:
        for i in range(1, len(argum)):
            if i % 2 and argum[i] not in ("-k", "-v"):
                helpInfo([])
                return
            elif i % 2:
                if argum[i] not in ("-k", "-v") or (
                    argum[i] == "-k" and i + 3 >= len(argum)
                ):
                    helpInfo([])
                    return
                if (i - 1) % 4 >= 1:
                    continue
                if argum[i + 1] in wheres:
                    print("The key should not be repeated")
                    exit()
                if argum[i] != "-k" and argum[i + 2] != "-v":
                    helpInfo([])
                    return
                wheres[argum[i + 1]] = argum[i + 3]
        try:
            columns, rowsObj, rowMass = database().getRow(argum[0], wheres)
        except Exception as e:
            print(e)
            exit()
        printTable(columns, rowMass)
        assent = input("Delete all these records from the table?[y/n]:").lower()
        if assent in ("y", "yes"):
            try:
                database().delete(argum[0], wheres)
            except Exception as e:
                print(e)
                exit()
            else:
                print("Entry deleted")
                exit()
    else:
        assent = input("Delete all records from the table?[y/n]:").lower()
        if assent in ("y", "yes"):
            try:
                database().delete(argum[0], wheres)
            except Exception as e:
                print(e)
                exit()
            else:
                print("Entry deleted")
                exit()


def editData(columns, current):
    value = {}
    search = "nextval("
    for column in columns:
        inp = input(
            f"{column[0]} field"
            + f"{'' if column[1] in (None, '') else f'(Default: {column[1]})' if str(column[1]).find(search) == -1 else '(Default:AUTO GENERATE)'}."
            + f" is_nullable({column[3]}).{' Format ' if str(column[2]).lower() == 'timestamp without time zone' else ''} Current[{current[column[0]]}]:"
        )
        while not checkType(column, inp):
            inp = input(
                f"Error input. {column[0]} field"
                + f"{'' if column[1] in (None, '') else f'(Default: {column[1]})' if str(column[1]).find(search) == -1 else '(Default:AUTO GENERATE)'}."
                + f" is_nullable({column[3]}).{' Format ' if str(column[2]).lower() == 'timestamp without time zone' else ''} Current[{current[column[0]]}]:"
            )
        inp = correctValue(column, inp)
        value[column[0]] = inp
    assent = input("Confirm adding the entry[y/n]:").lower()
    if assent in ("y", "yes"):
        return value
    else:
        return {}


def updateData(argum):
    wheres = {}
    if len(argum) != 1:
        for i in range(1, len(argum)):
            if i % 2 and argum[i] not in ("-k", "-v"):
                helpInfo([])
                return
            elif i % 2:
                if argum[i] not in ("-k", "-v") or (
                    argum[i] == "-k" and i + 3 >= len(argum)
                ):
                    helpInfo([])
                    return
                if (i - 1) % 4 >= 1:
                    continue
                if argum[i + 1] in wheres:
                    print("The key should not be repeated")
                    exit()
                if argum[i] != "-k" and argum[i + 2] != "-v":
                    helpInfo([])
                    return
                wheres[argum[i + 1]] = argum[i + 3]

        try:
            columnsTable = database().getInfoOfTable(argum[0])[1]
        except Exception as e:
            print(e)
            exit()

        if len([el for el in wheres if not el in [ell[0] for ell in columnsTable]]):
            print("One of the columns is not in the table")
            exit()

        try:
            columns, rowObj, rowMass = database().getRow(argum[0], wheres)
        except Exception as e:
            print(e)
            exit()
        if len(rowMass) != 1:
            print("The condition you set returned more than one row from the table")
            exit()
        newData = editData(database().getInfoOfTable(argum[0])[1], rowObj[0])
        if newData != {}:
            try:
                database().update(argum[0], wheres, newData)
            except Exception as e:
                print(e)
                exit()
            else:
                print("Entry updated")
    else:
        print("Set the conditions for selecting the record to edit")
        exit()


flagsList = {
    "-h": helpInfo,
    "-a": allTable,
    "-d": dataFromTable,
    "-s": infoTable,
    "-i": addData,
    "-r": deleteData,
    "-u": updateData,
}

if __name__ == "__main__":
    argum = sys.argv[1:]
    if argum[0] not in flagsList:
        helpInfo()
    else:
        flagsList[argum[0]](argum[1:])
