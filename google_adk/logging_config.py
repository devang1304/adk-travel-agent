"""
Logging Configuration for google-adk Framework
Provides structured logging with proper formatting and levels
"""

import logging
import logging.config
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
            
        return json.dumps(log_data)


class GoogleADKLogger:
    """Central logging configuration for google-adk framework"""
    
    _configured = False
    _loggers: Dict[str, logging.Logger] = {}
    
    @classmethod
    def configure(cls, 
                  log_level: str = "INFO",
                  log_format: str = "structured",
                  log_file: Optional[str] = None,
                  console_output: bool = True) -> None:
        """Configure logging for the entire framework"""
        
        if cls._configured:
            return
            
        # Convert string level to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create handlers
        handlers = []
        
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            if log_format == "structured":
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            console_handler.setLevel(numeric_level)
            handlers.append(console_handler)
            
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(StructuredFormatter())
            file_handler.setLevel(numeric_level)
            handlers.append(file_handler)
            
        # Configure root logger
        logging.basicConfig(
            level=numeric_level,
            handlers=handlers,
            force=True
        )
        
        # Silence noisy third-party loggers
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        
        cls._configured = True
        
    @classmethod
    def get_logger(cls, name: str, agent_name: Optional[str] = None) -> logging.Logger:
        """Get a configured logger instance"""
        if not cls._configured:
            cls.configure()
            
        logger_key = f"{name}:{agent_name}" if agent_name else name
        
        if logger_key not in cls._loggers:
            logger = logging.getLogger(name)
            
            # Create a custom adapter if agent_name is provided
            if agent_name:
                logger = GoogleADKLoggerAdapter(logger, {"agent_name": agent_name})
                
            cls._loggers[logger_key] = logger
            
        return cls._loggers[logger_key]


class GoogleADKLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to log records"""
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        super().__init__(logger, extra)
        
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra context to log records"""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs
        
    def log_operation(self, level: int, operation: str, message: str, 
                     correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log an operation with structured context"""
        extra = kwargs.get('extra', {})
        extra.update({
            'operation': operation,
            'correlation_id': correlation_id
        })
        kwargs['extra'] = extra
        self.log(level, message, **kwargs)
        
    def info_operation(self, operation: str, message: str, 
                      correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log info level operation"""
        self.log_operation(logging.INFO, operation, message, correlation_id, **kwargs)
        
    def error_operation(self, operation: str, message: str, 
                       correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log error level operation"""
        self.log_operation(logging.ERROR, operation, message, correlation_id, **kwargs)
        
    def warning_operation(self, operation: str, message: str, 
                         correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log warning level operation"""
        self.log_operation(logging.WARNING, operation, message, correlation_id, **kwargs)


def get_logger(name: str, agent_name: Optional[str] = None) -> logging.Logger:
    """Convenience function to get a logger"""
    return GoogleADKLogger.get_logger(name, agent_name)


def configure_logging(log_level: str = "INFO", 
                     log_format: str = "structured",
                     log_file: Optional[str] = None,
                     console_output: bool = True) -> None:
    """Convenience function to configure logging"""
    GoogleADKLogger.configure(log_level, log_format, log_file, console_output)