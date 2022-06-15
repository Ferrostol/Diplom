import datetime
import smtplib
from config import mailConf


class mailClient:
    def __init__(self):
        self.smtp = smtplib.SMTP(mailConf["server"], mailConf["port"])
        self.charset = "Content-Type: text/plain; charset=utf-8"
        self.mime = "MIME-Version: 1.0"
        self.subject = "Ошибки работы оборудования"

    def sendEmailError(self, typeErrorList, errorList):
        if len(errorList) == 0:
            return
        text = f"Дата: {str(datetime.datetime.now())}"
        for swt in errorList:
            text = (
                text
                + f"\r\nСвитч: Имя:{errorList[swt][0]['name_switches']} IP-адресом: {errorList[swt][0]['ip']} Ошибки:"
            )
            for el in errorList[swt]:
                text = (
                    text
                    + f"\r\n\t--Тип ошибки: {typeErrorList[el['typeEr'].value]}. {'Описание: ' + el['description'] if el['description'] != 'null' else ''}"
                )
        for toEmail in mailConf["to"]:
            body = "\r\n".join(
                [
                    f"From: {mailConf['user']}",
                    f"To: {mailConf['to']}",
                    f"Subject: {self.subject}",
                    self.mime,
                    self.charset,
                    "",
                    text,
                ]
            )
            self.smtp.sendmail(mailConf["user"], toEmail, body.encode("utf-8"))

    def __del__(self):
        self.smtp.quit()
