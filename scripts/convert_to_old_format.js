const GIT_COMMANDS = true;

const fs = require('fs');
const exec = require('child_process').exec;

async function main() {
    const modDirs = fs.readdirSync('../mods/')
    modDirs.push('..')

    for (const modDir of modDirs) {
        const baseDir = `${'../mods'}/${modDir}`;
        const mainLayersFile = `${baseDir}/layers.json`;
        const input = fs.readFileSync(mainLayersFile);

        const layers = JSON.parse(input.toString());

        if (!layers.Units) {
            console.log(`Skipping ${modDir} as it's already the old format`)
            continue;
        }

        const outputMaps = layers.Maps.map(l => {
            try {
                for (let t in l.teamConfigs) {
                    let defaultUnitName = l.teamConfigs[ t ].defaultFactionUnit || l.teamConfigs[ t ].defaultFaction;
                    if (!defaultUnitName) continue;

                    let defaultUnit = layers.Units[ defaultUnitName ];

                    if (!defaultUnit) {
                        console.log(`Unable to get the unit`, defaultUnitName, l.rawName)
                        let foundFix = false;
                        for (const avUnit of l.factions) {
                            defaultUnitName = avUnit.defaultUnit;
                            defaultUnit = layers.Units[ defaultUnitName ]
                            if (defaultUnit) {
                                foundFix = true;
                                break;
                            }
                        }
                        if (foundFix)
                            console.log(`Found fix for ${defaultUnitName}`)
                        else
                            console.log(`No fix found for ${defaultUnitName}`)
                    }

                    const faction = { ...defaultUnit };

                    faction.faction = faction.factionName || faction.displayName;
                    faction.unitObjectName = faction.unitObjectName;

                    for (let vehicle of faction.vehicles)
                        try {
                            vehicle.rawType = vehicle.classNames[ 0 ];
                        } catch (e) { }

                    l[ t ] = { ...l.teamConfigs[ t ], ...faction };
                } catch (error) {
                    // console.log(`Unable to update teamconfig ${t} for ${l.rawName} (${modDir})`, error.message)
                }
            }
            delete l.teamConfigs;
            if (!l.team1 || !l.team2) return;
            return l;
        }).filter(l => l != null)

        const output = layers;
        delete output.Maps;
        delete output.Units;
        delete output.Roles;

        output.Maps = outputMaps

        const outputPath = `${baseDir}/layers.old.json`;
        fs.writeFileSync(outputPath, JSON.stringify(output));
        exec(`git add ${outputPath}`, (error, stdout, stderr) => {
            if (error) {
                console.error(`exec error: ${error}`);
                return;
            }
        });
    }
}

main();