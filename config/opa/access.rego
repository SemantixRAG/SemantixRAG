package semantix.access

# Default deny
default allow = false

# Admin users have full access
allow {
    input.user_role == "admin"
}

# Read access for authenticated users
allow {
    input.action == "read"
    input.user_role == "viewer"
    input.tenant_id == input.user_tenant
}

# Write access for editors
allow {
    input.action == "write"
    input.user_role == "editor"
    input.tenant_id == input.user_tenant
}

# Data scientists can read and query
allow {
    input.action in ["read", "query"]
    input.user_role == "data_scientist"
    input.tenant_id == input.user_tenant
}

# Specific document access check
allow {
    input.action == "read"
    input.user_role == "viewer"
    input.document_tenant == input.user_tenant
}

# Deny access to sensitive PII data for non-admin
deny["pii_access"] {
    input.action == "read"
    input.resource_type == "pii"
    input.user_role != "admin"
    input.user_role != "compliance_officer"
}