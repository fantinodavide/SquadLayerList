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