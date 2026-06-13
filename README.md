# Farm Generation

Generate a small, configurable pecan orchard as a USDA layer for robotics
simulation. The generated layer references the existing tree and ground-cover
assets rather than copying their geometry. Repeated vegetation references are
marked instanceable so renderers can share their large source geometry.

The orchard is Z-up and uses meters. Trees are arranged in rows, ground-cover
patches tile the area around them, and an invisible static collision plane spans
the requested ground extent. A high-angle distant sun provides directional
lighting and shadows, while a dome light provides diffuse daytime sky fill.
Environment lights embedded in referenced assets are removed before use (see the assets section below).

## Install

Use the provided environment setup so Python can find NVIDIA USD, then install
the package in editable mode:

```bash
source env.sh
python -m pip install -e .
```

The active Python environment must provide `pxr` (USD) and PyYAML.

## Usage

Generate the default orchard:

```bash
source env.sh
generate-orchard orchard_config.yaml orchard_world.usda
```

The command accepts a YAML configuration file followed by the output filename.
All supported settings and defaults are shown in `orchard_config.yaml`.
`random_seed` is optional; omit it for different random transforms each run.

The output layer stores references relative to its own location. Keep the
`assets` directory and its texture subdirectories available at those relative
paths when moving or packaging the generated layer.

## Tests

Run the functional test from the project root:

```bash
source env.sh
python -m unittest discover -s tests
```

## Generation

Am IsaacSim render of the default orchard is shown below. 

![TestOrchard](orchard_world.png)

## Assets

Assets are not provided in this repository, due to licensing restrictions. The assets used here were exported from Blender - after opening the Blender version of the asset. This involved various manipulations of the blender asset to make it generate USD palatable to ... USD consumers. Generally speaking, Blender assets have too much complex logic for USD - eliminating Ambient Occlusion and simplifying the usage of the alpha texture are needed. Also, Blender seems to be injecting a light source into each asset, which causes an epileptic fit in IsaacSim. These can be deleted in the asset USDA file, although presumably there is a setting in Blender to not do this.

## AI assistance

ChatGPT 5.5 (OpenAI, 06/2026) and Codex (OpenAI, 06/2026) were used to assist in the creation of this repo and converting of assets to USD(A). As well, Gemini 1.5 Pro (Google, 06/2026) was used to assist in manipulation of the assets in Blender. See `codex_instruction1.txt` for the first set of instructions given to Codex to start code generation. Codex converged to pretty good results after a few iterations. It helps to know the right questions and doubts to have.