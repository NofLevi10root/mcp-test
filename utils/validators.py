# utils/validators.py
"""
Input validation utilities for security tools.
"""

import re
import ipaddress
from typing import Tuple
from urllib.parse import urlparse

def is_valid_ip(ip_string: str) -> bool:
    """
    Check if string is a valid IP address.
    
    Args:
        ip_string: String to validate
        
    Returns:
        bool: True if valid IP address
    """
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False

def is_valid_domain(domain: str) -> bool:
    """
    Check if string is a valid domain name.
    
    Args:
        domain: Domain to validate
        
    Returns:
        bool: True if valid domain
    """
    if not domain or len(domain) > 253:
        return False
    
    # Domain regex pattern
    pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'  
        r'[a-zA-Z]{2,}$'
    )
    
    return bool(pattern.match(domain))

def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_valid_email(email: str) -> bool:
    """
    Check if string is a valid email address.
    
    Args:
        email: Email to validate
        
    Returns:
        bool: True if valid email
    """
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email))

def validate_target(target: str) -> Tuple[bool, str, str]:
    """
    Validate and identify target type.
    
    Args:
        target: Target to validate
        
    Returns:
        Tuple[bool, str, str]: (is_valid, target_type, error_message)
    """
    if not target or not isinstance(target, str):
        return False, "unknown", "Target must be a non-empty string"
    
    target = target.strip()
    
    # Check if it's a URL
    if is_valid_url(target):
        return True, "url", ""
    
    # Check if it's an IP address
    if is_valid_ip(target):
        return True, "ip", ""
    
    # Check if it's a domain
    if is_valid_domain(target):
        return True, "domain", ""
    
    return False, "unknown", f"Invalid target format: {target}"

def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize input string for security.
    
    Args:
        input_str: Input to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized input
    """
    if not isinstance(input_str, str):
        return str(input_str)
    
    # Remove dangerous characters
    sanitized = re.sub(r'[;&|`$(){}\[\]<>]', '', input_str)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()