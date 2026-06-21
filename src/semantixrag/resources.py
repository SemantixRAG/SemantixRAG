"""Resource loader for package data files (e.g., .rego policies).

Uses importlib.resources for safe loading of package data, works correctly
when the package is installed as a wheel or in site-packages.
"""
import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Use importlib.resources for Python 3.12+, fallback to importlib_resources for 3.11
if sys.version_info >= (3, 12):
    from importlib.resources import files
else:
    from importlib_resources import files


def get_rego_policy(policy_name: str) -> str:
    """
    Load a Rego policy file from the package.
    
    Args:
        policy_name: Name of the policy file (e.g., 'access.rego', 'audit.rego', 'masking.rego')
    
    Returns:
        The contents of the .rego file as a string
        
    Raises:
        FileNotFoundError: If the policy file does not exist
    """
    try:
        # Access the config/opa directory within the semantixrag package
        opa_policies = files('semantixrag').joinpath('config', 'opa')
        policy_file = opa_policies.joinpath(policy_name)
        
        # Read and return the content
        if not policy_file.is_file():
            raise FileNotFoundError(f"Policy file not found: {policy_name}")
        
        return policy_file.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"Failed to load Rego policy '{policy_name}': {e}")
        raise


def get_all_rego_policies() -> dict[str, str]:
    """
    Load all Rego policy files from the package.
    
    Returns:
        Dictionary mapping policy names to their contents
    """
    policies = {}
    policy_names = ['access.rego', 'audit.rego', 'masking.rego']
    
    for policy_name in policy_names:
        try:
            policies[policy_name] = get_rego_policy(policy_name)
            logger.info(f"Loaded Rego policy: {policy_name}")
        except FileNotFoundError:
            logger.warning(f"Rego policy not found: {policy_name}")
        except Exception as e:
            logger.error(f"Error loading Rego policy '{policy_name}': {e}")
    
    return policies


def get_resource_path(resource_name: str) -> Optional[Path]:
    """
    Get the file path to a package resource.
    
    Note: This is mainly for debugging. For production use, prefer reading
    the resource content directly with get_rego_policy() or similar functions.
    
    Args:
        resource_name: Name of the resource (e.g., 'config/opa/access.rego')
    
    Returns:
        Path to the resource file, or None if not found
    """
    try:
        resource = files('semantixrag').joinpath(resource_name)
        if hasattr(resource, 'as_file'):
            # Using context manager for real file access
            from contextlib import contextmanager
            @contextmanager
            def get_path():
                with resource.as_file() as path:
                    yield path
            return next(get_path())
        else:
            # Fallback for virtual resources
            return None
    except Exception as e:
        logger.warning(f"Could not get path for resource '{resource_name}': {e}")
        return None
