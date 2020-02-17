import logging
import os

import yaml


class Config(dict):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def __init__(self):
        super().__init__()
        self.reload()

    def reload(self):
        with open(f'{self.base_dir}/settings.yml') as fd:
            self.update(yaml.safe_load(fd))
            logging.info('Config loaded.')
