# bot.py

import discord
import discord_slash
from discord_slash import SlashCommand
from discord_slash import SlashContext

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
ARRAY_BEDS[0] = (1020, 580)
ARRAY_BEDS[1] = (1020, 390)
ARRAY_BEDS[2] = (1020, 205)
ARRAY_BEDS[3] = (1020, 25)
ARRAY_BEDS[4] = (720, 25)
ARRAY_BEDS[5] = (720, 205)
ARRAY_BEDS[6] = (720, 390)
ARRAY_BEDS[7] = (720, 580)
ARRAY_BEDS[8] = (385, 580)
ARRAY_BEDS[9] = (385, 390)
ARRAY_BEDS[10] = (385, 205)
ARRAY_BEDS[11] = (385, 25)
ARRAY_BEDS[12] = (90, 25)
ARRAY_BEDS[13] = (90, 205)
ARRAY_BEDS[14] = (90, 390)
ARRAY_BEDS[15] = (90, 580)
ARRAY_BEDS[16] = (1310,410)
ARRAY_BEDS[17] = (1665, 410)

slash = None
guild_ids = []    
    
class Bot(discord.Client):
    PDSEnabled = True
    BedsEnabled = True
    FormationEnabled = True
    AdminCommandsEnabled = True
    RDVEnabled = True

    message_head = 0
    message_dispatch = 0
    channelPDS = 0

    radioLSMS = 000.0
    radioLSPD = 000.0
    radioBCMS = 0
    radioEvent = 0
    beds = []

    def __init__(self):
        global slash
        global guild_ids
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.channelIdHome = int(config['Channel']['Home'])
        self.channelIdPDS = int(config['Channel']['PDS'])
        if self.RDVEnabled:
            self.channelIdRDVChir = int(config['Channel']['RDVChirurgie'])
#           self.channelIdRDVChirArchive = int(config['Channel']['RDVChirurgieArchive'])
            self.channelIdRDVPsy = int(config['Channel']['RDVPsy'])
#           self.channelIdRDVPsyArchive = int(config['Channel']['RDVPsyArchive'])
#           self.channelIdRDVF1S = int(config['Channel']['RDVF1S'])
#           self.channelIdRDVF1SArchive = int(config['Channel']['RDVF1SArchive'])
        self.roleIdService = int(config['Role']['Service'])
        self.roleIdDispatch = int(config['Role']['Dispatch'])
        self.roleIdAstreinte = int(config['Role']['Astreinte'])
        self.roleIdAdmin = config['Role']['Admin']
        self.roleIdFichePatient = config['Role']['FichePatient']
        self.roleIdLSMS = int(config['Role']['LSMS'])
        self.formationChannel = int(config['Section']['Formation'])
        self.token = config['Discord']['Token']
        guild_ids = []
        tempList  = config['Discord']['GuildID'].split(',')
        for tempid in tempList:
            guild_ids.append((int(tempid)))
                
        intents = discord.Intents.all()
        self.client = discord.Client(intents=intents)       
        slash = SlashCommand(self.client, sync_commands=True)
       
        self.on_ready = self.client.event(self.on_ready)
        self.on_disconnect = self.client.event(self.on_disconnect)
        self.on_message = self.client.event(self.on_message)
        self.on_raw_reaction_add = self.client.event(self.on_raw_reaction_add)
        self.on_raw_reaction_remove = self.client.event(self.on_raw_reaction_remove)

        self.client.loop.create_task(self.background_task())
           
    async def background_task(self):
        await self.client.wait_until_ready()
        while not self.client.is_closed():
            await asyncio.sleep(50)
            now = datetime.now().time()
            if(self.PDSEnabled):
                await self.setRichPresence()
                if(now.hour == 5 and now.minute == 59):            
                    for member in self.channelPDS.guild.members:
                        if self.roleService in member.roles:
                            await self.setService(member, False, True)
                        if self.roleDispatch in member.roles:
                            await self.setDispatch(member, False, True)
                        if self.roleAstreinte in member.roles:
                            await self.setAstreinte(member, False, True)
                    await self.message_dispatch.clear_reactions()
                    await self.message_dispatch.add_reaction("🚑")
                    await self.message_dispatch.add_reaction("📱")
                    await self.message_dispatch.add_reaction("🎙️")
                    self.radioLSMS = 000.0
                    self.radioLSPD = 000.0
                    self.radioBCMS = 0
                    self.radioEvent = 0
                    data = {}
                    with open(DB_RADIO, 'w') as outfile:
                        json.dump(data, outfile)
                    await self.updateRadio()
            if(self.BedsEnabled):
                if(now.hour == 5 and now.minute == 59):
                    self.SaveToFile()

    async def on_disconnect(self):
        self.SaveToFile()

    async def on_message(self, message):
        if message.author == self.client.user:
            return
            
        if message.author.bot:
            return
        
        if message.channel.id == self.channelIdHome:
            await message.delete()

    async def on_ready(self):
        print(str(self.client.user) + " has connected to Discord")
        print("Bot ID is " + str(self.client.user.id))

        if(self.BedsEnabled or self.PDSEnabled or self.AdminCommandsEnabled):
            self.channelHome = self.client.get_channel(self.channelIdHome)
            await self.channelHome.purge()
        if(self.PDSEnabled):
            self.channelPDS = self.client.get_channel(self.channelIdPDS)
            self.roleService = self.channelHome.guild.get_role(self.roleIdService)
            self.roleDispatch = self.channelHome.guild.get_role(self.roleIdDispatch)
            self.roleAstreinte = self.channelHome.guild.get_role(self.roleIdAstreinte)
            activity = discord.Activity(type = discord.ActivityType.watching, name = "🚑 0 | 📱 0")
            await self.client.change_presence(activity=activity)
        if(self.RDVEnabled):
            self.channelRDVChir = self.client.get_channel(self.channelIdRDVChir)
#           self.channelRDVChirArchive = self.client.get_channel(self.channelIdRDVChirArchive)
            self.channelRDVPsy = self.client.get_channel(self.channelIdRDVPsy)
#           self.channelRDVPsyArchive = self.client.get_channel(self.channelIdRDVPsyArchive)
#           self.channelRDVF1S = self.client.get_channel(self.channelIdRDVF1S)
#           self.channelRDVF1SArchive = self.client.get_channel(self.channelIdRDVF1SArchive)
        if(self.AdminCommandsEnabled):
            self.roleAdmin = []
            self.roleFichePatient = []
            tempList  = self.roleIdAdmin.split(',')
            for tempRole in tempList:
                self.roleAdmin.append(self.channelHome.guild.get_role(int(tempRole)))
                self.roleFichePatient.append(self.channelHome.guild.get_role(int(tempRole)))
            tempList  = self.roleIdFichePatient.split(',')
            for tempRole in tempList:
                self.roleFichePatient.append(self.channelHome.guild.get_role(int(tempRole)))
        self.roleLSMS = self.channelHome.guild.get_role(self.roleIdLSMS)

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
                        self.radioBCMS = data["BCMS"]
                    except KeyError:
                        self.radioBCMS = 0
                    try:
                        self.radioEvent = data["Event"]
                    except KeyError:
                        self.radioEvent = 0
            except (json.decoder.JSONDecodeError, FileNotFoundError):
                self.radioLSMS = 000.0
                self.radioLSPD = 000.0
                self.radioBCMS = 0
                self.radioEvent = 0
                
            await self.updateRadio()
        if(self.BedsEnabled):
            try:
                self.beds = []
                with open(DB_BED, 'r') as json_file:
                    data = json.load(json_file)
                    for bed in data:
                        info = InfoBed(data[bed]["patient"], int(bed), data[bed]["lspd"])
                        self.beds.append(info)
            except (json.decoder.JSONDecodeError, FileNotFoundError):
                pass
            await self.updateImage() 
            
        print(str(self.client.user) + " is now ready!")
                  
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
                        await self.setAstreinte(user, False)
                    elif(payload.emoji.name == "🎙️"):
                        await self.setDispatch(user, False)
                        
        except discord.errors.NotFound:
            pass

    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != self.channelIdHome and payload.channel_id != self.channelIdRDVChir and payload.channel_id != self.channelIdRDVPsy: #and payload.channel_id != self.channelIdRDVF1S:
            return
    
        try:
            guild = self.client.get_guild(payload.guild_id)
            user = guild.get_member(payload.user_id)
            
            if user == self.client.user:
                return
        
            channel = self.client.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if(self.BedsEnabled and payload.message_id == self.message_head.id):
                if(payload.emoji.name == "🇦"):
                    await self.removeBed(0)
                elif(payload.emoji.name == "🇧"):
                    await self.removeBed(1)
                elif(payload.emoji.name == "🇨"):
                    await self.removeBed(2)
                elif(payload.emoji.name == "🇩"):
                    await self.removeBed(3)
                elif(payload.emoji.name == "🇪"):
                    await self.removeBed(4)
                elif(payload.emoji.name == "🇫"):
                    await self.removeBed(5)
                elif(payload.emoji.name == "🇬"):
                    await self.removeBed(6)
                elif(payload.emoji.name == "🇭"):
                    await self.removeBed(7)
                elif(payload.emoji.name == "🇮"):
                    await self.removeBed(8)
                elif(payload.emoji.name == "🇯"):
                    await self.removeBed(9)
                elif(payload.emoji.name == "🇰"):
                    await self.removeBed(10)
                elif(payload.emoji.name == "🇱"):
                    await self.removeBed(11)
                elif(payload.emoji.name == "🇲"):
                    await self.removeBed(12)
                elif(payload.emoji.name == "🇳"):
                    await self.removeBed(13)
                elif(payload.emoji.name == "🇴"):
                    await self.removeBed(14)
                elif(payload.emoji.name == "🇵"):
                    await self.removeBed(15)
                elif(payload.emoji.name == "🇶"):
                    await self.removeBed(16)
                elif(payload.emoji.name == "🇷"):
                    await self.removeBed(17)
                return
            elif(self.PDSEnabled and payload.message_id == self.message_dispatch.id):
                if(payload.emoji.name == "🚑"):
                    await self.setService(user, True)
                elif(payload.emoji.name == "📱"):
                    await self.setAstreinte(user, True)
                elif(payload.emoji.name == "🎙️"):
                    await self.setDispatch(user, True)
                return
            elif(self.RDVEnabled and payload.channel_id == self.channelIdRDVChir):
                if(payload.emoji.name == "✅"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    #await self.channelRDVChirArchive.send(embed=embedVar)
                    await message.delete()
                elif(payload.emoji.name == "❌"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    embedVar.color=COLOR_RED
                    #await self.channelRDVChirArchive.send(embed=embedVar)
                    await message.delete()
                return
            elif(self.RDVEnabled and payload.channel_id == self.channelIdRDVPsy):
                if(payload.emoji.name == "✅"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    #await self.channelRDVPsyArchive.send(embed=embedVar)
                    await message.delete()
                elif(payload.emoji.name == "❌"):
                    embedVar = message.embeds[0]
                    embedVar.set_footer(text=user.display_name)
                    embedVar.color=COLOR_RED
                    #await self.channelRDVPsyArchive.send(embed=embedVar)
                    await message.delete()
                return
            # elif(self.RDVEnabled and payload.channel_id == self.channelIdRDVF1S):
            #     if(payload.emoji.name == "✅"):
            #         embedVar = message.embeds[0]
            #         embedVar.set_footer(text=user.display_name)
            #         await self.channelRDVF1SArchive.send(embed=embedVar)
            #         await message.delete()
            #     elif(payload.emoji.name == "❌"):
            #         embedVar = message.embeds[0]
            #         embedVar.set_footer(text=user.display_name)
            #         embedVar.color=COLOR_RED
            #         await self.channelRDVF1SArchive.send(embed=embedVar)
            #         await message.delete()
            #    return
        
        except discord.errors.NotFound:
            pass

    async def NewMedic(self, context, name):
        category = discord.utils.get(context.guild.categories, id=self.formationChannel)
        now = datetime.now()
        current_time = now.strftime("%d/%m/%Y")
        temp = await context.guild.create_text_channel(name, category = category, topic = "RENTRÉ AU LSMS LE : " + current_time) 
        embedVar = discord.Embed(description = "INFORMATION GENERALES", color=COLOR_DEFAULT)
        await temp.send(embed=embedVar)
        await temp.send(" - Permis voiture")
        await temp.send(" - Permis poids lourd")
        await temp.send(" - Permis moto")
        await temp.send(" - Licence hélicoptère")
        await temp.send(" - A déjà piloté un hélicoptère")
        await temp.send(" - Permis de port d'arme")
        await temp.send(" - Conduite d'urgence")
        await temp.send(" - Intégrité")

        embedVar = discord.Embed(description = "FORMATION PRINCIPALE", color=COLOR_RED)
        await temp.send(embed=embedVar)
        await temp.send(" - Appel coma")
        await temp.send(" - Rédaction des rapports")
        await temp.send(" - Don du sang")
        await temp.send(" - Gestion des unités X")
        await temp.send(" - Parachute")
        await temp.send(" - Rappel")        
        await temp.send(" - Noyades")
        await temp.send(" - Opérations")
        await temp.send(" - Interventions Pompier")
        await temp.send(" - Bobologie")
        await temp.send(" - Visite médicale")
        embedVar = discord.Embed(description = "FORMATION SECONDAIRE", color=COLOR_RED)
        await temp.send(embed=embedVar)
        await temp.send(" - Premier service du jour")
        await temp.send(" - Conduite sur terrain accidenté")
        await temp.send(" - Exercice Hélico niveau 0")
        await temp.send(" - Visite médicale d'entrée en prison")
        await temp.send(" - Gestion des décès")
        await temp.send(" - Annoncer des situations difficiles")
        await temp.send(" - Communication radio")
        await temp.send(" - Secret médical")
        await temp.send(" - Psychologie légère")
        await temp.send(" - Dépendances")
        embedVar = discord.Embed(description = "FORMATION AVANCEE", color=0x0000ff)
        await temp.send(embed=embedVar)
        await temp.send(" - Terrain")
        await temp.send(" - Management")
        await temp.send(" - Enseignement")
        await temp.send(" - Spéciale")   
    
    async def AddRDV(self, patient, phone, category, medecine, reason, medic):
        embedVar = discord.Embed(color=COLOR_GREEN)
        embedVar.set_author(name="Prise de RDV", icon_url=IMG_LSMS_SCEAU)
        embedVar.add_field(name="Patient", value=patient, inline=True)
        embedVar.add_field(name="Téléphone", value=phone, inline=True)
        embedVar.add_field(name="Médecine Générale", value=medecine, inline=True)         
        embedVar.add_field(name="Raison", value=reason, inline=False)
        embedVar.set_footer(text=medic.display_name)        
        if(category == 1):
            await self.channelRDVPsy.send(embed=embedVar)
        elif(category == 2):
            await self.channelRDVChir.send(embed=embedVar)
        # elif(category == 3):
        #     await self.channelRDVF1S.send(embed=embedVar)        
    
    async def updateBed(self, infoBed):
        found = False
        for bed in self.beds:
            if(bed.bed == infoBed.bed):
                found = True
        if(not found):
            tempindex = 0
            for bed in self.beds:
                if int(bed.bed) < infoBed.bed:
                    tempindex = tempindex + 1
            self.beds.insert(tempindex, infoBed)
            await self.updateImage()
    
    async def updateRadio(self):
        embedVar = discord.Embed(color=COLOR_GREEN)
        embedVar.set_author(name="Gestion des Prises de Service", icon_url=IMG_LSMS_SCEAU)
        embedVar.set_thumbnail(url = IMG_RADIO)
        embedVar.add_field(name="💉", value=self.radioLSMS, inline=True)
        embedVar.add_field(name="👮", value=self.radioLSPD, inline=True)
#        embedVar.add_field(name="⛑️", value=self.radioBCMS, inline=True)
        if(self.radioBCMS != "0" and self.radioBCMS != 0):
            embedVar.add_field(name="⛑️", value=self.radioBCMS, inline=True)
        if(self.radioEvent != "0" and self.radioEvent != 0):
            embedVar.add_field(name="🏆", value=self.radioEvent, inline=True)
        if self.message_dispatch == 0:
            self.message_dispatch = await self.channelHome.send(embed=embedVar)
            await self.message_dispatch.add_reaction("🚑")
            await self.message_dispatch.add_reaction("📱")
            await self.message_dispatch.add_reaction("🎙️")
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
        
    async def setAstreinte(self, user, service = True, automatic = False):
        if service:
            color = COLOR_GREEN
            name = "En Astreinte"
            await user.add_roles(self.roleAstreinte)
        else:
            color = COLOR_RED
            name = "Fin de l'Astreinte"
            await user.remove_roles(self.roleAstreinte)
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
        countS = 0
        countD = 0
        for member in self.channelPDS.guild.members:
            if self.roleService in member.roles:
                countS = countS + 1
            if self.roleAstreinte in member.roles:
                countD = countD + 1
        activity = discord.Activity(type = discord.ActivityType.watching, name = "🚑 " + str(countS) + " | 📱 " + str(countD))
        await self.client.change_presence(activity=activity)

    async def updateImage(self):
        with io.BytesIO() as image_binary:
            image = Image.open("salles.png")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("Calibri Regular.ttf", 45)     
            for bed in self.beds:
                if(bed.lspd):
                    draw.ellipse((ARRAY_BEDS[bed.bed][0]-10, ARRAY_BEDS[bed.bed][1]-10, ARRAY_BEDS[bed.bed][0]+10, ARRAY_BEDS[bed.bed][1]+10), fill=(255, 0, 0), outline=(0, 0, 0))
                if(bed.bed == 16 or bed.bed == 17):
                    txt=Image.new('RGBA', (500,100), (0, 0, 0, 0))
                    d = ImageDraw.Draw(txt)
                    d.text( (0, 0), bed.patient.replace(" ", "\n", 1), fill='white', font=font, stroke_width=1, stroke_fill='black')
                    foreground = txt.rotate(90,  expand=1)
                    image.paste(foreground, (ARRAY_BEDS[bed.bed][0],-500+ARRAY_BEDS[bed.bed][1]), foreground)
                else:
                    draw.text(ARRAY_BEDS[bed.bed], bed.patient.replace(" ", "\n", 1), fill='white', font=font, stroke_width=1, stroke_fill='black')
            
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            try:
                await self.message_head.delete()
            except AttributeError:
                pass
    
            self.message_head = await self.client.get_channel(self.channelIdHome).send(file=discord.File(fp=image_binary, filename='lit.png'))
            for bed in self.beds:
                try:
                    if bed.bed == 0:
                        await self.message_head.add_reaction("🇦")
                    elif bed.bed == 1:
                        await self.message_head.add_reaction("🇧")
                    elif bed.bed == 2:
                        await self.message_head.add_reaction("🇨")
                    elif bed.bed == 3:
                        await self.message_head.add_reaction("🇩")
                    elif bed.bed == 4:
                        await self.message_head.add_reaction("🇪")
                    elif bed.bed == 5:
                        await self.message_head.add_reaction("🇫")
                    elif bed.bed == 6:
                        await self.message_head.add_reaction("🇬")
                    elif bed.bed == 7:
                        await self.message_head.add_reaction("🇭")
                    elif bed.bed == 8:
                        await self.message_head.add_reaction("🇮")
                    elif bed.bed == 9:
                        await self.message_head.add_reaction("🇯")
                    elif bed.bed == 10:
                        await self.message_head.add_reaction("🇰")
                    elif bed.bed == 11:
                        await self.message_head.add_reaction("🇱")
                    elif bed.bed == 12:
                        await self.message_head.add_reaction("🇲")                    
                    elif bed.bed == 13:
                        await self.message_head.add_reaction("🇳")
                    elif bed.bed == 14:
                        await self.message_head.add_reaction("🇴")
                    elif bed.bed == 15:
                        await self.message_head.add_reaction("🇵")
                    elif bed.bed == 16:
                        await self.message_head.add_reaction("🇶")
                    elif bed.bed == 17:
                        await self.message_head.add_reaction("🇷")

                except discord.errors.NotFound:
                    pass

    async def removeBed(self, slot):
        for bed in self.beds:
            if(bed.bed == slot):
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
            data["BCMS"] = self.radioBCMS
            data["Event"] = self.radioEvent
            with open(DB_RADIO, 'w') as outfile:
                json.dump(data, outfile)
                
    def Run(self):
        print("Starting bot ...")
        self.client.run(self.token)

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

@slash.slash(
    name="radio",
    description="Change les fréquences radio",
    options = [{
        "name": "organisme",
        "description": "Organisme pour lequel changer la fréquence radio",
        "type": 4,
        "required": True,
        "choices": [{
            "name": "1-LSMS",
            "value": 1
            },{
            "name": "2-LSPD",
            "value": 2
            },{
            "name": "3-BCMS",
            "value": 3
            },{
            "name": "4-Event",
            "value": 4}]
    },{
        "name": "frequence",
        "description": "Fréquence radio",
        "type": 3,
        "required": True
    }],
    guild_ids=guild_ids)
async def _radio(ctx: SlashContext, organisme: int, frequence: str):
    await ctx.defer(hidden=True)    
    authorized = False
    if bot.roleLSMS in ctx.author.roles:
        authorized = True
    for tempRole in bot.roleAdmin:
        if tempRole in ctx.author.roles:
           authorized = True

    if authorized:
        if(organisme == 1):
            bot.radioLSMS = frequence
        elif(organisme == 2):
            bot.radioLSPD = frequence
        elif(organisme == 3):
            bot.radioBCMS = frequence
        elif(organisme == 4):
            bot.radioEvent = frequence        
        await bot.updateRadio()
        await ctx.send(content="Modification des radios effectuée.", hidden=True)
    else:
        await ctx.send(content="Echec de la modification des radios !", hidden=True)

@slash.slash(
    name="lit",
    description="Place les patients sur les lits",
    options = [{
        "name": "nom",
        "description": "Prénom & Nom du patient",
        "type": 3,
        "required": True
    },{
        "name": "lettre",
        "description": "Lettre du lit",
        "type": 3,
        "required": True
    },{
        "name": "lspd",
        "description": "Surveillance LSPD/LSCS",
        "type": 4,
        "choices": [{
            "name": "Oui",
            "value": 1
            },{
            "name": "Non",
            "value": 0
            }]
    }],
    guild_ids=guild_ids)
async def _lit(ctx: SlashContext, nom: str, lettre: str, lspd: int=0):
    await ctx.defer(hidden=True)   
    authorized = False
    if bot.roleLSMS in ctx.author.roles:
        authorized = True
    for tempRole in bot.roleAdmin:
        if tempRole in ctx.author.roles:
           authorized = True

    if authorized:
        if lettre == "A":
            numero = 0
        elif lettre =="B":
            numero = 1
        elif lettre =="C":
            numero = 2
        elif lettre =="D":
            numero = 3
        elif lettre =="E":
            numero = 4
        elif lettre =="F":
            numero = 5
        elif lettre =="G":
            numero = 6
        elif lettre =="H":
            numero = 7
        elif lettre =="I":
            numero = 8
        elif lettre =="J":
            numero = 9
        elif lettre =="K":
            numero = 10
        elif lettre =="L":
            numero = 11
        elif lettre =="M":
            numero = 12
        elif lettre =="N":
            numero = 13
        elif lettre =="O":
            numero = 14
        elif lettre =="P":
            numero = 15
        elif lettre =="Q":
            numero = 16
        elif lettre =="R":
            numero = 17

        info = InfoBed(nom, numero, bool(lspd))
        await bot.updateBed(info)
        await ctx.send(content="Modification des lits effectuée.", hidden=True)
    else:    
        await ctx.send(content="Echec de la modification des lits !", hidden=True)

@slash.slash(
    name="save",
    description="[ADMIN] Sauvegarde avant reboot manuel",
    guild_ids=guild_ids)
async def _save(ctx: SlashContext):
    await ctx.defer(hidden=True)   
    authorized = False
    for tempRole in bot.roleAdmin:
        if tempRole in ctx.author.roles:
           authorized = True

    if authorized:
        bot.SaveToFile()
        await ctx.send(content="Sauvegarde manuelle effectuée.", hidden=True)
    else:
        await ctx.send(content="Echec de la sauvegarde manuelle !", hidden=True)

@slash.slash(
    name="new",
    description="[ADMIN] Ajoute un nouveau médecin",
    options = [{
        "name": "nom",
        "description": "Prénom & Nom du médecin",
        "type": 3,
        "required": True
    }],
    guild_ids=guild_ids)
async def _new(ctx: SlashContext, nom: str):
    await ctx.defer(hidden=True)   
    authorized = False
    for tempRole in bot.roleFichePatient:
        if tempRole in ctx.author.roles:
           authorized = True

    if authorized:
        await bot.NewMedic(ctx, nom)
        await ctx.send(content="Création d'un dossier de nouveau médecin effectuée.", hidden=True)
    else:
        await ctx.send(content="Echec de la création d'un dossier de nouveau médecin !", hidden=True)

@slash.slash(
    name="rdv",
    description="Crée une fiche de rendez-vous",
    options = [{
        "name": "nom",
        "description": "Prénom & Nom du patient",
        "type": 3,
        "required": True
    },{
        "name": "numero",
        "description": "Numéro de téléphone du patient",
        "type": 3,
        "required": True
    },{
        "name": "categorie",
        "description": "Type de rendez-vous",
        "type": 3,
        "required": True,
        "choices": [{
            "name": "Psychologie",
            "value": 1
            },{
            "name": "Chirurgie",
            "value": 2
            }]    
    },{
        "name": "medecine",
        "description": "Médecine Générale",
        "type": 4,
        "required": True,
        "choices": [{
            "name": "Oui",
            "value": 1
            },{
            "name": "Non",
            "value": 2
            }] 
    },{
        "name": "description",
        "description": "Besoin du patient",
        "type": 3,
        "required": True
    }],
    guild_ids=guild_ids)
async def _rdv(ctx: SlashContext, nom: str, numero: str, categorie: int, medecine: int, description: str ):
    await ctx.defer(hidden=True)
    authorized = False
    if bot.roleLSMS in ctx.author.roles:
        authorized = True
    for tempRole in bot.roleAdmin:
        if tempRole in ctx.author.roles:
           authorized = True

    if authorized:
        await bot.AddRDV(nom, numero, categorie, medecine, description, ctx.author)
        await ctx.send(content="Création d'un nouveau RDV.", hidden=True)
    else:
        await ctx.send(content="Echec de création de RDV !", hidden=True)
    
bot.Run()


@atexit.register
def goodbye():
    bot.SaveToFile()
