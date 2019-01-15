import asyncio

async def username(beatmapsetdiscussionobject, subpostobject):
	for oneuser in beatmapsetdiscussionobject["beatmapset"]["related_users"]:
		if subpostobject['user_id'] == oneuser['id']:
			if "bng" in oneuser['groups']:
				return oneuser['username']+" [BN]"
			elif "qat" in oneuser['groups']:
				return oneuser['username']+" [QAT]"
			else :
				return oneuser['username']

async def diffname(beatmapsetdiscussionobject, newevent):
	for onediff in beatmapsetdiscussionobject["beatmapset"]["beatmaps"]:
		if newevent['beatmap_id']: 
			if onediff['id'] == newevent['beatmap_id']:
				diffname = onediff['version']
		else:
			diffname = "All difficulties"
	return diffname

async def modtype(newevent):
	if newevent['resolved']:
		footer = {
			'icon': "https://i.imgur.com/jjxrPpu.png",
			'text': "RESOLVED",
			'color': 0x77b255,
		}
	else :
		if newevent['message_type'] == "praise":
			footer = {
				'icon': "https://i.imgur.com/2kFPL8m.png",
				'text': "Praise",
				'color': 0x44aadd,
			}
		elif newevent['message_type'] == "hype":
			footer = {
				'icon': "https://i.imgur.com/fkJmW44.png",
				'text': "Hype",
				'color': 0x44aadd,
			}
		elif newevent['message_type'] == "mapper_note":
			footer = {
				'icon': "https://i.imgur.com/HdmJ9i5.png",
				'text': "Note",
				'color': 0x8866ee,
			}
		elif newevent['message_type'] == "problem":
			footer = {
				'icon': "https://i.imgur.com/qxyuJFF.png",
				'text': "Problem",
				'color': 0xcc5288,
			}
		elif newevent['message_type'] == "suggestion":
			footer = {
				'icon': "https://i.imgur.com/Newgp6L.png",
				'text': "Suggestion",
				'color': 0xeeb02a,
			}
		else:
			footer = {
				'icon': "",
				'text': newevent['message_type'],
				'color': 0xbd3661,
			}
	return footer