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

DB_BED = "data.json"
DB_RADIO = "radio.json"

IMG_LSMS_SCEAU = "https://cdn.discordapp.com/attachments/637303563701321728/692506630499336192/lsms_sceau_1.png"
IMG_RADIO = "https://i.postimg.cc/qRmhx1qR/radio.png"

COLOR_RED = 15158332
COLOR_GREEN = 0x00ff00
COLOR_LIGHT_GREY = 12370112
COLOR_DARK_GOLD = 12745742
COLOR_DEFAULT = 0

ARRAY_BEDS = {}
ARRAY_BEDS['0'] = (110, 260)
ARRAY_BEDS['1'] = (470, 260)
ARRAY_BEDS['2'] = (95, 325)
ARRAY_BEDS['3'] = (410, 325)
ARRAY_BEDS['4'] = (95, 470)
ARRAY_BEDS['5'] = (410, 470)
ARRAY_BEDS['6'] = (95, 610)
ARRAY_BEDS['7'] = (410, 610)
ARRAY_BEDS['8'] = (710, 550)
ARRAY_BEDS['9'] = (970, 550)
        
class Bot(discord.Client):
    PDSEnabled = True
    BedsEnabled = True
    FormationEnabled = True
    AdminCommandsEnabled = True
    RDVEnabled = True

    message_head = 0
    message_dispatch = 0
    channelPDS = 0
    messagesBeds = []

    radioLSMS = 000.0
    radioLSPD = 000.0
    radioEvent = False
    beds = []

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.channelIdHome = int(config['Channel']['Home'])
        self.channelIdPDS = int(config['Channel']['PDS'])
        if self.RDVEnabled:
            self.channelIdRDVChir = int(config['Channel']['RDVChirurgie'])
            self.channelIdRDVChirArchive = int(config['Channel']['RDVChirurgieArchive'])
            self.channelIdRDVPsy = int(config['Channel']['RDVPsy'])
            self.channelIdRDVPsyArchive = int(config['Channel']['RDVPsyArchive'])
            self.channelIdRDVF1S = int(config['Channel']['RDVF1S'])
            self.channelIdRDVF1SArchive = int(config['Channel']['RDVF1SArchive'])
        self.roleIdService = int(config['Role']['Service'])
        self.roleIdDispatch = int(config['Role']['Dispatch'])
        self.roleIdAdmin = config['Role']['Admin']
        self.formationChannel = int(config['Section']['Formation'])
        token = config['Discord']['Token']
        
        self.client = discord.Client()
        
        self.on_ready = self.client.event(self.on_ready)
        self.on_disconnect = self.client.event(self.on_disconnect)
        self.on_message = self.client.event(self.on_message)
        self.on_raw_reaction_add = self.client.event(self.on_raw_reaction_add)
        self.on_raw_reaction_remove = self.client.event(self.on_raw_reaction_remove)

        self.client.loop.create_task(self.background_task())
        self.client.run(token)

    async def background_task(self):
        await self.client.wait_until_ready()
        while not self.client.is_closed():
            await asyncio.sleep(50)
            now = datetime.now().time()
            if(self.PDSEnabled):
                await self.setRichPresence()
                if(now.hour == 6 and now.minute == 0):            
                    for member in self.channelPDS.guild.members:
                        if self.roleService in member.roles:
                            await self.setService(member, False, True)
                        if self.roleDispatch in member.roles:
                            await self.setDispatch(member, False, True)
                    await self.message_dispatch.clear_reactions()
                    await self.message_dispatch.add_reaction("🚑")
                    await self.message_dispatch.add_reaction("📱")
                    self.radioLSMS = 000.0
                    self.radioLSPD = 000.0
                    self.radioEvent = False
                    data = {}
                    with open(DB_RADIO, 'w') as outfile:
                        json.dump(data, outfile)
                    await self.updateRadio()
            if(self.BedsEnabled):
                if(now.hour == 6 and now.minute == 0):
                    self.SaveToFile()

    async def on_disconnect(self):
        self.SaveToFile()

    async def on_message(self, message):
        if message.author == self.client.user:
            return
            
        if message.author.bot:
            return
        
        home = False
        if message.channel.id == self.channelIdHome:
            await message.delete()
            home = True
    
        admin = False
        for tempRole in self.roleAdmin:
            if tempRole in message.author.roles:
                admin = True
        
        if home and self.BedsEnabled and message.content.startswith("!lit "):
            response = message.content[5:].strip()
            temp = await message.channel.send(response)
            tempMessage = MessageBed(temp)
            self.messagesBeds.append(tempMessage)
            try:
                await temp.add_reaction("🗑️")
                temploc = []
                for bed in self.beds:
                    temploc.append(bed.bed)
                for x in range(0,10):
                    if not str(x) in temploc:
                        await temp.add_reaction(self.getReactionByNumber(x))
                await temp.add_reaction("👮")
                await temp.add_reaction("✅")
                await asyncio.sleep(30)
                await temp.delete()
                self.messagesBeds.remove(tempMessage)
            except discord.errors.NotFound:
                pass
        elif home and self.PDSEnabled and message.content.startswith("!LSMS "):
            self.radioLSMS = message.content[6:].strip()
            await self.updateRadio()
        elif home and self.PDSEnabled and message.content.startswith("!LSPD "):
            self.radioLSPD = message.content[6:].strip()
            await self.updateRadio()
        elif home and self.PDSEnabled and message.content.startswith("!Event"):
            self.radioEvent = message.content[6:].strip()
            if(self.radioEvent == ""):
                self.radioEvent = False
            await self.updateRadio()
        elif home and self.RDVEnabled and message.content.startswith("!rdv "):
            try:
                command = message.content[5:].strip().split("555")
                patient = command[0].strip()
                phone = "555" + command[1].split(" ", 1)[0].strip()
                reason = command[1].split(" ", 1)[1].strip()
        
                embedVar = discord.Embed(color=COLOR_GREEN)
                embedVar.set_author(name="Prise de RDV", icon_url=IMG_LSMS_SCEAU)
                embedVar.add_field(name="Patient", value=patient, inline=True)
                embedVar.add_field(name="Téléphone", value=phone, inline=True)
                embedVar.add_field(name="Raison", value=reason, inline=False)
                embedVar.set_footer(text=message.author.display_name)
                messageRDV = await message.channel.send(embed=embedVar)
                await messageRDV.add_reaction("🇨")
                await messageRDV.add_reaction("🇵")
                await messageRDV.add_reaction("🇫")
                #await messageRDV.add_reaction(self.emojiPsy)
                #await messageRDV.add_reaction(self.emojiChir)
                #await messageRDV.add_reaction(self.emojiF1S)
                await asyncio.sleep(30)
                await messageRDV.delete()
            except (discord.errors.NotFound, IndexError):
                pass
        elif home and self.FormationEnabled and admin and message.content.startswith("!new "):
            category = discord.utils.get(message.channel.guild.categories, id=self.formationChannel)
            now = datetime.now()
            current_time = now.strftime("%d/%m/%Y")
            temp = await message.channel.guild.create_text_channel(message.content[5:].strip(), category = category, topic = "RENTRÉ AU LSMS LE : " + current_time)        
            embedVar = discord.Embed(description = "FORMATION PRINCIPALE", color=COLOR_RED)
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
            embedVar = discord.Embed(description = "FORMATION SECONDAIRE", color=COLOR_DARK_GOLD)
            await temp.send(embed=embedVar)
            await temp.send(" - Conduite sur terrain accidenté")
            await temp.send(" - Diplôme")
            await temp.send(" - Exercice Hélico niveau 0")
            await temp.send(" - Obtention du permis port d'arme")
            await temp.send(" - Procédure fédérale")
            await temp.send(" - Rédaction de rapport")
            await temp.send(" - Visite médicale")
            embedVar = discord.Embed(description = "FORMATION SUPPLEMENTAIRES", color=COLOR_DEFAULT)
            await temp.send(embed=embedVar)
            await temp.send(" - Intégrité")
            await temp.send(" - Permis voiture")
            await temp.send(" - Permis poids lourd")
            await temp.send(" - Permis moto")
            await temp.send(" - A déjà piloté un hélicoptère")
            await temp.send(" - Licence hélicoptère")
        elif not home and admin and message.content.startswith("!del "):
            try:
                number = int(message.content[5:].strip())
                mgs = []
                await message.delete()
                async for singleMessage in message.channel.history(limit=number):
                    mgs.append(singleMessage) 
                await message.channel.delete_messages(mgs) 
            except ValueError:
                pass
        elif home and admin and message.content.startswith("!save"):
            self.SaveToFile()

    async def on_ready(self):
        print(str(self.client.user) + " has connected to Discord!")
    
        if(self.BedsEnabled or self.PDSEnabled or self.AdminCommandsEnabled):
            self.channelHome = self.client.get_channel(self.channelIdHome)
            await self.channelHome.purge()
        if(self.PDSEnabled):
            self.channelPDS = self.client.get_channel(self.channelIdPDS)
            self.roleService = self.channelHome.guild.get_role(self.roleIdService)
            self.roleDispatch = self.channelHome.guild.get_role(self.roleIdDispatch)
            activity = discord.Activity(type = discord.ActivityType.watching, name = "0 en service")
            await self.client.change_presence(activity=activity)
        if(self.RDVEnabled):
            self.channelRDVChir = self.client.get_channel(self.channelIdRDVChir)
            self.channelRDVChirArchive = self.client.get_channel(self.channelIdRDVChirArchive)
            self.channelRDVPsy = self.client.get_channel(self.channelIdRDVPsy)
            self.channelRDVPsyArchive = self.client.get_channel(self.channelIdRDVPsyArchive)
            self.channelRDVF1S = self.client.get_channel(self.channelIdRDVF1S)
            self.channelRDVF1SArchive = self.client.get_channel(self.channelIdRDVF1SArchive)
        if(self.AdminCommandsEnabled):
            self.roleAdmin = []
            tempList  = self.roleIdAdmin.split(',')
            for tempRole in tempList:
                self.roleAdmin.append(self.channelHome.guild.get_role(int(tempRole)))
    
        if(self.PDSEnabled):
            try:
                with open(DB_RADIO, 'r') as json_file:
                    data = json.load(json_file)
                    try:
                        self.radioLSMS = data["LSMS"]
                    except KeyError:
                        self.radioLSMS = 000.0
                    try:
                        self.radioLSPD = data["LSPD"]
                    except KeyError:
                        self.radioLSPD = 000.0
                    try:
                        self.radioEvent = data["Event"]
                    except KeyError:
                        self.radioEvent = False
            except (json.decoder.JSONDecodeError, FileNotFoundError):
                self.radioLSMS = 000.0
                self.radioLSPD = 000.0
                self.radioEvent = False
                
            await self.updateRadio()
        if(self.BedsEnabled):
            try:
                self.beds = []
                with open(DB_BED, 'r') as json_file:
                    data = json.load(json_file)
                    for bed in data:
                        info = InfoBed(data[bed]["patient"], bed, data[bed]["lspd"])
                        self.beds.append(info)
            except (json.decoder.JSONDecodeError, FileNotFoundError):
                pass
            await self.updateImage() 

    async def on_reaction_remove(self, reaction, user):
        if(user == reaction.message.author):
            return   
        if reaction.message.channel.id != self.channelIdHome:
            return
        
        if(self.PDSEnabled):
            if(reaction.message.id == self.message_dispatch.id):
                if(reaction.emoji == "🚑"):
                    await self.setService(user, False)
                elif(reaction.emoji == "📱"):
                    await self.setDispatch(user, False)
                    
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id != self.channelIdHome:
            return
        
        try:
            guild = self.client.get_guild(payload.guild_id)
            user = guild.get_member(payload.user_id)
            
            if user == self.client.user:
                return
        
            if(self.PDSEnabled):
                if(payload.message_id == self.message_dispatch.id):
                    if(payload.emoji.name == "🚑"):
                        await self.setService(user, False)
                    elif(payload.emoji.name == "📱"):
                        await self.setDispatch(user, False)
                        
        except discord.errors.NotFound:
            pass

    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != self.channelIdHome and payload.channel_id != self.channelIdRDVChir and payload.channel_id != self.channelIdRDVPsy and payload.channel_id != self.channelIdRDVF1S:
            return
    
        try:
            guild = self.client.get_guild(payload.guild_id)
            user = guild.get_member(payload.user_id)
            
            if user == self.client.user:
                return
        
            channel = self.client.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if(self.BedsEnabled and payload.message_id == self.message_head.id):
                if(payload.emoji.name == "0\u20E3"):
                    await self.removeBed(0)
                elif(payload.emoji.name == "1\u20E3"):
                    await self.removeBed(1)
                elif(payload.emoji.name == "2\u20E3"):
                    await self.removeBed(2)
                elif(payload.emoji.name == "3\u20E3"):
                    await self.removeBed(3)
                elif(payload.emoji.name == "4\u20E3"):
                    await self.removeBed(4)
                elif(payload.emoji.name == "5\u20E3"):
                    await self.removeBed(5)
                elif(payload.emoji.name == "6\u20E3"):
                    await self.removeBed(6)
                elif(payload.emoji.name == "7\u20E3"):
                    await self.removeBed(7)
                elif(payload.emoji.name == "8\u20E3"):
                    await self.removeBed(8)
                elif(payload.emoji.name == "9\u20E3"):
                    await self.removeBed(9)
                return
            elif(self.PDSEnabled and payload.message_id == self.message_dispatch.id):
                if(payload.emoji.name == "🚑"):
                    await self.setService(user, True)
                elif(payload.emoji.name == "📱"):
                    await self.setDispatch(user, True)
                return
            elif(self.RDVEnabled and payload.channel_id == self.channelIdHome):
                if(payload.emoji.name == "🇵"):
                    await self.channelRDVPsy.send(embed=message.embeds[0])
                    await message.delete()
                elif(payload.emoji.name == "🇨"):
                    await self.channelRDVChir.send(embed=message.embeds[0])
                    await message.delete()
                elif(payload.emoji.name == "🇫"):
                    await self.channelRDVF1S.send(embed=message.embeds[0])
                    await message.delete()
            elif(self.RDVEnabled and payload.channel_id == self.channelIdRDVChir):
                if(payload.emoji.name == "✅"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    await self.channelRDVChirArchive.send(embed=embedVar)
                    await message.delete()
                elif(payload.emoji.name == "❌"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    embedVar.color=COLOR_RED
                    await self.channelRDVChirArchive.send(embed=embedVar)
                    await message.delete()
                return
            elif(self.RDVEnabled and payload.channel_id == self.channelIdRDVPsy):
                if(payload.emoji.name == "✅"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    await self.channelRDVPsyArchive.send(embed=embedVar)
                    await message.delete()
                elif(payload.emoji.name == "❌"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    embedVar.color=COLOR_RED
                    await self.channelRDVPsyArchive.send(embed=embedVar)
                    await message.delete()
                return
            elif(self.RDVEnabled and payload.channel_id == self.channelIdRDVF1S):
                if(payload.emoji.name == "✅"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    await self.channelRDVF1SArchive.send(embed=embedVar)
                    await message.delete()
                elif(payload.emoji.name == "❌"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    embedVar.color=COLOR_RED
                    await self.channelRDVF1SArchive.send(embed=embedVar)
                    await message.delete()
                return
        
            if(self.BedsEnabled):
                for messageBed in self.messagesBeds:
                    if(messageBed.message.id == payload.message_id):
                        if(payload.emoji.name == "✅"):
                            await message.delete()
                            if(messageBed.bed != -1):
                                info = InfoBed(messageBed.message.content, str(messageBed.bed), messageBed.lspd)
                                found = False
                                for bed in self.beds:
                                    if(bed.bed == str(messageBed.bed)):
                                        found = True
                                if(not found):
                                    tempindex = 0
                                    for bed in self.beds:
                                        if int(bed.bed) < messageBed.bed:
                                            tempindex = tempindex + 1
                                    self.beds.insert(tempindex, info)
                                    await self.updateImage()
                            self.messagesBeds.remove(messageBed)
                        elif(payload.emoji.name == "🗑️"):
                            await message.delete()
                            self.messagesBeds.remove(messageBed)
                        elif(payload.emoji.name == "0\u20E3"):
                            messageBed.bed = 0
                        elif(payload.emoji.name == "1\u20E3"):
                            messageBed.bed = 1
                        elif(payload.emoji.name == "2\u20E3"):
                            messageBed.bed = 2
                        elif(payload.emoji.name == "3\u20E3"):
                            messageBed.bed = 3
                        elif(payload.emoji.name == "4\u20E3"):
                            messageBed.bed = 4
                        elif(payload.emoji.name == "5\u20E3"):
                            messageBed.bed = 5
                        elif(payload.emoji.name == "6\u20E3"):
                            messageBed.bed = 6
                        elif(payload.emoji.name == "7\u20E3"):
                            messageBed.bed = 7
                        elif(payload.emoji.name == "8\u20E3"):
                            messageBed.bed = 8
                        elif(payload.emoji.name == "9\u20E3"):
                            messageBed.bed = 9
                        elif(payload.emoji.name == "👮"):
                            messageBed.lspd = True
        except discord.errors.NotFound:
            pass
    
    async def updateRadio(self):
        embedVar = discord.Embed(color=COLOR_GREEN)
        embedVar.set_author(name="Gestion des Prises de Service", icon_url=IMG_LSMS_SCEAU)
        embedVar.set_thumbnail(url = IMG_RADIO)
        embedVar.add_field(name="💉", value=self.radioLSMS, inline=True)
        embedVar.add_field(name="👮", value=self.radioLSPD, inline=True)
        if(self.radioEvent != False):
            embedVar.add_field(name="🏆", value=self.radioEvent, inline=True)
        if self.message_dispatch == 0:
            self.message_dispatch = await self.channelHome.send(embed=embedVar)
            await self.message_dispatch.add_reaction("🚑")
            await self.message_dispatch.add_reaction("📱")
        else:
            await self.message_dispatch.edit(embed=embedVar)
    
    async def setService(self, user, service = True, automatic = False):
        if service:
            color = COLOR_GREEN
            name = "Prise de Service"
            await user.add_roles(self.roleService)
        else:
            color = COLOR_RED
            name = "Fin de Service"
            await user.remove_roles(self.roleService)
        if automatic:
            name = name + " (par la Centrale)"
    
        embedVar = discord.Embed(description = user.display_name, color=color)
        embedVar.timestamp = datetime.utcnow()
        embedVar.set_author(name=name, icon_url=IMG_LSMS_SCEAU)
        await self.channelPDS.send(embed=embedVar)
    
        await self.setRichPresence()

    async def setDispatch(self, user, dispatch = False, automatic = False):
        if dispatch:
            name = "Prise de Dispatch"
            await user.add_roles(self.roleDispatch)
        else:
            name = "Dispatch Relaché"
            await user.remove_roles(self.roleDispatch)
        if automatic:
            name = name + " (par la Centrale)"
    
        embedVar = discord.Embed(description = user.display_name, color=COLOR_LIGHT_GREY)
        embedVar.set_author(name=name, icon_url=IMG_LSMS_SCEAU)
        embedVar.timestamp = datetime.utcnow()
        await self.channelPDS.send(embed=embedVar)

    async def setRichPresence(self):
        count = 0
        for member in self.channelPDS.guild.members:
            if self.roleService in member.roles:
                count = count + 1            
        activity = discord.Activity(type = discord.ActivityType.watching, name = str(count) + " en service")
        await self.client.change_presence(activity=activity)

    async def updateImage(self):
        with io.BytesIO() as image_binary:
            image = Image.open("salles.png")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("Calibri Regular.ttf", 45)     
            for bed in self.beds:
                if(bed.bed == '0' or bed.bed == "1" or bed.bed == "8" or bed.bed == "9"):
                    txt=Image.new('RGBA', (500,100), (0, 0, 0, 0))
                    d = ImageDraw.Draw(txt)
                    d.text( (0, 0), bed.patient.replace(" ", "\n", 1), fill='white', font=font, stroke_width=1, stroke_fill='black')
                    foreground = txt.rotate(90,  expand=1)
                    image.paste(foreground, (ARRAY_BEDS[bed.bed][0],-500+ARRAY_BEDS[bed.bed][1]), foreground)
                else:
                    draw.text(ARRAY_BEDS[bed.bed], bed.patient.replace(" ", "\n", 1), fill='white', font=font, stroke_width=1, stroke_fill='black')
                if(bed.lspd):
                    draw.ellipse((ARRAY_BEDS[bed.bed][0]-10, ARRAY_BEDS[bed.bed][1]-10, ARRAY_BEDS[bed.bed][0]+10, ARRAY_BEDS[bed.bed][1]+10), fill=(255, 0, 0), outline=(0, 0, 0))
            
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            try:
                await self.message_head.delete()
            except AttributeError:
                pass
    
            self.message_head = await self.client.get_channel(self.channelIdHome).send(file=discord.File(fp=image_binary, filename='lit.png'))
            for bed in self.beds:
                try:
                    await self.message_head.add_reaction(self.getReactionByNumber(bed.bed))
                except discord.errors.NotFound:
                    pass

    def getReactionByNumber(self, number):
        return str(number) + "\u20E3"

    async def removeBed(self, slot):
        for bed in self.beds:
            if(bed.bed == str(slot)):
                self.beds.remove(bed)
                await self.updateImage()

    def SaveToFile(self):
        if self.BedsEnabled:
            data = {}
            for bed in self.beds:
                data[bed.bed] = {}
                data[bed.bed]["patient"] = bed.patient
                data[bed.bed]["lspd"] = bed.lspd    
            with open(DB_BED, 'w') as outfile:
                json.dump(data, outfile)
                
        if self.PDSEnabled:
            data = {}
            data["LSMS"] = self.radioLSMS
            data["LSPD"] = self.radioLSPD
            data["Event"] = self.radioEvent
            with open(DB_RADIO, 'w') as outfile:
                json.dump(data, outfile)

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

bot = Bot()

    
@atexit.register
def goodbye():
    bot.SaveToFile()
