import psycopg2

class database(object):
	def __init__(self):
		self.getConnect()
		self.getCursor()

	def getConnect(self):
		pass		
		

	def getCursor(self):
		self.cursor = self.connect.cursor()	

	# def __del__(self):
	# 	self.cursor.close()
	# 	self.connect.close()

	def getSwitches(self):
		sql = "select switches.id, switches.name, ip, port, err, model.name from switches join model on model.id=switches.model_id where status=true"
		self.cursor.execute(sql)
		swww = {}
		swt = self.cursor.fetchall()
		for el in swt:
			swww[el[0]] = {'switches_name': el[1], 'ip': el[2], 'port': el[3], 'err': el[4], 'model_name': el[5]}
		return swww

	def getMibs(self):
		sql = "select switches_id, community, proc, idleProc from switches join mibsList on mibsList.switches_id=switches.id where status=true"
		self.cursor.execute(sql)
		swww = {}
		swt = self.cursor.fetchall()
		for el in swt:
			swww[el[0]] = {'community': el[1], 'proc': el[2], 'idleProc': el[3]}
		return swww












# def addNewError(device, error):
# 	cursor = getCursorConnect()
# 	sql = f"insert into Errors (device_id, error) values({device}, '{error}')"
# 	cursor.execute(sql)


# def getDeviceError():
# 	cursor = getCursorConnect()
# 	sql = "select * from Device where job=1 and id in (select device_id from Errors)"
# 	cursor.execute(sql)
# 	return cursor.fetchall()


# def deleteError(device):
# 	cursor = getCursorConnect()
# 	sql = f"delete from Errors where device_id={device}"
# 	cursor.execute(sql)