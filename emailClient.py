import datetime
import smtplib
from config import mailConf, TYPE_ERROR, LIMIT


class mailClient:
    def sendEmailError(self, typeErrorList, errorList):
        self.smtp = smtplib.SMTP(mailConf["server"], mailConf["port"])
        self.charset = "Content-Type: text/plain; charset=utf-8"
        self.mime = "MIME-Version: 1.0"
        self.subject = "Ошибки работы оборудования"
        if len(errorList) == 0:
            return
        textEmail = f"Дата: {str(datetime.datetime.now())}"
        textSMS = f"Дата: {str(datetime.datetime.now())}"
        for swt in errorList:
            textEmail = (
                textEmail
                + f"\r\nИмя:{errorList[swt][0]['name_switches']} IP-адресом: {errorList[swt][0]['ip']} Ошибки:"
            )
            textSMS = textEmail
            for el in errorList[swt]:

                if el["typeEr"] == TYPE_ERROR.HOST_UNKNOWN:
                    textEmail = (
                        textEmail
                        + f"\r\n\t--Тип ошибки: {typeErrorList[el['typeEr'].value]}."
                    )
                    textSMS = textSMS + f"\r\n\t--{typeErrorList[el['typeEr'].value]}."

                elif el["typeEr"] == TYPE_ERROR.CPU_LOAD:
                    textEmail = (
                        textEmail
                        + f"\r\n\t--Тип ошибки: {typeErrorList[el['typeEr'].value]}. Описание: Загрузка процессора более {LIMIT.MAX_CPU_LOAD}%. = {el['description']}%."
                    )
                    textSMS = textSMS + f"\r\n\t--Процессор {el['description']}%."

                elif el["typeEr"] == TYPE_ERROR.TEMPERATURE:
                    textEmail = (
                        textEmail
                        + f"\r\n\t--Тип ошибки: {typeErrorList[el['typeEr'].value]}. Описание: Температура датчика {el['description'][0]} более {LIMIT.MAX_TEMPERATURE}%. = {el['description'][1]}C."
                    )
                    textSMS = (
                        textSMS
                        + f"\r\n\t--Температура датчик {el['description'][0]} = {el['description'][1]}С."
                    )

                elif el["typeEr"] == TYPE_ERROR.PORT_LOAD:
                    textEmail = (
                        textEmail
                        + f"\r\n\t--Тип ошибки: {typeErrorList[el['typeEr'].value]}. Описание: Ошибки на {el['description'][0]} {el['description'][1]} порта появилось {el['description'][2]} ошибок."
                    )
                    textSMS = (
                        textSMS
                        + f"\r\n\t--На {el['description'][0]} {el['description'][1]} порта {el['description'][2]} ошибок."
                    )

                elif el["typeEr"] == TYPE_ERROR.SNMP_ERROR:
                    textEmail = (
                        textEmail
                        + f"\r\n\t--Тип ошибки: {typeErrorList[el['typeEr'].value]}. Описание: {el['description']}"
                    )
                    textSMS = textSMS + f"\r\n\t--{typeErrorList[el['typeEr'].value]}."

        for toEmail in mailConf["toEmail"]:
            body = "\r\n".join(
                [
                    f"From: {mailConf['user']}",
                    f"To: {toEmail}",
                    f"Subject: {self.subject}",
                    self.mime,
                    self.charset,
                    "",
                    textEmail,
                ]
            )
            self.smtp.sendmail(mailConf["user"], toEmail, body.encode("utf-8"))

        for toEmail in mailConf["toEmailtoSMS"]:
            body = "\r\n".join(
                [
                    f"From: {mailConf['user']}",
                    f"To: {toEmail}",
                    f"Subject: {self.subject}",
                    self.mime,
                    self.charset,
                    "",
                    textSMS,
                ]
            )
            self.smtp.sendmail(mailConf["user"], toEmail, body.encode("utf-8"))

        self.smtp.quit()

    def sendEmailCorrecionError(self, deleteMass, switches):
        self.smtp = smtplib.SMTP(mailConf["server"], mailConf["port"])
        self.charset = "Content-Type: text/plain; charset=utf-8"
        self.mime = "MIME-Version: 1.0"
        self.subject = "Восстановление работы оборудования"
        if len(deleteMass) == 0:
            return
        textEmail = f"Дата: {str(datetime.datetime.now())}"
        for swt in deleteMass:
            textEmail = (
                textEmail
                + f"\r\nИмя:{switches[swt]['switches_name']} IP-адресом: {switches[swt]['ip']}:"
            )
            for typeEr in deleteMass[swt]:
                if typeEr == TYPE_ERROR.HOST_UNKNOWN:
                    textEmail = textEmail + f"\r\n\t--Соединение восстановлено."

                elif typeEr == TYPE_ERROR.CPU_LOAD:
                    textEmail = (
                        textEmail + f"\r\n\t--Загрузка процессора нормализовалась."
                    )

                elif typeEr == TYPE_ERROR.TEMPERATURE:
                    textEmail = textEmail + f"\r\n\t--Температура нормализовалась."

                elif typeEr == TYPE_ERROR.SNMP_ERROR:
                    textEmail = textEmail + f"\r\n\t--Работа SNMP нормализовалась."

        for toEmail in mailConf["toEmail"]:
            body = "\r\n".join(
                [
                    f"From: {mailConf['user']}",
                    f"To: {toEmail}",
                    f"Subject: {self.subject}",
                    self.mime,
                    self.charset,
                    "",
                    textEmail,
                ]
            )
            self.smtp.sendmail(mailConf["user"], toEmail, body.encode("utf-8"))

        for toEmail in mailConf["toEmailtoSMS"]:
            body = "\r\n".join(
                [
                    f"From: {mailConf['user']}",
                    f"To: {toEmail}",
                    f"Subject: {self.subject}",
                    self.mime,
                    self.charset,
                    "",
                    textEmail,
                ]
            )
            self.smtp.sendmail(mailConf["user"], toEmail, body.encode("utf-8"))

        self.smtp.quit()
