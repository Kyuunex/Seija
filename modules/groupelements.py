from modules import osuapi
from modules import osuembed
from modules import utils
from modules import osuwebapipreview
from modules import feedchecker

async def groupmain(client, user, groupname, groupurl, description, groupfeedchannellist, color):
	osuprofile = await osuapi.get_user(user)
	if not osuprofile: 
		osuprofile = {}
		osuprofile['username'] = "restricted user"
		osuprofile['user_id'] = user
	embed = await osuembed.groupmember(
		osuprofile, 
		groupname, 
		groupurl, 
		description % ("[%s](https://osu.ppy.sh/users/%s)" % (osuprofile['username'], str(osuprofile['user_id'])), "[%s](%s)" % (groupname, groupurl)),
		color
		)
	for groupfeedchannelid in groupfeedchannellist:
		channel = await utils.get_channel(client.get_all_channels(), int(groupfeedchannelid[0]))
		await channel.send(embed=embed)

async def groupcheck(client, groupfeedchannellist, groupid, groupname):
	userlist = await osuwebapipreview.groups(groupid)
	checkadditions = await feedchecker.compare(userlist, groupid, 'feedjsondata', 'feedtype', False, False)
	checkremovals = await feedchecker.compare(userlist, groupid, 'feedjsondata', 'feedtype', True, True)
	if checkadditions:
		for newuser in checkadditions:
			print("groupfeed | %s | added %s" % (groupname, newuser))
			await groupmain(client, newuser, groupname, "https://osu.ppy.sh/groups/%s" % (groupid), "**%s** \nhas been added to \nthe **%s**", groupfeedchannellist, 0xffbd0e)
	if checkremovals:
		for removeduser in checkremovals:
			print("groupfeed | %s | removed %s" % (groupname, removeduser))
			await groupmain(client, removeduser, groupname, "https://osu.ppy.sh/groups/%s" % (groupid), "**%s** \nhas been removed from \nthe **%s**", groupfeedchannellist, 0x2c0e6c)