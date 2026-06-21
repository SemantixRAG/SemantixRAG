package semantix.audit

# All actions require audit logging
default audit_required = true

# Skip audit for health checks
audit_required = false {
    input.action == "health_check"
}

# Determine audit level based on action
audit_level = "info" {
    input.action in ["read", "query"]
}

audit_level = "warning" {
    input.action in ["write", "update"]
}

audit_level = "critical" {
    input.action in ["delete", "admin", "dsar"]
}

# Actions requiring immediate notification
require_notification[action] {
    action := input.action
    audit_level == "critical"
}

# Retention period in days
retention_days = 365 {
    audit_level == "critical"
}

retention_days = 90 {
    audit_level == "warning"
}

retention_days = 30 {
    audit_level == "info"
}