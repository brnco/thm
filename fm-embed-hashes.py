#embed sums in filemaker
import pyodbc

pyodbc.pooling = True

connect_str = "UseRemoteConnection=0Pooling=No;PoolAllAsText=0; ApplicationsUsingThreads=1;FetchChunkSize=100;FileOpenCache=0;MaxTextLength=255;DSN=PBCore_Catalog;UID=Strecker;PWD:123456"

connection = pyodbc.connect(connect_str)
cursor = connection.cursor()
rows = cursor.execute("select * from PBCore_Catalog")

for row in rows:
	print row

connection.close()