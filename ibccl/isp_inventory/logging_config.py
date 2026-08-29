
import os
import logging
import logging.handlers
from django.conf import settings
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(settings.BASE_DIR, 'logs')
Path(LOGS_DIR).mkdir(exist_ok=True)


def get_log_level_from_settings():
    """
    Get log level from LogSettings model.
    Falls back to INFO if settings don't exist yet.
    """
    try:
        from isp_inventory.models import LogSettings
        log_settings = LogSettings.objects.first()
        if log_settings:
            return getattr(logging, log_settings.log_level, logging.INFO)
    except Exception:
        pass
    return logging.INFO


def configure_file_logging(logger_name, log_file, level=logging.INFO, max_bytes=10485760, backup_count=5):
    """
    Configure file logging for a specific logger with rotation.
    
    Args:
        logger_name: Name of the logger to configure
        log_file: Path to the log file
        level: Logging level
        max_bytes: Max size of log file before rotation (default 10MB)
        backup_count: Number of backup files to keep
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(file_handler)
    
    return logger


def get_activity_logger():
    """Get or create activity logger for user activity tracking."""
    try:
        from isp_inventory.models import LogSettings
        log_settings = LogSettings.objects.first()
        if log_settings and log_settings.enable_file_logging:
            level = getattr(logging, log_settings.log_level, logging.INFO)
            log_file = os.path.join(settings.BASE_DIR, log_settings.log_file_path)
            return configure_file_logging(
                'activity',
                log_file,
                level=level,
                max_bytes=log_settings.max_log_file_size,
                backup_count=log_settings.backup_count
            )
    except Exception:
        pass
    
    # Fallback: create a simple logger
    logger = logging.getLogger('activity')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def log_user_action(user, action, details='', level=logging.INFO):
    """
    Log user action to activity logger.
    
    Args:
        user: User object
        action: Action description
        details: Additional details
        level: Logging level
    """
    try:
        logger = get_activity_logger()
        username = user.username if user else 'Anonymous'
        message = f"User: {username} | Action: {action}"
        if details:
            message += f" | Details: {details}"
        logger.log(level, message)
    except Exception:
        pass


def log_system_event(event_type, message, level=logging.INFO):
    """
    Log system-level event.
    
    Args:
        event_type: Type of event (security, backup, system, etc.)
        message: Event message
        level: Logging level
    """
    try:
        logger = get_activity_logger()
        formatted_message = f"[{event_type.upper()}] {message}"
        logger.log(level, formatted_message)
    except Exception:
        pass


def setup_logging():
    """Initialize all logging handlers and configuration."""
    try:
        from isp_inventory.models import LogSettings
        log_settings = LogSettings.objects.first()
        if not log_settings:
            log_settings = LogSettings.objects.create()
        
        level = getattr(logging, log_settings.log_level, logging.INFO)
        
        # Configure activity logger if enabled
        if log_settings.enable_file_logging:
            log_file = os.path.join(settings.BASE_DIR, log_settings.log_file_path)
            configure_file_logging(
                'activity',
                log_file,
                level=level,
                max_bytes=log_settings.max_log_file_size,
                backup_count=log_settings.backup_count
            )
        
        # Configure Django logger
        django_logger = logging.getLogger('django')
        django_logger.setLevel(level)
        
        return True
    except Exception as e:
        print(f"Error setting up logging: {e}")
        return False
