import glob
import json
import os
from wiremongo import from_filemapping, WireMongo


async def read_filemappings(wiremongo: WireMongo):
    project_root = os.getcwd()
    resources_dir = os.path.join(project_root, 'tests', 'resources', 'mappings')
    mocks = list()
    for file_path in glob.glob(os.path.join(resources_dir, '*.json')):
        with open(file_path, "r") as file:
            mocks.append(from_filemapping(json.load(file)))
    wiremongo.mock(*mocks).build()
