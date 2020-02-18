#  This file is part of gentoogram-bot.
#
#  gentoogram-bot is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  gentoogram-bot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with gentoogram-bot.  If not, see <https://www.gnu.org/licenses/>.

import os

import yaml


class Config(dict):
    _config_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/settings.yml'

    def __init__(self):
        super().__init__()
        self.load()

    def load(self):
        with open(self._config_path) as fd:
            self.update(yaml.safe_load(fd))
