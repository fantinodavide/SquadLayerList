const fs = require('fs');

const datalist = JSON.parse(fs.readFileSync('../layers.json'))

const units = datalist.Units;
const vehicles = Object.values(units).flatMap(u => u.vehicles).map(v => ({ name: v.name, type: v.vehType }));

const groupedVehiclesByType = vehicles.reduce((acc, cur) => {
    let group = acc.get(cur.type);

    if (!group)
        group = acc.set(cur.type, new Set()).get(cur.type);

    group.add(cur.name)

    return acc;
}, new Map());

let output = '';

groupedVehiclesByType.forEach((val, key) => 
    output += `## ${key}\n${Array.from(val).map(n => `  - ${n}`).join('\n')}\n`
);

console.log(output)