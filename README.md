# Squad Layer Lists
This repo contains multiple layer lists compatible with SquadJS.
Via the `exporter.py` script, everyone can generate a layer list from the Squad SDK by just running the Python Script from the menu `File > Execute Python Script...`, the output will be in the `Saved` directory of the Squad SDK
# SquadJS Layer List Installation
Edit the file: `layers.js` with the following path (relative to SquadJS root): `squad-server/layers/layers.old.js`
Replace the default layer list at line `25` just like the following example:
```js
const response = await axios.get(
  'https://raw.githubusercontent.com/fantinodavide/SquadLayerList/main/layers.old.json'
);
```
# Choosing the proper json file
- `layers.json` is the main layer list, but for the majority of the files use a format not yet supported by SquadJS.
- `layers.old.json` is a conversion of the `layers.json` supported by the current version of SquadJS, use this one when it's available!
# Credits
Part of the exporter code has been taken from python scripts shipped with the Squad SDK, credit goes to OWI
