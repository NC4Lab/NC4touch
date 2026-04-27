import os
import yaml
from os.path import expanduser

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Config:
    """
    This class manages the configuration of the session, chamber and trainer
    """
    def __init__(self, config: dict = None, config_file: str = '~/config.yaml'):
        config = config or {}
        config_file = expanduser(config_file) if config_file else None
        
        if not isinstance(config, dict):
            logger.error("config must be a dictionary")
            config = {}
        
        # Construct config by loading parameters from config argument > config_file
        self.config = {}
        self.explicit_keys = set()
        self.config_file = config_file
        self.update_with_file(config_file)
        self.config.update(config)
        self.explicit_keys.update(config.keys())
    
    def __getitem__(self, key: str):
        return self.config.get(key, None)
    
    def __setitem__(self, key, value):
        self.config[key] = value
        self.explicit_keys.add(key)
        logger.debug(f"Config updated: {key} = {value}")
        self.save_config_file()

    def update_with_dict(self, config: dict):
        if not isinstance(config, dict):
            logger.error("config must be a dictionary")
            return
        
        self.config.update(config)
        self.explicit_keys.update(config.keys())
        logger.debug(f"Config updated: {config}")
        self.save_config_file()
    
    def update_with_file(self, config_file):
        if not config_file:
            return
        if os.path.isfile(config_file):
            try:
                with open(config_file, "r") as f:
                    loaded_config = yaml.safe_load(f) or {}
                    self.config.update(loaded_config)
                    self.explicit_keys.update(loaded_config.keys())
                    self.config_file = config_file
                    self.save_config_file()
            except Exception as e:
                logger.error(f"Error loading config file {config_file}: {e}")
                loaded_config = {}
        else:
            logger.warning(f"Config file {config_file} does not exist.")
    
    def ensure_param(self, param: str, default_value):
        if param not in self.config or param not in self.explicit_keys:
            self.config[param] = default_value
            logger.debug(f"Config parameter {param} not found. Setting to default value: {default_value}")
            self.save_config_file()
        # else:
            # logger.debug(f"Config parameter {param} already exists with value: {self.config[param]}")
        
    def save_config_file(self):
        if self.config_file:
            try:
                with open(self.config_file, "w") as f:
                    yaml.dump(self.config, f)
            except Exception as e:
                logger.error(f"Error saving config file {self.config_file}: {e}")
        else:
            logger.warning("No config file to save to.")