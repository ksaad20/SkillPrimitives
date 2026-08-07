Skill Primitives — Hugging Face Space

Interactive demo for decomposing robot manipulation datasets into composable skill primitives.

What It Does

Segment — Load a LeRobot dataset and extract primitives (reach, grasp, lift, transport, place)
Annotate — Label each primitive with natural language descriptions using LLMs
Compose — Chain primitives into novel task sequences from plain English instructions
Visualize — See the distribution of primitive types across episodes

Usage

Go to the Segment tab, enter a dataset name (e.g., lerobot/pusht), and click "Segment Episode"
Switch to the Annotate tab and click "Annotate" to generate descriptions
Go to the Compose tab, enter your own instructions, and click "Compose Task"
View the Visualize tab to see primitive distributions

Local Development

```
bash
cd spaces
pip install -r requirements.txt
python app.py

```
```
The app will start at http://localhost:7860.

```
Deployment

Deploy to Hugging Face Spaces:

```
bash
huggingface-cli repo create skill-primitives-demo --type space
huggingface-cli upload YOUR_USERNAME/skill-primitives-demo . --repo-type=space
Or connect this directory to a Space via Git integration.
