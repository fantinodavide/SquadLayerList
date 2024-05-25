const fs = require('fs');

async function main() {
    const input = fs.readFileSync('layers.json');

    const layers = JSON.parse(input.toString());

    const outputMaps = layers.Maps.map(l => {
        for (let t in l.teamConfigs) {
            const faction = { ...layers.Units[ l.teamConfigs[ t ].defaultFactionUnit ] };
            faction.faction = faction.displayName;
            faction.unitObjectName = faction.unitObjectName;

            for (let vehicle of faction.vehicles)
                try {
                    vehicle.rawType = vehicle.classNames[ 0 ];
                } catch (e) { }


            l[ t ] = { ...l.teamConfigs[ t ], ...faction };
        }
        delete l.teamConfigs;
        return l;
    })

    const output = layers;
    delete output.Maps;
    delete output.Units;
    delete output.Roles;

    output.Maps = outputMaps

    fs.writeFileSync('layers.old.json', JSON.stringify(output));
}

main();