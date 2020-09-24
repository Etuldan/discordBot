# bot.py

import discord
import io
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import asyncio
import json
import atexit
from datetime import datetime
import configparser

PDSEnabled = True
BedsEnabled = True
FormationEnabled = True
AdminCommandsEnable = True

databaseFile = "data.json"
fontFile = "Calibri Regular.ttf"

client = discord.Client()

config = configparser.ConfigParser()
config.read('config.ini')
channelHome = int(config['Channel']['Home'])
channelIdPDS = int(config['Channel']['PDS'])
roleIdService = int(config['Role']['Service'])
roleIdDispatch = int(config['Role']['Dispatch'])
roleIdAdmin = config['Role']['Admin']
formationChannel = int(config['Section']['Formation'])
TOKEN = config['Discord']['Token']

message_head = 0
message_dispatch = 0
channelPDS = 0
messagesBeds = []

beds = []

loc = {}
loc['0'] = (110, 260)
loc['1'] = (470, 260)
loc['2'] = (95, 325)
loc['3'] = (410, 325)
loc['4'] = (95, 470)
loc['5'] = (410, 470)
loc['6'] = (95, 610)
loc['7'] = (410, 610)
loc['8'] = (710, 550)
loc['9'] = (970, 550)

class MessageBed(object):
    def __init__(self, message):
        self.message = message
        self.lspd = False
        self.bed = -1

class InfoBed(object):
    def __init__(self, patient, bed, lspd):
        self.patient = patient
        self.lspd = lspd
        self.bed = bed

radioLSMS = 000.0
radioLSPD = 000.0
radioEvent = False
async def updateRadio():
    global message_dispatch

    embedVar = discord.Embed(color=0x00ff00)
    embedVar.set_author(name="Gestion des Prises de Service", icon_url="https://cdn.discordapp.com/attachments/637303563701321728/692506630499336192/lsms_sceau_1.png")
    embedVar.set_thumbnail(url = "https://i.postimg.cc/qRmhx1qR/radio.png")
    embedVar.add_field(name="💉", value=radioLSMS, inline=True)
    embedVar.add_field(name="👮", value=radioLSPD, inline=True)
    if(radioEvent != False):
        embedVar.add_field(name="🏆", value=radioEvent, inline=True)
    if message_dispatch == 0:
        message_dispatch = await channel.send(embed=embedVar)
        await message_dispatch.add_reaction("🚑")
        await message_dispatch.add_reaction("📱")
    else:
        await message_dispatch.edit(embed=embedVar)

async def setService(user, service = True, automatic = False):
    if service == True:
        color = 0x00ff00
        name = "Prise de Service"
        await user.add_roles(roleService)
    else:
        color = 0xff0000
        name = "Fin de Service"
        await user.remove_roles(roleService)
    if automatic == True:
        name = name + " (par la Centrale)"

    embedVar = discord.Embed(description = user.display_name, color=color)
    embedVar.timestamp = datetime.utcnow()
    embedVar.set_author(name=name, icon_url="https://cdn.discordapp.com/attachments/637303563701321728/692506630499336192/lsms_sceau_1.png")
    await channelPDS.send(embed=embedVar)

    await setRichPresence()
    
async def setDispatch(user, dispatch = False, automatic = False):
    if dispatch == True:
        name = "Prise de Dispatch"
        await user.add_roles(roleDispatch)
    else:
        name = "Dispatch Relaché"
        await user.remove_roles(roleDispatch)
    if automatic == True:
        name = name + " (par la Centrale)"

    embedVar = discord.Embed(description = user.display_name, color=12370112)
    embedVar.set_author(name=name, icon_url="https://cdn.discordapp.com/attachments/637303563701321728/692506630499336192/lsms_sceau_1.png")
    embedVar.timestamp = datetime.utcnow()
    await channelPDS.send(embed=embedVar)
    
async def setRichPresence():
    count = 0
    for member in channelPDS.guild.members:
        if roleService in member.roles:
            count = count + 1            
    activity = discord.Activity(type = discord.ActivityType.watching, name = str(count) + " en service")
    await client.change_presence(activity=activity)
    
async def updateImage(beds):
    global message_head
         
    with io.BytesIO() as image_binary:
        image = Image.open("salles.png")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(fontFile, 45)     
        for bed in beds:
            if(bed.bed == '0' or bed.bed == "1" or bed.bed == "8" or bed.bed == "9"):
                txt=Image.new('RGBA', (500,100), (0, 0, 0, 0))
                d = ImageDraw.Draw(txt)
                d.text( (0, 0), bed.patient.replace(" ", "\n"), fill='white', font=font, stroke_width=1, stroke_fill='black')
                foreground = txt.rotate(90,  expand=1)
                image.paste(foreground, (loc[bed.bed][0],-500+loc[bed.bed][1]), foreground)
            else:
                draw.text(loc[bed.bed], bed.patient.replace(" ", "\n"), fill='white', font=font, stroke_width=1, stroke_fill='black')
            if(bed.lspd == True):
                draw.ellipse((loc[bed.bed][0]-10, loc[bed.bed][1]-10, loc[bed.bed][0]+10, loc[bed.bed][1]+10), fill=(255, 0, 0), outline=(0, 0, 0))
        
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        try:
            await message_head.delete()
        except AttributeError:
            pass

        message_head = await client.get_channel(channelHome).send(file=discord.File(fp=image_binary, filename='lit.png'))
        for bed in beds:
            try:
                await message_head.add_reaction(getReactionByNumber(bed.bed))
            except discord.errors.NotFound:
                pass

async def background_task():
    global radioLSMS
    global radioLSPD
    global radioEvent

    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(50)
        if(PDSEnabled):
            await setRichPresence()
            now = datetime.now().time()
            if(now.hour == 6 and now.minute == 0):            
                for member in channelPDS.guild.members:
                    if roleService in member.roles:
                        await setService(member, False, True)
                    if roleDispatch in member.roles:
                        await setDispatch(member, False, True)
                await message_dispatch.clear_reactions()
                await message_dispatch.add_reaction("🚑")
                await message_dispatch.add_reaction("📱")
                radioLSMS = 000.0
                radioLSPD = 000.0
                radioEvent = False
                await updateRadio()

def getReactionByNumber(number):
    return str(number) + "\u20E3"

@client.event
async def on_ready():
    global message_dispatch
    global beds
    global roleService
    global roleDispatch
    global roleAdmin
    global channelPDS
    global channel
    
    print(f'{client.user} has connected to Discord!')

    if(BedsEnabled or PDSEnabled or AdminCommandsEnable):
        channel = client.get_channel(channelHome)
        await channel.purge()
    if(PDSEnabled):
        channelPDS = client.get_channel(channelIdPDS)
        roleService = channel.guild.get_role(roleIdService)
        roleDispatch = channel.guild.get_role(roleIdDispatch)
        activity = discord.Activity(type = discord.ActivityType.watching, name = "0 en service")
        await client.change_presence(activity=activity)
    if(AdminCommandsEnable):
        roleAdmin = []
        tempList  = roleIdAdmin.split(',')
        for tempRole in tempList:
            roleAdmin.append(channel.guild.get_role(int(tempRole)))

    if(PDSEnabled):
        await updateRadio()
    if(BedsEnabled):
        with open(databaseFile) as json_file:
            data = json.load(json_file)
            beds = []
            for bed in data:
                info = InfoBed(data[bed]["patient"], bed, data[bed]["lspd"])
                beds.append(info)
            await updateImage(beds)

def SaveToFile():
    global beds
    
    data = {}
    for bed in beds:
        data[bed.bed] = {}
        data[bed.bed]["patient"] = bed.patient
        data[bed.bed]["lspd"] = bed.lspd
    
    with open(databaseFile, 'w') as outfile:
        json.dump(data, outfile)

@atexit.register
def goodbye():
    if(BedsEnabled):
        SaveToFile()
    
@client.event
async def on_disconnect():
    if(BedsEnabled):
        SaveToFile()

@client.event
async def on_message(message):
    global messagesBeds
    global beds
    global radioLSMS
    global radioLSPD
    global radioEvent
    
    if message.author == client.user:
        return
    
    home = False
    if message.channel.id == channelHome:
        await message.delete()
        home = True
    
    admin = False
    for tempRole in roleAdmin:
        if tempRole in message.author.roles:
            admin = True
    
    if home and BedsEnabled and message.content.startswith("!lit ") == True:
        response = message.content[5:].strip()
        temp = await message.channel.send(response)
        tempMessage = MessageBed(temp)
        messagesBeds.append(tempMessage)
        try:
            await temp.add_reaction("🗑️")
            loc = []
            for bed in beds:
                loc.append(bed.bed)
            for x in range(0,10):
                if not str(x) in loc:
                    await temp.add_reaction(getReactionByNumber(x))
            await temp.add_reaction("👮")
            await temp.add_reaction("✅")
            await asyncio.sleep(30)
            await temp.delete()
            messagesBeds.remove(tempMessage)
        except discord.errors.NotFound:
            pass
    elif home and PDSEnabled and message.content.startswith("!LSMS ") == True:
        radioLSMS = message.content[6:].strip()
        await updateRadio()
    elif home and PDSEnabled and message.content.startswith("!LSPD ") == True:
        radioLSPD = message.content[6:].strip()
        await updateRadio()
    elif home and PDSEnabled and message.content.startswith("!Event") == True:
        radioEvent = message.content[6:].strip()
        print(radioEvent)
        if(radioEvent == ""):
            radioEvent = False
        await updateRadio()
    elif home and FormationEnabled and admin and message.content.startswith("!new ") == True:
        category = discord.utils.get(message.channel.guild.categories, id=formationChannel)
        now = datetime.now()
        current_time = now.strftime("%d/%m/%Y")
        temp = await message.channel.guild.create_text_channel(message.content[5:].strip(), category = category, topic = "RENTRÉ AU LSMS LE : " + current_time)        
        embedVar = discord.Embed(description = "FORMATION PRINCIPALE", color=15158332)
        await temp.send(embed=embedVar)
        await temp.send(" - Appel coma")
        await temp.send(" - Conduite d'urgence")
        await temp.send(" - Don du sang")
        await temp.send(" - Gestion des unités X")
        await temp.send(" - Parachute / Rappel")
        await temp.send(" - Natation / Plongée")
        await temp.send(" - Opérations")
        await temp.send(" - Pompier")
        await temp.send(" - Soin des maladies")
        embedVar = discord.Embed(description = "FORMATION SECONDAIRE", color=12745742)
        await temp.send(embed=embedVar)
        await temp.send(" - Conduite sur terrain accidenté")
        await temp.send(" - Diplôme")
        await temp.send(" - Exercice Hélico niveau 0")
        await temp.send(" - Obtention du permis port d'arme")
        await temp.send(" - Procédure fédérale")
        await temp.send(" - Rédaction de rapport")
        await temp.send(" - Visite médicale")
        embedVar = discord.Embed(description = "FORMATION SUPPLEMENTAIRES", color=0)
        await temp.send(embed=embedVar)
        await temp.send(" - Intégrité")
        await temp.send(" - Permis voiture")
        await temp.send(" - Permis poids lourd")
        await temp.send(" - Permis moto")
        await temp.send(" - A déjà piloté un hélicopère")
        await temp.send(" - Licence hélicoptère")
    elif not home and admin and message.content.startswith("!del ") == True:
        try:
            number = int(message.content[5:].strip())
            mgs = []
            await message.delete()
            async for singleMessage in message.channel.history(limit=number):
                mgs.append(singleMessage) 
            await message.channel.delete_messages(mgs) 
        except ValueError:
            pass

async def removeBed(slot):
    for bed in beds:
        if(bed.bed == str(slot)):
            beds.remove(bed)
            await updateImage(beds)

@client.event
async def on_reaction_remove(reaction, user):
    global message_dispatch
    
    if(user == reaction.message.author):
        return   
    if reaction.message.channel.id != channelHome:
        return
    
    if(PDSEnabled):
        if(reaction.message.id == message_dispatch.id):
            if(reaction.emoji == "🚑"):
                await setService(user, False)
            elif(reaction.emoji == "📱"):
                await setDispatch(user, False)
   
@client.event
async def on_reaction_add(reaction, user):
    global messagesBeds
    global message_head
    global message_dispatch
    global beds
    
    if(user == reaction.message.author):
        return   
    if reaction.message.channel.id != channelHome:
        return

    if(BedsEnabled and reaction.message.id == message_head.id):
        if(reaction.emoji == "0\u20E3"):
            await removeBed(0)
        elif(reaction.emoji == "1\u20E3"):
            await removeBed(1)
        elif(reaction.emoji == "2\u20E3"):
            await removeBed(2)
        elif(reaction.emoji == "3\u20E3"):
            await removeBed(3)
        elif(reaction.emoji == "4\u20E3"):
            await removeBed(4)
        elif(reaction.emoji == "5\u20E3"):
            await removeBed(5)
        elif(reaction.emoji == "6\u20E3"):
            await removeBed(6)
        elif(reaction.emoji == "7\u20E3"):
            await removeBed(7)
        elif(reaction.emoji == "8\u20E3"):
            await removeBed(8)
        elif(reaction.emoji == "9\u20E3"):
            await removeBed(9)
        return
    elif(PDSEnabled and reaction.message.id == message_dispatch.id):
        if(reaction.emoji == "🚑"):
            await setService(user, True)
        elif(reaction.emoji == "📱"):
            await setDispatch(user, True)
        return

    if(BedsEnabled):
        for message in messagesBeds:
            if(message.message.id == reaction.message.id):
                if(reaction.emoji == "✅"):
                    await reaction.message.delete()
                    if(message.bed != -1):
                        info = InfoBed(message.message.content, str(message.bed), message.lspd)
                        found = False
                        for bed in beds:
                            if(bed.bed == str(message.bed)):
                                found = True
                        if(not found):
                            loc = 0
                            for bed in beds:
                                if int(bed.bed) < message.bed:
                                    loc = loc + 1
                            beds.insert(loc, info)
                            await updateImage(beds)
                    messagesBeds.remove(message)
                elif(reaction.emoji == "🗑️"):
                    await reaction.message.delete()
                    messagesBeds.remove(message)
                elif(reaction.emoji == "0\u20E3"):
                    message.bed = 0
                elif(reaction.emoji == "1\u20E3"):
                    message.bed = 1
                elif(reaction.emoji == "2\u20E3"):
                    message.bed = 2
                elif(reaction.emoji == "3\u20E3"):
                    message.bed = 3
                elif(reaction.emoji == "4\u20E3"):
                    message.bed = 4
                elif(reaction.emoji == "5\u20E3"):
                    message.bed = 5
                elif(reaction.emoji == "6\u20E3"):
                    message.bed = 6
                elif(reaction.emoji == "7\u20E3"):
                    message.bed = 7
                elif(reaction.emoji == "8\u20E3"):
                    message.bed = 8
                elif(reaction.emoji == "9\u20E3"):
                    message.bed = 9
                elif(reaction.emoji == "👮"):
                    message.lspd = True
                    
client.loop.create_task(background_task())
client.run(TOKEN)
