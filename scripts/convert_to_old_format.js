const fs = require('fs');

async function main() {
    const modDirs = fs.readdirSync('../mods/')

    for(const modDir of modDirs){
        const baseDir = `${'../mods'}/${modDir}`;
        const mainLayersFile = `${baseDir}/layers.json`;
        const input = fs.readFileSync(mainLayersFile);
    
        const layers = JSON.parse(input.toString());

        if(!layers.Units){
            console.log(`Skipping ${modDir} as it's already the old format`)
            continue;
        }
    
        const outputMaps = layers.Maps.map(l => {
            for (let t in l.teamConfigs) {
                try {
                    const faction = { ...layers.Units[ l.teamConfigs[ t ].defaultFactionUnit || l.teamConfigs[ t ].defaultFaction ] };

                    faction.faction = faction.displayName;
                    faction.unitObjectName = faction.unitObjectName;
        
                    for (let vehicle of faction.vehicles)
                        try {
                            vehicle.rawType = vehicle.classNames[ 0 ];
                        } catch (e) { }
        
        
                    l[ t ] = { ...l.teamConfigs[ t ], ...faction };
                } catch (error) {
                    console.log(`Unable to update teamconfig ${t} for ${l.rawName} (${modDir})`, error.message)
                }
            }
            delete l.teamConfigs;
            return l;
        })
    
        const output = layers;
        delete output.Maps;
        delete output.Units;
        delete output.Roles;
    
        output.Maps = outputMaps
    
        fs.writeFileSync(`${baseDir}/layers.old.json`, JSON.stringify(output));
    }
}

main();