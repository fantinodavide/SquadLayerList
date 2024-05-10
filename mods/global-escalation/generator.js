const fs = require('node:fs');

const parserRegex = /^\s*(?<fullName>(?<mod>[^\s_]+)_(?<level>[^\s_]+)_((?<gamemode>[^\s_]+)_)?((?<version>V\d+)_)?(?<faction1>\w+)(-|_)(?<faction2>\w+)) \(.+\)/gi

const raw = fs.readFileSync('raw.txt').toString();

const output = {
    Maps: raw.replace(/\r\n/g, '\n').split('\n')
        .map(l => {
            const rawParsed = parserRegex.exec(l);
            const parsed = rawParsed?.groups;
            if (!parsed) {
                console.log(`unable to parse "${l}"`)
                return;
            }

            const ret = {
                Name: parsed.fullName,
                rawName: parsed.fullName,
                levelName: parsed.level,
                minimapTexture: "",
                lightingLevel: "",
                lighting: "Day",
                border: [],
                team1: {
                    faction: parsed.faction1,
                    teamSetupName: parsed.faction1,
                    tickets: 0,
                    playerPercent: 50,
                    disabledVeh: true,
                    intelOnEnemy: 0,
                    actions: 0,
                    commander: true,
                    vehicles: []
                },
                team2: {
                    faction: parsed.faction2,
                    teamSetupName: parsed.faction2,
                    tickets: 0,
                    playerPercent: 50,
                    disabledVeh: true,
                    intelOnEnemy: 0,
                    actions: 0,
                    commander: true,
                    vehicles: []
                },
                type: "",
                mapName: parsed.level,
                gamemode: parsed.gamemode,
                layerVersion: parsed.version,
                mapSize: "0x0 km",
                mapSizeType: "Playable Area"
            }

            return ret;
        })
        .filter(l => l != null)
}
fs.writeFileSync('layers.json', JSON.stringify(output, null, 2))