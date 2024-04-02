##########################
##  CONFIGURATION HERE  ##
##########################

LAYER_PREFIX_FILTER = [ "GC_" ] # If the layer starts with one of the array elements, it will be included in the exported list, everything else will be removed.

MINIFY_OUTPUT = True # If set to True, the output will not have indentation, if set to False, the output will have an indentation of 2 spaces.

##########################
## END OF CONFIGURATION ##
##########################

import csv
import unreal
import inspect
import json
import re
import os
import configparser

from string import digits

import sys

class LayerExporter(object):
    DefaultGameSettings = {}
    
    RequiredOutputFactions = []
    LayersSoftDependencies = []
    FactionTracker = {}
    LegendTracker = {}
    ChangesTracker = {}
    AllVehicles = {}
    LevelAssets = {}
    FactionSetupAssets = {}
    Factions = {}
    Roles = {}
    MeleeWeapons = []
    
    LayersData = {}
    FactionSetupData = {}

    def __init__(self, _export_path="", _previous_layer_filepath="", _previous_vehicle_filepath="", _previous_layer_list=None, _asset_registry=None, _FactionTable=None):
        self.asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        self.FactionTable = unreal.EditorAssetLibrary.find_asset_data('/Game/Settings/Factions/FactionTable.FactionTable').get_asset()

        self.previous_layer_list = _previous_layer_list
        self.previous_layer_filepath = _previous_layer_filepath
        self.previous_vehicle_filepath = _previous_vehicle_filepath
        self.export_path = _export_path

        self.FactionTracker.clear()
        self.LegendTracker.clear()
        self.ChangesTracker.clear()
        
    def ExportLayerData(self, _Layer):
        Layer = _Layer.get_asset()
        levelId = Layer.get_editor_property("LevelId").__str__()
        
        if levelId not in self.LevelAssets:
            # print(f"Unable to find {levelId} in LevelAssets")
            return

        self.GetLayerSoftDependencies(Layer)
        
        team_index = 0
        
        LayerDataTable = Layer.get_editor_property("Data").get_editor_property("DataTable")
        LayerRowName = Layer.get_editor_property("Data").get_editor_property("RowName")
                    
        PersistentLightingType = Layer.get_editor_property("PersistentLightingType").row_name.__str__()
        if PersistentLightingType == "None":
            PersistentLightingType = None
        
        layer_name = Layer.get_name()
        LayerGamemodeDataTable = Layer.get_editor_property("Gamemode").get_editor_property("DataTable")
        LayerGamemodeRowName = Layer.get_editor_property("Gamemode").get_editor_property("RowName")
        self.LayersData[layer_name] = {}
        self.LayersData[layer_name]["Name"] = Layer.get_display_name().__str__()
        self.LayersData[layer_name]["rawName"] = LayerRowName.__str__()
        self.LayersData[layer_name]["levelName"] = LayerRowName.__str__()
        self.LayersData[layer_name]["fName"] = Layer.get_fname().__str__()
        # self.LayersData[layer_name]["modId"] = modId
        self.LayersData[layer_name]["gamemode"] = LayerGamemodeRowName.__str__()
        
        print(Layer.get_mod_id())
        
        self.LayersData[layer_name]["persistentLightingType"] = PersistentLightingType
        self.LayersData[layer_name]["lightingLevel"] = self.GetLightingLayerName(Layer)
        self.LayersData[layer_name]["minimapTexture"] = self.GetMinimapTexture(Layer)
        
        self.LayersData[layer_name]["mapId"] = levelId
        
        self.LayersData[layer_name]["biome"] = self.LevelAssets[levelId].get_editor_property("Biome").name
        self.LayersData[layer_name]["mapName"] = self.LevelAssets[levelId].get_display_name().__str__()
        
        self.LayersData[layer_name]["commander"] = not Layer.game_flags.commander_disabled
        # print(Layer.game_flags)

        layerVersionRegex = re.compile(r"v\d+$", flags=re.IGNORECASE)
        layerVersion = layerVersionRegex.search(layer_name)

        if layerVersion:
            self.LayersData[layer_name]["layerVersion"] = layerVersion.group()
        
        self.LayersData[layer_name]["separatedFactionsList"] = False
        self.LayersData[layer_name]["factions"] = []
        self.LayersData[layer_name]["teamConfigs"] = {}
        self.LayersData[layer_name]["objectives"] = {}
        
        objectives = Layer.get_editor_property("ObjectiveLocations")
        mainCount = 0
        for objective in objectives:
            name = objective.name_id.__str__()
            isMain = False
            
            if name == "Main":
                mainCount+=1
                isMain = True
            
            order = int(objective.order)
            if isMain and mainCount == 2:
                order*=100
                
            objId = f"{order}"
            if int(order) < 10:
                objId = f"0{objId}"
                
            
            if isMain:
                objectName = f"{objId}-Team{mainCount}{name}"
            else:
                objectName = f"{objId}-{name}"
            
            objectName = objectName.replace(" ", "")
            self.LayersData[layer_name]["objectives"][objectName] = {}
            self.LayersData[layer_name]["objectives"][objectName]["pointPosition"] = order
            self.LayersData[layer_name]["objectives"][objectName]["name"] = name
            self.LayersData[layer_name]["objectives"][objectName]["objectName"] = objectName
            self.LayersData[layer_name]["objectives"][objectName]["location_x"] = objective.location.x
            self.LayersData[layer_name]["objectives"][objectName]["location_y"] = objective.location.y
            self.LayersData[layer_name]["objectives"][objectName]["location_z"] = objective.location.z
            
        
        TeamConfigs = Layer.get_editor_property("TeamConfigs")

        for teamConfig in TeamConfigs:
            team_index = int(teamConfig.get_editor_property("Index").value)
            
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"] = {}
            
            defaultFaction = teamConfig.get_editor_property("SpecificFactionSetup")
            if defaultFaction:
                self.RequiredOutputFactions.append(defaultFaction.get_editor_property("FactionId").__str__())
                self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["defaultFaction"] = defaultFaction.get_editor_property("Data").get_editor_property("RowName")
            
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["index"] = team_index
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["playerPercentage"] = teamConfig.get_editor_property("PlayerPercentage")
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["tickets"] = teamConfig.get_editor_property("tickets")
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["disabledVeh"] = teamConfig.get_editor_property("DisableVehicleDuringStaggingPhase")

            isAttackingTeam = teamConfig.call_method("IsAttackingTeam")
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["isAttackingTeam"] = isAttackingTeam
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["isDefendingTeam"] = not isAttackingTeam
            
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["allowedAlliances"] = []
            for allowedAlliance in teamConfig.get_editor_property("Allowed Alliances"):
                self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["allowedAlliances"].append(self.enumToValue(allowedAlliance))
                                    
            self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["allowedFactionSetupTypes"] = []

            for allowedFactionSetup in teamConfig.get_editor_property("AllowedFactionSetupTypes"):
                self.LayersData[layer_name]["teamConfigs"][f"team{team_index}"]["allowedFactionSetupTypes"].append(self.enumToValue(allowedFactionSetup))
        
        
        factionsList = {}
        
        factionsList[1] = Layer.get_editor_property("FactionsList")
        factionsList[2] = Layer.get_editor_property("FactionsListTeamTwo")
        # separatedFactionsList = Layer.get_editor_property("Separated Factions List")
        separatedFactionsList = factionsList[2] is not None and len(factionsList[2]) > 0
        self.LayersData[layer_name]["separatedFactionsList"] = separatedFactionsList
        for teamIndex in factionsList:
            if factionsList[teamIndex] is None:
                continue
            for factionId in factionsList[teamIndex]:
                factionStruct = factionsList[teamIndex][factionId]
                faction = {}
                faction["factionId"] = factionId.__str__()
                faction["defaultUnit"] = None
                
                if separatedFactionsList:
                    faction["availableOnTeams"] = [ teamIndex ]
                else:
                    faction["availableOnTeams"] = [ 1, 2 ]
                
                faction["types"] = []
                
                for factionType in factionStruct.types:
                    faction["types"].append(factionType.__str__())
                
                if factionStruct.faction:
                    faction["defaultUnit"] = factionStruct.faction.get_editor_property("Data").get_editor_property("RowName").__str__()

                self.RequiredOutputFactions.append(factionId.__str__())
                
                self.LayersData[layer_name]["factions"].append(faction)
    
    def enumToValue(self, enum):
        # print(enum)
        if(type(enum) == str):
            return enum
        else:
            return enum.name
    
    def enumToIndex(self, enum):
        return int(enum.__str__().split('.')[1].split(':')[1])
    
    def GetGameplayLayerPath(self, Layer):
        return re.sub(re.compile(r"(^\[)|(\.[^\.]+\]$)"), '', Layer.get_editor_property("Worlds").__str__())
    
    def GetLightingLayerName(self, Layer):
        package_name = self.GetGameplayLayerPath(Layer)

        dependency_options = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)
        dependencies = self.asset_registry.get_dependencies(package_name, dependency_options)
        if dependencies != None:
            for dep in dependencies:
                if dep != None:
                    dep_name_str = str(dep)
                    if "LL" in dep_name_str:
                        return os.path.basename(dep_name_str)
        return ""
    
    def GetMinimapTexture(self, Layer):
        package_name = self.GetGameplayLayerPath(Layer)

        dependency_options = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)
        dependencies = self.asset_registry.get_dependencies(package_name, dependency_options)
        if dependencies != None:
            for dep in dependencies:
                if dep != None:
                    dep_name_str = str(dep)
                    minimapRegex = re.compile(r"_minimap$",flags=re.IGNORECASE)
                    if minimapRegex.search(dep_name_str):
                        ret = os.path.basename(dep_name_str)
                        return ret
        return ""

    def GetNumberOfVehicles(self, FactionSetup, Type = ""):
        Vehicles = FactionSetup.get_editor_property("Vehicles")
        amount = 0
        InitialDelay = 0

        for Vehicle in Vehicles:
            if Vehicle != None:
                VehicleSetting = Vehicle.get_editor_property("Setting")
                    
                if VehicleSetting.get_editor_property("VehicleType").name == Type:
                    amount += 1
                    DelaySettings = Vehicle.get_editor_property("Delay")
                    if DelaySettings != None:
                        InitialDelay = unreal.MathLibrary.get_total_minutes(DelaySettings.get_editor_property("InitialDelay"))
            
        Result = ""
        if amount > 0:
            Result = str(amount)
            if InitialDelay > 0:
                Result += " @ " + str(InitialDelay).split('.')[0] + "min"

        return Result
    
    def Contains(self, ID, Name):
        Name = Name.replace(' ', '')
        index = int(0)
        
        column_names_list = self.previous_layer_list[0].split(',')
        name_index = column_names_list.index("Layer Name")
        id_index = column_names_list.index("ID")
        
        for L in self.previous_layer_list:
            split_L = L.split(',')
            if len(split_L) > 1:
                current_level_name = split_L[name_index].replace(' ', '')
                if current_level_name == Name:
                    return split_L
            index += 1

        return -1
    
    def IncrementTracker(self, Tracker, Key):
        try:
            Tracker[Key] += 1
        except KeyError:
            Tracker[Key] = 1

        return Tracker[Key]

    def LoadLevelList(self):
        asset_filter = unreal.ARFilter(class_names=["BP_SQLevel_C"])
        levels = self.asset_registry.get_assets(asset_filter)
        for level in levels:
            levelAsset = level.get_asset()
            levelName = levelAsset.get_editor_property("Data").get_editor_property("RowName").__str__()
            self.LevelAssets[levelName] = levelAsset
        return self.LevelAssets
    
    def LoadFactionSetups(self):
        asset_filter = unreal.ARFilter(class_names=["BP_SQFactionSetup_C"], package_names=self.LayersSoftDependencies)
        rawAssets = self.asset_registry.get_assets(asset_filter)
        for rawAsset in rawAssets:
            asset = rawAsset.get_asset()
            assetName = asset.get_editor_property("Data").get_editor_property("RowName").__str__()
            factionId = asset.get_editor_property("FactionId").__str__()
            # if factionId not in self.RequiredOutputFactions:
            #     continue
            self.FactionSetupAssets[assetName] = asset
        return self.FactionSetupAssets
    
    def LoadFactions(self):
        asset_filter = unreal.ARFilter(class_names=["BP_SQFaction_C"])
        rawAssets = self.asset_registry.get_assets(asset_filter)
        for rawAsset in rawAssets:
            asset = rawAsset.get_asset()
            assetName = asset.get_editor_property("Data").get_editor_property("RowName").__str__()
            # if factionId not in self.RequiredOutputFactions:
            #     continue
            if assetName in self.RequiredOutputFactions:
                self.Factions[assetName] = asset
        return self.Factions
    
    def LoadLayerList(self):
        asset_filter = unreal.ARFilter(class_names=["BP_SQLayer_C"])
        Layerslist = []
        for rawAsset in self.asset_registry.get_assets(asset_filter):
            asset = rawAsset.get_asset()
            LayerRowName = asset.get_editor_property("Data").get_editor_property("RowName").__str__()
            
            keep = len(LAYER_PREFIX_FILTER) == 0
            
            for prefix in LAYER_PREFIX_FILTER:
                if LayerRowName.startswith(prefix):
                    keep = True
            
            if not keep:
                continue
            
            Layerslist.append(rawAsset)
        return Layerslist
    
    def GenerateFactionSetupList(self):
        for factionName in self.FactionSetupAssets:
            FactionSetup = self.FactionSetupAssets[factionName]
            factionType = ""

            try:
                factionType = self.enumToValue(FactionSetup.get_editor_property("Type"))        
            except:
                pass
            
            factionId = FactionSetup.get_editor_property("FactionId").__str__()
            
            self.FactionSetupData[factionName] = {}
            self.FactionSetupData[factionName]["unitObjectName"] = factionName
            self.FactionSetupData[factionName]["factionId"] = factionId
            self.FactionSetupData[factionName]["factionShortName"] = FactionSetup.get_editor_property("FactionId").__str__()
            self.FactionSetupData[factionName]["type"] = factionType
            self.FactionSetupData[factionName]["displayName"] =  FactionSetup.get_display_name().__str__()
            
            if self.Factions[factionId]:
                self.FactionSetupData[factionName]["alliance"] = self.enumToValue(self.Factions[factionId].get_editor_property("Alliance"))
            else:
                print(f"Unable to get faction {factionId}")
                    
            self.FactionSetupData[factionName]["actions"] = FactionSetup.actions.__len__()
            self.FactionSetupData[factionName]["intelOnEnemy"] = FactionSetup.get_editor_property("Intelligence On Enemy")
            self.FactionSetupData[factionName]["useCommanderActionNearVehicle"] = FactionSetup.get_editor_property("CanUseCommanderActionNearVehicle")
            self.FactionSetupData[factionName]["hasBuddyRally"] = FactionSetup.get_editor_property("HasBuddyRally")
            
            self.FactionSetupData[factionName]["roles"] = []
            self.FactionSetupData[factionName]["vehicles"] = []
            
            Vehicles = FactionSetup.get_editor_property("Vehicles")
            for Vehicle in Vehicles:
                VehicleBlueprint = ""
                VehicleSettings = Vehicle.get_editor_property("Setting")
                VehicleRespawnData = Vehicle.get_editor_property("Delay")
                VehicleCountData = Vehicle.get_editor_property("LimitedCount")

                VehicleName = ""
                VehicleCount = 0
                InitialDelay = 0
                RespawnTime = 0
                VehicleIcon = ""
                VehicleType = ""
                SpawnerSize = ""
                VehicleVersions = ""
                rowName = ""

                if VehicleSettings != None:
                    VehicleDataTable = VehicleSettings.get_editor_property("Data").get_editor_property("DataTable")
                    VehicleRowName = str(VehicleSettings.get_editor_property("Data").get_editor_property("RowName"))
                    VehicleType = VehicleSettings.get_editor_property("VehicleType")
                    SpawnerSize = VehicleSettings.get_editor_property("SpawnerSize").__str__().split('.')[1].split(':')[0]
                    VehicleVersions = VehicleSettings.get_editor_property("VehicleVersions")

                    vehicleDependencyOptions = unreal.AssetRegistryDependencyOptions(True, False, False, False, False)
                    vehicleDependencies = self.asset_registry.get_dependencies(VehicleSettings.get_path_name().split('.')[0], vehicleDependencyOptions)
                    vehicleBlueprints = []
                    for vD in vehicleDependencies:
                        vehicleBlueprints.append(os.path.basename(vD.__str__()) + "_C")

                    row_names = unreal.DataTableFunctionLibrary.get_data_table_row_names(VehicleDataTable)
                    icon_col_name = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(VehicleDataTable, "Icon")
                    columns_name = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(VehicleDataTable, "DisplayName")
                    VehicleName = ""
                    VehicleIcon = ""
                    try:
                        row_index = row_names.index(VehicleRowName)
                        ColumnValues = columns_name[row_index].split(',')
                        VehicleName = ColumnValues[len(ColumnValues) -1].replace("\"", "")[:-1]
                        VehicleIcon = icon_col_name[row_index].split(',')[0].split('.')[1]
                    except:
                        pass
            
                if VehicleRespawnData != None:            
                    InitialDelay = unreal.MathLibrary.get_total_minutes(VehicleRespawnData.get_editor_property("InitialDelay"))
                    RespawnTime = unreal.MathLibrary.get_total_minutes(VehicleRespawnData.get_editor_property("Delay"))
            
                if VehicleCountData != None:
                    VehicleCount = VehicleCountData.get_editor_property("BaseAvailability")
            
                vehName = VehicleName.__str__().strip()
                vehType = self.enumToValue(VehicleType) #.__str__().split('.')[1].split(':')[0]
            
                self.FactionSetupData[factionName]["vehicles"].append({
                    "name": vehName,
                    "rowName": VehicleRowName,
                    "type": vehName,
                    "count": VehicleCount,
                    "delay": InitialDelay,
                    "respawnTime": RespawnTime,
                    "vehType": vehType,
                    "spawnerSize": SpawnerSize,
                    "icon": VehicleIcon,
                    "classNames": vehicleBlueprints
                })

            Roles = FactionSetup.get_editor_property("Roles")
            
            count = 0
            for Role in Roles:
                RoleSettings = Role.get_editor_property("Setting")
                RoleObj = {}
                
                if RoleSettings != None:
                    DataTable = RoleSettings.get_editor_property("Data").get_editor_property("DataTable")
                    RowName = str(RoleSettings.get_editor_property("Data").get_editor_property("RowName"))
                    RoleObj["rowName"] = RowName
                    RoleObj["displayName"] = RoleSettings.get_display_name().__str__()
                    
                    self.FactionSetupData[factionName]["roles"].append(RowName)
                    
                    if RowName in self.Roles:
                        continue

                    RoleObj["inventory"] = []
                    Inventory = RoleSettings.get_editor_property("Inventory")
                    if Inventory is not None:
                        slotIndex = -1
                        for inventorySlot in Inventory:
                            slotIndex += 1
                            items = inventorySlot.weapon_items
                            itemIndex = -1
                            for item in items:
                                itemIndex += 1
                                ItemObj = {}
                                # print(item.__dir__())
                                
                                # if count == 0:
                                #     print(item.equipable_item.__dir__())
                                
                                if item.equipable_item is not None:
                                    ItemObj["className"] =  unreal.Paths.get_extension(item.equipable_item.get_path_name())
                                    # ItemObj["parentClassName"] =  item.equipable_item.static_class().__str__()
                                    ItemObj["isMelee"] = self.IsMeleeWeapon(item.equipable_item)
                                ItemObj["slotIndex"] = slotIndex
                                ItemObj["itemIndex"] = itemIndex
                                ItemObj["minimum_count_on_spawn"] = item.minimum_count_on_spawn
                                ItemObj["max_allowed_in_inventory"] = item.max_allowed_in_inventory
                                ItemObj["cannot_rearm"] = item.cannot_rearm
                                RoleObj["inventory"].append(ItemObj)
                    self.Roles[RowName] = RoleObj
                    
                
            
    def GetHardDependencies(self, item):
        package_name = unreal.Paths.set_extension(item.get_path_name(),"")
        deps = []
        dependency_options = unreal.AssetRegistryDependencyOptions(False, True, False, False, False)
        dependencies = self.asset_registry.get_dependencies(package_name, dependency_options)
        if dependencies != None:
            for dep in dependencies:
                if dep != None:
                    dep_name_str = str(dep)
                    deps.append(dep_name_str)
        return deps
    
    def GetLayerSoftDependencies(self, layer):
        package_name = unreal.Paths.set_extension(layer.get_path_name(),"")
        dependency_options = unreal.AssetRegistryDependencyOptions(True, False, False, False, False)
        dependencies = self.asset_registry.get_dependencies(package_name, dependency_options)
        if dependencies != None:
            for dep in dependencies:
                if dep != None:
                    if dep not in self.LayersSoftDependencies:
                        self.LayersSoftDependencies.append(dep)
        return self.LayersSoftDependencies        

    def IsMeleeWeapon(self, inventoryItem):
        deps = self.GetHardDependencies(inventoryItem)

        for dep in deps:
            if "BP_GenericMelee" in dep:
                wpName = unreal.Paths.get_extension(inventoryItem.get_path_name())
                if wpName not in self.MeleeWeapons:
                    self.MeleeWeapons.append(wpName)
                return True
        return False

    def GetDefaultGameSettings(self):
        config_path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.combine([unreal.Paths.source_config_dir(), "DefaultGame.ini"]))
        print(f"Default Editor Config Path: {config_path}")
        print(f"Generated Config Dir: {unreal.Paths.generated_config_dir()}")
        print(f"Source Config Dir: {unreal.Paths.source_config_dir()}")
        print(f"Project Config Dir: {unreal.Paths.project_config_dir()}")
        config = configparser.ConfigParser(strict=False)
        error = False
        encodings = [ "utf-16", "utf-16-be", "utf-16-le", "utf-8" ]
        for encoding in encodings:
            try:
                with open(config_path, 'r', encoding=encoding) as f:
                    config.read_file(f)
            except:
                print(f"Failed to read the Default Game Settings file using encoding {encoding}")
                continue
            break
        
        if error:
            print("Unable to get Default Game Settings")
            return
        
        self.DefaultGameSettings["ProjectName"] = config.get('/Script/EngineSettings.GeneralProjectSettings', 'ProjectName', fallback='Not Found').__str__()
        print(f"Project Name: {self.DefaultGameSettings['ProjectName']}")
        self.DefaultGameSettings["ProjectVersion"] = config.get('/Script/EngineSettings.GeneralProjectSettings', 'ProjectVersion', fallback='Not Found').__str__()
        print(f"Project Version: {self.DefaultGameSettings['ProjectVersion']}")

    def ExportToJSON(self):        
        contentDir = unreal.Paths.engine_content_dir()

        if self.export_path == "":
            self.export_path = unreal.Paths.project_saved_dir()
        save_path = self.export_path + "layers.json"

        print(f"Engine content dir: {contentDir}")
        print("Base Path: " + self.export_path)
        print("Layer JSON Output Path: " + save_path)
        self.GetDefaultGameSettings()
        
        self.LoadLevelList()
        print("Number of Levels (Vanilla + MOD): " + str(len(self.LevelAssets)))
        
        Layerslist = self.LoadLayerList()
        number_of_layers = len(Layerslist)
        print("Number of Layers: " + str(number_of_layers))

        with unreal.ScopedSlowTask(len(Layerslist), "Generating JSON list") as slow_task:                
            slow_task.make_dialog(True)

            asset_id = 1
            for asset in Layerslist:
                if slow_task.should_cancel():
                    break

                self.ExportLayerData(asset)
                asset_id += 1
                slow_task.enter_progress_frame(1)

            self.LoadFactions()
            print("Number of Factions: " + str(len(self.Factions)))

            self.LoadFactionSetups()
            print("Number of FactionSetups: " + str(len(self.FactionSetupAssets)))
            self.GenerateFactionSetupList()

            indentation = 2
            if MINIFY_OUTPUT:
                indentation = None
                
            with open(save_path, 'w') as f:
                json.dump({
                    "DefaultGameSettings": self.DefaultGameSettings,
                    "Maps": list(self.LayersData.values()),
                    "Units": self.FactionSetupData,
                    "Roles": list(self.Roles.values()),
                    "MeleeWeapons": self.MeleeWeapons
                }, f, indent=indentation)

        return self.export_path

if __name__ == "__main__":
    input_size = len(sys.argv)

    export_path=""
    previous_layer_filepath=""
    previous_vehicle_filepath=""

    if input_size > 1:
        export_path = sys.argv[1]

    if input_size > 2:
        previous_layer_filepath = sys.argv[2]

    if input_size > 3:
        previous_vehicle_filepath = sys.argv[3]

    LExporter = LayerExporter(export_path, previous_layer_filepath, previous_vehicle_filepath)
    LExporter.ExportToJSON()