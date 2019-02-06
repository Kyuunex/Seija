import json
import time
from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import osuwebapipreview
from modules import osuwebapipreview

async def comparelists(list1, list2, reverse):
	difference = []
	if reverse:
		comparelist1 = list2
		comparelist2 = list1
	else:
		comparelist1 = list1
		comparelist2 = list2
	for i in comparelist1:
		if not i in comparelist2:
			difference.append(i)
	return difference

async def compare(result, lookupvalue, tablename, lookupkey, updatedb, reverse):
	if not await dbhandler.select(tablename, lookupkey, [[lookupkey, lookupvalue]]):
		await dbhandler.insert(tablename, (lookupvalue, json.dumps(result)))
		return None
	else :
		if result:
			localdata = json.loads((await dbhandler.select(tablename, 'contents', [[lookupkey, lookupvalue]]))[0][0])
			comparison = await comparelists(result, localdata, reverse)
			if comparison:
				if updatedb:
					await dbhandler.update(tablename, 'contents', json.dumps(result), lookupkey, lookupvalue)
					print("db is updating for sure %s" % (lookupvalue))
				return comparison
			else:
				return None
		else :
			print('connection problems?')
			return None
