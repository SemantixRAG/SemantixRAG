"""Example: Using the SemantixRAG Resource Loader

This file demonstrates how to safely load .rego policy files from the 
SemantixRAG package using the new importlib.resources-based loader.

Works correctly in:
- Development mode: pip install -e .
- Editable installs: pip install -e src/semantixrag/
- Installed wheels: pip install semantixrag
- Zipped packages
"""

# Example 1: Load a single Rego policy
# ====================================

from semantixrag.resources import get_rego_policy

# Load the access control policy
try:
    access_policy = get_rego_policy('access.rego')
    print("Access Policy Content:")
    print(access_policy)
except FileNotFoundError as e:
    print(f"Policy not found: {e}")


# Example 2: Load all Rego policies
# ==================================

from semantixrag.resources import get_all_rego_policies

# Load all policies at once
policies = get_all_rego_policies()

for policy_name, content in policies.items():
    print(f"\n--- {policy_name} ---")
    print(f"Length: {len(content)} characters")
    print(f"First 100 chars: {content[:100]}...")


# Example 3: Use in a policy engine setup
# ========================================

import logging
from semantixrag.resources import get_all_rego_policies

logger = logging.getLogger(__name__)

def initialize_opa_policies():
    """Initialize OPA with SemantixRAG policies."""
    try:
        policies = get_all_rego_policies()
        
        for policy_name, content in policies.items():
            # Send to OPA or process locally
            logger.info(f"Loaded policy: {policy_name}")
            
            # Example: Send to OPA server
            # response = requests.put(
            #     f"http://localhost:8181/v1/policies/{policy_name}",
            #     data=content,
            # )
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize policies: {e}")
        return False


# Example 4: Use in compliance module
# ====================================

from semantixrag.compliance.pii_scanner import PIIScanner
from semantixrag.resources import get_rego_policy

class CustomPolicyScanner(PIIScanner):
    """PII Scanner with custom masking policy."""
    
    def __init__(self):
        super().__init__()
        # Load masking policy
        self.masking_policy = get_rego_policy('masking.rego')
        
    def apply_custom_masking(self, text: str) -> str:
        """Apply custom masking based on policy."""
        # Use self.masking_policy here
        return text


# Example 5: Testing resource loading
# ====================================

def test_resources_availability():
    """Test that all resources are available."""
    from semantixrag.resources import get_rego_policy
    
    required_policies = ['access.rego', 'audit.rego', 'masking.rego']
    
    for policy_name in required_policies:
        try:
            content = get_rego_policy(policy_name)
            assert len(content) > 0, f"{policy_name} is empty"
            print(f"✓ {policy_name}: {len(content)} bytes")
        except Exception as e:
            print(f"✗ {policy_name}: {e}")
            raise


# Example 6: Handling resource loading in different contexts
# ===========================================================

import sys
from pathlib import Path
from semantixrag.resources import get_rego_policy

def load_policy_safely(policy_name: str) -> str:
    """
    Load a policy with comprehensive error handling.
    
    Works in:
    - Normal installation: pip install semantixrag
    - Development: pip install -e .
    - Development with src-layout: package in src/semantixrag/
    """
    try:
        # Primary method: importlib.resources (works everywhere)
        content = get_rego_policy(policy_name)
        return content
        
    except FileNotFoundError:
        # Fallback for development (not recommended for production)
        # This only works when running from the project directory
        dev_path = Path(__file__).parent / 'config' / 'opa' / policy_name
        if dev_path.exists():
            return dev_path.read_text(encoding='utf-8')
        raise
        
    except Exception as e:
        raise RuntimeError(
            f"Failed to load policy '{policy_name}': {e}. "
            f"Make sure semantixrag is properly installed."
        )


if __name__ == "__main__":
    # Run examples
    print("SemantixRAG Resource Loader Examples\n")
    print("=" * 50)
    
    try:
        print("\n1. Loading single policy:")
        access_policy = get_rego_policy('access.rego')
        print(f"   ✓ Loaded access.rego ({len(access_policy)} bytes)")
        
        print("\n2. Loading all policies:")
        all_policies = get_all_rego_policies()
        print(f"   ✓ Loaded {len(all_policies)} policies")
        for name in all_policies:
            print(f"     - {name}: {len(all_policies[name])} bytes")
        
        print("\n3. Testing resource availability:")
        test_resources_availability()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
