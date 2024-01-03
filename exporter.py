import csv
import unreal
import inspect
import json
import re
import os

from string import digits

import sys

SQUADJS_COMPATIBLE = True
# SAVE_DICTIONARY = False

class LayerExporter(object):
    FactionTracker = {}
    LegendTracker = {}
    ChangesTracker = {}
    AllVehicles = {}
    LayerVehiclesAmounts = {}
    LevelAssets = {}

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
        

    def GetTeamName(self, FactionID):
        row_names = unreal.DataTableFunctionLibrary.get_data_table_row_names(self.FactionTable)
        columns_name = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(self.FactionTable, "DisplayName")

        #TODO: hack because some FactionSetup are using "US" as a faction ID instead of "USA", and US doesn't exist in the FactionTable.
        if FactionID == "US":
            FactionID = "USA"

        row_index = row_names.index(FactionID)
        ColumnValues = columns_name[row_index].split(',')
        name = re.sub(re.compile(r"^\s"), '', ColumnValues[len(ColumnValues) -1].replace("\"", ""))
        name = name.replace('\\', '')
    
        return name[:-1]
    def ExportLayerData(self, Layer, Teams):
        team_index = 0
        LayerDataTable = Layer.get_editor_property("Data").get_editor_property("DataTable")
        LayerRowName = Layer.get_editor_property("Data").get_editor_property("RowName")
        
        for Team in Teams:
            team_index = int(Team.get_editor_property("Index").value)
            
            FactionSetup = Team.get_editor_property("SpecificFactionSetup")
            Vehicles = FactionSetup.get_editor_property("Vehicles")
            Faction_ID =  FactionSetup.get_editor_property("FactionId")
            
        
            team_name = self.GetTeamName(Faction_ID)
            layer_name = Layer.get_name()
            levelId = ""
            if not layer_name in self.LayerVehiclesAmounts:
                LayerGamemodeDataTable = Layer.get_editor_property("Gamemode").get_editor_property("DataTable")
                LayerGamemodeRowName = Layer.get_editor_property("Gamemode").get_editor_property("RowName")

                layerVersionRegex = re.compile(r"v\d+$", flags=re.IGNORECASE)
                layerVersion = layerVersionRegex.search(layer_name)
                # print(layerVersion.group())
                
                self.LayerVehiclesAmounts[layer_name] = {}
                self.LayerVehiclesAmounts[layer_name]["Name"] = Layer.get_display_name().__str__()
                self.LayerVehiclesAmounts[layer_name]["rawName"] = LayerRowName.__str__()
                self.LayerVehiclesAmounts[layer_name]["levelName"] = LayerRowName.__str__()
                self.LayerVehiclesAmounts[layer_name]["fName"] = Layer.get_fname().__str__()
                # self.LayerVehiclesAmounts[layer_name]["modId"] = Layer.mod_id
                self.LayerVehiclesAmounts[layer_name]["gamemode"] = LayerGamemodeRowName.__str__()
                self.LayerVehiclesAmounts[layer_name]["lightingLevel"] = self.GetLightingName(Layer)
                self.LayerVehiclesAmounts[layer_name]["minimapTexture"] = self.GetMinimapTexture(Layer)
                
                # self.GetCaptureZones(Layer)

                if layerVersion:
                    self.LayerVehiclesAmounts[layer_name]["layerVersion"] = layerVersion.group()
                
                levelId = Layer.get_editor_property("LevelId").__str__()
                
                if not levelId in self.LevelAssets:
                    self.LevelAssets[levelId] = self.GetLevelByLayer(Layer)

                if levelId in self.LevelAssets:
                    self.LayerVehiclesAmounts[layer_name]["biome"] = self.LevelAssets[levelId].get_editor_property("Biome").name
                    self.LayerVehiclesAmounts[layer_name]["mapName"] = self.LevelAssets[levelId].get_display_name().__str__()
                    self.LayerVehiclesAmounts[layer_name]["mapId"] = levelId

            if layer_name in self.LayerVehiclesAmounts: # and team_index >= 1 and team_index <= 2:
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"] = {}
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["faction"] = team_name
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["teamSetupName"] =  FactionSetup.get_display_name().__str__()
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["tickets"] = Team.tickets
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["playerPercent"] = Team.player_percentage
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["factionShortName"] = Faction_ID.__str__()
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["commander"] = not Layer.game_flags.commander_disabled
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["disabledVeh"] = Team.get_editor_property("DisableVehicleDuringStaggingPhase")
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["buddyRally"] = FactionSetup.get_editor_property("HasBuddyRally")
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["actions"] = FactionSetup.actions.__len__()
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["intelOnEnemy"] = Team.get_editor_property("Intelligence On Enemy")
                self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["vehicles"] = []
                # print(FactionSetup.__dir__())

            index = 0
            done = False

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
                    row_index = row_names.index(VehicleRowName)
                    ColumnValues = columns_name[row_index].split(',')
                    VehicleName = ColumnValues[len(ColumnValues) -1].replace("\"", "")[:-1]
                    VehicleIcon = icon_col_name[row_index].split(',')[0].split('.')[1]
            
                if VehicleRespawnData != None:            
                    InitialDelay = unreal.MathLibrary.get_total_minutes(VehicleRespawnData.get_editor_property("InitialDelay"))
                    RespawnTime = unreal.MathLibrary.get_total_minutes(VehicleRespawnData.get_editor_property("Delay"))
            
                if VehicleCountData != None:
                    VehicleCount = VehicleCountData.get_editor_property("BaseAvailability")
            
                vehName = VehicleName.__str__().strip()
                vehType = VehicleType.__str__().split('.')[1].split(':')[0]
            
                if layer_name in self.LayerVehiclesAmounts:
                    self.LayerVehiclesAmounts[layer_name][f"team{team_index}"]["vehicles"].append({"name": vehName, "type": vehName, "vehicleType": vehType, "count": VehicleCount, "teamID": team_index, "initialDelay": InitialDelay, "respawnTime": RespawnTime, "spawnerSize": SpawnerSize, "icon": VehicleIcon, "classNames": vehicleBlueprints})
                else:
                    print(f"Error: Layer \"{layer_name}\" not found in self.LayerVehiclesAmounts")
                    
                index+=1
    
    def enumToValue(x, enum):
        return enum.__str__().split('.')[1].split(':')[0]
    
    def enumToIndex(x, enum):
        return int(enum.__str__().split('.')[1].split(':')[1])
    
    def GetCaptureZones(self, Layer):
        layerPath = Layer.get_path_name().replace("Gameplay_LayerData", "Gameplay_Layers").split('.')[0]
        dependencyOptions = unreal.AssetRegistryDependencyOptions(False, True, False, False, False)
        dependencies = self.asset_registry.get_dependencies(layerPath, dependencyOptions)
        print(dependencies)
        # if dependencies != None:
        #     for dep in dependencies:
        #         if dep != None:
        #             dep_name_str = str(dep)
        #             # minimapRegex = re.compile(r"_minimap$",flags=re.IGNORECASE)
        #             # if minimapRegex.search(dep_name_str):
        #                 ret = os.path.basename(dep_name_str)
        #                 return ret
        return ""

    def LayerHasVehicle(self, Layer, Vehicle):
        layerPath = Layer.get_path_name().replace("Gameplay_LayerData", "Gameplay_Layers").split('.')[0]
        vehicleDependencyOptions = unreal.AssetRegistryDependencyOptions(True, True, False, False, False)
        vehicleReferencers = self.asset_registry.get_referencers(Vehicle, vehicleDependencyOptions)
        print(vehicleReferencers)
        return layerPath in vehicleReferencers
    
    def GetLightingName(self, Layer):
        package_name = Layer.get_path_name()
        if "Gameplay_LayerData" in package_name:
            package_name = Layer.get_path_name().replace("Gameplay_LayerData", "Gameplay_Layers").split('.')[0]
        else:
            package_name = Layer.get_path_name().replace("Gameplay_Layer_Data", "Gameplay_Layers").split('.')[0]

        dependency_options = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)
        dependencies = self.asset_registry.get_dependencies(package_name, dependency_options)
        if dependencies != None:
            for dep in dependencies:
                if dep != None:
                    dep_name_str = str(dep)
                    if "LL" in dep_name_str:
                        return os.path.basename(dep_name_str)
        return ""
    
    def GetLevelByLayer(self, Layer):
        levelID = Layer.get_editor_property("LevelId").__str__()
        LevelList = unreal.SQChunkSettings.get_default_object().get_editor_property("LevelsToCook")
        
        for level in LevelList:
            levelRowName = str(level.get_editor_property("Data").get_editor_property("RowName"))
            if levelRowName == levelID:
                return level
        
        return ""
    
    def GetMinimapTexture(self, Layer):
        package_name = Layer.get_path_name()
        if "Gameplay_LayerData" in package_name:
            package_name = Layer.get_path_name().replace("Gameplay_LayerData", "Gameplay_Layers").split('.')[0]
        else:
            package_name = Layer.get_path_name().replace("Gameplay_Layer_Data", "Gameplay_Layers").split('.')[0]

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
    
    def GetVehicleBlueprint(self, Layer):
        package_name = Layer.get_path_name()
        if "Gameplay_LayerData" in package_name:
            package_name = Layer.get_path_name().replace("Gameplay_LayerData", "Gameplay_Layers").split('.')[0]
        else:
            package_name = Layer.get_path_name().replace("Gameplay_Layer_Data", "Gameplay_Layers").split('.')[0]

        dependency_options = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)
        dependencies = self.asset_registry.get_dependencies(package_name, dependency_options)
        if dependencies != None:
            for dep in dependencies:
                if dep != None:
                    dep_name_str = str(dep)
                    print(dep_name_str)
                    if True: # just a random condition, will be replaced later
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

    def ExportToJSON(self):
        contentDir = unreal.Paths.engine_content_dir()

        Layerslist = unreal.SQChunkSettings.get_default_object().get_editor_property("LayersToCook")

        number_of_assets = len(Layerslist)
        print("Number of assets: " + str(number_of_assets))

        if self.export_path == "":
            self.export_path = unreal.Paths.project_saved_dir()

        save_path = self.export_path + "layers.json"

        print(f"Engine content dir: {contentDir}")
        print("Base Path: " + self.export_path)
        print("Layer JSON Output Path: " + save_path)

        with unreal.ScopedSlowTask(len(Layerslist), "Generating JSON list") as slow_task:                
            slow_task.make_dialog(True)

            asset_id = 1
            for asset in Layerslist:
                if slow_task.should_cancel():
                    break

                Teams = asset.get_editor_property("TeamConfigs")
                self.ExportLayerData(asset, Teams)
                asset_id += 1
                slow_task.enter_progress_frame(1)
            
            with open(save_path, 'w') as f:
                if SQUADJS_COMPATIBLE:
                    json.dump({ "Maps": list(self.LayerVehiclesAmounts.values())}, f, indent=2)
                else:
                    json.dump(self.LayerVehiclesAmounts, f, indent=2)

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