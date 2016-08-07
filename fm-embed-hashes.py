#embed sums in filemaker
import jaydebeapi

conn = jaydebeapi.connect('com.filemaker.jdbc.Driver',['jdbc:filemaker://192.168.19.3/PBCore_Catalog','Strecker','123456'],'/Library/Java/Extensions/fmjdbc.jar')

curs = conn.cursor()

print curs.fetchall()