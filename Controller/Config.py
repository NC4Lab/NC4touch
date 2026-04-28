import logging
logger = logging.getLogger(f"session_logger.{__name__}")

class Config:
    """In-memory configuration store for session, chamber, and trainers."""

    def __init__(self, config: dict = None):
        config = config or {}
        
        if not isinstance(config, dict):
            logger.error("config must be a dictionary")
            config = {}
        
        self.config = {}
        self.explicit_keys = set()
        self.config.update(config)
        self.explicit_keys.update(config.keys())
    
    def __getitem__(self, key: str):
        return self.config.get(key, None)
    
    def __setitem__(self, key, value):
        self.config[key] = value
        self.explicit_keys.add(key)
        logger.debug(f"Config updated: {key} = {value}")

    def update_with_dict(self, config: dict):
        if not isinstance(config, dict):
            logger.error("config must be a dictionary")
            return
        
        self.config.update(config)
        self.explicit_keys.update(config.keys())
        logger.debug(f"Config updated: {config}")
    
    def ensure_param(self, param: str, default_value):
        if param not in self.config and param not in self.explicit_keys:
            self.config[param] = default_value
            logger.debug(f"Config parameter {param} not found. Setting to default value: {default_value}")
        # else:
            # logger.debug(f"Config parameter {param} already exists with value: {self.config[param]}")